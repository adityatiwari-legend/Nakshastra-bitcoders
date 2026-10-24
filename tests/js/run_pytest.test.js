/**
 * Tests for scripts/run-pytest.js (cross-platform pytest runner).
 */
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const { spawnSync } = require('node:child_process');

const { findPython, DEFAULT_CANDIDATES } = require('../../scripts/run-pytest');

test('run-pytest: candidate order matches specification', () => {
  assert.deepEqual(DEFAULT_CANDIDATES, [
    '.venv/Scripts/python.exe',
    '.venv/bin/python',
    'python3',
    'python',
  ]);
});

test('run-pytest: findPython finds active python on system', () => {
  const py = findPython();
  assert.ok(py, 'findPython should resolve an interpreter');

  const check = spawnSync(py, ['--version'], { encoding: 'utf8' });
  assert.equal(check.status, 0);
  assert.match(check.stdout + check.stderr, /Python 3\./);
});

test('run-pytest: resolves mock venv relative to rootDir before fallback', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'orbisluna-test-'));
  try {
    const mockVenvScripts = path.join(tmpDir, '.venv', 'Scripts');
    fs.mkdirSync(mockVenvScripts, { recursive: true });
    const mockExe = path.join(mockVenvScripts, 'python.exe');
    fs.writeFileSync(mockExe, 'dummy');

    const resolved = findPython(['.venv/Scripts/python.exe', 'python'], tmpDir);
    assert.equal(resolved, mockExe);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test('run-pytest: resolves mock POSIX venv relative to rootDir before system python', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'orbisluna-test-posix-'));
  try {
    const mockVenvBin = path.join(tmpDir, '.venv', 'bin');
    fs.mkdirSync(mockVenvBin, { recursive: true });
    const mockBin = path.join(mockVenvBin, 'python');
    fs.writeFileSync(mockBin, 'dummy');

    const resolved = findPython(['.venv/bin/python', 'python'], tmpDir);
    assert.equal(resolved, mockBin);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test('run-pytest: CLI forwards flags to pytest (tested with --version)', () => {
  const root = path.resolve(__dirname, '../..');
  const runner = path.join(root, 'scripts', 'run-pytest.js');
  const result = spawnSync('node', [runner, '--version'], {
    cwd: root,
    encoding: 'utf8',
  });
  assert.equal(result.status, 0);
  assert.match(result.stdout + result.stderr, /pytest/i);
});
