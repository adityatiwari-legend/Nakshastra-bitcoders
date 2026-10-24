/**
 * Lunar Coordinate System & Geospatial Utilities
 * Moon 2000 Polar Stereographic Projection (lat_0 = -90 deg, lon_0 = 0 deg)
 * Spherical Lunar Radius R = 1,737,400 m
 */

export const MOON_RADIUS_M = 1737400.0;

/**
 * Converts Polar Stereographic (X, Y in meters) to Lunar Latitude & Longitude in degrees.
 */
export function stereoToLonLat(x: number, y: number): { lat: number; lon: number } {
  const r = Math.sqrt(x * x + y * y);
  if (r === 0) {
    return { lat: -90.0, lon: 0.0 };
  }
  const c = 2.0 * Math.atan(r / (2.0 * MOON_RADIUS_M));
  const lat = -90.0 + (c * 180.0) / Math.PI;
  const lon = ((Math.atan2(x, -y) * 180.0) / Math.PI + 360.0) % 360.0;
  return {
    lat: Number(lat.toFixed(4)),
    lon: Number(lon.toFixed(4)),
  };
}

/**
 * Converts Lunar Longitude & Latitude in degrees to Polar Stereographic (X, Y in meters).
 */
export function lonLatToStereo(lon: number, lat: number): { x: number; y: number } {
  const latRad = (lat * Math.PI) / 180.0;
  const lonRad = (lon * Math.PI) / 180.0;
  const denom = 1.0 - Math.sin(latRad);
  if (denom <= 1e-12) {
    return { x: 0, y: 0 };
  }
  const k = (2.0 * MOON_RADIUS_M) / denom;
  const x = k * Math.cos(latRad) * Math.sin(lonRad);
  const y = -k * Math.cos(latRad) * Math.cos(lonRad);
  return {
    x: Number(x.toFixed(1)),
    y: Number(y.toFixed(1)),
  };
}

/**
 * Converts grid indices (col, row) to Polar Stereographic coordinates (X, Y).
 */
export function gridToStereo(
  col: number,
  row: number,
  bounds: { left: number; top: number },
  pixelSizeM: number
): { x: number; y: number } {
  const x = bounds.left + col * pixelSizeM;
  const y = bounds.top - row * pixelSizeM;
  return { x: Number(x.toFixed(1)), y: Number(y.toFixed(1)) };
}

/**
 * Converts Polar Stereographic coordinates (X, Y) to nearest grid indices (col, row).
 */
export function stereoToGrid(
  x: number,
  y: number,
  bounds: { left: number; top: number },
  pixelSizeM: number,
  width: number,
  height: number
): { col: number; row: number } {
  const col = Math.round((x - bounds.left) / pixelSizeM);
  const row = Math.round((bounds.top - y) / pixelSizeM);
  return {
    col: Math.max(0, Math.min(width - 1, col)),
    row: Math.max(0, Math.min(height - 1, row)),
  };
}

export function formatLatLon(lat: number, lon: number): string {
  const latDir = lat < 0 ? 'S' : 'N';
  const lonDir = lon > 180 ? 'W' : 'E';
  const displayLon = lon > 180 ? 360 - lon : lon;
  return `${Math.abs(lat).toFixed(3)}° ${latDir}, ${displayLon.toFixed(3)}° ${lonDir}`;
}

export function formatDistance(km: number): string {
  if (km < 1.0) {
    return `${(km * 1000).toFixed(0)} m`;
  }
  return `${km.toFixed(2)} km`;
}

export function formatDuration(hours: number): string {
  if (hours < 1.0) {
    return `${Math.round(hours * 60)} min`;
  }
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  return `${h}h ${m}m`;
}
