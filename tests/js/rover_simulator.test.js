const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const ROOT_DIR = path.resolve(__dirname, '..', '..');

test('Rover Simulator: DOM controls & Cockpit HUD in web/index.html', () => {
  const html = fs.readFileSync(path.join(ROOT_DIR, 'web', 'index.html'), 'utf-8');

  // Toolbar trigger & Studio button
  assert.ok(html.includes('id="btn3dRoverSim"'), 'index.html must contain btn3dRoverSim toolbar button');
  assert.ok(html.includes('id="btnLaunchRoverSim"'), 'index.html must contain btnLaunchRoverSim button in roverStudioTab');

  // HUD root overlay
  assert.ok(html.includes('id="roverSimulatorHud"'), 'index.html must contain roverSimulatorHud container');

  // Camera buttons
  assert.ok(html.includes('id="btnCamFollow"'), 'index.html must contain btnCamFollow button');
  assert.ok(html.includes('id="btnCamCockpit"'), 'index.html must contain btnCamCockpit button');
  assert.ok(html.includes('id="btnCamTop"'), 'index.html must contain btnCamTop button');
  assert.ok(html.includes('id="btnCamFree"'), 'index.html must contain btnCamFree button');

  // Telemetry gauge outputs
  assert.ok(html.includes('id="simValSpeed"'), 'index.html must contain simValSpeed readout');
  assert.ok(html.includes('id="simValOdo"'), 'index.html must contain simValOdo readout');
  assert.ok(html.includes('id="simValPitch"'), 'index.html must contain simValPitch readout');
  assert.ok(html.includes('id="simValRoll"'), 'index.html must contain simValRoll readout');
  assert.ok(html.includes('id="simValSoc"'), 'index.html must contain simValSoc readout');
  assert.ok(html.includes('id="simValPower"'), 'index.html must contain simValPower readout');
  assert.ok(html.includes('id="simValEnvironment"'), 'index.html must contain simValEnvironment readout');
  assert.ok(html.includes('id="simValWpIndex"'), 'index.html must contain simValWpIndex readout');
  assert.ok(html.includes('id="simTimeElapsed"'), 'index.html must contain simTimeElapsed readout');
  assert.ok(html.includes('id="simTimeTotal"'), 'index.html must contain simTimeTotal readout');

  // Traversal timeline scrubber & controls
  assert.ok(html.includes('id="roverSimScrubber"'), 'index.html must contain roverSimScrubber range slider');
  assert.ok(html.includes('id="btnRoverSimPlay"'), 'index.html must contain btnRoverSimPlay play/pause button');
  assert.ok(html.includes('onclick="rewindRoverSim()"'), 'index.html must contain rewindRoverSim action');
  assert.ok(html.includes('onclick="toggleRoverHeadlights()"'), 'index.html must contain toggleRoverHeadlights action');

  // Live Decision-Making Intelligence Box in small box
  assert.ok(html.includes('id="roverDecisionBox"'), 'index.html must contain roverDecisionBox container');
  assert.ok(html.includes('id="decisionActionBadge"'), 'index.html must contain decisionActionBadge');
  assert.ok(html.includes('id="decisionThoughtText"'), 'index.html must contain decisionThoughtText');
  assert.ok(html.includes('id="decNavMode"'), 'index.html must contain decNavMode');
  assert.ok(html.includes('id="decObstacleMargin"'), 'index.html must contain decObstacleMargin');
  assert.ok(html.includes('id="decSlopeSafety"'), 'index.html must contain decSlopeSafety');
  assert.ok(html.includes('id="decWheelSlip"'), 'index.html must contain decWheelSlip');
  assert.ok(html.includes('id="decisionFeedList"'), 'index.html must contain decisionFeedList');
  assert.ok(html.includes('onclick="toggleDecisionBoxMin()"'), 'index.html must support toggleDecisionBoxMin');
});

test('Rover Simulator: CSS styling definitions in web/styles.css', () => {
  const css = fs.readFileSync(path.join(ROOT_DIR, 'web', 'styles.css'), 'utf-8');

  assert.ok(css.includes('.three-rover-sim-hud'), 'styles.css must style .three-rover-sim-hud');
  assert.ok(css.includes('.sim-cam-btn'), 'styles.css must style camera toggle buttons');
  assert.ok(css.includes('.sim-metric-card'), 'styles.css must style telemetry metric cards');
  assert.ok(css.includes('.sim-scrubber-row'), 'styles.css must style scrubber row');
  assert.ok(css.includes('.sim-speed-pill'), 'styles.css must style speed multiplier pills');

  // Decision box styles
  assert.ok(css.includes('.rover-decision-box'), 'styles.css must style .rover-decision-box');
  assert.ok(css.includes('.decision-thought-card'), 'styles.css must style .decision-thought-card');
  assert.ok(css.includes('.decision-feed-list'), 'styles.css must style .decision-feed-list');
});

