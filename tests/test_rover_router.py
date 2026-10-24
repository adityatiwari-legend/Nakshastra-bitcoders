"""
Unit and integration tests for OrbisLuna Rover Optimal Routing & Traverse Module
"""

import numpy as np
import pytest
import config
from rover_router import (
    compute_cost_surface,
    find_nearest_traversable,
    find_optimal_rover_path,
    find_psr_science_targets,
)


@pytest.fixture
def test_terrain_grid():
    """Build a deterministic 50x50 test raster terrain."""
    np.random.seed(42)
    shape = (50, 50)
    dem = np.zeros(shape, dtype=np.float32) + 100.0  # Flat plain at 100m
    slope = np.zeros(shape, dtype=np.float32) + 2.0   # Safe 2 deg slope
    roughness = np.zeros(shape, dtype=np.float32) + 0.5  # Smooth 0.5m
    hazard = np.ones(shape, dtype=np.uint8)          # All Class 1 (Safe)
    psr = np.zeros(shape, dtype=np.uint8)            # All illuminated

    # Add a steep cliff across columns 20 to 22 (impassable Class 3 Unsafe)
    # with a gap at rows 24-26 (passable valley)
    hazard[:, 20:23] = config.CLASS_UNSAFE
    slope[:, 20:23] = 25.0
    dem[:, 20:23] = 180.0

    # Leave a corridor
    hazard[24:27, 20:23] = config.CLASS_SAFE
    slope[24:27, 20:23] = 3.0
    dem[24:27, 20:23] = 105.0

    # Add a smooth PSR cold trap in the upper right quadrant with gentle depression
    for r in range(5, 15):
        for c in range(35, 45):
            psr[r, c] = 1
            hazard[r, c] = config.CLASS_SHADOWED_UNKNOWN
            dist_from_edge = min(r - 5, 14 - r, c - 35, 44 - c)
            dem[r, c] = 100.0 - (dist_from_edge * 3.0)  # max 12m drop over 4 px -> 3m/20m = 8.5 deg slope
            slope[r, c] = 8.5

    return dem, slope, roughness, hazard, psr


def test_cost_surface_impassability(test_terrain_grid):
    dem, slope, roughness, hazard, psr = test_terrain_grid
    cost = compute_cost_surface(dem, slope, roughness, hazard, psr, pixel_size_m=20.0)

    # Impassable wall
    assert np.isinf(cost[10, 21])
    # Passable corridor
    assert np.isfinite(cost[25, 21])
    # Plain
    assert np.isfinite(cost[10, 10])
    # Shadow has shadow penalty
    assert cost[10, 40] > cost[10, 10]


def test_find_nearest_traversable(test_terrain_grid):
    dem, slope, roughness, hazard, psr = test_terrain_grid
    cost = compute_cost_surface(dem, slope, roughness, hazard, psr, pixel_size_m=20.0)

    # Query inside impassable wall (10, 21)
    snapped = find_nearest_traversable(cost, (10, 21), search_radius=10)
    assert snapped is not None
    assert not np.isinf(cost[snapped[0], snapped[1]])


def test_rover_path_navigates_around_hazard(test_terrain_grid):
    dem, slope, roughness, hazard, psr = test_terrain_grid
    start = (25, 5)   # Left side
    goal = (25, 45)   # Right side

    res = find_optimal_rover_path(
        dem=dem,
        slope_deg=slope,
        roughness_m=roughness,
        hazard_classes=hazard,
        psr_mask=psr,
        start_rc=start,
        goal_rc=goal,
        pixel_size_m=20.0,
    )

    assert res["status"] == "SUCCESS"
    assert res["distance_3d_m"] > 0
    assert len(res["waypoints"]) > 0

    # Ensure path went through the corridor (around row 24-26, col 20-22)
    path_cols = [w["col"] for w in res["waypoints"]]
    assert 21 in path_cols
    corridor_steps = [w for w in res["waypoints"] if w["col"] in (20, 21, 22)]
    for step in corridor_steps:
        assert 23 <= step["row"] <= 27


