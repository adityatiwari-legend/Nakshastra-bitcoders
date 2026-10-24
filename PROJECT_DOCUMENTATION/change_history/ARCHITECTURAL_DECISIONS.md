# Architectural Decisions (A1–A10)

**Canonical source of the decision IDs:** core doc
[`../05_SYSTEM_ARCHITECTURE.md`](../05_SYSTEM_ARCHITECTURE.md) §9 — this file is the extended
record (context / alternatives / consequences) for the same IDs. **New decisions get the next
free ID (`A11`, `A12`, …) — never renumber.**

> Governance (two-person team): a change to a 🔴 decision (see §3) needs (a) a written entry
> appended below, (b) doc 05 §9 updated, (c) impact scan in `MIGRATION_NOTES.md`, (d) agreement
> of both members. Anything less is a drive-by change (rule echoed in doc 22).

---

## A1 — No web framework; Python stdlib `http.server`
- **Context:** hackathon timeline, zero-extra-deps goal (`.agents/rules/lunasafe.md`).
- **Chosen:** `web_server.py:22` uses `ThreadingHTTPServer` + a hand-rolled `route` dispatch.
- **Alternatives:** FastAPI/Flask (would buy routing, validation, middleware, test clients).
- **Consequences:** ✅ no dependency, runs in the pinned venv as-is; ❌ no request validation
  helpers, no CSRF protection, manual multipart/CORS, 0 test infrastructure (T-19 if this grows).

## A2 — All thresholds live in `config.py`, imported as a module and mutated at runtime
- **Context:** live sliders must re-classify without restarting.
- **Chosen:** `web_server.py:341-362` writes request values straight into `config.*`.
- **Alternatives:** immutable per-request params (thread-safe, but every helper would need
  plumbing), external config file (I/O on each slider).
- **Consequences:** ✅ 3-line hot path, single source for CLI+web; ❌ process-wide hidden state —
  **Issue I-11**, race-prone under concurrent requests, subprocesses don't see the values (**I-04**).

## A3 — Science core is arrays-in/arrays-out
- **Context:** testability and reuse between CLI, web fast path, and notebooks.
- **Chosen:** e.g. `hazard.classify_hazard_surface(...)` takes ndarrays (`hazard.py:61-67`).
- **Consequences:** ✅ hermetic unit tests (32-test suite is only possible because of this);
  ❌ the web layer must hold whole rasters in RAM (`RASTER_CACHE`), bounding resolution (I-02
  territory) and keeping everything single-tenant.

## A4 — Web fast path re-derives hazard from cached terrain
- **Context:** sliders must feel instant (≲100 ms).
- **Chosen:** `web_server.py:448-459` reuses cached slope/roughness; only classification reruns.
- **Consequences:** ✅ ~ms latency; ❌ by design, moving a slider cannot change terrain metrics —
  document this to users (feature doc 07 does).

## A5 — Full pipeline = separate subprocess, not in-process call
- **Context:** long-running work must not block the HTTP thread; crash isolation.
- **Chosen:** `web_server.py:373-381` `Popen([PYTHON_BIN, "main.py", ...])`.
- **Consequences:** ✅ server stays responsive, logs streamable; ❌ child re-reads `config.py`
  from disk → slider/proxy parameters silently lost (**I-04**). Fix: forward a params JSON.

## A6 — Synthetic fallback instead of hard failure
- **Context:** the demo must never show a stack trace.
- **Chosen:** `io_utils.py:392-404` falls back to the synthetic DEM on missing/bad `--dem`.
- **Consequences:** ✅ always-on demo; ❌ a typo'd path silently produces synthetic numbers —
  mitigated only by provenance banners (keep them loud, `active_dataset`).

## A7 — Class 4 `Shadowed-Unknown` is its own class
- **Context:** project rule — unknown must never be presented as safe.
- **Chosen:** `hazard.py:111-113`; enforced downstream by audit rule 8.
- **Consequences:** ✅ central safety idea of the product; ❌ a real fraction of terrain stays
  unclassified until I-07 (shadow term always 0) is fixed.

## A8 — Auditor re-implements classifier logic (independent implementation)
- **Context:** a validator that calls the code under test proves nothing.
- **Chosen:** `validate.py:103-137` re-derives expectations from `config`.
- **Consequences:** ✅ genuine independence (mutation test TC-AUTO-30 passes); ❌ two
  implementations can **drift** — the web rule-4 key bug (**I-03**) is exactly this failure class.
  Mitigation: TC-PLAN-04 pins producer/consumer key sets together.

## A9 — Frontend: one 4.5k-line JS file, no build step
- **Context:** zero toolchain (no node), open-from-server simplicity.
- **Chosen:** `web/app.js` (≈4 560 L) + `index.html` + vendored three.js.
- **Consequences:** ✅ runs anywhere, vendorable/offline; ❌ hard to test (T-16), implicit
  init order, `innerHTML`-heavy surface (SEC-04-adjacent), no tree-shaking. Migration path:
  `MIGRATION_NOTES.md` §5.

## A10 — Artifacts (`outputs/`, `data/`) are committed to git
- **Context:** judges/demo users get results without running anything.
- **Chosen:** 24 files under `outputs/` + 10.5 MB JP2 tracked; no root `.gitignore`.
- **Consequences:** ✅ zero-setup demo, reviewable results; ❌ binary churn in every diff,
  tests rewrite tracked files (doc 14 §4), and staleness bugs become *committable* (**I-06** —
  `web_data.json` vs rasters). Decision required: track-with-script or ignore (T-14, doc 18 §5).

---

## §3 Decision classes

| Class | Members | Change rule |
| :--- | :--- | :--- |
| 🔴 **Safety/science semantics** | A3, A7, A8 (+ CRS guard, class IDs, honesty rules) | both members + tests + docs 05/19/22 |
| 🟠 **Contracts** | A2, A4, A5, A10 (+ REST shapes, artifact names) | docs 09/10 + `api_documentation/` + migration checklist |
| 🟢 **Implementation detail** | A1, A6, A9 | normal code review |

## §4 Pending decisions (parked for the team — not taken yet)

| ID (proposed) | Question | Trigger |
| :--- | :--- | :--- |
| A11 | Track or ignore `outputs/` in git? | T-14 |
| A12 | Keep stdlib server or adopt FastAPI? | T-19 |
| A13 | Single-user local-only vs LAN demo (auth, bind address)? | SEC-02/03 |
| A14 | Report: fix in place or regenerate-only (drop hard-coded stats)? | I-14 |

*Append the chosen option here when decided; give it the next permanent ID.*
