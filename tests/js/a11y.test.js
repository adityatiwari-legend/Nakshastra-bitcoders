const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

test('A11y: recalculation delta string formatting', () => {
  function formatA11yDelta(safeKm2, baselineSafeKm2) {
    const dSafe = safeKm2 - baselineSafeKm2;
    const safeDirection = dSafe >= 0 ? `up ${Math.abs(dSafe).toFixed(2)} km²` : `down ${Math.abs(dSafe).toFixed(2)} km²`;
    const deltaText = Math.abs(dSafe) < 0.01 ? 'unchanged' : safeDirection;
    return `Recalculation: Safe area ${safeKm2.toFixed(1)} km², ${deltaText} from baseline.`;
  }

  assert.equal(
    formatA11yDelta(12.4, 13.2),
    'Recalculation: Safe area 12.4 km², down 0.80 km² from baseline.'
  );
  assert.equal(
    formatA11yDelta(14.5, 13.2),
    'Recalculation: Safe area 14.5 km², up 1.30 km² from baseline.'
  );
  assert.equal(
    formatA11yDelta(13.204, 13.2),
    'Recalculation: Safe area 13.2 km², unchanged from baseline.'
  );
});

test('A11y: layer cycle cycling modulo navigation', () => {
  const layers = ['hazard', 'hillshade', 'slope', 'roughness', 'psr'];
  function cycleLayer(currentIndex, direction) {
    if (direction === 'next') return (currentIndex + 1) % layers.length;
    if (direction === 'prev') return (currentIndex - 1 + layers.length) % layers.length;
    return currentIndex;
  }

  assert.equal(cycleLayer(0, 'next'), 1);
  assert.equal(cycleLayer(4, 'next'), 0); // wrap forward
  assert.equal(cycleLayer(0, 'prev'), 4); // wrap backward
  assert.equal(cycleLayer(3, 'prev'), 2);
});

test('A11y: inspector step boundary clamping', () => {
  const width = 100;
  const height = 80;
  function stepInspector(pixel, key) {
    let col = pixel.col;
    let row = pixel.row;
    if (key === 'ArrowLeft') col = Math.max(0, col - 1);
    if (key === 'ArrowRight') col = Math.min(width - 1, col + 1);
    if (key === 'ArrowUp') row = Math.max(0, row - 1);
    if (key === 'ArrowDown') row = Math.min(height - 1, row + 1);
    return { col, row };
  }

  assert.deepEqual(stepInspector({ col: 0, row: 50 }, 'ArrowLeft'), { col: 0, row: 50 });
  assert.deepEqual(stepInspector({ col: 99, row: 50 }, 'ArrowRight'), { col: 99, row: 50 });
  assert.deepEqual(stepInspector({ col: 50, row: 0 }, 'ArrowUp'), { col: 50, row: 0 });
  assert.deepEqual(stepInspector({ col: 50, row: 79 }, 'ArrowDown'), { col: 50, row: 79 });
  assert.deepEqual(stepInspector({ col: 50, row: 50 }, 'ArrowRight'), { col: 51, row: 50 });
});

test('A11y: styles.css contains required accessibility tokens', () => {
  const css = fs.readFileSync(path.join(__dirname, '../../web/styles.css'), 'utf8');
  assert.ok(css.includes('.sr-only'), 'Must include .sr-only class');
  assert.ok(css.includes(':focus-visible'), 'Must include :focus-visible rules');
  assert.ok(css.includes('prefers-reduced-motion'), 'Must include prefers-reduced-motion media query');
  assert.ok(css.includes('.shortcuts-modal-overlay'), 'Must include shortcuts modal classes');
});

test('A11y: index.html contains canvas a11y roles and live regions', () => {
  const html = fs.readFileSync(path.join(__dirname, '../../web/index.html'), 'utf8');
  assert.ok(html.includes('id="a11yLiveAnnouncer"'), 'Must have aria-live announcer');
  assert.ok(html.includes('id="mapCanvas"'), 'Must have mapCanvas');
  assert.ok(html.includes('role="application"'), 'Must have application role on canvas');
  assert.ok(html.includes('id="shortcutsDialog"'), 'Must have shortcutsDialog modal');
  assert.ok(html.includes('role="dialog"'), 'shortcutsDialog must have role dialog');
});
