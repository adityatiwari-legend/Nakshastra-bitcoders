# `mission_report.py` — Two-Page PDF Mission Report (229 lines)

> Role: renders `outputs/mission_report.pdf` (cover page + metrics/audit page) using matplotlib
  as the PDF backend (`PdfPages`), reading mostly from `outputs/` files.

**Status:** 🟠 renders reliably but **contains hard-coded values** · **Tested by:** none (M-06) ·
**Issues:** **I-14** (hard-coded stats/audit/timezone).

---

## 1. Entry points

| Symbol | Line | Notes |
| :--- | :-: | :--- |
| `generate_pdf_mission_report(output_path=None)` | 22 | main API; default `outputs/mission_report.pdf` |
| `if __name__ == "__main__"` | 227 | CLI: `python mission_report.py` |
| **Web trigger** | `web_server.py:793-798` | first `GET /api/download/mission_report.pdf` generates on demand, then serves it |

Import is **lazy** inside the web handler (`import mission_report` at `:794`) so startup stays fast.

## 2. Report structure

**Page 1 — cover:** title block, dataset provenance banner (`SYNTHETIC DEMO` / `NASA LRO LOLA`),
4-panel mini map (reuses raster arrays), mission metadata, timestamp labelled **"UTC"** (`:71`).

**Page 2 — metrics:** hazard class table (from `hazard_summary.csv` / stats fallback),
PSR area, rule-audit table, key parameters, footer disclaimer.

Data sources, in order of preference (`:40-100`): read `outputs/*` via `io_utils.read_geotiff` →
fall back to **module-level constants** on any exception (`:48` `except Exception: pass`,
`:51-58` fallback stats dict).

## 3. The I-14 defects (all verified in source)

| Location | Defect | Effect |
| :--- | :--- | :--- |
| `:167-177` | rule-audit table rows are literals `"0 / PASSED"` — the validator is never called | the PDF certifies "no violations" even if the last run had some |
| `:51-58` | fallback stats are hard-coded sample numbers | a read failure silently prints plausible fake metrics |
| `:71` | `datetime.now()` labelled "UTC" | wrong timestamp (local time) |
| `:48` | blanket `except Exception: pass` | any read error becomes "defaults look fine" |

**Why it matters:** this PDF is the most judge-facing artifact; a fabricated "0 violations" row
violates the honesty rules (`.agents/rules/lunasafe.md`).

**Fix (T-03):**
1. call `validate.process_validation_pipeline(...)` (or accept an injected `rule_audit` dict) and
   print real `total_violations` + per-rule counts;
2. on missing data, print `N/A` — never numbers;
3. `datetime.now(timezone.utc).strftime(...)`;
4. replace `except Exception: pass` with an error banner in the document.

## 4. Testing gap

No test file exists (M-06). Suggested minimal test (T-08 scope):
```python
def test_report_contains_real_audit(tmp_path, monkeypatch):
    # run pipeline into tmp_path outputs, generate report, then
    # assert the PDF's text layer (via pypdf or pdftotext) contains the real violation count
```
Adding a text-extraction assertion is the only way to catch hard-coded strings.

## 5. Dependencies & behaviour notes

- **matplotlib only** (+ `io_utils`, `config`); no LaTeX, no reportlab — PDF text is vector glyphs.
- Dark theme inherited from `config.FIGURE_STYLE` — the report is intentionally dark.
- Embedded figures are downsampled for page fit; full-resolution map is a separate download.
- Regeneration is cheap (<1 s); it overwrites the file each time it's missing — there's no caching
  beyond "file exists" in the web handler.

## 6. Extending the report

- Add a section: allocate a new page via `pdf.savefig(fig_page3, …)` and pass in the extra data —
  prefer **injecting a dict argument** (e.g. `generate_pdf_mission_report(path, extras={...})`)
  rather than re-reading more files, so the web layer can supply live values.
- Keep every number traceable to either `outputs/` or a function call; no literals (I-14 rule).
