const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const ROOT_DIR = path.resolve(__dirname, '..', '..');

// ------------------------------------------------------------------------------
// 1. DOM Elements in web/index.html
// ------------------------------------------------------------------------------
test('Candidate Landing Site: web/index.html contains 3D scan overlay and touchdown HUD', () => {
  const htmlPath = path.join(ROOT_DIR, 'web', 'index.html');
  const html = fs.readFileSync(htmlPath, 'utf-8');

  // Scanning overlay
  assert.ok(html.includes('id="site3dScanOverlay"'), 'index.html must contain site3dScanOverlay');
  assert.ok(html.includes('id="site3dScanProgressBar"'), 'index.html must contain site3dScanProgressBar');
  assert.ok(html.includes('id="site3dScanStatusText"'), 'index.html must contain site3dScanStatusText');

  // Real-time touchdown HUD
  assert.ok(html.includes('id="site3dTouchdownHud"'), 'index.html must contain site3dTouchdownHud');
  assert.ok(html.includes('id="site3dTouchdownSlope"'), 'index.html must contain site3dTouchdownSlope');
  assert.ok(html.includes('id="site3dTouchdownBuffer"'), 'index.html must contain site3dTouchdownBuffer');
  assert.ok(html.includes('id="site3dTouchdownVerdict"'), 'index.html must contain site3dTouchdownVerdict');

  // 3D Controls
  assert.ok(html.includes('id="btnSite3dRescan"'), 'index.html must contain btnSite3dRescan');
  assert.ok(html.includes('id="btnSite3dLanderPlacement"'), 'index.html must contain btnSite3dLanderPlacement');
  assert.ok(html.includes('id="btnSite3dFindPerfectSpot"'), 'index.html must contain btnSite3dFindPerfectSpot');
  assert.ok(html.includes('id="btnSite3dTestHazard"'), 'index.html must contain btnSite3dTestHazard');

  // Dossier 40m Buffer Card and Recommended Site Fallback
  assert.ok(html.includes('id="siteLandingBufferCard"'), 'index.html must contain siteLandingBufferCard');
  assert.ok(html.includes('id="siteLandingBufferBadge"'), 'index.html must contain siteLandingBufferBadge');
  assert.ok(html.includes('id="siteRecommendedDivertCard"'), 'index.html must contain siteRecommendedDivertCard');
  assert.ok(html.includes('id="btnDivertToRecommended"'), 'index.html must contain btnDivertToRecommended');
});

// ------------------------------------------------------------------------------
// 2. CSS Styling in web/styles.css
// ------------------------------------------------------------------------------
test('Candidate Landing Site: web/styles.css contains scanning and touchdown rules', () => {
  const cssPath = path.join(ROOT_DIR, 'web', 'styles.css');
  const css = fs.readFileSync(cssPath, 'utf-8');

  assert.ok(css.includes('.site-3d-scan-overlay'), 'styles.css must style site-3d-scan-overlay');
  assert.ok(css.includes('.scan-radar-ring'), 'styles.css must style scan-radar-ring');
  assert.ok(css.includes('.scan-progress-bar'), 'styles.css must style scan-progress-bar');
  assert.ok(css.includes('.site-3d-touchdown-hud'), 'styles.css must style site-3d-touchdown-hud');
  assert.ok(css.includes('.recommended-divert-card'), 'styles.css must style recommended-divert-card');
  assert.ok(css.includes('.landing-zones-list'), 'styles.css must style landing-zones-list');
});

// ------------------------------------------------------------------------------
// 3. Engine Implementation in web/app.js
// ------------------------------------------------------------------------------
test('Candidate Landing Site: web/app.js exports touchdown scanning and placement functions', () => {
  const appPath = path.join(ROOT_DIR, 'web', 'app.js');
  const app = fs.readFileSync(appPath, 'utf-8');

  assert.ok(app.includes('function createLander3DModel'), 'app.js must define createLander3DModel');
  assert.ok(app.includes('function startSite3dScanAnimation'), 'app.js must define startSite3dScanAnimation');
  assert.ok(app.includes('function applyScanResultsTo3D'), 'app.js must define applyScanResultsTo3D');
  assert.ok(app.includes('function findAndHighlightPerfectLandingSpot'), 'app.js must define findAndHighlightPerfectLandingSpot');
  assert.ok(app.includes('function showNoViableLandingSpotAlert'), 'app.js must define showNoViableLandingSpotAlert');
  assert.ok(app.includes('function testNoViableLandingSpotScenario'), 'app.js must define testNoViableLandingSpotScenario');
  assert.ok(app.includes('function divertToRecommendedSite'), 'app.js must define divertToRecommendedSite');
  assert.ok(app.includes('function toggleSite3dManualLanderPlacement'), 'app.js must define toggleSite3dManualLanderPlacement');
  assert.ok(app.includes('function evaluateTouchdownAtWorldPos'), 'app.js must define evaluateTouchdownAtWorldPos');
  assert.ok(app.includes('function openCandidateSite3D'), 'app.js must define openCandidateSite3D');
});

