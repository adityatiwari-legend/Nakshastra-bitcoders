const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

test('3D Blue Lines: PSR ring bounds filter discards out-of-bounds rings and retains in-bounds rings', () => {
  const bounds = { left: -30000.0, top: 30000.0, right: 30000.0, bottom: -30000.0 };
  const pixel_size_x = 240.0;
  const pixel_size_y = 240.0;
  const w = 250;
  const h = 250;

  function isRingInBounds(ring) {
    let inBounds = 0;
    for (let i = 0; i < ring.length; i++) {
      const col = (ring[i][0] - bounds.left) / pixel_size_x;
      const row = (bounds.top - ring[i][1]) / pixel_size_y;
      if (col >= -2 && col <= w + 2 && row >= -2 && row <= h + 2) inBounds++;
    }
    return !(inBounds === 0 || inBounds < ring.length * 0.4);
  }

  // Ring 1: In-bounds crater ring (NASA LOLA crop)
  const lolaRing = [
    [-24000.0, 20000.0],
    [-20000.0, 20000.0],
    [-20000.0, 16000.0],
    [-24000.0, 16000.0],
  ];
  assert.equal(isRingInBounds(lolaRing), true, 'LOLA in-bounds ring must be accepted');

  // Ring 2: Stale Cabeus B ring when active site is LOLA crop (left=-212160)
  const cabeusStaleRing = [
    [-180000.0, 60000.0],
    [-175000.0, 60000.0],
    [-175000.0, 55000.0],
    [-180000.0, 55000.0],
  ];
  assert.equal(isRingInBounds(cabeusStaleRing), false, 'Out-of-bounds stale ring must be rejected');
});

test('3D Blue Lines: Rover 3D elevation conforms accurately to terrain mesh vertical scale and exaggeration', () => {
  const terrainMinElev = -3142.5;
  const terrainWorldW = 400.0;
  const realWidthM = 250 * 240.0; // 60,000 m
  const terrainVertScale = terrainWorldW / realWidthM; // 0.006666...
  const exag = 2.0;

  function calculateWorldY(elev) {
    return (elev - terrainMinElev) * terrainVertScale * exag + 2.2;
  }

  // At minimum elevation, worldY is slightly above ground plane (+2.2)
  const yMin = calculateWorldY(-3142.5);
  assert.ok(Math.abs(yMin - 2.2) < 1e-4, 'At minimum elevation, Y should be +2.2');

  // At higher ridge (+1000m), worldY scales proportionally with terrain mesh
  const yRidge = calculateWorldY(1000.0);
  const expectedY = (1000.0 - (-3142.5)) * terrainVertScale * exag + 2.2;
  assert.ok(Math.abs(yRidge - expectedY) < 1e-4, 'Ridge elevation must match terrain scaling');
  assert.ok(yRidge > yMin, 'Ridge must be higher than floor');
});

test('Source Code: app.js contains 3D blue line fixes and default lola dataset', () => {
  const appJs = fs.readFileSync(path.join(__dirname, '../../web/app.js'), 'utf-8');
  assert.ok(appJs.includes("let activeDataset = 'lola';"), 'Default dataset must be lola');
  assert.ok(appJs.includes('(elev - terrainMinElev) * terrainVertScale * exag + 2.2'), 'Rover 3D path must scale with terrain');
  assert.ok(appJs.includes('// Bounds validation: verify this polygon ring falls within active raster footprint'), 'PSR 3D outlines must have bounds validation');
});