def test_rover_battery_simulation(test_terrain_grid):
    dem, slope, roughness, hazard, psr = test_terrain_grid
    start = (25, 25)
    goal = (10, 40)   # Inside the PSR shadow cold trap

    res = find_optimal_rover_path(
        dem=dem,
        slope_deg=slope,
        roughness_m=roughness,
        hazard_classes=hazard,
        psr_mask=psr,
        start_rc=start,
        goal_rc=goal,
        pixel_size_m=20.0,
    )

    assert res["status"] == "SUCCESS"
    assert res["shadow_fraction_pct"] > 0
    assert 0.0 <= res["final_battery_soc_pct"] <= 100.0


def test_psr_science_targets_discovery(test_terrain_grid):
    dem, slope, roughness, hazard, psr = test_terrain_grid
    targets = find_psr_science_targets(hazard, psr, slope, dem, top_n=2)
    assert len(targets) > 0
    for t in targets:
        assert psr[t["row"], t["col"]] == 1
        assert t["slope_deg"] < 12.0


def test_avoid_psr_makes_shadow_impassable(test_terrain_grid):
    dem, slope, roughness, hazard, psr = test_terrain_grid
    cost_avoid = compute_cost_surface(
        dem, slope, roughness, hazard, psr, pixel_size_m=20.0, avoid_psr=True
    )
    cost_allow = compute_cost_surface(
        dem, slope, roughness, hazard, psr, pixel_size_m=20.0, avoid_psr=False
    )
    # PSR cell at (10, 40): impassable when avoiding, traversable (with penalty) otherwise
    assert np.isinf(cost_avoid[10, 40])
    assert np.isfinite(cost_allow[10, 40])
    assert cost_allow[10, 40] > cost_allow[10, 10]


def test_avoid_psr_blocks_goal_in_shadow(test_terrain_grid):
    dem, slope, roughness, hazard, psr = test_terrain_grid
    res = find_optimal_rover_path(
        dem=dem,
        slope_deg=slope,
        roughness_m=roughness,
        hazard_classes=hazard,
        psr_mask=psr,
        start_rc=(25, 25),
        goal_rc=(10, 40),  # inside PSR
        pixel_size_m=20.0,
        options={"avoid_psr": True},
    )
    if res["status"] == "SUCCESS":
        # Goal was snapped out of the PSR — route must never enter shadow cells
        for wp in res["waypoints"]:
            assert psr[wp["row"], wp["col"]] == 0
        assert res["shadow_fraction_pct"] == 0.0
        assert res["avoid_psr"] is True
    else:
        assert res["status"] in ("FAILED", "NO_PATH_FOUND")
        assert "Avoid-PSR" in res["error"] or "avoid" in res["error"].lower()


def test_route_hazard_breakdown_present(test_terrain_grid):
    dem, slope, roughness, hazard, psr = test_terrain_grid
    res = find_optimal_rover_path(
        dem=dem,
        slope_deg=slope,
        roughness_m=roughness,
        hazard_classes=hazard,
        psr_mask=psr,
        start_rc=(10, 10),
        goal_rc=(10, 40),
        pixel_size_m=20.0,
    )
    assert res["status"] == "SUCCESS"
    hb = res["hazard_breakdown"]
    for key in ("safe", "caution", "unsafe", "shadowed"):
        assert key in hb
        assert "pct" in hb[key]
        assert "pixels" in hb[key]
    total_pct = hb["safe"]["pct"] + hb["caution"]["pct"] + hb["unsafe"]["pct"] + hb["shadowed"]["pct"]
    assert abs(total_pct - 100.0) < 2.0


# ---------------------------------------------------------------------------
# Phase 5E: known-grid exact route tests (deterministic A* expectations)
# ---------------------------------------------------------------------------

def _flat_grid(shape):
    """Uniform safe, flat, lit grid - cost is uniform so A* routes are unique."""
    dem = np.full(shape, 100.0, dtype=np.float32)
    slope = np.full(shape, 2.0, dtype=np.float32)
    rough = np.full(shape, 0.5, dtype=np.float32)
    hazard = np.full(shape, config.CLASS_SAFE, dtype=np.uint8)
    psr = np.zeros(shape, dtype=np.uint8)
    return dem, slope, rough, hazard, psr


