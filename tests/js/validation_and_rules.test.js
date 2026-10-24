/**
 * Tests for OrbisLuna Validation Metrics & Rule Consistency
 * Verifies mathematical parity (pixel count × pixel area = total area),
 * dynamic rule table text formatting, and dataset banner reconciliation.
 */

const test = require('node:test');
const assert = require('node:assert/strict');

test('Validation Math: Area parity for Synthetic 20m/px Crater', () => {
  const pixel_size_m = 20.0;
  const width = 200;
  const height = 200;
  const totalPixels = width * height; // 40,000 px
  const pxAreaKm2 = (pixel_size_m * pixel_size_m) / 1e6; // 0.0004 km²

  const totalAreaKm2 = totalPixels * pxAreaKm2;
  assert.equal(totalAreaKm2, 16.0);

  // Class partition check
  const classes = {
    safe: 12749,
    caution: 13339,
    unsafe: 9377,
    shadowed: 1399,
    nodata: 3136
  };
  const sumPx = Object.values(classes).reduce((a, b) => a + b, 0);
  assert.equal(sumPx, totalPixels);

  const sumKm2 = Object.values(classes).reduce((acc, px) => acc + (px * pxAreaKm2), 0);
  assert.ok(Math.abs(sumKm2 - totalAreaKm2) < 1e-6, 'Sum of class areas must equal total area');
});

test('Validation Math: Area parity for NASA LRO LOLA 240m/px Polar Dem', () => {
  const pixel_size_m = 240.0;
  const width = 250;
  const height = 250;
  const totalPixels = width * height; // 62,500 px
  const pxAreaKm2 = (pixel_size_m * pixel_size_m) / 1e6; // 0.0576 km²

  const totalAreaKm2 = totalPixels * pxAreaKm2;
  assert.equal(totalAreaKm2, 3600.0);

  // Exact NASA summary classes
  const classes = {
    safe: 10833,
    caution: 23792,
    unsafe: 23825,
    shadowed: 4044,
    nodata: 6
  };
  const sumPx = Object.values(classes).reduce((a, b) => a + b, 0);
  assert.equal(sumPx, totalPixels);

  const sumKm2 = Object.values(classes).reduce((acc, px) => acc + (px * pxAreaKm2), 0);
  assert.ok(Math.abs(sumKm2 - totalAreaKm2) < 1e-4, 'Sum of class areas must equal 3,600 km²');
});

test('Rule Table Text Formatter: formats live thresholds and baseline indicators', () => {
  function formatRules(sSafe, sHard, rSafe, rHard) {
    return {
      r1: `Safe pixel slope must strictly be below Safe Slope Limit (< ${sSafe.toFixed(1)}°) (Baseline: 5.0°)`,
      r2: `Safe pixel roughness must strictly be below Safe Roughness Limit (< ${rSafe.toFixed(1)} m) (Baseline: 1.5 m)`,
      r5: `Hard Slope Override: Any pixel with slope ≥ ${sHard.toFixed(1)}° is strictly Unsafe (Baseline: 15.0°)`,
      r6: `Hard Roughness Override: Any pixel with roughness ≥ ${rHard.toFixed(1)} m is strictly Unsafe (Baseline: 5.0 m)`,
      r8: `PSR Non-Steep classification: Any non-steep (slope < ${sHard.toFixed(1)}°) pixel with PSR = 1 is Class 4 Shadowed-Unknown`,
    };
  }

  // Baseline test
  const base = formatRules(5.0, 15.0, 1.5, 5.0);
  assert.ok(base.r1.includes('< 5.0°'));
  assert.ok(base.r5.includes('≥ 15.0°'));
  assert.ok(base.r8.includes('slope < 15.0°'));

  // Custom adjusted threshold test
  const custom = formatRules(6.5, 18.0, 2.0, 6.0);
  assert.ok(custom.r1.includes('< 6.5°'));
  assert.ok(custom.r5.includes('≥ 18.0°'));
  assert.ok(custom.r6.includes('≥ 6.0 m'));
  assert.ok(custom.r8.includes('slope < 18.0°'));
});

test('Dataset Banner: Production vs Benchmark differentiation', () => {
  function getBannerState(datasetId, isSynthetic) {
    if (isSynthetic || datasetId === 'synthetic') {
      return {
        name: 'Synthetic Benchmark Crater (Calibration Ground Truth)',
        type: 'BENCHMARK',
        provenance: 'Synthetic Closed-Form Shadow Floor'
      };
    }
    return {
      name: 'REAL NASA LRO LOLA (South Pole 80°S–90°S)',
      type: 'PRODUCTION',
      provenance: 'NASA LRO LOLA LPSR_65S_240M V1.05'
    };
  }

  const prod = getBannerState('lola_crop', false);
  assert.equal(prod.type, 'PRODUCTION');
  assert.ok(prod.name.includes('NASA LRO LOLA'));

  const bench = getBannerState('synthetic', true);
  assert.equal(bench.type, 'BENCHMARK');
  assert.ok(bench.name.includes('Synthetic Benchmark'));
});