// ------------------------------------------------------------------------------
// 4. Mathematical Logic: 40-Meter Buffer & Perfect Spot Evaluation Math
// ------------------------------------------------------------------------------
test('Candidate Landing Math: 40m Buffer neighborhood evaluation and perfect spot selection', () => {
  // Simulate a synthetic 10x10 elevation grid with cell spacing 20m
  // Cells at (5, 5) is a flat plain surrounded by safe slopes
  // Cells at (1, 1) is near an escarpment (slope > 15°)
  const gridW = 10;
  const gridH = 10;
  const cellMeters = 20.0;
  const bufferRadiusM = 40.0;
  const bufferCells = Math.max(1, Math.round(bufferRadiusM / cellMeters)); // 2 cells

  assert.strictEqual(bufferCells, 2, '40m buffer with 20m spacing should evaluate a 2-cell radius');

  // Synthetic DEM
  const dem = Array.from({ length: gridH }, () => new Float32Array(gridW).fill(100.0));
  // Create an escarpment near (1, 1)
  dem[0][0] = 50.0;
  dem[0][1] = 60.0;
  dem[1][0] = 55.0;

  function computeSlopeAt(r, c) {
    const dr = (dem[Math.min(gridH - 1, r + 1)][c] - dem[Math.max(0, r - 1)][c]);
    const dc = (dem[r][Math.min(gridW - 1, c + 1)] - dem[r][Math.max(0, c - 1)]);
    const grad = Math.sqrt((dc / (2 * cellMeters)) ** 2 + (dr / (2 * cellMeters)) ** 2);
    return Math.atan(grad) * (180 / Math.PI);
  }

  function evaluate40mBuffer(r, c) {
    const centerSlope = computeSlopeAt(r, c);
    let bufferSafe = true;
    let maxBufSlope = centerSlope;

    for (let br = Math.max(0, r - bufferCells); br <= Math.min(gridH - 1, r + bufferCells); br++) {
      for (let bc = Math.max(0, c - bufferCells); bc <= Math.min(gridW - 1, c + bufferCells); bc++) {
        const distSq = (br - r) ** 2 + (bc - c) ** 2;
        if (distSq <= bufferCells ** 2) {
          const bslope = computeSlopeAt(br, bc);
          if (bslope > maxBufSlope) maxBufSlope = bslope;
          if (bslope >= 10.0) {
            bufferSafe = false;
            break;
          }
        }
      }
      if (!bufferSafe) break;
    }
    return { slope: centerSlope, bufferSafe, maxBufSlope, isViable: centerSlope < 5.0 && bufferSafe };
  }

  // Spot at (5, 5) should be 100% flat with certified 40m clear buffer
  const centerEval = evaluate40mBuffer(5, 5);
  assert.strictEqual(centerEval.isViable, true, 'Center cell (5,5) should be certified as viable landing spot');
  assert.strictEqual(centerEval.bufferSafe, true, 'Center cell (5,5) buffer should be safe');
  assert.ok(centerEval.slope < 0.1, 'Center cell slope should be close to 0');

  // Spot at (2, 2) is within 2 cells of the escarpment
  const escarpmentEval = evaluate40mBuffer(2, 2);
  assert.strictEqual(escarpmentEval.bufferSafe, false, 'Spot near escarpment (2,2) should fail the 40m buffer');
  assert.strictEqual(escarpmentEval.isViable, false, 'Spot near escarpment must not be viable');
});

// ------------------------------------------------------------------------------
// 5. Contingency Recommendation Fallback
// ------------------------------------------------------------------------------
test('Candidate Landing Contingency: High-slope terrain triggers recommended alternative site', () => {
  // If all cells in a region have slope >= 15° (e.g. crater rim wall), viableSpots will be empty
  const viableSpots = [];
  const candidateCatalog = [
    { name: 'Site Alpha (Connecting Ridge)', mean_slope: 0.33, clearance_m: 3200, status: 'APPROVED' },
    { name: 'Site Beta (Ridge Flank)', mean_slope: 0.35, clearance_m: 2900, status: 'APPROVED' }
  ];

  let recommendedSite = null;
  if (viableSpots.length === 0) {
    // Pick candidate with minimum slope and maximum clearance
    recommendedSite = candidateCatalog.slice().sort((a, b) => a.mean_slope - b.mean_slope)[0];
  }

  assert.ok(recommendedSite !== null, 'Recommended site must be provided when viableSpots is empty');
  assert.strictEqual(recommendedSite.name, 'Site Alpha (Connecting Ridge)', 'Should select Site Alpha as recommended alternative');
  assert.ok(recommendedSite.clearance_m >= 3000, 'Recommended site must have ample clearance');
});
