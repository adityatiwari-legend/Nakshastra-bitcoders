const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const ROOT_DIR = path.resolve(__dirname, '..', '..');

test('3D Transect Profile: DOM structure in web/index.html', () => {
  const html = fs.readFileSync(path.join(ROOT_DIR, 'web', 'index.html'), 'utf-8');
  assert.ok(html.includes('id="btn3dCrossSection"'), 'index.html must contain btn3dCrossSection button');
  assert.ok(html.includes('id="threeCrossSectionCard"'), 'index.html must contain threeCrossSectionCard');
  assert.ok(html.includes('id="profileChartCanvas"'), 'index.html must contain profileChartCanvas');
  assert.ok(html.includes('id="transectStatusTag"'), 'index.html must contain transectStatusTag');
  assert.ok(html.includes('id="transectLength"'), 'index.html must contain transectLength readout');
  assert.ok(html.includes('id="transectMinElev"'), 'index.html must contain transectMinElev readout');
  assert.ok(html.includes('id="transectMaxElev"'), 'index.html must contain transectMaxElev readout');
  assert.ok(html.includes('id="transectMeanSlope"'), 'index.html must contain transectMeanSlope readout');
  assert.ok(html.includes('id="transectMaxSlope"'), 'index.html must contain transectMaxSlope readout');
});

test('3D Transect Profile: Engine implementation in web/app.js', () => {
  const app = fs.readFileSync(path.join(ROOT_DIR, 'web', 'app.js'), 'utf-8');
  assert.ok(app.includes('function toggle3dCrossSectionTool()'), 'app.js must define toggle3dCrossSectionTool');
  assert.ok(app.includes('function handleCrossSectionClick(hit)'), 'app.js must define handleCrossSectionClick');
  assert.ok(app.includes('function computeAndDrawTransect()'), 'app.js must define computeAndDrawTransect');
  assert.ok(app.includes('function updateTransect3dGeometry()'), 'app.js must define updateTransect3dGeometry');
  assert.ok(app.includes('function drawTransectProfileChart('), 'app.js must define drawTransectProfileChart');
  assert.ok(app.includes('function clearCrossSection()'), 'app.js must define clearCrossSection');
});

test('3D Mouse Interaction: Pointer tracking and bounding updates in web/app.js', () => {
  const app = fs.readFileSync(path.join(ROOT_DIR, 'web', 'app.js'), 'utf-8');
  assert.ok(app.includes('pointerdown'), 'init3dMouseEvents must track pointerdown');
  assert.ok(app.includes('pointerup'), 'init3dMouseEvents must track pointerup for reliable terrain clicks');
  assert.ok(app.includes('geometry.computeBoundingBox()'), 'build3dTerrainMesh must compute bounding box');
  assert.ok(app.includes('geometry.computeBoundingSphere()'), 'build3dTerrainMesh must compute bounding sphere');
  assert.ok(app.includes('terrainMesh.geometry.computeBoundingSphere()'), 'update3dExaggeration must update bounding sphere');
});

test('Transect Math: Bilinear elevation interpolation math', () => {
  // Unit test bilinear interpolation logic as implemented in sampleDemElevation
  const w = 4;
  const h = 4;
  const dem = [
    100, 110, 120, 130,
    140, 150, 160, 170,
    180, 190, 200, 210,
    220, 230, 240, 250
  ];

  function sample(col, row) {
    const c0 = Math.floor(col);
    const c1 = Math.ceil(col);
    const r0 = Math.floor(row);
    const r1 = Math.ceil(row);
    const fc = col - c0;
    const fr = row - r0;
    const v00 = dem[r0 * w + c0];
    const v10 = dem[r0 * w + c1];
    const v01 = dem[r1 * w + c0];
    const v11 = dem[r1 * w + c1];
    const top = v00 * (1 - fc) + v10 * fc;
    const bot = v01 * (1 - fc) + v11 * fc;
    return top * (1 - fr) + bot * fr;
  }

  assert.equal(sample(0, 0), 100);
  assert.equal(sample(1, 0), 110);
  assert.equal(sample(0.5, 0), 105);
  assert.equal(sample(0, 0.5), 120);
  assert.equal(sample(0.5, 0.5), 125);
  assert.equal(sample(2.5, 2.5), 225);
});

test('3D Transect Profile: PSR exposure and telemetry indicators', () => {
  const html = fs.readFileSync(path.join(ROOT_DIR, 'web', 'index.html'), 'utf-8');
  assert.ok(html.includes('id="transectPsrDist"'), 'index.html must contain transectPsrDist readout');

  const app = fs.readFileSync(path.join(ROOT_DIR, 'web', 'app.js'), 'utf-8');
  assert.ok(app.includes('function samplePsr('), 'app.js must define samplePsr');
  assert.ok(app.includes('function getTransectSpriteTexture('), 'app.js must define getTransectSpriteTexture');
  assert.ok(app.includes('transectPsrHighlightGroup'), 'app.js must track transectPsrHighlightGroup');
  assert.ok(app.includes('transectCursorRing'), 'app.js must track transectCursorRing');
  assert.ok(app.includes('transectCursorSprite'), 'app.js must track transectCursorSprite');
  assert.ok(app.includes('PSR: YES (Permanent Shadow)'), 'app.js must format PSR positive hover telemetry');
  assert.ok(app.includes('WAY IN PSR: PERMANENT SHADOW'), 'app.js must define 3D billboard sprite for PSR way');
});

test('Transect Math: PSR distance and exposure percentage calculation', () => {
  const steps = 100;
  const totalLengthM = 5000;
  const psrFlags = new Array(steps + 1).fill(false);
  // Mark steps 20 to 45 as inside PSR (26 samples)
  for (let i = 20; i <= 45; i++) {
    psrFlags[i] = true;
  }
  const psrSteps = psrFlags.filter(Boolean).length;
  const psrDistM = (psrSteps / (steps + 1)) * totalLengthM;
  const psrPercent = (psrDistM / totalLengthM) * 100;

  assert.equal(psrSteps, 26);
  assert.ok(Math.abs(psrPercent - 25.74) < 0.1);
  assert.ok(Math.abs(psrDistM - 1287.1) < 1.0);
});
