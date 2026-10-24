// Phase 5E: worker protocol tests (simulated browser worker globals).
// Loads web/worker.js under `self === global` with an importScripts polyfill
// and drives the documented init/preview message protocol.
'use strict';

const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ROOT = path.resolve(__dirname, '..', '..');
const out = [];
global.self = global;
global.postMessage = (m, transfer) => out.push({ m, transfer: transfer || [] });
global.importScripts = () => { require(path.join(ROOT, 'web', 'hazard_core.js')); };

vm.runInThisContext(fs.readFileSync(path.join(ROOT, 'web', 'worker.js'), 'utf8'), {
  filename: 'worker.js',
});

const N = 16;
const arrays = {
  dem: new Float32Array(N).fill(100),
  slope: new Float32Array([1, 1, 1, 1, 16, 16, 6, 6, 1, 1, 1, 1, 8, 8, 1, 1]),
  roughness: new Float32Array([1, 1, 6, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]),
  psr: new Uint8Array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0]),
  nodata: -9999,
};
const params = { sSafe: 5, sCaut: 10, sHard: 15, rSafe: 2, rHard: 5, wS: 0.5, wR: 0.3, wD: 0.2, pxAreaKm2: 0.0004 };

test('worker registers onmessage', () => {
  assert.strictEqual(typeof global.onmessage, 'function');
});

test('preview before init returns error', () => {
  out.length = 0;
  global.onmessage({ data: { cmd: 'preview', id: 1, params } });
  assert.strictEqual(out.length, 1);
  assert.strictEqual(out[0].m.cmd, 'error');
  assert.strictEqual(out[0].m.id, 1);
});

test('init responds ready', () => {
  global.onmessage({ data: { cmd: 'init', arrays } });
  assert.strictEqual(out[1].m.cmd, 'ready');
});

test('preview echoes params, transfers hazard, exact hand-computed classes', () => {
  global.onmessage({ data: { cmd: 'preview', id: 7, params } });
  assert.strictEqual(out.length, 3);
  const r = out[2].m;
  assert.strictEqual(r.cmd, 'preview');
  assert.strictEqual(r.id, 7);
  assert.deepStrictEqual(r.params, params, 'params must be echoed for applyPreviewResults');
  assert.strictEqual(r.res.hazard, null, 'hazard stripped from structured clone');
  assert.ok(r.hazardBuffer instanceof ArrayBuffer);
  assert.strictEqual(r.hazardBuffer.byteLength, N, 'exact-size buffer');
  assert.strictEqual(out[2].transfer.length, 1, 'zero-copy transfer list');

  const hazard = new Uint8Array(r.hazardBuffer);
  const expected = [1, 1, 3, 1, 3, 3, 2, 2, 1, 1, 1, 4, 2, 2, 1, 1];
  assert.deepStrictEqual(Array.from(hazard), expected);
  const c = r.res;
  assert.strictEqual(c.safeCnt + c.cautionCnt + c.unsafeCnt + c.shadowCnt + c.nodataCnt, N);
  assert.strictEqual(c.violations.total, 0, 'hand grid has zero rule violations');
  assert.strictEqual(c.sens.bars.length, 3);
  assert.strictEqual(c.sens.curve.length, 10);
});

test('sequential previews keep ids', () => {
  global.onmessage({ data: { cmd: 'preview', id: 8, params } });
  assert.strictEqual(out[3].m.id, 8);
});
