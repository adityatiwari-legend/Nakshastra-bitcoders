# KNOWLEDGE_GAPS — what nobody can answer from the repository

Everything below survived a full documentation pass (2026-10-17) and still has **no in-repo
answer**. Labels: `NOT FOUND` (searched, absent) · `UNTESTED` (possible, never exercised here) ·
`DECISION` (team must choose). When a gap closes, move the entry to the relevant doc and note the
date here.

---

## A. Data provenance

| # | Gap | Label | Notes / first move |
| :-: | :--- | :--- | :--- |
| A1 | **Which downloader URL is authoritative:** `data/DOWNLOAD_INSTRUCTIONS.md:23` vs `web_server.py:633` disagree (Issue **M-03**). Neither was fetched during this run. | UNTESTED | run `POST /api/download-lola` once on a network-enabled machine; keep the winner, delete the loser |
| A2 | **Exact provenance of `data/ldem_75s_240m.jp2`** (product ID, version, retrieval date) — only inferable from the filename (`ldem_75s` = 75 arc-sec LOLA) | NOT FOUND | record it in `DOWNLOAD_INSTRUCTIONS.md` |
| A3 | **How `data/lola_psr_mask.tif` was produced.** Code treats it as ground truth for metrics, but its generating script is absent — `prepare_lola_dataset.py` builds the same *depth<−900 m* heuristic (**I-08**), so it may be that heuristic, not an atlas | NOT FOUND / INFERRED | either find the source or label the file "heuristic"; blocks honest P/R UI (task T-23) |
| A4 | Does the LOLA ingest path still work end-to-end today (download → convert → align)? | UNTESTED | I-15 hard-codes `e:\sistec\LunaSafe`; try it before a demo |

## B. Product intent

| # | Gap | Label | Notes |
| :-: | :--- | :-: | :--- |
| B1 | **Which numbers in `README.md`/`PROJECT_SPECIFICATION.md` were ever *measured* vs written for the pitch** (e.g. "60 FPS", "0 violations across 40 000 pixels", judge-tour duration) | PARTIALLY VERIFIED | audit list in doc 19 §E; a tour UI exists (`tourState`/`tourStepBadge` in `app.js`) but was never run in this pass |
| B2 | Intended meaning of `suitability_pct` for stakeholders (score is internal weighting 0.35/0.30/0.20/0.15 — no external definition) | INFERRED | document the formula in UI copy if shown to judges |
| B3 | Whether `scikit-image` and `pandas` were **planned** for something (both pinned, zero imports — **I-16**) | NOT FOUND | ask original author; else drop the pins (T-16) |
| B4 | Why `dashboard.html` + `build_interactive_ui.py` still ship (superseded by `web/`; no importer found) | INFERRED (legacy) | decide: delete or freeze (doc 06, T-14-adjacent) |

## C. Operations & process

| # | Gap | Label | Notes |
| :-: | :--- | :-: | :--- |
| C1 | **No LICENSE file anywhere** → reuse/distribution terms for this repo are undefined (also matters for the NASA-derived data) | NOT FOUND | add a LICENSE as an explicit team decision |
| C2 | Deployment target for judges (local laptop only? LAN? hosted?) — `web_server.py` binds all interfaces (**SEC-02**) but nothing is published | DECISION | doc 17 §1 options E… |
| C3 | Which requirement file is canonical (`requirements.txt` vs `requirement.txt`) | DECISION | recommend `requirements.txt` (T-16) |
| C4 | Where the `outputs/` binaries should live long-term (git vs release assets) | DECISION | T-14 |
| C5 | Original author's environment (OS/venv path assumptions: `prepare_lola_dataset.py:15`, `README` `file:///e:/…` links) | INFERRED: Windows, E: drive | portable-path work is T-18 |
| C6 | No issue tracker/PR history exists — rationale for past choices is only reconstructable from this folder | NOT FOUND | start GitHub issues; reference `I-`/`T-` IDs |

## D. Engineering unknowns (nice to resolve during M-B)

| # | Gap | Label | Notes |
| :-: | :--- | :-: | :--- |
| D1 | Exact source of every future `pytest` warning (current baseline: 1, located — doc 14 §5) | ✅ closed 2026-10-17 | re-check on dep upgrades |
| D2 | Behaviour of `psr_polygons_bundle.zip` consumers (built on demand; nobody has verified the zip contents round-trip) | UNTESTED | add to TC-MAN-09 |
| D3 | Whether `ThreadingHTTPServer` + `config` mutation races under two concurrent browsers (I-11 is logical; race is untested) | UNTESTED | T-06 + T-08 |
| D4 | Frontend behaviour when `web_data.json` is newer than RAM cache after a CLI-only run (server serves stale `RASTER_CACHE`?) | UNTESTED | part of T-10; restart server after CLI runs |

## E. How to close a gap

1. Reproduce/decide → 2. capture the result in the owning doc (labels upgraded to VERIFIED) →
3. add a regression check if it's code → 4. strike the row from this file with a date.
