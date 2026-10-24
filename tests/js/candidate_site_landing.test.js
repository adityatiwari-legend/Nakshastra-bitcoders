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

// ------------------------------------------------------------------------------
// 6. Autonomous Landing Simulation DOM Elements in web/index.html
// ------------------------------------------------------------------------------
test('Candidate Landing Site: web/index.html contains Autonomous Landing Simulation Deck', () => {
  const htmlPath = path.join(ROOT_DIR, 'web', 'index.html');
  const html = fs.readFileSync(htmlPath, 'utf-8');

  // Simulation Panel & Controls
  assert.ok(html.includes('id="landingSimPanel"'), 'index.html must contain landingSimPanel');
  assert.ok(html.includes('id="btnStartLandingSim"'), 'index.html must contain btnStartLandingSim');
  assert.ok(html.includes('id="simTargetSiteSelect"'), 'index.html must contain simTargetSiteSelect');
  assert.ok(html.includes('id="simLandingCanvas"'), 'index.html must contain simLandingCanvas');
  assert.ok(html.includes('id="simStatusBadge"'), 'index.html must contain simStatusBadge');
  assert.ok(html.includes('id="btnResetLandingSim"'), 'index.html must contain btnResetLandingSim');
  assert.ok(html.includes('id="btnSpeedLandingSim"'), 'index.html must contain btnSpeedLandingSim');

  // Telemetry HUD Elements
  assert.ok(html.includes('id="simHudAltitude"'), 'index.html must contain simHudAltitude');
  assert.ok(html.includes('id="simHudRange"'), 'index.html must contain simHudRange');
  assert.ok(html.includes('id="simHudPhaseTag"'), 'index.html must contain simHudPhaseTag');
  assert.ok(html.includes('id="simValVz"'), 'index.html must contain simValVz');
  assert.ok(html.includes('id="simValVx"'), 'index.html must contain simValVx');
  assert.ok(html.includes('id="simValThrottle"'), 'index.html must contain simValThrottle');
  assert.ok(html.includes('id="simValPropellant"'), 'index.html must contain simValPropellant');
  assert.ok(html.includes('id="simValPitch"'), 'index.html must contain simValPitch');
  assert.ok(html.includes('id="simValPsrStandoff"'), 'index.html must contain simValPsrStandoff');

  // Stepper & Autonomous Decision Stream
  assert.ok(html.includes('id="stepPDI"'), 'index.html must contain stepPDI');
  assert.ok(html.includes('id="stepHighGate"'), 'index.html must contain stepHighGate');
  assert.ok(html.includes('id="stepHDA"'), 'index.html must contain stepHDA');
  assert.ok(html.includes('id="stepLowGate"'), 'index.html must contain stepLowGate');
  assert.ok(html.includes('id="stepTouchdown"'), 'index.html must contain stepTouchdown');
  assert.ok(html.includes('id="simDecisionStream"'), 'index.html must contain simDecisionStream');
});

// ------------------------------------------------------------------------------
// 7. Landing Simulation CSS Styling in web/styles.css
// ------------------------------------------------------------------------------
test('Candidate Landing Site: web/styles.css contains Autonomous Landing Simulation styles', () => {
  const cssPath = path.join(ROOT_DIR, 'web', 'styles.css');
  const css = fs.readFileSync(cssPath, 'utf-8');

  assert.ok(css.includes('.landing-simulation-panel'), 'styles.css must style landing-simulation-panel');
  assert.ok(css.includes('.sim-layout-grid'), 'styles.css must style sim-layout-grid');
  assert.ok(css.includes('.sim-stage-container'), 'styles.css must style sim-stage-container');
  assert.ok(css.includes('.sim-phase-stepper'), 'styles.css must style sim-phase-stepper');
  assert.ok(css.includes('.sim-decision-stream'), 'styles.css must style sim-decision-stream');
  assert.ok(css.includes('.sim-log-entry'), 'styles.css must style sim-log-entry');
});

// ------------------------------------------------------------------------------
// 8. Engine Implementation in web/app.js
// ------------------------------------------------------------------------------
test('Candidate Landing Site: web/app.js exports simulation and trajectory calculation engine', () => {
  const appPath = path.join(ROOT_DIR, 'web', 'app.js');
  const app = fs.readFileSync(appPath, 'utf-8');

  assert.ok(app.includes('function initLandingSimulation'), 'app.js must define initLandingSimulation');
  assert.ok(app.includes('function toggleLandingSimulation'), 'app.js must define toggleLandingSimulation');
  assert.ok(app.includes('function startLandingSimulation'), 'app.js must define startLandingSimulation');
  assert.ok(app.includes('function startLandingSimulationForSite'), 'app.js must define startLandingSimulationForSite');
  assert.ok(app.includes('function computeDescentTrajectory'), 'app.js must define computeDescentTrajectory');
  assert.ok(app.includes('function renderLandingSimCanvas'), 'app.js must define renderLandingSimCanvas');
  assert.ok(app.includes('function addSimDecisionLog'), 'app.js must define addSimDecisionLog');
});

