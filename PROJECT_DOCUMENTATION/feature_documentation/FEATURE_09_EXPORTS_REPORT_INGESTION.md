# Feature — Exports, Mission Report & NASA Data Ingestion

**IDs:** F-09 · **Status:** 🟠 exports solid; report has hard-coded values · **Owner:** `mapping.py`, `mission_report.py`, `web_server.py:601-864`, `prepare_lola_dataset.py`
**Issues:** **I-14** (report), I-15 (converter path), M-03 (URL drift), SEC-01 (download route traversal).

---

## 1. Export surface (what a user can take away)

| Artifact | Content | Trigger |
| :--- | :--- | :--- |
| `lunasafe_hazard_map.png` | 4-panel 300 DPI figure | produced by phase 5; `GET /api/download/lunasafe_hazard_map.png` |
| `lunasafe_hazard_map.pdf` | vector version of the same | phase 5 / download |
| `hazard_summary.csv` | 5-class table (count, km², %) | phase 4 / download |
| `landing_sites.json` | Top-3 sites + boulder sample | phase 7 / download |
| `psr_polygons.geojson` (+ `.zip` bundle) | shadow regions with areas | phase 2 / download (zip built on demand, `web_server.py:800+`) |
| `mission_report.pdf` | 2-page report | **generated on first download request** (`:793-798`) or `python mission_report.py` |
| Map Studio **snapshot PNG** | current canvas view | client-side (`exportCurrentViewAsPng:1558`) |
| 3D **snapshot PNG** | current WebGL frame | client-side (`capture3dSnapshot:2735`) |
| Terminal **log copy** | pipeline log text | client-side (`copyTerminalLogs:3821`) |

Server rules: files must live in `outputs/` (else 404); names are **not sanitised** (SEC-01 — fix
via T-13); responses set `Content-Disposition: attachment`.

## 2. Mission report contents (and its defect)

- **Page 1:** title, provenance banner, mini map, mission metadata, timestamp (⚠ labelled "UTC" but
  local time, `mission_report.py:71`).
- **Page 2:** hazard table, PSR area, **rule-audit table**, parameters, disclaimer.
- 🔴 **I-14:** the audit table is literal `"0 / PASSED"` (`:167-177`) and fallback stats are
  hard-coded (`:51-58`) — the PDF may certify compliance it never checked. Fix T-03 injects real
  `rule_audit` values and prints `N/A` instead of sample numbers.
- No test exists; suggested text-extraction assertion in `module_documentation/MISSION_REPORT_MODULE.md` §4.

## 3. NASA LOLA ingestion (two paths, one file pair)

| Path | Trigger | Code | Result |
| :--- | :--- | :--- | :--- |
| In-app downloader | `POST /api/download-lola` (`downloadLolaDataset:3898`) + status polling | `web_server.py:601-667` | 1) existing GeoTIFFs → done; 2) local `data/ldem_75s_240m.jp2` > 5 MB → convert; 3) HTTPS GET from PDS (`:633`, 30 s timeout, progress → 80 %) then convert |
| Manual | `python prepare_lola_dataset.py` | `prepare_lola_dataset.py:19-104` | JP2 → `data/lola_south_pole_dem.tif` + `data/lola_psr_mask.tif` (depth < −900 m heuristic, I-08) |

After both GeoTIFFs exist, **every** dataset selector flips to real mode (CLI + web badge +
export bundle logic). ⚠️ The converter hard-codes `e:\sistec\LunaSafe` (I-15) and the in-app URL
differs from `data/DOWNLOAD_INSTRUCTIONS.md:23` (M-03).

Status JSON: `DOWNLOAD_STATUS {running, progress, message, success}` — polled by the UI
(`app.js` status ribbon); 409 if already running.

## 4. Offline-first posture

Everything except the optional CDN fonts/KaTeX works with **no internet**: artifacts are committed,
the JP2 is committed, three.js is vendored. Ingestion is opt-in.

## 5. Quality gaps & tasks

| Gap | ID | Task |
| :--- | :-: | :-: |
| Report can print false audit pass | I-14 | T-03 |
| Download route traversal / no allowlist | SEC-01 | T-13 |
| Converter not portable | I-15 | T-18 |
| URL drift | M-03 | T-18 |
| No tests for report/download routes | M-06 | T-08 |
| Export set not discoverable from the UI (e.g. no "download all") | — | nice-to-have |

## 6. Manual verification checklist (release gate)

```powershell
python main.py --force-synthetic
# then start the server and:
curl.exe -o map.png  http://localhost:8050/api/download/lunasafe_hazard_map.png
curl.exe -o csv      http://localhost:8050/api/download/hazard_summary.csv
curl.exe -o report   http://localhost:8050/api/download/mission_report.pdf
# open report: verify the audit row matches:  curl.exe -X POST .../api/audit
```
(Run the last comparison *after* T-03 — today they can disagree.)
