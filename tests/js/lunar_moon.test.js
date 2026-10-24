const test = require('node:test');
const assert = require('node:assert/strict');

// Mock browser global if running in node
global.THREE = require('../../web/vendor/three.min.js');
const LunarMoon = require('../../web/lunar_moon.js');

test('LunarMoon: Spherical forward and inverse coordinate bijection', () => {
  const testCoords = [
    { lat: -89.9, lon: 0.0 },      // Shackleton
    { lat: -86.0434, lon: 0.1514 }, // Malapert Massif
    { lat: -85.3955, lon: 31.1899 },// Mons Mouton
    { lat: -83.8864, lon: 58.4089 },// Nobile Rim 2
    { lat: 0.0, lon: 0.0 },         // Equator Prime Meridian
    { lat: 45.0, lon: 90.0 }        // Northern Hemisphere test
  ];

  for (const c of testCoords) {
    const s = LunarMoon.latLonToSphere(c.lat, c.lon, 500.0);
    const inv = LunarMoon.sphereToLatLon(s.x, s.y, s.z);
    assert.ok(Math.abs(inv.lat - c.lat) < 0.005, `Latitude mismatch for ${c.lat}: got ${inv.lat}`);
    assert.ok(Math.abs(inv.lon - c.lon) < 0.005, `Longitude mismatch for ${c.lon}: got ${inv.lon}`);
  }
});

test('LunarMoon: South Pole Polar Stereographic forward & inverse transformation', () => {
  const testPoints = [
    { lat: -89.9, lon: 0.0 },
    { lat: -86.0434, lon: 0.1514 },
    { lat: -87.2013, lon: 126.5711 } // Slater Plain
  ];

  for (const pt of testPoints) {
    const stereo = LunarMoon.latLonToStereo(pt.lat, pt.lon);
    assert.ok(typeof stereo.easting === 'number' && isFinite(stereo.easting));
    assert.ok(typeof stereo.northing === 'number' && isFinite(stereo.northing));

    const inv = LunarMoon.stereoToLatLon(stereo.easting, stereo.northing);
    assert.ok(Math.abs(inv.lat - pt.lat) < 0.01, `Stereo inverse lat mismatch: ${inv.lat} vs ${pt.lat}`);
    assert.ok(Math.abs(inv.lon - pt.lon) < 0.01, `Stereo inverse lon mismatch: ${inv.lon} vs ${pt.lon}`);
  }
});

test('LunarMoon: Scientific data raster query handles bounds and NoData strictly', () => {
  LunarMoon.setScientificData({
    width: 10,
    height: 10,
    pixel_size_x: 240.0,
    pixel_size_y: 240.0,
    bounds: [-1200.0, -1200.0, 1200.0, 1200.0],
    nodata: -9999.0,
    dem: new Array(100).fill(150.0),
    slope: new Array(100).fill(4.2),
    roughness: new Array(100).fill(1.1),
    psr: new Array(100).fill(0),
    hazard_classes: new Array(100).fill(1),
    illumination: new Array(100).fill(0.85)
  });

  // Query inside bounds (South pole 89.99°S, 0° -> ~300m northing, well within [-1200, 1200])
  const inside = LunarMoon.queryScientificDataAt(-89.99, 0.0);
  assert.equal(inside.in_coverage, true);
  assert.equal(inside.elevation_m, 150.0);
  assert.equal(inside.slope_deg, 4.2);
  assert.equal(inside.hazard_class, 1);
  assert.equal(inside.suitability_score > 70, true);

  // Query far outside bounds (Equator 0°, 0°)
  const outside = LunarMoon.queryScientificDataAt(0.0, 0.0);
  assert.equal(outside.in_coverage, false);
  assert.equal(outside.elevation_m, null);
  assert.equal(outside.slope_deg, null);
  assert.equal(outside.hazard_class, null);
});

test('LunarMoon: Scientific data raster query handles object bounds {left, bottom, right, top}', () => {
  LunarMoon.setScientificData({
    width: 10,
    height: 10,
    pixel_size_x: 240.0,
    pixel_size_y: 240.0,
    bounds: {
      left: -1200.0,
      bottom: -1200.0,
      right: 1200.0,
      top: 1200.0
    },
    nodata: -9999.0,
    dem: new Array(100).fill(210.0),
    slope: new Array(100).fill(3.5),
    roughness: new Array(100).fill(0.8),
    psr: new Array(100).fill(0),
    hazard_classes: new Array(100).fill(1),
    illumination: new Array(100).fill(0.92)
  });

  const inside = LunarMoon.queryScientificDataAt(-89.99, 0.0);
  assert.equal(inside.in_coverage, true);
  assert.equal(inside.elevation_m, 210.0);
  assert.equal(inside.slope_deg, 3.5);
  assert.equal(inside.hazard_class, 1);
});

test('LunarMoon: NaN safety guarantees for coordinates, focus, and transformations', () => {
  // 1. stereoToLatLon with NaN
  const invNaN = LunarMoon.stereoToLatLon(NaN, NaN);
  assert.ok(Number.isFinite(invNaN.lat), 'invNaN.lat must be finite');
  assert.ok(Number.isFinite(invNaN.lon), 'invNaN.lon must be finite');

  // 2. latLonToStereo with NaN
  const fwdNaN = LunarMoon.latLonToStereo(NaN, NaN);
  assert.ok(Number.isFinite(fwdNaN.easting), 'fwdNaN.easting must be finite');
  assert.ok(Number.isFinite(fwdNaN.northing), 'fwdNaN.northing must be finite');

  // 3. latLonToSphere with NaN
  const sphereNaN = LunarMoon.latLonToSphere(NaN, NaN);
  assert.ok(Number.isFinite(sphereNaN.x), 'sphereNaN.x must be finite');
  assert.ok(Number.isFinite(sphereNaN.y), 'sphereNaN.y must be finite');
  assert.ok(Number.isFinite(sphereNaN.z), 'sphereNaN.z must be finite');

  // 4. sphereToLatLon with NaN
  const sphereInvNaN = LunarMoon.sphereToLatLon(NaN, NaN, NaN);
  assert.ok(Number.isFinite(sphereInvNaN.lat), 'sphereInvNaN.lat must be finite');
  assert.ok(Number.isFinite(sphereInvNaN.lon), 'sphereInvNaN.lon must be finite');

  // 5. focusLocation with NaN should not throw
  assert.doesNotThrow(() => {
    LunarMoon.focusLocation(NaN, NaN, 680);
  });
});

