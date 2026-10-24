const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const ROOT_DIR = path.resolve(__dirname, '..', '..');

test('3D Site Inspection: web/index.html contains modal & 3D viewport mount', () => {
  const htmlPath = path.join(ROOT_DIR, 'web', 'index.html');
  const html = fs.readFileSync(htmlPath, 'utf-8');
  assert.ok(html.includes('id="siteInspectionModal"'), 'index.html must contain siteInspectionModal');
  assert.ok(html.includes('id="siteInspection3dMount"'), 'index.html must contain siteInspection3dMount');
  assert.ok(html.includes('btnSite3dWireframe'), 'index.html must contain wireframe toggle button');
  assert.ok(html.includes('btnSite3dAutoRotate'), 'index.html must contain auto-rotate toggle button');
  assert.ok(html.includes('btnSiteActivate'), 'index.html must contain site activate button');
});

test('3D Site Inspection: web/styles.css contains modal and 3D viewport rules', () => {
  const cssPath = path.join(ROOT_DIR, 'web', 'styles.css');
  const css = fs.readFileSync(cssPath, 'utf-8');
  assert.ok(css.includes('.site-inspection-modal-overlay'), 'styles.css must style site-inspection modal overlay');
  assert.ok(css.includes('.site-inspection-window'), 'styles.css must style site-inspection window');
  assert.ok(css.includes('.site-3d-canvas-wrap'), 'styles.css must style 3D canvas container');
});

test('3D Site Inspection: web/app.js implements inspection modal engine and 3D mesh generator', () => {
  const appPath = path.join(ROOT_DIR, 'web', 'app.js');
  const app = fs.readFileSync(appPath, 'utf-8');
  assert.ok(app.includes('function openSiteInspectionModal'), 'app.js must define openSiteInspectionModal');
  assert.ok(app.includes('function closeSiteInspectionModal'), 'app.js must define closeSiteInspectionModal');
  assert.ok(app.includes('function initSitePopup3d'), 'app.js must define initSitePopup3d');
  assert.ok(app.includes('function buildSite3dTerrain'), 'app.js must define buildSite3dTerrain');
  assert.ok(app.includes('function activateSiteFromInspection'), 'app.js must define activateSiteFromInspection');
});

test('3D Site Inspection: web/lunar_moon.js enriches marker telemetry for interactive clicks', () => {
  const moonPath = path.join(ROOT_DIR, 'web', 'lunar_moon.js');
  const moon = fs.readFileSync(moonPath, 'utf-8');
  assert.ok(moon.includes('telemetry.is_marker = true'), 'lunar_moon.js must mark clicks as is_marker');
  assert.ok(moon.includes('telemetry.site_id = siteData.id'), 'lunar_moon.js must attach site_id');
});