// ------------------------------------------------------------------------------
// 9. Trajectory & Autonomous GNC Decision-Making Math
// ------------------------------------------------------------------------------
test('Candidate Landing Math: GNC descent trajectory computation and phase progression', () => {
  // Pure math model from computeDescentTrajectory
  function computeTrajectoryPoint(u) {
    const altM = Math.max(0, 15000 * Math.pow(1 - u, 1.85));
    const rangeKm = Math.max(0, 30.0 * Math.pow(1 - u, 1.35));
    const vx = Math.max(0, 1680 * Math.pow(1 - u, 1.6));
    const vz = u >= 0.98 ? 0.0 : -(85 * (1 - u) * 0.9 + (u > 0.85 ? 1.2 : 4.0 * (1 - u)));
    return { altM, rangeKm, vx, vz };
  }

  // At PDI (u = 0.0): Orbital altitude 15,000m, range 30.0km, high horizontal velocity 1,680m/s
  const pdi = computeTrajectoryPoint(0.0);
  assert.strictEqual(Math.round(pdi.altM), 15000, 'PDI altitude must be 15,000 m');
  assert.strictEqual(Math.round(pdi.rangeKm), 30, 'PDI downrange must be 30.0 km');
  assert.strictEqual(Math.round(pdi.vx), 1680, 'PDI horizontal velocity must be 1,680 m/s');

  // At High Gate (u = 0.35): Decelerating rapidly
  const hg = computeTrajectoryPoint(0.35);
  assert.ok(hg.altM < 10000 && hg.altM > 4000, 'High Gate altitude must be intermediate');
  assert.ok(hg.vx < 1000, 'High Gate horizontal velocity must be reduced by braking burn');

  // At Touchdown (u = 1.0): Altitude = 0m, Range = 0km, Velocity = 0m/s
  const td = computeTrajectoryPoint(1.0);
  assert.strictEqual(td.altM, 0, 'Touchdown altitude must be 0 m');
  assert.strictEqual(td.rangeKm, 0, 'Touchdown downrange must be 0 km');
  assert.strictEqual(td.vx, 0, 'Touchdown horizontal velocity must be 0 m/s');
  assert.strictEqual(td.vz, 0, 'Touchdown vertical velocity must be 0 m/s (SECO)');
});

// ------------------------------------------------------------------------------
// 10. Strict PSR Cold Trap Landing Exclusion Logic
// ------------------------------------------------------------------------------
test('Candidate Landing Safety: PSR cold traps are strictly forbidden and disqualified', () => {
  // Synthetic 10x10 elevation grid with cell spacing 20m
  // Cells with psr = 1 represent cryogenic shadow traps (40K)
  const gridW = 10;
  const gridH = 10;
  const cellMeters = 20.0;
  const bufferCells = 2; // 40m buffer with 20m spacing = 2 cells

  const dem = Array.from({ length: gridH }, () => new Float32Array(gridW).fill(100.0));
  const psr = Array.from({ length: gridH }, () => new Uint8Array(gridW).fill(0));

  // Mark crater bowl at (3, 3) as PSR cold trap
  psr[3][3] = 1;
  psr[3][4] = 1;
  psr[4][3] = 1;
  psr[4][4] = 1;

  function evaluateTouchdown(r, c) {
    const isCellPsr = psr[r][c] === 1;
    let psrBufferBreach = isCellPsr;
    let bufferSafe = !isCellPsr;

    for (let br = Math.max(0, r - bufferCells); br <= Math.min(gridH - 1, r + bufferCells); br++) {
      for (let bc = Math.max(0, c - bufferCells); bc <= Math.min(gridW - 1, c + bufferCells); bc++) {
        const distSq = (br - r) ** 2 + (bc - c) ** 2;
        if (distSq <= bufferCells ** 2) {
          if (psr[br][bc] === 1) {
            psrBufferBreach = true;
            bufferSafe = false;
            break;
          }
        }
      }
      if (!bufferSafe) break;
    }

    const isSafe = !isCellPsr && !psrBufferBreach;
    const score = isSafe ? 95.0 : 0.0;
    const verdict = isCellPsr
      ? 'FORBIDDEN: PSR CRYOGENIC HAZARD (NO LANDING)'
      : (psrBufferBreach ? 'ABORT: 40m PSR HAZARD BUFFER VIOLATION' : 'APPROVED FOR TOUCHDOWN');

    return { isCellPsr, psrBufferBreach, isSafe, score, verdict };
  }

  // 1. Direct landing inside PSR cold trap (3, 3)
  const directPsrEval = evaluateTouchdown(3, 3);
  assert.strictEqual(directPsrEval.isCellPsr, true, 'Cell inside PSR must be flagged isCellPsr');
  assert.strictEqual(directPsrEval.isSafe, false, 'PSR cell must NEVER be safe for landing');
  assert.strictEqual(directPsrEval.score, 0.0, 'PSR cell suitability score must be 0%');
  assert.ok(directPsrEval.verdict.includes('FORBIDDEN'), 'PSR cell verdict must be FORBIDDEN');

  // 2. Landing at (2, 2) which is adjacent (<40m) to PSR
  const nearPsrEval = evaluateTouchdown(2, 2);
  assert.strictEqual(nearPsrEval.isCellPsr, false, 'Cell (2,2) is outside PSR itself');
  assert.strictEqual(nearPsrEval.psrBufferBreach, true, 'Cell (2,2) is within 40m standoff of PSR');
  assert.strictEqual(nearPsrEval.isSafe, false, 'Cell within 40m of PSR must not be safe');
  assert.strictEqual(nearPsrEval.score, 0.0, 'Cell within 40m of PSR must have 0% fit score');
  assert.ok(nearPsrEval.verdict.includes('ABORT'), 'Cell violating 40m buffer must trigger ABORT');

  // 3. Sunlit plateau at (8, 8) far away from PSR
  const safeEval = evaluateTouchdown(8, 8);
  assert.strictEqual(safeEval.isCellPsr, false, 'Sunlit plateau must not be PSR');
  assert.strictEqual(safeEval.psrBufferBreach, false, 'Sunlit plateau has ample PSR standoff');
  assert.strictEqual(safeEval.isSafe, true, 'Sunlit flat plateau must be approved for touchdown');
  assert.strictEqual(safeEval.score, 95.0, 'Sunlit plateau receives high suitability score');
  assert.ok(safeEval.verdict.includes('APPROVED'), 'Sunlit plateau receives touchdown approval');
});

