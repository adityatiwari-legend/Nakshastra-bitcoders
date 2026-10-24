"""
OrbisLuna Rover Optimal Route & Traverse Planning Engine
Autonomous Surface Mobility & Kinematic Pathfinding for Artemis-Era Lunar Exploration.

Implements multi-objective energy-aware A* pathfinding on lunar digital elevation models,
accounting for slope resistance, terramechanics, surface roughness, hazard clearance,
shadow excursions, and battery state-of-charge (SoC) management.
"""

import heapq
import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import rasterio
from scipy import ndimage

import config


def compute_cost_surface(
    dem: np.ndarray,
    slope_deg: np.ndarray,
    roughness_m: np.ndarray,
    hazard_classes: np.ndarray,
    psr_mask: np.ndarray,
    pixel_size_m: float = config.SYNTHETIC_PIXEL_SIZE_M,
    max_slope_deg: float = 15.0,
    weight_slope: float = 2.5,
    weight_roughness: float = 1.5,
    weight_shadow: float = 2.0,
    weight_clearance: float = 2.0,
    avoid_psr: bool = False,
    avoid_unsafe: bool = False,
) -> np.ndarray:
    """
    Computes static cell traversal cost multipliers.
    Impassable terrain (NoData, Unsafe Class 3 if avoid_unsafe, excessive slope) receives infinity.
    When avoid_psr=True, permanent-shadow cells are also impassable.
    """
    rows, cols = hazard_classes.shape
    cost_grid = np.ones((rows, cols), dtype=np.float32)

    # Impassability masks:
    # Rovers can traverse slopes up to max_slope_deg (e.g. 15 deg) and drive into cold-traps
    # unless avoid_psr is set. Strictly impassable terrain for rover mobility:
    # 1. NoData / Void rasters
    # 2. Extreme slope >= max_slope_deg (cliffs / rollover hazard)
    # 3. NaN values
    # 4. PSR cells when the operator enabled the avoid-PSR constraint
    # 5. Class 3 (Unsafe) cells when the operator enabled the avoid-Unsafe constraint
    impassable = (
        (hazard_classes == config.CLASS_NODATA)
        | (slope_deg >= max_slope_deg)
        | np.isnan(dem)
        | np.isnan(slope_deg)
    )
    if avoid_psr:
        impassable = impassable | (psr_mask > 0) | (hazard_classes == config.CLASS_SHADOWED_UNKNOWN)
    if avoid_unsafe:
        impassable = impassable | (hazard_classes == config.CLASS_UNSAFE)

    # Rocket-lander unsafe terrain (e.g., slopes 10-15 deg or high roughness)
    # is traversable with caution by rover, but incurs a traversability friction penalty
    if not avoid_unsafe:
        lander_unsafe_non_psr = (hazard_classes == config.CLASS_UNSAFE) & (psr_mask == 0) & (~impassable)
        cost_grid[lander_unsafe_non_psr] += 3.0

    # Cliff edge clearance buffer: penalize proximity to rollover cliffs (slope >= max_slope_deg) or NoData voids
    cliff_mask = (slope_deg >= max_slope_deg) | (hazard_classes == config.CLASS_NODATA)
    if np.any(cliff_mask):
        dist_to_cliff_px = ndimage.distance_transform_edt(~cliff_mask)
        dist_to_cliff_m = dist_to_cliff_px * pixel_size_m
        buffer_zone = (dist_to_cliff_m < config.LANDING_CLEARANCE_BUFFER_M) & (~impassable)
        clearance_penalty = (1.0 - (dist_to_cliff_m / config.LANDING_CLEARANCE_BUFFER_M)) * weight_clearance
        cost_grid[buffer_zone] += clearance_penalty[buffer_zone].astype(np.float32)

    # Roughness penalty (normalized by resolution-scaled hard-unsafe limit)
    rough_hard_ref = config.scaled_roughness_thresholds(pixel_size_m)["hard_unsafe_min"]
    norm_rough = np.clip(roughness_m / rough_hard_ref, 0.0, 1.0)
    cost_grid += (norm_rough * weight_roughness).astype(np.float32)

    # Shadow traversal penalty (Class 4 or PSR cold traps)
    in_shadow = (psr_mask > 0) | (hazard_classes == config.CLASS_SHADOWED_UNKNOWN)
    cost_grid[in_shadow] += float(weight_shadow)

    cost_grid[impassable] = np.inf
    return cost_grid


