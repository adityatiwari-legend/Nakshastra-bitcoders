import { LunarDataset, RoutePoint, RouteResult } from '@/types';
import { gridToStereo, stereoToLonLat } from './gis';

// Min-heap for fast A* frontier management
class PriorityQueue<T> {
  private heap: { item: T; priority: number }[] = [];

  push(item: T, priority: number) {
    this.heap.push({ item, priority });
    this.bubbleUp(this.heap.length - 1);
  }

  pop(): T | undefined {
    if (this.heap.length === 0) return undefined;
    const top = this.heap[0].item;
    const bottom = this.heap.pop()!;
    if (this.heap.length > 0) {
      this.heap[0] = bottom;
      this.sinkDown(0);
    }
    return top;
  }

  get size(): number {
    return this.heap.length;
  }

  private bubbleUp(index: number) {
    const element = this.heap[index];
    while (index > 0) {
      const parentIndex = (index - 1) >> 1;
      const parent = this.heap[parentIndex];
      if (element.priority >= parent.priority) break;
      this.heap[index] = parent;
      this.heap[parentIndex] = element;
      index = parentIndex;
    }
  }

  private sinkDown(index: number) {
    const length = this.heap.length;
    const element = this.heap[index];
    while (true) {
      let leftChildIndex = (index << 1) + 1;
      let rightChildIndex = leftChildIndex + 1;
      let swapIndex: number | null = null;
      let minPriority = element.priority;

      if (leftChildIndex < length) {
        const leftChild = this.heap[leftChildIndex];
        if (leftChild.priority < minPriority) {
          swapIndex = leftChildIndex;
          minPriority = leftChild.priority;
        }
      }

      if (rightChildIndex < length) {
        const rightChild = this.heap[rightChildIndex];
        if (rightChild.priority < minPriority) {
          swapIndex = rightChildIndex;
        }
      }

      if (swapIndex === null) break;
      this.heap[index] = this.heap[swapIndex];
      this.heap[swapIndex] = element;
      index = swapIndex;
    }
  }
}

const SQRT2 = Math.SQRT2;
const DIRS = [
  { dx: 1, dy: 0, distMult: 1.0 },
  { dx: -1, dy: 0, distMult: 1.0 },
  { dx: 0, dy: 1, distMult: 1.0 },
  { dx: 0, dy: -1, distMult: 1.0 },
  { dx: 1, dy: 1, distMult: SQRT2 },
  { dx: -1, dy: 1, distMult: SQRT2 },
  { dx: 1, dy: -1, distMult: SQRT2 },
  { dx: -1, dy: -1, distMult: SQRT2 },
];

/**
 * Executes multi-factor A* pathfinding across the lunar digital elevation model.
 */
