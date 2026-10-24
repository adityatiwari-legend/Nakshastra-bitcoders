#!/usr/bin/env node
/**
 * Cross-platform pytest runner (zero dependencies).
 *
 * Picks a Python interpreter in priority order:
 *   1. .venv/Scripts/python.exe  (Windows venv)
 *   2. .venv/bin/python           (POSIX venv)
 *   3. python3                    (system, POSIX convention)
 *   4. python                     (system, Windows convention)
 *
 * Runs `<python> -m pytest tests -q` and forwards any extra CLI args.
 * Exits with the child process's exit code so `npm test` propagates failures.
 */
'use strict';

const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..');

const DEFAULT_CANDIDATES = [
  '.venv/Scripts/python.exe',
  '.venv/bin/python',
  'python3',
  'python',
];

/**
 * Returns the first working Python interpreter path, or null.
 * @param {string[]} [candidates]
 * @param {string} [rootDir]
 */
function findPython(candidates = DEFAULT_CANDIDATES, rootDir = ROOT) {
  for (const candidate of candidates) {
    if (candidate.includes('/') || candidate.includes('\\')) {
      const fullPath = path.isAbsolute(candidate) ? candidate : path.join(rootDir, candidate);
      if (fs.existsSync(fullPath)) {
        return fullPath;
      }
      continue;
    }

    try {
      const probe = spawnSync(candidate, ['--version'], {
        stdio: 'ignore',
        windowsHide: true,
      });
      if (probe.status === 0) {
        return candidate;
      }
    } catch {
      // Ignore spawn errors for missing commands
    }
  }
  return null;
}

function runPytest(args = process.argv.slice(2), rootDir = ROOT) {
  const py = findPython(DEFAULT_CANDIDATES, rootDir);
  if (!py) {
    console.error('ERROR: No Python interpreter found.');
    console.error('Searched: ' + DEFAULT_CANDIDATES.join(', '));
    process.exit(1);
  }

  const result = spawnSync(py, ['-m', 'pytest', 'tests', '-q', ...args], {
    cwd: rootDir,
    stdio: 'inherit',
  });

  if (result.error) {
    console.error('[run-pytest] Failed to launch pytest:', result.error.message);
    process.exit(1);
  }

  process.exit(result.status ?? 1);
}

if (require.main === module) {
  runPytest();
}

module.exports = {
  DEFAULT_CANDIDATES,
  findPython,
  runPytest,
};
