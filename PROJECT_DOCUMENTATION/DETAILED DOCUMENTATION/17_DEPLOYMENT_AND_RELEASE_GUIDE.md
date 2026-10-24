# 17 — Deployment and Release Guide

> **Reality check (VERIFIED):** LunaSafe has no deployment pipeline — no Dockerfile, no CI/CD
> workflow, no cloud config, no packaging metadata (`pyproject.toml`/`setup.py` absent). The
> supported "deployment" is: *a laptop running `web_server.py` on localhost for a demo*. This
> document documents that reality, then gives repeatable recipes for the next-best options and a
> release checklist.

---

## 1. Deployment options matrix

| Option | How | Effort | Fit | Notes |
| :--- | :--- | :-: | :--- | :--- |
| **A. Localhost demo (current, supported)** | `run_website.bat` → `http://localhost:8050` | 0 | hackathon judging, offline demo | fully offline except optional CDN fonts/KaTeX |
| **B. LAN demo for multiple viewers** | start with `--host 0.0.0.0` (requires code change, `web_server.py:840` binds `""` already → it *is* LAN-exposed today) | 0 ⚠ | projector + judge laptops | **first apply hardening T-13** — see doc 16 |
| **C. Two-lane demo** | one terminal runs the CLI, one runs the server; swap `outputs/` between runs | low | showing both entry points | restart server after swapping outputs |
| **D. Frozen demo VM / second laptop** | clone repo, run §2 checklist offline | low | travel/hackathon risk mitigation | pre-seed `outputs/` + `data/` so no run is needed on site |
| **E. Containerise** | write a `Dockerfile` (python:3.13-slim + `requirements.txt`, `EXPOSE 8050`) | medium | future | **does not exist yet**; matplotlib `Agg` is already headless-safe (`config.py:148-151`) |
| **F. Static hosting of the UI alone** | not viable | — | — | the console requires `/api/*`; `index.html`+`app.js` without a server show zeros |
| **G. PaaS (Fly/Render/Railway)** | as E plus persistent disk for `outputs/` | high | future | bundle is per-process; **one instance only** (in-memory `RASTER_CACHE` + shared `outputs/`), no auth ⇒ must not be public (doc 16) |

**Not supported:** multi-user/serverless/autoscale — architecture is single-process, file-mediated
(doc 05 §10).

---

## 2. Repeatable offline demo setup (Option D checklist)

Run on the prepared machine the night before:

```powershell
git clone https://github.com/kushbansal2005/ORBISLUNA.git
cd ORBISLUNA
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# ensure the demo artifacts are current
.\.venv\Scripts\python.exe main.py --force-synthetic
.\.venv\Scripts\python.exe export_web_data.py

# verify
.\.venv\Scripts\python.exe -m pytest -q --ignore=tests\test_main.py
run_website.bat        # then walk the 90-second script in doc 13 §4.4
```

Pre-flight items:
- [ ] `.venv` + all 10 pins installed (no network needed afterwards)
- [ ] `data/synthetic_dem.tif` + `synthetic_psr.tif` present (fallback dataset)
- [ ] `data/lola_*` present **iff** you want the REAL badge — otherwise rename/move them for a synthetic demo
- [ ] `outputs/` has the 15 artifacts + `web_data.json` matching the raster grid (doc 15 §11 one-liner)
- [ ] Chrome/Edge installed with WebGL enabled (3D tab)
- [ ] Port 8050 free; firewall rule allowing `python.exe` **only if** Option B is intended
- [ ] Presentation laptop battery/charger, and a *second* way to show `outputs/*.png` in case of disaster

---

## 3. What "release" means for this project

| Artifact type | Where it lives | Release action |
| :--- | :--- | :--- |
| Source | git branch `main` (2 commits as of 2026-10-17) | commit + tag (see §4) |
| Environment | `requirements.txt` (pinned) | freeze any new deps into **both** requirement files until `requirement.txt` is deleted (Issue I-16) |
| Data | `data/` (committed inputs) | keep JP2 provenance in `data/DOWNLOAD_INSTRUCTIONS.md` |
| Products | `outputs/` (committed artifacts) | regenerate & commit, or stop tracking (team decision T-14) |
| Docs | `PROJECT_DOCUMENTATION/` | deliver as-is; regenerate via `_generation/` |
| Report | `outputs/mission_report.pdf` | rebuild before sharing — contains known hard-coded text (Issue I-14) |

