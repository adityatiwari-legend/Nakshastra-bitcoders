export type ActiveModule = 'psr' | 'landing' | 'routing' | 'distribution';

export type DatasetStatus = 'ready' | 'loading' | 'processing' | 'error';

export interface DatasetBounds {
  left: number;
  right: number;
  bottom: number;
  top: number;
}

export interface PSRRegion {
  id: number;
  name: string;
  pixelX: number;
  pixelY: number;
  coordX: number;
  coordY: number;
  latitude: number;
  longitude: number;
  areaKm2: number;
  perimeterM: number;
  centerElevM: number;
  centerSlopeDeg: number;
  provenance: string;
}

export interface CandidateLandingSite {
  id: string;
  name: string;
  designation: string;
  rank: number;
  pixelX: number;
  pixelY: number;
  coordX: number;
  coordY: number;
  latitude: number;
  longitude: number;
  elevationM: number;
  meanSlopeDeg: number;
  maxSlopeDeg: number;
  clearanceBufferM: number; // 40.0m safety clearance buffer
  distToPsrM: number;
  status: 'APPROVED FOR DESCENT' | 'CAUTION — MODERATE INCLINE' | 'REJECTED — ROLLOVER HAZARD';
  missionRole: string;
}

export interface ClassStat {
  id: string;
  name: string;
  pixelCount: number;
  areaKm2: number;
  percentage: number;
  percentageValid: number;
  color: string;
  description: string;
}

export interface Waypoint {
  name: string;
  pixelX: number;
  pixelY: number;
  coordX: number;
  coordY: number;
  latitude: number;
  longitude: number;
}

export interface LunarDataset {
  id: string;
  name: string;
  tag: string;
  isReal: boolean;
  source: string;
  crs: string;
  coverage: string;
  width: number;
  height: number;
  pixelSizeM: number;
  bounds: DatasetBounds;
  nodata: number;
  minElev: number;
  maxElev: number;
  totalPixels: number;
  validPixels: number;
  totalAreaKm2: number;
  validAreaKm2: number;
  psrCount: number;
  psrAreaKm2: number;
  regions: PSRRegion[];
  landingSites: CandidateLandingSite[];
  classes: ClassStat[];
  dem: number[];
  slope: number[];
  psr: number[];
  defaultStart: Waypoint;
  defaultGoal: Waypoint;
}

export interface RoutePoint {
  pixelX: number;
  pixelY: number;
  coordX: number;
  coordY: number;
  latitude: number;
  longitude: number;
  elevationM: number;
  slopeDeg: number;
  isPSR: boolean;
}

export interface RouteResult {
  feasible: boolean;
  statusMessage: string;
  distance2dKm: number;
  distance3dKm: number;
  elevationGainM: number;
  elevationLossM: number;
  avgSlopeDeg: number;
  maxSlopeDeg: number;
  traversalCost: number;
  estimatedDurationHours: number;
  shadowDistanceKm: number;
  shadowFractionPct: number;
  pathPoints: RoutePoint[];
}