def test_known_grid_exact_route_single_channel():
    """Only one row of a 7x9 grid is open: the route must be EXACTLY that row."""
    dem, slope, rough, hazard, psr = _flat_grid((7, 9))
    hazard[:, :] = config.CLASS_UNSAFE   # seal everything
    hazard[2, :] = config.CLASS_SAFE     # single open channel: row 2

    res = find_optimal_rover_path(
        dem=dem, slope_deg=slope, roughness_m=rough,
        hazard_classes=hazard, psr_mask=psr,
        start_rc=(2, 1), goal_rc=(2, 7), pixel_size_m=20.0,
    )
    assert res["status"] == "SUCCESS"
    got = [(w["row"], w["col"]) for w in res["waypoints"]]
    # Diagonals are blocked by sealed rows 1 and 3, so the unique feasible
    # route is the straight segment (2,1) -> (2,7).
    expected = [(2, c) for c in range(1, 8)]
    assert got == expected
    assert res["distance_3d_m"] > 0


def test_known_grid_route_forced_through_single_gap():
    """A wall with one gap: every route must cross col 4 at exactly (3,4)."""
    dem, slope, rough, hazard, psr = _flat_grid((7, 9))
    hazard[:, 4] = config.CLASS_UNSAFE   # full-height wall at col 4
    hazard[3, 4] = config.CLASS_SAFE     # sole gap

    start, goal = (0, 1), (6, 7)
    res = find_optimal_rover_path(
        dem=dem, slope_deg=slope, roughness_m=rough,
        hazard_classes=hazard, psr_mask=psr,
        start_rc=start, goal_rc=goal, pixel_size_m=20.0,
    )
    assert res["status"] == "SUCCESS"
    got = [(w["row"], w["col"]) for w in res["waypoints"]]
    # 8-connected moves change col by at most 1, so col 4 is visited exactly once.
    crossing = [rc for rc in got if rc[1] == 4]
    assert crossing == [(3, 4)]
    assert start in got and goal in got
    # Never enters a sealed (wall) cell
    for r, c in got:
        if c == 4:
            assert (r, c) == (3, 4)


def test_avoid_unsafe_parameter():
    """Verify avoid_unsafe=True strictly treats Class 3 Unsafe as impassable."""
    dem, slope, rough, hazard, psr = _flat_grid((10, 10))
    # Wall of Class 3 Unsafe across column 5
    hazard[:, 5] = config.CLASS_UNSAFE
    # Slopes are gentle (2 deg), so without avoid_unsafe the rover CAN traverse Class 3 with friction penalty
    res_allow = find_optimal_rover_path(
        dem=dem, slope_deg=slope, roughness_m=rough,
        hazard_classes=hazard, psr_mask=psr,
        start_rc=(5, 2), goal_rc=(5, 8), pixel_size_m=20.0,
        options={"avoid_unsafe": False}
    )
    assert res_allow["status"] == "SUCCESS"
    assert res_allow["avoid_unsafe"] is False

    # With avoid_unsafe=True, Class 3 is impassable, so col 5 cannot be crossed
    res_avoid = find_optimal_rover_path(
        dem=dem, slope_deg=slope, roughness_m=rough,
        hazard_classes=hazard, psr_mask=psr,
        start_rc=(5, 2), goal_rc=(5, 8), pixel_size_m=20.0,
        options={"avoid_unsafe": True}
    )
    assert res_avoid["status"] == "NO_PATH_FOUND"


def test_rover_start_relocation_and_hazard_breakdown():
    """Test start snapping warning and hazard class breakdown structure."""
    dem, slope, rough, hazard, psr = _flat_grid((10, 10))
    # Place a steep cell at start_rc (0, 0)
    slope[0, 0] = 35.0
    hazard[0, 0] = config.CLASS_UNSAFE

    res = find_optimal_rover_path(
        dem=dem, slope_deg=slope, roughness_m=rough,
        hazard_classes=hazard, psr_mask=psr,
        start_rc=(0, 0), goal_rc=(0, 5), pixel_size_m=20.0,
        options={"max_slope_deg": 15.0}
    )
    assert res["status"] == "SUCCESS"
    assert len(res["warnings"]) > 0
    assert "relocated to nearest traversable cell" in res["warnings"][0]
    assert "cells_above_limit_count" in res
    assert res["cells_above_limit_count"] == 0
    assert "hazard_breakdown" in res
    assert "safe" in res["hazard_breakdown"]
    assert "pct" in res["hazard_breakdown"]["safe"]

