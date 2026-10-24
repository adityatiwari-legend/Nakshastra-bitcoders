/*
 * worker.js — Phase 5 Web Worker for the full-grid hazard preview compute.
 *
 * The heaviest recurring client computation (classify 62,500 px + 9-point rule
 * audit + sensitivity charts on every slider event) runs here so the main
 * thread only does DOM/canvas work. Note: rover pathfinding itself runs
 * server-side (A* in rover_router.py via POST /api/rover-route); this worker
 * covers the equivalent heavy client-side grid math.
 *
 * Protocol:
 *   main -> { cmd: 'init', arrays: {dem, slope, roughness, psr, nodata} }
 *       <- { cmd: 'ready' }
 *   main -> { cmd: 'preview', id, params }
 *       <- { cmd: 'preview', id, res, hazardBuffer }   (buffer transferred)
 *
 * On any error the worker posts { cmd: 'error' } and the main thread falls
 * back to synchronous HazardCore.previewAll on the main thread.
 */
'use strict';

importScripts('/hazard_core.js');

let ARRAYS = null;

self.onmessage = function (e) {
  const msg = e.data;
  if (!msg || !msg.cmd) return;
  try {
    if (msg.cmd === 'init') {
      ARRAYS = msg.arrays;
      self.postMessage({ cmd: 'ready' });
      return;
    }
    if (msg.cmd === 'preview') {
      if (!ARRAYS) {
        self.postMessage({ cmd: 'error', id: msg.id, reason: 'not initialized' });
        return;
      }
      const res = HazardCore.previewAll(ARRAYS, msg.params);
      // Echo params back so applyPreviewResults(res, params) has them.
      // Transfer the hazard bytes zero-copy (fall back to an exact-size copy
      // if the view ever spans a larger buffer).
      const out = Object.assign({}, res);
      out.hazard = null;
      let hazardBuffer = res.hazard.buffer;
      if (res.hazard.byteLength !== res.hazard.buffer.byteLength) {
        hazardBuffer = res.hazard.slice().buffer;
      }
      self.postMessage(
        { cmd: 'preview', id: msg.id, params: msg.params, res: out, hazardBuffer: hazardBuffer },
        [hazardBuffer]
      );
      return;
    }
  } catch (err) {
    self.postMessage({
      cmd: 'error',
      id: msg.id,
      reason: (err && err.message) ? err.message : String(err),
    });
  }
};
