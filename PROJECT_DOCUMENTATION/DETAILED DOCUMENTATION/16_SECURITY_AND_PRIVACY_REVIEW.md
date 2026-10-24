# 16 — Security and Privacy Review

*Method: source inspection of every network-facing code path in `web_server.py` (864 lines), the
frontend, and a repo-wide search for secrets. Date: 2026-10-17. Scope: this is a **local hackathon
demo**, so findings are rated for "LAN demo" threat, not internet exposure.*

**Verdict:** no secrets are leaked and no personal data is processed, but the server must be
treated as **unauthenticated, LAN-wide, arbitrary-read** until task **T-13** is done. It is safe for
a closed demo room; it is not safe on a public network.

---

## 1. Threat model (as deployed today)

| Aspect | Reality |
| :--- | :--- |
| Trust boundary | Everything between the browser and `web_server.py` is trusted; **there is no authentication or authorisation anywhere** |
| Bind address | `""` → **all interfaces** (`web_server.py:840`) — every device on the LAN can reach it |
| Attack surface | 7 unauthenticated POST endpoints, 14 GET/other routes, static file serving rooted at the **repository root** |
| Assets | source code, `.git` history, `outputs/*`, `data/*`, availability of the host (CPU/disk), the ability to trigger a subprocess |
| Realistic adversaries | curious judge on the demo Wi-Fi, malicious webpage visited on the same machine (CORS `*`), accidental mis-click |

---

## 2. Findings

### SEC-01 — Arbitrary file read via path traversal in three custom routes — **HIGH**

| Field | Detail |
| :--- | :--- |
| Where | `/vendor/*` (`web_server.py:134-140`), `/outputs/*` (`:143-149`), `/api/download/<name>` (`:129-131` → `:789`) |
| Mechanism | the remainder after the prefix is joined to a directory with **no** `..` filtering and no `resolve()`/`startswith()` check: `ROOT_DIR / "web" / rel_path` (`:136`), `ROOT_DIR / rel_path` (`:145`), `out_dir / filename` (`:791`) |
| Proof (concept) | `curl http://localhost:8050/vendor/../../config.py` → serves `config.py`<br>`curl http://localhost:8050/outputs/../requirements.txt` → serves `requirements.txt`<br>`curl -OJ http://localhost:8050/api/download/../config.py` → downloads as an attachment |
| Impact | full source disclosure, including `web_server.py` itself (attacker learns every other weakness), `.venv` contents, anything else under the checkout |
| Fix | `p = (base / rel).resolve(); require str(p).startswith(str(base.resolve()) + os.sep)` — apply in all three handlers; additionally allowlist download names |