def find_nearest_traversable(
    cost_grid: np.ndarray,
    target_rc: Tuple[int, int],
    search_radius: int = 15,
) -> Optional[Tuple[int, int]]:
    """
    If a selected start/goal is on impassable terrain, search outward for the nearest traversable cell.
    """
    r0, c0 = target_rc
    rows, cols = cost_grid.shape
    if 0 <= r0 < rows and 0 <= c0 < cols and not np.isinf(cost_grid[r0, c0]):
        return (r0, c0)

    best_coord = None
    best_dist = float("inf")

    for dr in range(-search_radius, search_radius + 1):
        for dc in range(-search_radius, search_radius + 1):
            r = r0 + dr
            c = c0 + dc
            if 0 <= r < rows and 0 <= c < cols:
                if not np.isinf(cost_grid[r, c]):
                    dist = math.hypot(dr, dc)
                    if dist < best_dist:
                        best_dist = dist
                        best_coord = (r, c)

    return best_coord


def find_optimal_rover_path(
    dem: np.ndarray,
    slope_deg: np.ndarray,
    roughness_m: np.ndarray,
    hazard_classes: np.ndarray,
    psr_mask: np.ndarray,
    start_rc: Tuple[int, int],
    goal_rc: Tuple[int, int],
    pixel_size_m: float = config.SYNTHETIC_PIXEL_SIZE_M,
    transform: Optional[rasterio.Affine] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Computes the optimal traversable path for a lunar rover between start_rc and goal_rc.
    Uses A* algorithm on an 8-connected grid with physical energy & terramechanics costs.
    """
    opts = options or {}
    max_slope_deg = float(opts.get("max_slope_deg", config.SLOPE_HARD_UNSAFE_MIN))
    weight_slope = float(opts.get("weight_slope", 2.5))
    weight_roughness = float(opts.get("weight_roughness", 1.5))
    weight_shadow = float(opts.get("weight_shadow", 2.0))
    weight_clearance = float(opts.get("weight_clearance", 2.0))
    rover_speed_mps = float(opts.get("rover_speed_mps", 0.1))  # 0.1 m/s = 360 m/h
    battery_wh = float(opts.get("battery_capacity_wh", 2000.0))
    p_drive_w = float(opts.get("power_drive_w", 120.0))
    p_heater_dark_w = float(opts.get("power_heater_dark_w", 80.0))
    p_solar_w = float(opts.get("power_solar_w", 250.0))
    avoid_psr = bool(opts.get("avoid_psr", False))
    avoid_unsafe = bool(opts.get("avoid_unsafe", False))

    rows, cols = hazard_classes.shape

    # 1. Base static cost surface
    cost_grid = compute_cost_surface(
        dem=dem,
        slope_deg=slope_deg,
        roughness_m=roughness_m,
        hazard_classes=hazard_classes,
        psr_mask=psr_mask,
        pixel_size_m=pixel_size_m,
        max_slope_deg=max_slope_deg,
        weight_slope=weight_slope,
        weight_roughness=weight_roughness,
        weight_shadow=weight_shadow,
        weight_clearance=weight_clearance,
        avoid_psr=avoid_psr,
        avoid_unsafe=avoid_unsafe,
    )

    # 2. Verify / snap start and goal
    start = find_nearest_traversable(cost_grid, start_rc)
    goal = find_nearest_traversable(cost_grid, goal_rc)

    warnings: List[str] = []
    if start is not None and start != start_rc:
        r0, c0 = start_rc
        s_val = float(slope_deg[r0, c0]) if 0 <= r0 < rows and 0 <= c0 < cols else 0.0
        warnings.append(
            f"Selected start point ({r0}, {c0}) was relocated to nearest traversable cell ({start[0]}, {start[1]}) "
            f"because original location was impassable or steep ({s_val:.1f}° vs limit {max_slope_deg:.1f}°)."
        )
    if goal is not None and goal != goal_rc:
        r0, c0 = goal_rc
        s_val = float(slope_deg[r0, c0]) if 0 <= r0 < rows and 0 <= c0 < cols else 0.0
        warnings.append(
            f"Selected goal point ({r0}, {c0}) was relocated to nearest traversable cell ({goal[0]}, {goal[1]}) "
            f"because original location was impassable or steep ({s_val:.1f}° vs limit {max_slope_deg:.1f}°)."
        )

    if start is None:
        return {
            "status": "FAILED",
            "error": (
                "Start coordinate is completely trapped by impassable terrain. "
                "Try raising the slope limit, disabling the avoid-PSR constraint, or picking a different start point."
            ),
            "start": list(start_rc),
            "goal": list(goal_rc),
            "warnings": warnings,
        }
    if goal is None:
        msg = (
            "Goal coordinate is completely inaccessible or in deep hazard zone. "
            "Try raising the slope limit, disabling the avoid-PSR constraint, or picking a different destination."
        )
        if avoid_psr:
            msg += " Note: with Avoid-PSR enabled, shadowed cold traps are treated as impassable."
        return {"status": "FAILED", "error": msg, "start": list(start), "goal": list(goal_rc)}

    # 3. 8-Connected Movements
    # [dr, dc, base_dist_factor]
    SQRT2 = math.sqrt(2.0)
    MOVES = [
        (-1, 0, 1.0),
        (1, 0, 1.0),
        (0, -1, 1.0),
        (0, 1, 1.0),
        (-1, -1, SQRT2),
        (-1, 1, SQRT2),
        (1, -1, SQRT2),
        (1, 1, SQRT2),
    ]

    # Priority queue: (f_score, g_score, (r, c))
    gr, gc = goal
    sr, sc = start

    def heuristic(r: int, c: int) -> float:
        # Octile heuristic scaled by distance
        dx = abs(c - gc)
        dy = abs(r - gr)
        return pixel_size_m * (max(dx, dy) + (SQRT2 - 1.0) * min(dx, dy))

    open_set = []
    heapq.heappush(open_set, (heuristic(sr, sc), 0.0, (sr, sc)))

    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    g_score: Dict[Tuple[int, int], float] = {(sr, sc): 0.0}
    closed_set = set()

    found = False

    while open_set:
        f, current_g, current = heapq.heappop(open_set)
        if current in closed_set:
            continue
        closed_set.add(current)

        if current == goal:
            found = True
            break

        cr, cc = current
        cz = float(dem[cr, cc])

        for dr, dc, dist_factor in MOVES:
            nr = cr + dr
            nc = cc + dc

            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
            if (nr, nc) in closed_set:
                continue

            cell_cost = cost_grid[nr, nc]
            if np.isinf(cell_cost):
                continue

            # Physical step distance
            step_d_m = pixel_size_m * dist_factor
            nz = float(dem[nr, nc])
            delta_z = nz - cz

            # Micro-slope between current and neighbor
            step_slope_deg = math.degrees(math.atan2(abs(delta_z), step_d_m))
            if step_slope_deg >= max_slope_deg:
                continue

            # Terramechanics & slope resistance
            if delta_z > 0:
                # Uphill: motor torque required grows nonlinearly with slope
                slope_mult = 1.0 + weight_slope * ((step_slope_deg / max_slope_deg) ** 1.8)
            else:
                # Downhill: slight brake control cost
                slope_mult = 1.0 + 0.3 * weight_slope * (step_slope_deg / max_slope_deg)

            edge_cost = step_d_m * cell_cost * slope_mult
            tentative_g = current_g + edge_cost

            if tentative_g < g_score.get((nr, nc), float("inf")):
                came_from[(nr, nc)] = current
                g_score[(nr, nc)] = tentative_g
                f_score = tentative_g + heuristic(nr, nc)
                heapq.heappush(open_set, (f_score, tentative_g, (nr, nc)))

    if not found:
        msg = (
            "No safe continuous traverse corridor exists between start and destination under the current constraints. "
            f"Try raising the slope limit above {max_slope_deg:.1f}°"
            + (", disabling the Avoid-PSR constraint" if avoid_psr else "")
            + ", or choosing different start/goal points on sunlit safe terrain."
        )
        return {
            "status": "NO_PATH_FOUND",
            "error": msg,
            "start": list(start),
            "goal": list(goal),
            "avoid_psr": avoid_psr,
            "max_slope_deg": max_slope_deg,
        }

    # 4. Reconstruct Path
    path_rc = []
    curr = goal
    while curr in came_from:
        path_rc.append(curr)
        curr = came_from[curr]
    path_rc.append(start)
    path_rc.reverse()

    # 5. Extract Detailed Traverse Telemetry
    total_2d_dist_m = 0.0
    total_3d_dist_m = 0.0
    elev_gain_m = 0.0
    elev_loss_m = 0.0
    slopes = []
    roughnesses = []
    shadow_count = 0

    waypoints = []
    battery_profile = []
    current_soc_pct = 100.0  # Start fully charged

    for i in range(len(path_rc)):
        r, c = path_rc[i]
        z = float(dem[r, c])
        slp = float(slope_deg[r, c])
        rgh = float(roughness_m[r, c])
        h_class = int(hazard_classes[r, c])
        is_dark = bool(psr_mask[r, c] > 0 or h_class == config.CLASS_SHADOWED_UNKNOWN)

        slopes.append(slp)
        roughnesses.append(rgh)

        if is_dark:
            shadow_count += 1

        if i > 0:
            pr, pc = path_rc[i - 1]
            pz = float(dem[pr, pc])
            step_2d = math.hypot(c - pc, r - pr) * pixel_size_m
            dz = z - pz
            step_3d = math.sqrt(step_2d**2 + dz**2)
            total_2d_dist_m += step_2d
            total_3d_dist_m += step_3d

            if dz > 0:
                elev_gain_m += dz
            else:
                elev_loss_m += abs(dz)

            # Battery State-of-Charge Simulation
            step_time_s = step_3d / max(rover_speed_mps, 0.01)
            step_hours = step_time_s / 3600.0

            if is_dark:
                # In shadow: driving + survival heaters consume energy
                drain_wh = (p_drive_w + p_heater_dark_w) * step_hours
                current_soc_pct -= (drain_wh / battery_wh) * 100.0
            else:
                # In sunlight: solar array generates power while driving
                net_power = p_solar_w - p_drive_w
                charge_wh = net_power * step_hours
                current_soc_pct += (charge_wh / battery_wh) * 100.0

            current_soc_pct = max(0.0, min(100.0, current_soc_pct))

        battery_profile.append(round(current_soc_pct, 1))

        # Coordinate conversion
        if transform is not None:
            east, north = rasterio.transform.xy(transform, r, c, offset="center")
        else:
            east, north = (c * pixel_size_m, -r * pixel_size_m)

        waypoints.append({
            "index": i,
            "row": r,
            "col": c,
            "easting_m": round(east, 2),
            "northing_m": round(north, 2),
            "elevation_m": round(z, 2),
            "slope_deg": round(slp, 2),
            "roughness_m": round(rgh, 2),
            "hazard_class": h_class,
            "is_shadow": is_dark,
            "battery_soc_pct": round(current_soc_pct, 1),
            "cumulative_dist_m": round(total_3d_dist_m, 1),
        })

    # Summary metrics
    avg_slope = float(np.mean(slopes)) if slopes else 0.0
    max_slope = float(np.max(slopes)) if slopes else 0.0
    duration_hours = (total_3d_dist_m / max(rover_speed_mps, 0.01)) / 3600.0
    shadow_pct = (shadow_count / max(len(path_rc), 1)) * 100.0

    # Hazard class breakdown along the traverse (waypoint counts + 3D distance share)
    class_px = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    class_dist_m = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    for i, wp in enumerate(waypoints):
        hc = int(wp.get("hazard_class", 0))
        if hc in class_px:
            class_px[hc] += 1
        if i > 0:
            seg = waypoints[i]["cumulative_dist_m"] - waypoints[i - 1]["cumulative_dist_m"]
            if hc in class_dist_m:
                class_dist_m[hc] += max(seg, 0.0)
    total_wp = max(len(waypoints), 1)
    hazard_breakdown = {
        "safe": {"pixels": class_px[1], "pct": round(class_px[1] / total_wp * 100, 1), "distance_m": round(class_dist_m[1], 1)},
        "caution": {"pixels": class_px[2], "pct": round(class_px[2] / total_wp * 100, 1), "distance_m": round(class_dist_m[2], 1)},
        "unsafe": {"pixels": class_px[3], "pct": round(class_px[3] / total_wp * 100, 1), "distance_m": round(class_dist_m[3], 1)},
        "shadowed": {"pixels": class_px[4], "pct": round(class_px[4] / total_wp * 100, 1), "distance_m": round(class_dist_m[4], 1)},
    }

    # Slope limit compliance
    cells_above_limit_count = sum(1 for slp in slopes if slp >= max_slope_deg)
    if cells_above_limit_count > 0:
        warnings.append(f"{cells_above_limit_count} points along the route meet or exceed the slope limit of {max_slope_deg:.1f}°.")

    return {
        "status": "SUCCESS",
        "rover_model": "OrbisLuna Artemis Polar Rover",
        "start_coord": {"row": start[0], "col": start[1]},
        "goal_coord": {"row": goal[0], "col": goal[1]},
        "total_steps": len(path_rc),
        "distance_2d_m": round(total_2d_dist_m, 2),
        "distance_3d_m": round(total_3d_dist_m, 2),
        "distance_km": round(total_3d_dist_m / 1000.0, 3),
        "elevation_gain_m": round(elev_gain_m, 2),
        "elevation_loss_m": round(elev_loss_m, 2),
        "avg_slope_deg": round(avg_slope, 2),
        "max_slope_deg": round(max_slope, 2),
        "estimated_duration_hours": round(duration_hours, 2),
        "shadow_distance_m": round((shadow_pct / 100.0) * total_3d_dist_m, 2),
        "shadow_fraction_pct": round(shadow_pct, 1),
        "final_battery_soc_pct": round(current_soc_pct, 1),
        "avoid_psr": avoid_psr,
        "avoid_unsafe": avoid_unsafe,
        "cells_above_limit_count": cells_above_limit_count,
        "warnings": warnings,
        "hazard_breakdown": hazard_breakdown,
        "waypoints": waypoints,
        "path_coordinates": [[w["col"], w["row"]] for w in waypoints],
    }


def find_psr_science_targets(
    hazard_classes: np.ndarray,
    psr_mask: np.ndarray,
    slope_deg: np.ndarray,
    dem: np.ndarray,
    top_n: int = 3,
    start_rc: Optional[Tuple[int, int]] = None,
    pixel_size_m: float = 20.0,
) -> List[Dict[str, Any]]:
    """
    Locates the most accessible, high-value water ice / volatile sampling targets
    inside Class 4 (Shadowed-Unknown) cold traps or PSRs.
    """
    # Valid targets: inside PSR
    if start_rc is not None:
        candidate_mask = (psr_mask > 0) & (slope_deg < 12.0)
        if not np.any(candidate_mask):
            candidate_mask = (psr_mask > 0) & (slope_deg < 18.0)
            if not np.any(candidate_mask):
                candidate_mask = (psr_mask > 0)
                if not np.any(candidate_mask):
                    return []
    else:
        candidate_mask = (psr_mask > 0) & (hazard_classes == config.CLASS_SHADOWED_UNKNOWN) & (slope_deg < 8.0)
        if not np.any(candidate_mask):
            candidate_mask = (psr_mask > 0) & (slope_deg < 12.0)
            if not np.any(candidate_mask):
                candidate_mask = (psr_mask > 0) & (slope_deg < 18.0)
                if not np.any(candidate_mask):
                    return []

    # Rank candidates by proximity to start position (if provided), slope, and depression depth
    rows, cols = np.where(candidate_mask)
    candidates = []
    for r, c in zip(rows, cols):
        slp = float(slope_deg[r, c])
        elev = float(dem[r, c])
        if start_rc is not None:
            dist_m = math.hypot(r - start_rc[0], c - start_rc[1]) * pixel_size_m
            score = -(dist_m / 100.0) - slp * 2.0 - elev * 0.01
        else:
            score = -slp * 10.0 - elev * 0.05
        candidates.append((score, r, c, slp, elev))

    candidates.sort(key=lambda x: x[0], reverse=True)

    # Pick spatially distributed targets
    selected = []
    min_dist_px = 10 if start_rc is not None else 20
    for score, r, c, slp, elev in candidates:
        if all(math.hypot(r - sr, c - sc) >= min_dist_px for sr, sc in [(x["row"], x["col"]) for x in selected]):
            selected.append({
                "target_id": f"PSR-Target-{chr(65 + len(selected))}",
                "row": int(r),
                "col": int(c),
                "slope_deg": round(slp, 2),
                "elevation_m": round(elev, 2),
                "type": "Cryogenic Volatile Sampling Zone",
            })
            if len(selected) >= top_n:
                break

    return selected
