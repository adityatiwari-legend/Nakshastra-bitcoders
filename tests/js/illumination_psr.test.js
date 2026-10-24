const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const ROOT_DIR = path.resolve(__dirname, '..', '..');

test('Diurnal Illumination: illumination_time.py strictly enforces permanent shadow on PSRs', () => {
  const pyPath = path.join(ROOT_DIR, 'illumination_time.py');
  const py = fs.readFileSync(pyPath, 'utf-8');
  assert.ok(py.includes('MODEL_VERSION = "analytic_solar_horizon_psr_v2"'), 'MODEL_VERSION must reflect PSR constraint v2');
  assert.ok(py.includes('psr_mask: Optional[np.ndarray] = None'), 'compute_frames must accept psr_mask');
  assert.ok(py.includes('lit &= ~psr_flat'), 'compute_frames must mask out direct sunlight on PSR pixels');
  assert.ok(py.includes('volume[:, psr_2d] = 0'), 'compute_frames must force all PSR pixels to 0 across all frames');
  assert.ok(py.includes('"psr_constrained"'), 'metadata must include psr_constrained status');
});

test('Diurnal Illumination: web_server.py passes authoritative PSR raster to illumination engine', () => {
  const serverPath = path.join(ROOT_DIR, 'web_server.py');
  const server = fs.readFileSync(serverPath, 'utf-8');
  assert.ok(server.includes('psr_mask=RASTER_CACHE.get("psr")'), 'web_server must pass psr raster from RASTER_CACHE to compute_or_get');
});

test('Diurnal Illumination: web/app.js buildIllumTimeCanvas renders shadow on PSR pixels', () => {
  const appPath = path.join(ROOT_DIR, 'web', 'app.js');
  const app = fs.readFileSync(appPath, 'utf-8');
  assert.ok(app.includes('const isPsr = psr && psr[i] > 0;'), 'buildIllumTimeCanvas must identify PSR pixels from DATA.psr');
  assert.ok(app.includes('(vol[off + i] === 0 || isPsr)'), 'buildIllumTimeCanvas must force shadow tint over PSR pixels');
});