> Note: the *stdlib* fallback (`super().do_GET()`, `:152`) is **not** vulnerable to `..` traversal
> (Python's `translate_path` drops `..` segments), but see SEC-02.

### SEC-02 — Whole-repository static file server + directory listings, no auth — **HIGH**

| Field | Detail |
| :--- | :--- |
| Where | `SimpleHTTPRequestHandler(directory=str(ROOT_DIR))` at `web_server.py:93`, fallback `:152` |
| Mechanism | any file under the checkout that isn't matched by an earlier route is served; directories render an **HTML listing** |
| Reachable | `/.git/config`, `/.git/HEAD`, `/requirements.txt`, `/.agents/rules/lunasafe.md`, `/.venv/…`, `/data/*`, `/tests/*`, `/**/` listings |
| Impact | source + **full git history** exfiltration with a browser; `POST /api/run-pipeline` (`SEC-04`) can then be aimed at what was learned |
| Fix | serve `web/` only: `SimpleHTTPRequestHandler(directory=str(ROOT_DIR/"web"))`, and disable listing with a custom `list_directory` → 404 |

### SEC-03 — No authentication, wide-open CORS, all-interfaces bind — **HIGH (by design, must be documented)**

- No auth on any route; no session cookie exists at all.
- Every JSON response sets `Access-Control-Allow-Origin: *` (`web_server.py:196`) → **any web page
  the demo machine visits can call the API from JavaScript** (read `/api/data`, trigger
  `POST /api/run-pipeline`, read `/api/logs`).
- Binding `""` (`:840`) exposes the above to the entire LAN.

**Mitigations (T-13):** bind `127.0.0.1` by default (`--host` flag), drop or restrict the CORS
header, and add a simple token check for POST routes.

### SEC-04 — Unauthenticated command execution: subprocess spawn — **MEDIUM**

| Field | Detail |
| :--- | :--- |
| Where | `web_server.py:373-381` `subprocess.Popen([PYTHON_BIN, "main.py", ...])` |
| Mitigating factor | argv is a **fixed list** — no shell, no user-controlled string is concatenated → **not** classic command injection |
| Real risk | (a) anyone on the LAN can burn CPU/disk repeatedly → trivial DoS; (b) stdout is captured into an unbounded-in-principle log list; (c) with SEC-01 they know exactly what will run |
| Fix | auth token + rate limit; cap `PIPELINE_LOGS` length |

### SEC-05 — Unbounded upload to a fixed path — **MEDIUM**

| Field | Detail |
| :--- | :--- |
| Where | `POST /api/upload-raster` (`web_server.py:669-679`) |
| Mechanism | `self.rfile.read(int(self.headers.get("Content-Length", 0)))` → RAM; writes to **fixed** `data/custom_upload.tif`; no MIME, size, or CRS validation |
| Impact | memory DoS with a huge `Content-Length`; arbitrary overwrite of one file with attacker bytes; a later reader may treat it as a GeoTIFF |
| Note | dead endpoint — no frontend caller (Issue I-12) → **safest fix: delete the route** |

### SEC-06 — JSON parsing and input validation gaps — **MEDIUM**

- `read_json_body` swallows all errors → `{}` (`:207`) — no 400, silent misconfiguration.
- Thresholds are `float(body.get(...))` with **no range check** (`:422-435`): `NaN`, `Infinity`
  (JSON `1e999` → `inf`) or negative values are accepted and written into `config`. `float("nan")`
  propagates into `np.clip` comparisons → classification arrays can silently become all-zeros/all-unsafe.
  (`json.loads("NaN")` is also accepted by Python's parser.)
- `validate-geotiff` `filename` is joined into `data/` (`:745-747`) → same traversal class as SEC-01,
  mitigated only by the fact it must be *readable by rasterio*.
- Fix: `math.isfinite(v)` + `0 <= v <= sane_max` per key; return 400 with the offending field.

### SEC-07 — Missing SRI on all CDN resources; old vendored three.js — **LOW**

| Resource | Line | Issue |
| :--- | :--- | :--- |
| `fonts.googleapis.com` CSS | `web/index.html:11` | no `integrity` |
| `cdn.jsdelivr.net` KaTeX 0.16.8 css+js | `index.html:16-17` | no `integrity` |
| CDN fallback three.js **r128** + OrbitControls | `index.html:25-26` (only used if the vendored file fails) | no `integrity`; r128 is from 2021 |
| vendored `three.min.js` (r128) | `web/vendor/` | loaded first (`:20`) — good for offline, but frozen at a 2021 release |

Impact: a compromised CDN executes script in the demo origin (which can then call the API →
SEC-03/04 chain). Fix: add `integrity`/`crossorigin` attributes or self-host KaTeX (already the
pattern used for three.js); plan a three.js upgrade path (P3).

### SEC-08 — DOM sink usage in the frontend — **LOW**

19 `innerHTML =` assignments in `web/app.js` (e.g. `:3053`, `:3608`, `:3968`) interpolate
**server-provided** strings (rule descriptions, class names, violation counts, site names).
Today those values originate in `config.py`/pipeline outputs, so exploitation requires first
controlling the server response (SEC-01/04). Fix: `textContent` for data fields, or a tiny
`esc()` helper.

### SEC-09 — Supply chain / dependency posture — **LOW**

- All 10 direct deps **exact-pinned** (good); **no hashes** (`--require-hashes` unused) and no lockfile.
- `pyflakes` present in the venv but not declared (drift, Issue I-16).
- No automated dependency scanning / CI (T-07).
- `numpy/scipy/rasterio` wheels come from PyPI — standard risk, accepted for a demo.

### SEC-10 — Subprocess stdout/stderr handling — **LOW**

`stderr=subprocess.STDOUT` (`:377`) is fine; but a failing child still ends with
`PIPELINE_RUNNING=False` in `finally` (`:402-404`) only — a hang (no output, blocked child) leaves
the UI "BUSY" forever with no timeout. Fix: `process.wait(timeout=…)` + kill.

---

## 3. What is *not* a problem (verified clean)

| Check | Result |
| :--- | :--- |
| Secrets/keys/tokens in the repo | **none** — greps for `API_KEY`, `SECRET`, `TOKEN`, `PASSWORD`, `PRIVATE` return nothing; no `.env` file |
| Personal data (PII) | **none collected** — no accounts, forms, analytics, cookies, localStorage of user identity, or telemetry |
| Cookies / sessions | none (nothing to steal, no CSRF surface beyond CSRF-able POSTs) |
| Database credentials | no database |
| Injection via shell | subprocess argv is a fixed list; no `shell=True`, no string-built commands |
| TLS | N/A for localhost demo; LAN traffic is plaintext HTTP (acceptable only if SEC-03 is fixed by binding loopback) |
| NASA data licence | public-domain PDS/USGS data; redistribution of the JP2 is acceptable |
| Prototype pollution / deserialization | JSON only via `json.loads` — no `pickle`, no `eval` of user data |
| Static path traversal in stdlib fallback | Python's `translate_path` drops `..` (but see SEC-02 for listing exposure) |

---

## 4. Privacy statement (for reviewers)

> LunaSafe processes **no personal data**. It runs entirely on the local machine, makes one optional
> outbound HTTP GET to NASA's public PDS archive, and loads optional styling assets from
> jsDelivr/Google Fonts. No analytics, no tracking, no accounts, no cookies. Raster and report data
> are scientific products only. If the console is exposed beyond `localhost`, every page view and
> API call traverses the LAN unencrypted — bind to loopback for anything beyond a trusted demo.

---

## 5. Hardening checklist (task T-13, ordered)

| # | Change | Effort | Neutralises |
| :-: | :--- | :-: | :--- |
| 1 | Bind `127.0.0.1` by default; `--host 0.0.0.0` opt-in | S | SEC-03 (network half) |
| 2 | Resolve+prefix-check all three custom file routes | S | SEC-01 |
| 3 | Restrict static serving to `web/`; `list_directory` → 404 | S | SEC-02 |
| 4 | Remove `/api/upload-raster` (unused) or validate size/type | S | SEC-05 |
| 5 | Range/finite validation on every POST numeric key; 400 on bad JSON | M | SEC-06 |
| 6 | Constant-time token header for all POST routes; reject others | M | SEC-03/04 |
| 7 | Drop `Access-Control-Allow-Origin: *` (same-origin only) | S | SEC-03 (web half) |
| 8 | Add SRI to the 3 CDN tags; keep vendored three.js first | S | SEC-07 |
| 9 | `textContent` over `innerHTML` for data-driven nodes | M | SEC-08 |
| 10 | `wait(timeout)` + kill for the pipeline subprocess; cap log buffer | S | SEC-10 |
| 11 | `pip install --require-hashes` + Dependabot/CI | M | SEC-09 |

*(S = <1 h, M = 1–3 h with tests — see `testing_documentation/` for the suggested route tests.)*

---

## 6. Reporting

If you find additional issues in this repository, report them at
`https://github.com/anomalyco/opencode/issues` (tooling) or open an issue in the LunaSafe repo
itself for project bugs.
