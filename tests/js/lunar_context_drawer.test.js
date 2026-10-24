const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const ROOT_DIR = path.resolve(__dirname, '..', '..');

test('Lunar Context Drawer: Close button and DOM setup', () => {
  const html = fs.readFileSync(path.join(ROOT_DIR, 'web', 'index.html'), 'utf-8');

  assert.ok(html.includes('id="lunarContextDrawer"'), 'index.html must contain lunarContextDrawer');
  assert.ok(html.includes('id="btnDrawerClose"'), 'index.html must contain btnDrawerClose');
  assert.ok(html.includes('closeLunarContextDrawer'), 'index.html must invoke closeLunarContextDrawer on click');
});

test('Lunar Context Drawer: CSS styling and visibility rules', () => {
  const css = fs.readFileSync(path.join(ROOT_DIR, 'web', 'styles.css'), 'utf-8');

  assert.ok(css.includes('.lunar-context-drawer'), 'styles.css must style .lunar-context-drawer');
  assert.ok(css.includes('.drawer-close-btn'), 'styles.css must style .drawer-close-btn');
  assert.ok(css.includes('.drawer-close-btn:hover'), 'styles.css must provide hover styling for .drawer-close-btn');
  assert.ok(css.includes('pointer-events: none;'), 'styles.css must disable pointer events when closed');
});

test('Lunar Context Drawer: JS function and event listeners in app.js', () => {
  const app = fs.readFileSync(path.join(ROOT_DIR, 'web', 'app.js'), 'utf-8');

  assert.ok(app.includes('function closeLunarContextDrawer('), 'app.js must define closeLunarContextDrawer');
  assert.ok(app.includes('drawer.classList.remove(\'open\')'), 'closeLunarContextDrawer must remove open class');
  assert.ok(app.includes('btnDrawerClose'), 'app.js must attach event listener to btnDrawerClose');
});