export function computeRoverRoute(
  dataset: LunarDataset,
  startCol: number,
  startRow: number,
  goalCol: number,
  goalRow: number,
  maxSlopeDeg: number = 16.0
): RouteResult {
  const { width, height, pixelSizeM, bounds, dem, slope, psr, nodata } = dataset;

  // Clamp start and goal to grid
  const sc = Math.max(0, Math.min(width - 1, Math.round(startCol)));
  const sr = Math.max(0, Math.min(height - 1, Math.round(startRow)));
  const gc = Math.max(0, Math.min(width - 1, Math.round(goalCol)));
  const gr = Math.max(0, Math.min(height - 1, Math.round(goalRow)));

  const startIndex = sr * width + sc;
  const goalIndex = gr * width + gc;

  // Check start & goal validity
  if (dem[startIndex] <= nodata + 1.0 || isNaN(dem[startIndex])) {
    return createEmptyRouteResult(false, 'Starting location is located in NoData / void terrain.');
  }
  if (dem[goalIndex] <= nodata + 1.0 || isNaN(dem[goalIndex])) {
    return createEmptyRouteResult(false, 'Destination is located in NoData / void terrain.');
  }

  // Pre-allocate cost and parent arrays
  const totalCells = width * height;
  const gScore = new Float32Array(totalCells).fill(Infinity);
  const cameFrom = new Int32Array(totalCells).fill(-1);
  const closedSet = new Uint8Array(totalCells);

  const pq = new PriorityQueue<number>();

  gScore[startIndex] = 0;

  const goalZ = dem[goalIndex];
  const initialH = Math.hypot(
    (gc - sc) * pixelSizeM,
    (gr - sr) * pixelSizeM,
    goalZ - dem[startIndex]
  );

  pq.push(startIndex, initialH);

  let reached = false;
  let iterations = 0;
  const maxIterations = 200000;

  while (pq.size > 0 && iterations < maxIterations) {
    iterations++;
    const current = pq.pop()!;

    if (current === goalIndex) {
      reached = true;
      break;
    }

    if (closedSet[current]) continue;
    closedSet[current] = 1;

    const currentG = gScore[current];
    const cx = current % width;
    const cy = (current / width) | 0;
    const currentZ = dem[current];

    for (let i = 0; i < DIRS.length; i++) {
      const dir = DIRS[i];
      const nx = cx + dir.dx;
      const ny = cy + dir.dy;

      if (nx < 0 || nx >= width || ny < 0 || ny >= height) continue;

      const neighbor = ny * width + nx;
      if (closedSet[neighbor]) continue;

      const nz = dem[neighbor];
      if (nz <= nodata + 1.0 || isNaN(nz)) continue;

      const nSlope = slope[neighbor];
      const step2dDist = pixelSizeM * dir.distMult;
      const elevDiff = Math.abs(nz - currentZ);
      const gradeAngle = (Math.atan2(elevDiff, step2dDist) * 180.0) / Math.PI;

      // Impassability: slope or steep grade exceeding safe vehicle threshold
      // Note: destinations inside PSR are allowed; steep walls are avoided
      const effectiveSlope = Math.max(nSlope, gradeAngle);
      if (effectiveSlope > maxSlopeDeg && neighbor !== goalIndex) {
        continue;
      }

      // Cost formulation:
      // Base step distance
      // Slope penalty: non-linear energy expenditure on grades
      const slopeFactor = 1.0 + 3.0 * Math.pow(effectiveSlope / maxSlopeDeg, 2);

      // PSR thermal excursion penalty (requires battery heaters; not impassable)
      const isNeighborPSR = psr[neighbor] > 0;
      const psrFactor = isNeighborPSR ? 1.35 : 1.0;

      const stepCost = step2dDist * slopeFactor * psrFactor;
      const tentativeG = currentG + stepCost;

      if (tentativeG < gScore[neighbor]) {
        cameFrom[neighbor] = current;
        gScore[neighbor] = tentativeG;

        // Admissible 3D Euclidean distance heuristic
        const h = Math.hypot(
          (gc - nx) * pixelSizeM,
          (gr - ny) * pixelSizeM,
          goalZ - nz
        );
        pq.push(neighbor, tentativeG + h);
      }
    }
  }

  if (!reached) {
    return createEmptyRouteResult(
      false,
      `No feasible path found. Direct terrain between start and goal exceeds maximum allowable slope (${maxSlopeDeg.toFixed(0)}°) or enters sensor void.`
    );
  }

  // Reconstruct path from goal back to start
  const pathIndices: number[] = [];
  let curr = goalIndex;
  while (curr !== -1) {
    pathIndices.push(curr);
    curr = cameFrom[curr];
  }
  pathIndices.reverse();

  // Metrics computation along path
  let distance2dM = 0;
  let distance3dM = 0;
  let elevationGainM = 0;
  let elevationLossM = 0;
  let sumSlope = 0;
  let maxObservedSlope = 0;
  let shadowDistanceM = 0;
  let totalTraverseSeconds = 0;

  const NOMINAL_ROVER_SPEED_MPS = 0.10; // Nominal NASA VIPER speed = 0.10 m/s (approx 360 m/h)

  const pathPoints: RoutePoint[] = [];

  for (let i = 0; i < pathIndices.length; i++) {
    const idx = pathIndices[i];
    const px = idx % width;
    const py = (idx / width) | 0;
    const z = dem[idx];
    const s = slope[idx];
    const isP = psr[idx] > 0;

    const stereo = gridToStereo(px, py, bounds, pixelSizeM);
    const lonLat = stereoToLonLat(stereo.x, stereo.y);

    pathPoints.push({
      pixelX: px,
      pixelY: py,
      coordX: stereo.x,
      coordY: stereo.y,
      latitude: lonLat.lat,
      longitude: lonLat.lon,
      elevationM: Number(z.toFixed(1)),
      slopeDeg: Number(s.toFixed(1)),
      isPSR: isP,
    });

    if (i > 0) {
      const prevIdx = pathIndices[i - 1];
      const prevX = prevIdx % width;
      const prevY = (prevIdx / width) | 0;
      const prevZ = dem[prevIdx];

      const step2d = Math.hypot((px - prevX) * pixelSizeM, (py - prevY) * pixelSizeM);
      const dz = z - prevZ;
      const step3d = Math.hypot(step2d, dz);

      distance2dM += step2d;
      distance3dM += step3d;

      if (dz > 0) elevationGainM += dz;
      else elevationLossM += Math.abs(dz);

      sumSlope += s;
      if (s > maxObservedSlope) maxObservedSlope = s;

      if (isP) {
        shadowDistanceM += step2d;
      }

      // Rover speed degradation model on slopes: v = v0 * cos(slope)
      const slopeRad = (s * Math.PI) / 180.0;
      const stepSpeed = Math.max(0.025, NOMINAL_ROVER_SPEED_MPS * Math.cos(slopeRad));
      totalTraverseSeconds += step3d / stepSpeed;
    }
  }

  const distance2dKm = distance2dM / 1000.0;
  const distance3dKm = distance3dM / 1000.0;
  const avgSlopeDeg = pathPoints.length > 1 ? sumSlope / (pathPoints.length - 1) : 0;
  const shadowDistanceKm = shadowDistanceM / 1000.0;
  const shadowFractionPct = distance2dM > 0 ? (shadowDistanceM / distance2dM) * 100.0 : 0;
  const estimatedDurationHours = totalTraverseSeconds / 3600.0;

  let statusMessage = 'Optimal feasible path computed across terrain.';
  if (maxObservedSlope > 12.0) {
    statusMessage = 'Path feasible with steep sections. Reduced velocity recommended.';
  } else if (shadowFractionPct > 40.0) {
    statusMessage = 'Path feasible with high shadow exposure. Verify battery heater budget.';
  }

  return {
    feasible: true,
    statusMessage,
    distance2dKm: Number(distance2dKm.toFixed(2)),
    distance3dKm: Number(distance3dKm.toFixed(2)),
    elevationGainM: Number(elevationGainM.toFixed(1)),
    elevationLossM: Number(elevationLossM.toFixed(1)),
    avgSlopeDeg: Number(avgSlopeDeg.toFixed(1)),
    maxSlopeDeg: Number(maxObservedSlope.toFixed(1)),
    traversalCost: Number(gScore[goalIndex].toFixed(0)),
    estimatedDurationHours: Number(estimatedDurationHours.toFixed(2)),
    shadowDistanceKm: Number(shadowDistanceKm.toFixed(2)),
    shadowFractionPct: Number(shadowFractionPct.toFixed(1)),
    pathPoints,
  };
}

function createEmptyRouteResult(feasible: boolean, statusMessage: string): RouteResult {
  return {
    feasible,
    statusMessage,
    distance2dKm: 0,
    distance3dKm: 0,
    elevationGainM: 0,
    elevationLossM: 0,
    avgSlopeDeg: 0,
    maxSlopeDeg: 0,
    traversalCost: 0,
    estimatedDurationHours: 0,
    shadowDistanceKm: 0,
    shadowFractionPct: 0,
    pathPoints: [],
  };
}