There are **no version numbers anywhere** (no `__version__`, no tags, no CHANGELOG). For a
hackathon submission that is acceptable; before any public release, tag `v0.1.0` and add a
`CHANGELOG.md` (T-17).

---

## 4. Git release procedure (as the repo works today)

```powershell
# 1. confirm a clean, passing state
git status
git log --oneline -5
.\.venv\Scripts\python.exe -m pytest -q

# 2. decide about regenerated artifacts (doc 06 §3)
git diff --stat outputs/

# 3. stage explicitly — never `git add -A` (it picks up __pycache__ churn)
git add PROJECT_DOCUMENTATION/   # or the specific files you changed
git commit -m "docs: <what changed>"

# 4. tag for a release milestone
git tag -a v0.1.0 -m "hackathon snapshot: pipeline + Mission Control console"
git push origin main --tags
```

**Branch model:** none defined — everything lands on `main`. If two people start editing in
parallel (the intended team), adopt short-lived branches:
`git switch -c fix/audit-key-rule4` → commit → open PR → one reviewer → merge.
Document that convention in `18_GIT_WORKFLOW_AND_CHANGE_HISTORY.md` once agreed.

---

## 5. Pre-release quality gate (recommended order)

| # | Gate | Command | Pass criteria |
| :-: | :--- | :--- | :--- |
| 1 | Lint | `python -m pyflakes *.py tests\*.py` | no output (tool already installed, undeclared — I-16) |
| 2 | Unit+integration tests | `python -m pytest -q` | `32 passed` |
| 3 | Artifact restore decision | `git checkout -- outputs/` or commit intentionally | tree clean |
| 4 | Bundle freshness | doc 15 §11 comparison one-liner | bundle grid == raster grid |
| 5 | Rule audit | `curl -X POST localhost:8050/api/audit` | `"status":"PASSED"` *(caveat: Rule 4 key bug I-03)* |
| 6 | Security sanity | doc 16 §5 items 1–4 at minimum | loopback bind, no traversal, no upload route |
| 7 | Docs sync | link check over `PROJECT_DOCUMENTATION/` | no broken relative links |

---

## 6. Running as a "service" (optional, Windows)

For a kiosk-style demo, keep it simple — no NSSM/Task Scheduler needed:

```powershell
# terminal stays open (recommended: you see the log)
.\.venv\Scripts\python.exe web_server.py

# detached (PowerShell 7+)
Start-Process -WindowStyle Hidden ".venv\Scripts\python.exe" -ArgumentList "web_server.py"
```

Startup order matters only for correctness of the first paint: `outputs/` must exist *before* the
server starts, otherwise `/api/recalculate` 400s until a run (doc 13 §4.2).

Reverse proxy (only if someone insists on port 80): nginx/caddy in front, but **do not** expose the
raw app publicly — no auth exists (doc 16 SEC-03).

---

## 7. Post-release monitoring & support

| Need | Available today | Gap |
| :--- | :--- | :--- |
| Liveness | `GET /health` every 2.5 s from the UI | no external probe |
| Failure signal | UI badges (`ONLINE`/`BUSY`), log pane | no alerting, no log file (stdout only) |
| Data integrity | 9-rule audit endpoint | always-green Rule 4 (I-03) |
| Bug reports | GitHub issues | none wired for this repo |
| Version identification | none | add `GET /api/version` (git SHA) as part of T-17 |

---

## 8. Common release mistakes to avoid

1. **Committing a stale `web_data.json`** while `outputs/*.tif` changed → UI shows old geometry
   (this is exactly the current state, Issue I-06).
2. **Shipping the report with "0 / PASSED" hard-coded** (I-14) — regenerate only after fixing
   `mission_report.py`, or remove the page-2 audit table.
3. **Running `git add -A`** → re-commits 22 `.pyc` binaries (doc 06 §3).
4. **Revealing the console on open Wi-Fi** — it is unauthenticated and LAN-bound (doc 16).
5. **Claiming real-PSR validation numbers** when `data/independent_psr_reference.tif` is absent —
   the API correctly returns `null`; keep that honesty in slides.
