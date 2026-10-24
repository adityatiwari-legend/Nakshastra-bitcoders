#!/usr/bin/env node
/*
 * LunaSafe dependency-free build verification (Phase 5D).
 * Steps: JS syntax -> pyflakes -> index.html local-asset integrity ->
 * script ordering -> no blocking Three.js in <head>.
 * `--lint` runs only the first two steps.
 */
'use strict';

const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const LINT_ONLY = process.argv.includes('--lint');
let failures = 0;
const ok = (m) => console.log('  PASS  ' + m);
const bad = (m) => { failures++; console.error('  FAIL  ' + m); };

console.log('[1/5] JavaScript syntax (node --check)');
for (const f of ['web/app.js', 'web/hazard_core.js', 'web/worker.js', 'web/lunar_moon.js']) {
  const r = spawnSync(process.execPath, ['--check', path.join(ROOT, f)], { encoding: 'utf8' });
  if (r.status === 0) ok(f);
  else bad(f + '\n' + (r.stderr || ''));
}

console.log('[2/5] Python lint (pyflakes)');
const rootPy = fs.readdirSync(ROOT).filter((f) => f.endsWith('.py'));
const testPy = fs.readdirSync(path.join(ROOT, 'tests')).filter((f) => f.endsWith('.py'))
  .map((f) => path.join('tests', f));
const pyFiles = rootPy.concat(testPy);
const { findPython } = require('./run-pytest');
const py = findPython() || 'python';
const pf = spawnSync(py, ['-m', 'pyflakes', ...pyFiles], { cwd: ROOT, encoding: 'utf8' });
if (pf.error) {
  bad('pyflakes could not run: ' + pf.error.message);
} else if (pf.status === 0) {
  ok(pyFiles.length + ' Python files clean');
} else {
  bad('pyflakes reported issues:\n' + (pf.stdout || '') + (pf.stderr || ''));
}

if (LINT_ONLY) {
  console.log(failures ? `\nLINT FAILED (${failures})` : '\nLINT PASSED');
  process.exit(failures ? 1 : 0);
}

console.log('[3/5] index.html local asset integrity');
const html = fs.readFileSync(path.join(ROOT, 'web', 'index.html'), 'utf8');
const refs = [...html.matchAll(/(?:src|href)="(\/[^"]+)"/g)].map((m) => m[1]);
const skip = (p) => p.startsWith('/api') || p === '/favicon.ico' || p.startsWith('/outputs/')
  || p.startsWith('/data/') || p.startsWith('/api');
const localPath = (p) => {
  if (p === '/app.js') return 'web/app.js';
  if (p === '/hazard_core.js') return 'web/hazard_core.js';
  if (p === '/lunar_moon.js') return 'web/lunar_moon.js';
  if (p === '/worker.js') return 'web/worker.js';
  if (p === '/styles.css') return 'web/styles.css';
  if (p.startsWith('/vendor/')) return 'web' + p;
  return null;
};
let assets = 0;
for (const p of [...new Set(refs)]) {
  if (skip(p)) continue;
  const rel = localPath(p);
  if (!rel) { bad('unmapped local reference ' + p); continue; }
  assets++;
  if (fs.existsSync(path.join(ROOT, rel))) ok(p + ' -> ' + rel);
  else bad('missing ' + p + ' (expected ' + rel + ')');
}
// worker.js + hazard_core.js are fetched at runtime (not always in HTML)
for (const rel of ['web/worker.js', 'web/hazard_core.js']) {
  if (fs.existsSync(path.join(ROOT, rel))) ok(rel + ' present');
  else bad('missing ' + rel);
}
ok(assets + ' HTML local references verified');

console.log('[4/5] critical script ordering');
const hi = html.indexOf('<script src="/hazard_core.js">');
const ai = html.indexOf('<script src="/app.js">');
if (hi !== -1 && ai !== -1 && hi < ai) ok('hazard_core.js before app.js');
else bad('hazard_core.js must appear before app.js in index.html');

console.log('[5/5] lazy Three.js (not in <head>)');
const head = html.slice(0, html.indexOf('</head>'));
if (head.includes('/vendor/three.min.js')) bad('blocking three.min.js found in <head>');
else ok('three.js is lazy-loaded (absent from <head>)');

console.log(failures ? `\nBUILD FAILED (${failures} issue(s))` : '\nBUILD PASSED');
process.exit(failures ? 1 : 0);
