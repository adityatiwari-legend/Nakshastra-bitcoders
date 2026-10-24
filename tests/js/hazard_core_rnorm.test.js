/*
 * hazard_core rNorm tests — the resolution-scaled roughness normalization
 * divisor (BUG-041 family): callers pass effective meters (18/60 at 240 m/px)
 * while legacy callers omit rNorm and keep divisor = rHard bit-identically.
 */
const test = require('node:test');
const assert = require('node:assert');
const core = require('../../web/hazard_core.js');

// One valid pixel: slope 4 deg, roughness 4 m, non-PSR.
const arrays = { dem: [100], slope: [4], roughness: [4], psr: [0], nodata: -9999 };
const base = {
  sSafe: 6, sCaut: 10, sHard: 15,
  rSafe: 18, rHard: 60,       // effective (scaled) meters
  wS: 0.5, wR: 0.3, wD: 0.2,
  pxAreaKm2: 0.0576,
};

test('rNorm=60 (scaled): score = 0.153 < 0.25 -> Safe', () => {
  const r = core.previewAll(arrays, { ...base, rNorm: 60 });
  assert.strictEqual(r.hazard[0], 1);
  assert.strictEqual(r.safeCnt, 1);
});

test('rNorm=5 (raw): score = 0.373 >= 0.25 -> Caution', () => {
  const r = core.previewAll(arrays, { ...base, rNorm: 5 });
  assert.strictEqual(r.hazard[0], 2);
  assert.strictEqual(r.cautionCnt, 1);
});

test('omitted rNorm falls back to divisor = rHard (legacy semantics)', () => {
  // rHard: 5 -> divisor 5, same as raw normalization; r=4 < rHard not hard.
  const r = core.previewAll(arrays, { ...base, rHard: 5 });
  assert.strictEqual(r.hazard[0], 2);
});

test('sensitivity() honors the explicit rNorm divisor', () => {
  const scaled = core.sensitivity(arrays, 6, 15, 18, 60, 0.5, 0.3, 0.2, 0.0576, null, 60);
  // Safe at every bar threshold: s=4 < sSafe=6, score < 0.25, r=4 < rSafe=18.
  assert.ok(scaled.bars[0].safe_km2 > 0, 'scaled norm classifies pixel Safe');
  const raw = core.sensitivity(arrays, 6, 15, 18, 60, 0.5, 0.3, 0.2, 0.0576, null, 5);
  assert.strictEqual(raw.bars[0].safe_km2, 0, 'raw norm demotes pixel out of Safe');
});

test('bars[t].unsafe predicate matches curve[t] (hard-slope scenario)', () => {
  // slope=4, rough=4, rNorm=60 -> score=0.153; not hard for any t >= 5.
  const s = core.sensitivity(arrays, 6, 15, 18, 60, 0.5, 0.3, 0.2, 0.0576, null, 60);
  const bar5 = s.bars.find(b => b.threshold === 5.0);
  const curve5 = s.curve.find(c => c.slope_deg === 5.0);
  assert.strictEqual(bar5.unsafe_km2, curve5.unsafe_km2);
  assert.strictEqual(bar5.unsafe_km2, 0);

  // Raise the pixel above both gates: slope 9 >= t=5 but < 7... t=7 unsafe, t=15 not.
  const steep = { dem: [100], slope: [9], roughness: [4], psr: [0], nodata: -9999 };
  const s2 = core.sensitivity(steep, 6, 15, 18, 60, 0.5, 0.3, 0.2, 0.0576, null, 60);
  const b5 = s2.bars.find(b => b.threshold === 5.0);
  const c5 = s2.curve.find(c => c.slope_deg === 5.0);
  const b15 = s2.bars.find(b => b.threshold === 15.0);
  assert.ok(b5.unsafe_km2 > 0, 'slope 9 >= 5 hard-unsafe at t=5');
  assert.strictEqual(b5.unsafe_km2, c5.unsafe_km2, 'bar/curve predicate parity');
  assert.strictEqual(b15.unsafe_km2, 0, 'slope 9 < 15 -> not hard at t=15');
});
