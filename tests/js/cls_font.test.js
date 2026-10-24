const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

test('CLS Font: metric calculation derivation formulas', () => {
  // Metric formulas:
  // sizeAdjust = (targetAvgWidth / fallbackAvgWidth)
  // ascentOverride = (targetAscent / targetUPM) / sizeAdjust
  // descentOverride = (abs(targetDescent) / targetUPM) / sizeAdjust
  // lineGapOverride = (targetLineGap / targetUPM) / sizeAdjust

  function deriveMetrics(target, fallback) {
    const sizeAdjust = target.avgWidth / fallback.avgWidth;
    const ascentOverride = (target.ascent / target.upm) / sizeAdjust;
    const descentOverride = (Math.abs(target.descent) / target.upm) / sizeAdjust;
    const lineGapOverride = (target.lineGap / target.upm) / sizeAdjust;
    return {
      sizeAdjust: +(sizeAdjust * 100).toFixed(0),
      ascentOverride: +(ascentOverride * 100).toFixed(0),
      descentOverride: +(descentOverride * 100).toFixed(1),
      lineGapOverride: +(lineGapOverride * 100).toFixed(0)
    };
  }

  // Inter vs Arial (real font table metrics: 1.0743 ratio)
  const interMetrics = deriveMetrics(
    { upm: 2048, ascent: 1984, descent: -494, lineGap: 0, avgWidth: 1074.3 },
    { upm: 2048, ascent: 1854, descent: -434, lineGap: 67, avgWidth: 1000.0 }
  );
  assert.equal(interMetrics.sizeAdjust, 107);
  assert.equal(interMetrics.ascentOverride, 90);
  assert.equal(interMetrics.descentOverride, 22.5);
  assert.equal(interMetrics.lineGapOverride, 0);

  // Outfit vs Arial (real font table metrics: 1.02 ratio)
  const outfitMetrics = deriveMetrics(
    { upm: 1000, ascent: 1000, descent: -250, lineGap: 0, avgWidth: 1020 },
    { upm: 1000, ascent: 905, descent: -212, lineGap: 33, avgWidth: 1000 }
  );
  assert.equal(outfitMetrics.sizeAdjust, 102);
  assert.equal(outfitMetrics.ascentOverride, 98);
  assert.equal(outfitMetrics.descentOverride, 24.5);
  assert.equal(outfitMetrics.lineGapOverride, 0);
});

test('CLS Font: web/styles.css contains font fallbacks and metric overrides', () => {
  const rawCss = fs.readFileSync(path.join(__dirname, '../../web/styles.css'), 'utf8');
  const css = rawCss.replace(/\r\n/g, '\n');

  // Verify @font-face declarations
  assert.ok(css.includes("font-family: 'Inter Fallback';"), 'Must have Inter Fallback @font-face');
  assert.ok(css.includes("font-family: 'Outfit Fallback';"), 'Must have Outfit Fallback @font-face');
  assert.ok(css.includes("font-family: 'JetBrains Mono Fallback';"), 'Must have JetBrains Mono Fallback @font-face');

  // Verify CSS metric overrides
  assert.ok(css.includes('size-adjust: 107%;'));
  assert.ok(css.includes('ascent-override: 90%;'));
  assert.ok(css.includes('descent-override: 22.5%;'));
  assert.ok(css.includes('line-gap-override: 0%;'));

  // Verify font variables in :root
  assert.ok(css.includes('--font-sans:'));
  assert.ok(css.includes("'Inter Fallback'"));
  assert.ok(css.includes('--font-display:'));
  assert.ok(css.includes("'Outfit Fallback'"));
  assert.ok(css.includes('--font-mono:'));
  assert.ok(css.includes("'JetBrains Mono Fallback'"));

  // Verify reserved layout dimensions for zero-reflow
  assert.ok(css.includes('min-height: 48px;'), 'Header has fixed min-height 48px');
  assert.ok(css.includes('min-height: 42px;'), 'Tabs container has reserved min-height 42px');
  assert.ok(css.includes('min-height: 38px;'), 'Tab button has reserved min-height 38px');
  assert.ok(css.includes('min-height: 58px;'), 'KPI box has reserved min-height 58px');
  assert.ok(css.includes('min-height: 24px;'), 'KPI large value has reserved min-height 24px');
  assert.ok(css.includes('font-variant-numeric: tabular-nums;'), 'Numeric elements preserve tabular-nums');
});

test('CLS Font: web/index.html includes preconnect, display=swap, and preload', () => {
  const html = fs.readFileSync(path.join(__dirname, '../../web/index.html'), 'utf8');

  assert.ok(html.includes('rel="preconnect" href="https://fonts.googleapis.com"'));
  assert.ok(html.includes('rel="preconnect" href="https://fonts.gstatic.com" crossorigin'));
  assert.ok(html.includes('&display=swap'));
  assert.ok(html.includes('rel="preload" as="style"'));
});
