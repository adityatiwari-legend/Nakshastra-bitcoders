const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const ROOT_DIR = path.resolve(__dirname, '..', '..');
const EMOJI_REGEX = /[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]|[\u{1F000}-\u{1F02F}]|[\u{1F0A0}-\u{1F0FF}]|[\u{1F100}-\u{1F64F}]|[\u{1F680}-\u{1F6FF}]|[\u{2300}-\u{23FF}]|[\u{2B50}-\u{2B55}]|[\u{203C}-\u{2049}]/u;

test('Lucide Icons: vendor library exists and is non-empty', () => {
  const vendorPath = path.join(ROOT_DIR, 'web', 'vendor', 'lucide.min.js');
  assert.ok(fs.existsSync(vendorPath), 'web/vendor/lucide.min.js should exist');
  const stat = fs.statSync(vendorPath);
  assert.ok(stat.size > 100000, 'lucide.min.js should be the full vendor bundle');
});

test('Lucide Icons: web/index.html loads Lucide and contains vector icon hooks', () => {
  const indexPath = path.join(ROOT_DIR, 'web', 'index.html');
  const indexHtml = fs.readFileSync(indexPath, 'utf-8');
  assert.ok(indexHtml.includes('vendor/lucide.min.js'), 'index.html must load lucide.min.js');
  assert.ok(indexHtml.includes('data-lucide="moon"'), 'index.html should have moon icon');
  assert.ok(indexHtml.includes('data-lucide="satellite"'), 'index.html should have satellite icon');
  assert.ok(indexHtml.includes('data-lucide="navigation"'), 'index.html should have navigation icon');
  assert.ok(indexHtml.includes('data-lucide="target"'), 'index.html should have target icon');
});

test('Lucide Icons: web/styles.css contains vector icon styling tokens', () => {
  const cssPath = path.join(ROOT_DIR, 'web', 'styles.css');
  const css = fs.readFileSync(cssPath, 'utf-8');
  assert.ok(css.includes('.lucide') || css.includes('[data-lucide]'), 'styles.css must style lucide vector icons');
  assert.ok(css.includes('stroke-width'), 'styles.css should specify stroke width for crisp vector icons');
});

test('Lucide Icons: web/app.js initializes and observes Lucide', () => {
  const appPath = path.join(ROOT_DIR, 'web', 'app.js');
  const appJs = fs.readFileSync(appPath, 'utf-8');
  assert.ok(appJs.includes('initLucideSystem'), 'app.js should define initLucideSystem');
  assert.ok(appJs.includes('createIcons'), 'app.js should call createIcons');
});

test('Clean UI: zero emojis in web/index.html, web/styles.css, web/app.js', () => {
  const targets = ['web/index.html', 'web/styles.css', 'web/app.js'];
  for (const rel of targets) {
    const fullPath = path.join(ROOT_DIR, rel);
    const content = fs.readFileSync(fullPath, 'utf-8');
    const lines = content.split('\n');
    const violations = [];
    lines.forEach((line, idx) => {
      if (EMOJI_REGEX.test(line)) {
        violations.push(`Line ${idx + 1}: ${line.trim().slice(0, 80)}`);
      }
    });
    assert.equal(violations.length, 0, `Found emojis in ${rel}:\n${violations.join('\n')}`);
  }
});
