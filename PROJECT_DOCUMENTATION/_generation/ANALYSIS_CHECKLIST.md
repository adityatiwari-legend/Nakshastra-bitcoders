# ANALYSIS_CHECKLIST — evidence rules for this documentation set

**Purpose:** make every statement in `PROJECT_DOCUMENTATION/` auditable. Core docs cite
`file:line`; this file defines *how* those claims were produced and how to re-verify them.

**Run:** 2026-10-17 · **Method:** read-only inspection of `E:\sistec\LunaSafe` (`main` @ `fa36e99`),
plus the explicitly recorded command executions below. **No pre-existing project file was modified**
(only `PROJECT_DOCUMENTATION/` was created).

---

## 1. Evidence labels (used verbatim in the docs)

| Label | Meaning | Minimum evidence |
| :--- | :--- | :--- |
| `VERIFIED` | Observed directly | line-accurate source read, **or** a command output captured in this run |
| `PARTIALLY VERIFIED` | Some parts observed, some assumed | mixed evidence; both sides stated |
| `INFERRED` | Reasoned, not observed | logic + code context; phrased as inference |
| `NOT FOUND` | Searched and absent | search terms described (e.g. "repo-wide search for auth/secret") |
| `NOT APPLICABLE` | Structurally impossible here | e.g. "database" when storage is files only |
| `PLANNED` / `TODO` | Not present; proposed work | tied to a `T-nn` task ID |

## 2. Verification commands executed (reproducible)

```powershell
# history / identity
git log --format="%H|%ad|%an|%s" --date=iso; git show --stat c3d26dd; git show --stat fa36e99
git status --porcelain

# tests (destructive to outputs/ → restore afterwards)
.\.venv\Scripts\python.exe -m pytest -q                      # 32 passed, 1 warning, 25.28 s
.\.venv\Scripts\python.exe -m pytest -q --ignore=tests\test_main.py -W error
                                                             # located the warning (doc 14 §5)
git checkout -- outputs/lunasafe_hazard_map.pdf outputs/psr_polygons.dbf

# static analysis (baseline for T-07)
$files = (Get-ChildItem -File *.py, tests\*.py).FullName
.\.venv\Scripts\python.exe -m pyflakes @files                # 9 findings (recorded in testing doc §4)

# data facts
Get-Content outputs\hazard_summary.csv                       # 5 rows, sums to grid
# JSON schemas: json.load of outputs/web_data.json (17 keys, 250×250) and landing_sites.json
# GeoTIFF tags: rasterio open + tags()/nodata reads for every outputs/*.tif
```

## 3. Standard review procedure (per source file)

1. Read the file **in full** (no sampling) at a pinned commit; record line ranges used.
2. Cross-check claims against a second source (tests, config, git history, runtime output).
3. For UI claims: cite `web/app.js`/`index.html` line anchors (approximate markers — marked as such).
4. Record defects immediately in the issue format of doc 19 with `file:line` evidence.
5. Never state a number that wasn't read from a file or produced by a command.

## 4. Honesty guard (mirrors `.agents/rules/lunasafe.md`)

- No fabricated accuracy metrics, no invented endpoints/fields/flags.
- Marketing text in `../README.md` is treated as a **claim to check**, not a source.
- Where docs and code disagree, **code + command output win** (and the doc gets corrected —
  see `DOCUMENTATION_CHANGELOG.md` for every correction made).

## 5. Explicit non-actions (scope guard)

- ❌ No edits to `*.py`, `web/*`, `tests/*`, `outputs/*`, `data/*`, `requirements*`, launchers.
- ❌ No commits, no tags, no pushes, no new dependencies installed.
- ✅ Tests **were** executed once for verification, with the two dirty files restored via
  `git checkout -- outputs/…` (documented side effect, see testing doc §2).
- ✅ Only `PROJECT_DOCUMENTATION/` was written (all files untracked at handover).

## 6. Coverage obligations

- Every source module ↔ at least one doc: see `DOCUMENTATION_COVERAGE.md`.
- Every issue ↔ evidence + task: doc 19 + doc 20.
- Every doc ↔ index entry: `../README.md` §5 (link-validated — see
  `DOCUMENTATION_CHANGELOG.md`).

## 7. Re-audit triggers

Re-run §2 commands and update the docs when: a commit lands · dependencies change · a `T-nn`
task completes · the demo dataset changes · before any public release (doc 17 §5 gate).
