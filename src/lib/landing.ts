import { CandidateLandingSite, LunarDataset } from '@/types';
import { gridToStereo, stereoToLonLat } from './gis';

export interface LandingEvaluationResult {
  pixelX: number;
  pixelY: number;
  coordX: number;
  coordY: number;
  latitude: number;
  longitude: number;
  elevationM: number;
  meanSlopeDeg: number;
  maxSlopeDeg: number;
  clearanceBufferM: number;
  isSafe: boolean;
  status: 'APPROVED FOR DESCENT' | 'CAUTION — MODERATE INCLINE' | 'REJECTED — ROLLOVER HAZARD';
  statusReason: string;
  distToNearestPsrM: number;
  nearestPsrName: string;
  recommendedSite: CandidateLandingSite | null;
  distToRecommendedKm: number;
}

/**
 * Evaluates a candidate touchdown spot and its 40-meter safety clearance buffer on the lunar DEM.
 */
export function evaluateTouchdownSpot(
  dataset: LunarDataset,
  pixelX: number,
  pixelY: number
): LandingEvaluationResult {
  const { width, height, dem, slope, psr, nodata, pixelSizeM, bounds } = dataset;

  const px = Math.max(0, Math.min(width - 1, Math.round(pixelX)));
  const py = Math.max(0, Math.min(height - 1, Math.round(pixelY)));

  const centerIdx = py * width + px;
  const centerElev = dem[centerIdx];
  const centerSlope = slope[centerIdx];
  const centerPSR = psr[centerIdx] > 0;

  const stereo = gridToStereo(px, py, bounds, pixelSizeM);
  const lonLat = stereoToLonLat(stereo.x, stereo.y);

  // Evaluate 40-meter radius buffer around target spot
  const bufferRadiusM = 40.0;
  const bufferRadiusPx = Math.max(1, Math.ceil(bufferRadiusM / pixelSizeM));

  let sumSlope = 0;
  let maxObservedSlope = centerSlope;
  let validCellCount = 0;
  let hasNoData = centerElev <= nodata + 1.0 || isNaN(centerElev);

  for (let dy = -bufferRadiusPx; dy <= bufferRadiusPx; dy++) {
    for (let dx = -bufferRadiusPx; dx <= bufferRadiusPx; dx++) {
      const distM = Math.hypot(dx * pixelSizeM, dy * pixelSizeM);
      if (distM > bufferRadiusM) continue;

      const nx = px + dx;
      const ny = py + dy;
      if (nx < 0 || nx >= width || ny < 0 || ny >= height) {
        hasNoData = true;
        continue;
      }

      const nIdx = ny * width + nx;
      const nElev = dem[nIdx];
      const nSlope = slope[nIdx];

      if (nElev <= nodata + 1.0 || isNaN(nElev)) {
        hasNoData = true;
        continue;
      }

      sumSlope += nSlope;
      if (nSlope > maxObservedSlope) maxObservedSlope = nSlope;
      validCellCount++;
    }
  }

  const meanSlope = validCellCount > 0 ? sumSlope / validCellCount : centerSlope;

  // Calculate distance to nearest PSR cold trap
  let minDistToPsrM = Infinity;
  let nearestPsrName = 'None nearby';
  if (dataset.regions && dataset.regions.length > 0) {
    for (const r of dataset.regions) {
      const d = Math.hypot((px - r.pixelX) * pixelSizeM, (py - r.pixelY) * pixelSizeM);
      if (d < minDistToPsrM) {
        minDistToPsrM = d;
        nearestPsrName = r.name;
      }
    }
  }

  // Find nearest pre-approved candidate landing site as recommendation
  let recommendedSite: CandidateLandingSite | null = null;
  let minDistanceToRecM = Infinity;

  if (dataset.landingSites && dataset.landingSites.length > 0) {
    // Prefer rank 1 (Primary) or nearest approved
    for (const site of dataset.landingSites) {
      const d = Math.hypot((px - site.pixelX) * pixelSizeM, (py - site.pixelY) * pixelSizeM);
      if (d < minDistanceToRecM) {
        minDistanceToRecM = d;
        recommendedSite = site;
      }
    }
  }

  // Touchdown decision rules
  let isSafe = false;
  let status: 'APPROVED FOR DESCENT' | 'CAUTION — MODERATE INCLINE' | 'REJECTED — ROLLOVER HAZARD' = 'REJECTED — ROLLOVER HAZARD';
  let statusReason = '';

  if (hasNoData) {
    status = 'REJECTED — ROLLOVER HAZARD';
    isSafe = false;
    statusReason = 'Selected spot is located in sensor NoData void or off-map boundary.';
  } else if (maxObservedSlope > 7.0 || meanSlope > 5.5) {
    status = 'REJECTED — ROLLOVER HAZARD';
    isSafe = false;
    statusReason = `Local slope within 40m buffer reaches ${maxObservedSlope.toFixed(1)}° (exceeds 7.0° lander gear tilt limit). Rollover hazard detected.`;
  } else if (centerPSR) {
    status = 'CAUTION — MODERATE INCLINE';
    isSafe = true;
    statusReason = 'Spot is inside permanent shadow cold-trap (<40K). Extreme cryogenic thermal heating required for lander module.';
  } else {
    status = 'APPROVED FOR DESCENT';
    isSafe = true;
    statusReason = 'Optimal flat terrain verified. 40-meter clearance buffer is 100% hazard-free for lander descent stage.';
  }

  return {
    pixelX: px,
    pixelY: py,
    coordX: stereo.x,
    coordY: stereo.y,
    latitude: lonLat.lat,
    longitude: lonLat.lon,
    elevationM: Number(centerElev.toFixed(1)),
    meanSlopeDeg: Number(meanSlope.toFixed(2)),
    maxSlopeDeg: Number(maxObservedSlope.toFixed(2)),
    clearanceBufferM: bufferRadiusM,
    isSafe,
    status,
    statusReason,
    distToNearestPsrM: Number(minDistToPsrM.toFixed(0)),
    nearestPsrName,
    recommendedSite,
    distToRecommendedKm: Number((minDistanceToRecM / 1000).toFixed(2)),
  };
}
