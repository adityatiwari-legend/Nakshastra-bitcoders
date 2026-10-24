/*
 * hazard_core.js — pure, DOM-free hazard classification + sensitivity math.
 *
 * Phase 5 extraction: this module is the SINGLE source of truth for the two
 * hot full-grid computations and runs in THREE contexts:
 *   1. main thread (synchronous fallback when the Web Worker is unavailable)
 *   2. web/worker.js via importScripts('/hazard_core.js')
 *   3. Node (module.exports) for unit tests
 *
 * Logic is moved verbatim from app.js previewReclassifyClient() and
 * computeSensitivityData(); behavior must remain bit-identical.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  }
  if (root) {
    root.HazardCore = api;
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  /**
   * Sensitivity bars + curve over the active grid.
   * aoiSet: a Set of linear indices restricts sampling to an AOI subset;
   * anything else (null / undefined / legacy numbers) means the full grid.
   * Full-grid exact sampling (parity with the server's numpy masks — the
   * historical 2x subsample made chart annotations drift from the KPIs).
   * rNorm (optional): roughness normalization divisor. Callers that apply
   * resolution scaling pass it explicitly; when omitted the divisor falls
   * back to rHard (legacy behavior, keeps existing tests bit-identical).
   */
  function sensitivity(arrays, sSafe, sHard, rSafe, rHard, wS, wR, wD, pxAreaKm2, validPx, rNorm) {
    const slope = arrays.slope;
    const rough = arrays.roughness;
    const psr = arrays.psr;
    const dem = arrays.dem;
    const nodata = arrays.nodata;
    const totalPx = slope.length;
    const aoiSet = (validPx instanceof Set) ? validPx : null;
    const step = 1; // exact full-grid (runs in the Web Worker)
    const rNormDiv = (typeof rNorm === 'number' && isFinite(rNorm) && rNorm > 0) ? rNorm : (rHard || 5.0);

    // 1. Bar Chart: class split at hard-unsafe slope limits 5°, 10°, 15°.
    // t is the scenario's hard-unsafe slope limit, so bars[t].unsafe_km2
    // equals the curve point at t (identical predicate on both sides).
    const barThresholds = [5.0, 10.0, 15.0];
    const barsData = barThresholds.map(t => {
      let sCnt = 0, cCnt = 0, uCnt = 0, shCnt = 0;

      for (let i = 0; i < totalPx; i += step) {
        if (aoiSet && !aoiSet.has(i)) continue;
        const d = dem[i];
        const s = slope[i];
        const r = rough[i];
        const p = psr ? psr[i] : 0;
        if (d === nodata || isNaN(d) || s === nodata || isNaN(s)) continue;

        const sNorm = Math.min(1.0, Math.max(0.0, s / 15.0));
        const rNorm2 = Math.min(1.0, Math.max(0.0, r / rNormDiv));
        const scoreH = wS * sNorm + wR * rNorm2;
        const isHard = s >= t || r >= rHard;

        if (scoreH >= 0.60 || isHard) uCnt++;
        else if (p === 1) shCnt++;
        else if (scoreH < 0.25 && s < sSafe && r < rSafe) sCnt++;
        else cCnt++;
      }

      return {
        threshold: t,
        safe_km2: sCnt * pxAreaKm2,
        caution_km2: cCnt * pxAreaKm2,
        unsafe_km2: uCnt * pxAreaKm2,
        shadow_km2: shCnt * pxAreaKm2,
      };
    });

    // 2. Line Chart: Unsafe area vs slope threshold (3° to 25°)
    const curveSlopePoints = [3.0, 5.0, 7.0, 9.0, 11.0, 13.0, 15.0, 17.0, 20.0, 25.0];
    const curveData = curveSlopePoints.map(st => {
      let uCnt = 0;
      for (let i = 0; i < totalPx; i += step) {
        if (aoiSet && !aoiSet.has(i)) continue;
        const d = dem[i];
        const s = slope[i];
        const r = rough[i];
        if (d === nodata || isNaN(d) || s === nodata || isNaN(s)) continue;
        const sNorm = Math.min(1.0, Math.max(0.0, s / 15.0));
        const rNorm2 = Math.min(1.0, Math.max(0.0, r / rNormDiv));
        const scoreH = wS * sNorm + wR * rNorm2;
        if (scoreH >= 0.60 || s >= st || r >= rHard) uCnt++;
      }
      return {
        slope_deg: st,
        unsafe_km2: uCnt * pxAreaKm2,
      };
    });

    return { bars: barsData, curve: curveData };
  }

  /**
   * Full preview computation: 5-class hazard array + class counts + live
   * 9-point rule audit + sensitivity charts, in one call.
   *
   * arrays: { dem, slope, roughness, psr, nodata }
   * p: { sSafe, sCaut, sHard, rSafe, rHard, wS, wR, wD, pxAreaKm2 }
   *
   * Returns { hazard, safeCnt, cautionCnt, unsafeCnt, shadowCnt, nodataCnt,
   *           validPx, violations: {v1..v9, total}, sens }
   * hazard is a fresh Uint8Array (safe to transfer between threads).
   */
  function previewAll(arrays, p) {
    const dem = arrays.dem;
    const slope = arrays.slope;
    const rough = arrays.roughness;
    const psr = arrays.psr;
    const nodata = arrays.nodata;
    const totalPx = slope.length;
    const hazard = new Uint8Array(totalPx);

    const sSafe = p.sSafe;
    const sHard = p.sHard;
    const rSafe = p.rSafe;
    const rHard = p.rHard;
    const wS = p.wS;
    const wR = p.wR;
    const wD = p.wD;
    const pxAreaKm2 = p.pxAreaKm2;
    // Roughness normalization divisor: explicit p.rNorm (resolution-scaled by
    // the caller) wins; otherwise fall back to rHard (legacy semantics).
    const rNormDiv = (typeof p.rNorm === 'number' && isFinite(p.rNorm) && p.rNorm > 0) ? p.rNorm : (rHard || 5.0);

    let safeCnt = 0;
    let cautionCnt = 0;
    let unsafeCnt = 0;
    let shadowCnt = 0;
    let nodataCnt = 0;

    // Rule Audit counters
    let v1 = 0, v2 = 0, v3 = 0, v4 = 0, v5 = 0, v6 = 0, v7 = 0, v8 = 0, v9 = 0;

    for (let i = 0; i < totalPx; i++) {
      const d = dem[i];
      const s = slope[i];
      const r = rough[i];
      const pPsr = psr ? psr[i] : 0;

      // Rule 9: NoData strictly Class 0, never Safe
      if (d === nodata || isNaN(d) || s === nodata || isNaN(s)) {
        hazard[i] = 0;
        nodataCnt++;
        continue;
      }

      // Normalized criteria scores
      const sNorm = Math.min(1.0, Math.max(0.0, s / 15.0));
      const rNorm = Math.min(1.0, Math.max(0.0, r / rNormDiv));
      const dNorm = 0.0;
      const scoreH = wS * sNorm + wR * rNorm + wD * dNorm;

      // Hard physical overrides
      const isHardSlope = s >= sHard;
      const isHardRough = r >= rHard;
      const isHardOverride = isHardSlope || isHardRough;

      let cls = 0;
      if (scoreH >= 0.60 || isHardOverride) {
        cls = 3; // Unsafe
        unsafeCnt++;
      } else if (pPsr === 1) {
        cls = 4; // Shadowed-Unknown
        shadowCnt++;
      } else if (scoreH < 0.25 && s < sSafe && r < rSafe) {
        cls = 1; // Safe
        safeCnt++;
      } else {
        cls = 2; // Caution
        cautionCnt++;
      }

      hazard[i] = cls;

      // Live 9-point rule auditing
      if (cls === 1) {
        if (s >= sSafe) v1++;
        if (r >= rSafe) v2++;
        if (scoreH >= 0.25) v3++;
        if (pPsr === 1) v4++;
      }
      if (isHardOverride && cls !== 3) v5++;
      if (scoreH >= 0.60 && cls !== 3) v7++;
      if (pPsr === 1 && (cls === 1 || cls === 2)) v8++;
    }

    const validPx = safeCnt + cautionCnt + unsafeCnt + shadowCnt;
    const violations = { v1, v2, v3, v4, v5, v6, v7, v8, v9 };
    violations.total = v1 + v2 + v3 + v4 + v5 + v6 + v7 + v8 + v9;

    const sens = sensitivity(arrays, sSafe, sHard, rSafe, rHard, wS, wR, wD,
                             pxAreaKm2, null, rNormDiv);

    return {
      hazard,
      safeCnt, cautionCnt, unsafeCnt, shadowCnt, nodataCnt,
      validPx,
      violations,
      sens,
    };
  }

  return { sensitivity, previewAll };
});