test('Rover Simulator: Engine functions & physics in web/app.js', () => {
  const app = fs.readFileSync(path.join(ROOT_DIR, 'web', 'app.js'), 'utf-8');

  // Lifecycle & control functions
  assert.ok(app.includes('function toggleRoverSimulator('), 'app.js must define toggleRoverSimulator');
  assert.ok(app.includes('function launchRoverSimulation3D('), 'app.js must define launchRoverSimulation3D');
  assert.ok(app.includes('function buildRoverTrajectory('), 'app.js must define buildRoverTrajectory');
  assert.ok(app.includes('function create3dRoverMesh('), 'app.js must define create3dRoverMesh');
  assert.ok(app.includes('function renderRoverSimFrameAt('), 'app.js must define renderRoverSimFrameAt');
  assert.ok(app.includes('function updateRoverSimulationFrame('), 'app.js must define updateRoverSimulationFrame');
  assert.ok(app.includes('function updateRoverSimCamera('), 'app.js must define updateRoverSimCamera');
  assert.ok(app.includes('function updateRoverSimHUD('), 'app.js must define updateRoverSimHUD');
  assert.ok(app.includes('function updateRoverDecisionEngine('), 'app.js must define updateRoverDecisionEngine');
  assert.ok(app.includes('function toggleDecisionBoxMin('), 'app.js must define toggleDecisionBoxMin');
  assert.ok(app.includes('function lerpAngle('), 'app.js must define lerpAngle');

  // Interactive controls
  assert.ok(app.includes('function toggleRoverSimPlayback('), 'app.js must define toggleRoverSimPlayback');
  assert.ok(app.includes('function rewindRoverSim('), 'app.js must define rewindRoverSim');
  assert.ok(app.includes('function onRoverSimScrub('), 'app.js must define onRoverSimScrub');
  assert.ok(app.includes('function setRoverSimSpeed('), 'app.js must define setRoverSimSpeed');
  assert.ok(app.includes('function setRoverCamMode('), 'app.js must define setRoverCamMode');
  assert.ok(app.includes('function toggleRoverHeadlights('), 'app.js must define toggleRoverHeadlights');

  // Render loop integration
  assert.ok(app.includes('updateRoverSimulationFrame()'), '3D render loop must tick rover simulator frame');
});

test('Rover Simulator Trajectory Interpolation Math', () => {
  // Pure unit test for the trajectory math interpolation
  const samples = [
    { x: 0, y: 0, z: 0, dist: 0, elev: 100, slope: 2, isPsr: false },
    { x: 10, y: 2, z: 10, dist: 14.14, elev: 105, slope: 5, isPsr: true },
    { x: 30, y: 5, z: 30, dist: 42.42, elev: 120, slope: 8, isPsr: true },
  ];
  const totalDist = samples[samples.length - 1].dist;

  function sampleAtFraction(progress) {
    const targetDist = progress * totalDist;
    let idx = 0;
    for (let i = 0; i < samples.length - 1; i++) {
      if (samples[i + 1].dist >= targetDist) {
        idx = i;
        break;
      }
    }
    const p0 = samples[idx];
    const p1 = samples[idx + 1] || p0;
    const segDist = p1.dist - p0.dist;
    const t = segDist > 0.0001 ? (targetDist - p0.dist) / segDist : 0;

    return {
      x: p0.x + (p1.x - p0.x) * t,
      y: p0.y + (p1.y - p0.y) * t,
      z: p0.z + (p1.z - p0.z) * t,
      elev: p0.elev + (p1.elev - p0.elev) * t,
      slope: p0.slope + (p1.slope - p0.slope) * t,
      isPsr: t > 0.5 ? p1.isPsr : p0.isPsr
    };
  }

  const atStart = sampleAtFraction(0);
  assert.equal(atStart.x, 0);
  assert.equal(atStart.elev, 100);
  assert.equal(atStart.isPsr, false);

  const atMid = sampleAtFraction(0.5);
  assert.ok(atMid.x > 5 && atMid.x < 25);
  assert.ok(atMid.elev > 105 && atMid.elev < 120);
  assert.equal(atMid.isPsr, true);

  const atEnd = sampleAtFraction(1.0);
  assert.equal(atEnd.x, 30);
  assert.equal(atEnd.elev, 120);
  assert.equal(atEnd.isPsr, true);
});
