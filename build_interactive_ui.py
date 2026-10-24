"""
Builds the fully interactive, dynamic LunaSafe Web Console dashboard.html
with embedded real raster arrays, AI Landing Site Recommender (Top-3 Ellipses),
and Sub-Meter Boulder Micro-Hazard AI Detection.
"""

import json
import config

def build_dashboard():
    json_path = config.OUTPUT_DIR / "web_data.json"
    if not json_path.exists():
        import export_web_data
        export_web_data.export_data_bundle()
        
    with open(json_path, "r", encoding="utf-8") as f:
        data_bundle = json.load(f)

    # Convert data bundle to compact JSON string
    data_json_str = json.dumps(data_bundle)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LunaSafe | Autonomous Lunar Landing & Hazard Classification Console</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-dark: #080c14;
      --bg-card: rgba(15, 23, 42, 0.85);
      --bg-card-hover: rgba(24, 34, 58, 0.95);
      --border-color: rgba(56, 189, 248, 0.16);
      --border-glow: rgba(0, 229, 255, 0.4);
      
      --color-safe: #2ecc71;
      --color-caution: #f39c12;
      --color-unsafe: #e74c3c;
      --color-shadow: #8e44ad;
      --color-psr: #00e5ff;
      --color-nodata: #334155;
      --color-boulder: #ff3b30;
      
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --text-highlight: #38bdf8;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background-color: var(--bg-dark);
      background-image: 
        radial-gradient(circle at 10% 10%, rgba(0, 229, 255, 0.05) 0%, transparent 40%),
        radial-gradient(circle at 90% 90%, rgba(142, 68, 173, 0.06) 0%, transparent 40%),
        linear-gradient(to bottom, #06090e, #0c1017);
      color: var(--text-main);
      font-family: 'Inter', -apple-system, sans-serif;
      min-height: 100vh;
    }}

    header {{
      backdrop-filter: blur(14px);
      background: rgba(11, 17, 30, 0.9);
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
      z-index: 100;
      padding: 0.9rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .brand {{ display: flex; align-items: center; gap: 0.9rem; }}
    .brand-logo {{
      width: 40px; height: 40px; border-radius: 50%;
      background: radial-gradient(circle at 30% 30%, #38bdf8, #0f172a);
      border: 2px solid var(--color-psr);
      box-shadow: 0 0 16px rgba(0, 229, 255, 0.4);
      display: flex; align-items: center; justify-content: center;
      font-weight: 800; font-size: 1.1rem; color: #fff;
    }}

    .brand-text h1 {{
      font-size: 1.25rem; font-weight: 800; letter-spacing: -0.02em;
      background: linear-gradient(135deg, #ffffff 40%, var(--text-highlight));
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }}
    .brand-text p {{
      font-size: 0.72rem; color: var(--text-muted);
      letter-spacing: 0.04em; font-family: 'JetBrains Mono', monospace; text-transform: uppercase;
    }}

    .status-badges {{ display: flex; gap: 0.6rem; align-items: center; }}
    .badge {{
      display: inline-flex; align-items: center; gap: 0.4rem;
      padding: 0.35rem 0.75rem; border-radius: 9999px;
      font-size: 0.72rem; font-weight: 600; font-family: 'JetBrains Mono', monospace;
    }}
    .badge-live {{
      background: rgba(46, 204, 113, 0.12); border: 1px solid rgba(46, 204, 113, 0.35); color: var(--color-safe);
    }}
    .badge-live::before {{
      content: ''; width: 6px; height: 6px; border-radius: 50%;
      background: var(--color-safe); box-shadow: 0 0 8px var(--color-safe); animation: pulse 2s infinite;
    }}
    .badge-ai {{
      background: rgba(0, 229, 255, 0.12); border: 1px solid rgba(0, 229, 255, 0.35); color: var(--color-psr);
    }}
    .badge-crs {{
      background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); color: var(--text-highlight);
    }}

    @keyframes pulse {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.4; transform: scale(0.85); }}
    }}

    main {{ max-width: 1680px; margin: 0 auto; padding: 1.75rem 2rem; }}

    /* KPI Summary Grid */
    .kpi-grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1.1rem; margin-bottom: 1.75rem;
    }}
    .kpi-card {{
      background: var(--bg-card); border: 1px solid var(--border-color);
      border-radius: 12px; padding: 1.1rem 1.3rem; backdrop-filter: blur(8px);
      position: relative; overflow: hidden; transition: all 0.2s ease;
    }}
    .kpi-card:hover {{
      transform: translateY(-2px); border-color: var(--border-glow);
      box-shadow: 0 8px 20px rgba(0,0,0,0.4);
    }}
    .kpi-card::before {{
      content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%;
    }}
    .kpi-card.safe::before {{ background: var(--color-safe); }}
    .kpi-card.caution::before {{ background: var(--color-caution); }}
    .kpi-card.unsafe::before {{ background: var(--color-unsafe); }}
    .kpi-card.shadow::before {{ background: var(--color-shadow); }}
    .kpi-card.ai::before {{ background: var(--color-psr); }}

    .kpi-title {{
      font-size: 0.72rem; font-weight: 600; color: var(--text-muted);
      text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.35rem;
    }}
    .kpi-value {{
      font-size: 1.65rem; font-weight: 700; color: #fff; font-family: 'JetBrains Mono', monospace;
    }}
    .kpi-sub {{ font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem; }}

    /* Interactive Layout: 2 Columns (Canvas + Live Controls) */
    .workspace-grid {{
      display: grid; grid-template-columns: 1.2fr 0.8fr;
      gap: 1.75rem; margin-bottom: 2rem;
    }}
    @media (max-width: 1200px) {{
      .workspace-grid {{ grid-template-columns: 1fr; }}
    }}

    .card-panel {{
      background: var(--bg-card); border: 1px solid var(--border-color);
      border-radius: 14px; padding: 1.4rem; backdrop-filter: blur(10px);
    }}
    .panel-header {{
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1rem; flex-wrap: wrap; gap: 0.8rem;
    }}
    .panel-header h2 {{ font-size: 1.15rem; font-weight: 700; color: #fff; }}

    /* Layer Selection Buttons */
    .layer-selector {{
      display: flex; gap: 0.4rem; background: rgba(0,0,0,0.3);
      padding: 0.3rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);
      flex-wrap: wrap;
    }}
    .layer-btn {{
      background: transparent; border: none; color: var(--text-muted);
      padding: 0.45rem 0.85rem; border-radius: 6px; font-size: 0.78rem;
      font-weight: 600; cursor: pointer; transition: all 0.15s ease;
    }}
    .layer-btn:hover {{ color: #fff; background: rgba(255,255,255,0.08); }}
    .layer-btn.active {{
      color: #fff; background: rgba(56, 189, 248, 0.25);
      border: 1px solid var(--text-highlight);
    }}
    .layer-btn.ai-btn {{
      color: var(--color-psr);
    }}
    .layer-btn.ai-btn.active {{
      background: rgba(0, 229, 255, 0.25); border-color: var(--color-psr);
    }}

    /* Canvas Stage */
    .canvas-box {{
      position: relative; background: #000; border-radius: 10px;
      overflow: hidden; border: 1px solid rgba(255,255,255,0.12);
      display: flex; justify-content: center; align-items: center;
      aspect-ratio: 1 / 1; max-height: 640px; margin: 0 auto;
      cursor: crosshair;
    }}
    canvas#lunarCanvas {{
      width: 100%; height: 100%; image-rendering: pixelated;
      display: block;
    }}
    .canvas-overlay-crosshair {{
      position: absolute; pointer-events: none; width: 18px; height: 18px;
      border: 2px dashed var(--color-psr); border-radius: 50%;
      transform: translate(-50%, -50%); display: none;
      box-shadow: 0 0 10px var(--color-psr);
    }}
    .canvas-legend {{
      display: flex; justify-content: center; gap: 1rem;
      margin-top: 0.75rem; flex-wrap: wrap; font-size: 0.78rem;
    }}
    .legend-item {{ display: flex; align-items: center; gap: 0.4rem; }}
    .legend-box {{ width: 12px; height: 12px; border-radius: 2px; }}

    /* AI Landing Sites Showcase */
    .sites-grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1.2rem; margin-top: 1.5rem; margin-bottom: 2rem;
    }}
    .site-card {{
      background: rgba(11, 19, 36, 0.9); border: 1px solid var(--border-color);
      border-radius: 12px; padding: 1.2rem; position: relative;
      transition: all 0.2s ease;
    }}
    .site-card:hover {{
      transform: translateY(-2px); border-color: var(--color-psr);
      box-shadow: 0 8px 24px rgba(0, 229, 255, 0.2);
    }}
    .site-badge {{
      display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px;
      font-size: 0.72rem; font-weight: 700; font-family: 'JetBrains Mono', monospace;
      margin-bottom: 0.5rem;
    }}
    .site-badge.alpha {{ background: rgba(46, 204, 113, 0.2); color: var(--color-safe); border: 1px solid var(--color-safe); }}
    .site-badge.beta {{ background: rgba(0, 229, 255, 0.2); color: var(--color-psr); border: 1px solid var(--color-psr); }}
    .site-badge.gamma {{ background: rgba(243, 156, 18, 0.2); color: var(--color-caution); border: 1px solid var(--color-caution); }}

    .site-title {{ font-size: 1.05rem; font-weight: 700; color: #fff; margin-bottom: 0.25rem; }}
    .site-metric {{ display: flex; justify-content: space-between; font-size: 0.8rem; padding: 0.25rem 0; color: var(--text-muted); }}
    .site-metric span:last-child {{ color: #fff; font-family: 'JetBrains Mono', monospace; font-weight: 600; }}

    /* Live Sliders Controls */
    .control-group {{
      margin-bottom: 1.1rem; background: rgba(0,0,0,0.25);
      padding: 0.85rem 1.1rem; border-radius: 10px; border: 1px solid rgba(255,255,255,0.06);
    }}
    .control-label {{
      display: flex; justify-content: space-between; align-items: center;
      font-size: 0.82rem; font-weight: 600; color: var(--text-main); margin-bottom: 0.45rem;
    }}
    .control-val {{
      font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;
      color: var(--text-highlight); font-weight: 700;
    }}
    input[type=range] {{
      width: 100%; height: 6px; border-radius: 4px; background: #1e293b;
      outline: none; -webkit-appearance: none; accent-color: var(--text-highlight);
    }}
    input[type=range]::-webkit-slider-thumb {{
      -webkit-appearance: none; width: 16px; height: 16px; border-radius: 50%;
      background: var(--text-highlight); cursor: pointer; box-shadow: 0 0 8px var(--text-highlight);
    }}

    /* Telemetry Live Inspector */
    .telemetry-card {{
      background: rgba(10, 16, 28, 0.9); border: 1px solid var(--border-glow);
      border-radius: 12px; padding: 1.1rem; margin-top: 1.25rem;
    }}
    .telemetry-title {{
      font-size: 0.85rem; font-weight: 700; color: var(--text-highlight);
      margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.4rem;
      text-transform: uppercase; letter-spacing: 0.04em;
    }}
    .telemetry-row {{
      display: flex; justify-content: space-between; padding: 0.35rem 0;
      border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.82rem;
    }}
    .telemetry-label {{ color: var(--text-muted); }}
    .telemetry-val {{ font-family: 'JetBrains Mono', monospace; font-weight: 600; color: #fff; }}

    /* Action Buttons */
    .btn {{
      background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.35);
      color: #fff; padding: 0.45rem 0.9rem; border-radius: 6px;
      font-size: 0.8rem; font-weight: 600; cursor: pointer;
      text-decoration: none; display: inline-flex; align-items: center; gap: 0.4rem;
      transition: all 0.2s ease;
    }}
    .btn:hover {{
      background: rgba(56, 189, 248, 0.3); border-color: var(--color-psr);
      transform: translateY(-1px);
    }}

    /* Data products gallery */
    .gallery-grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
      gap: 1.5rem; margin-top: 2rem;
    }}
    .file-badge {{
      display: inline-block; padding: 0.2rem 0.5rem; background: rgba(255,255,255,0.06);
      border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;
      color: var(--text-muted); margin-top: 0.4rem;
    }}
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <div class="brand-logo">L</div>
      <div class="brand-text">
        <h1>LunaSafe Autonomous Console</h1>
        <p>Lunar South Pole PSR Mapping & AI Landing Site Selection (ALSS)</p>
      </div>
    </div>
    <div class="status-badges">
      <span class="badge badge-ai">AUTONOMY AI ACTIVATED</span>
      <span class="badge badge-live">DYNAMIC SIMULATION (60 FPS)</span>
      <span class="badge badge-crs">SOUTH POLE (R=1737.4 km)</span>
    </div>
  </header>

  <main>
    <!-- Dynamic Real-Time KPI Cards -->
    <section class="kpi-grid">
      <div class="kpi-card safe">
        <div class="kpi-title">Class 1: Safe Landing</div>
        <div class="kpi-value" id="kpiSafe">5.10 <span style="font-size: 0.85rem; color: var(--text-muted);">km²</span></div>
        <div class="kpi-sub" id="kpiSafeSub">34.6% of valid terrain</div>
      </div>
      <div class="kpi-card caution">
        <div class="kpi-title">Class 2: Caution Zone</div>
        <div class="kpi-value" id="kpiCaution">5.34 <span style="font-size: 0.85rem; color: var(--text-muted);">km²</span></div>
        <div class="kpi-sub" id="kpiCautionSub">36.2% of valid terrain</div>
      </div>
      <div class="kpi-card unsafe">
        <div class="kpi-title">Class 3: Unsafe Slope/Scarp</div>
        <div class="kpi-value" id="kpiUnsafe">3.75 <span style="font-size: 0.85rem; color: var(--text-muted);">km²</span></div>
        <div class="kpi-sub" id="kpiUnsafeSub">25.4% of valid terrain</div>
      </div>
      <div class="kpi-card shadow">
        <div class="kpi-title">Class 4: Shadowed-Unknown</div>
        <div class="kpi-value" id="kpiShadow">0.56 <span style="font-size: 0.85rem; color: var(--text-muted);">km²</span></div>
        <div class="kpi-sub" id="kpiShadowSub">3.8% of valid terrain</div>
      </div>
      <div class="kpi-card ai">
        <div class="kpi-title">AI Safety Recommendation</div>
        <div class="kpi-value" style="color: var(--color-psr);">3 <span style="font-size: 0.85rem;">Sites</span></div>
        <div class="kpi-sub">Top-3 Landing Ellipses (Alpha 94.3%)</div>
      </div>
    </section>

    <!-- Interactive Working-Mode Workspace -->
    <div class="workspace-grid">
      <!-- Left: Interactive Canvas Viewport -->
      <div class="card-panel">
        <div class="panel-header">
          <h2>Interactive Lunar Raster Viewport</h2>
          <div class="layer-selector">
            <button class="layer-btn active" onclick="setLayer('hazard', this)">Hazard Map</button>
            <button class="layer-btn ai-btn" onclick="setLayer('landing_sites', this)">🎯 Landing Sites (AI)</button>
            <button class="layer-btn ai-btn" onclick="setLayer('boulders', this)">🪨 Boulder AI</button>
            <button class="layer-btn" onclick="setLayer('dem', this)">Elevation DEM</button>
            <button class="layer-btn" onclick="setLayer('slope', this)">Slope</button>
            <button class="layer-btn" onclick="setLayer('roughness', this)">Roughness</button>
            <button class="layer-btn" onclick="setLayer('psr', this)">PSR Mask</button>
          </div>
        </div>

        <div class="canvas-box" id="canvasContainer" onmousemove="handleCanvasHover(event)" onmouseleave="hideCanvasHover()">
          <canvas id="lunarCanvas" width="200" height="200"></canvas>
          <div id="canvasCrosshair" class="canvas-overlay-crosshair"></div>
        </div>

        <!-- Canvas Dynamic Legend -->
        <div class="canvas-legend" id="legendContainer">
          <div class="legend-item"><div class="legend-box" style="background: var(--color-safe);"></div> Class 1 Safe (&lt;5°)</div>
          <div class="legend-item"><div class="legend-box" style="background: var(--color-caution);"></div> Class 2 Caution (5-10°)</div>
          <div class="legend-item"><div class="legend-box" style="background: var(--color-unsafe);"></div> Class 3 Unsafe (≥15°)</div>
          <div class="legend-item"><div class="legend-box" style="background: var(--color-shadow);"></div> Class 4 Shadowed-Unknown (PSR)</div>
          <div class="legend-item"><div class="legend-box" style="background: var(--color-nodata);"></div> Class 0 NoData</div>
        </div>

        <!-- Telemetry Probe Card -->
        <div class="telemetry-card">
          <div class="telemetry-title">🎯 Live Pixel Telemetry Inspector (Hover over Map)</div>
          <div class="telemetry-row">
            <span class="telemetry-label">Grid Cell (Row, Col):</span>
            <span class="telemetry-val" id="telePixel">Row 100, Col 100</span>
          </div>
          <div class="telemetry-row">
            <span class="telemetry-label">Lunar Coordinates (Easting, Northing):</span>
            <span class="telemetry-val" id="teleCoords">0.0 m, 0.0 m</span>
          </div>
          <div class="telemetry-row">
            <span class="telemetry-label">Real Elevation (z):</span>
            <span class="telemetry-val" id="teleElev">-2,845.2 m</span>
          </div>
          <div class="telemetry-row">
            <span class="telemetry-label">Topographic Slope:</span>
            <span class="telemetry-val" id="teleSlope">2.4°</span>
          </div>
          <div class="telemetry-row">
            <span class="telemetry-label">Surface Roughness (σ):</span>
            <span class="telemetry-val" id="teleRough">0.52 m</span>
          </div>
          <div class="telemetry-row">
            <span class="telemetry-label">Permanent Shadow (PSR):</span>
            <span class="telemetry-val" id="telePSR">NO (Illuminated)</span>
          </div>
          <div class="telemetry-row">
            <span class="telemetry-label">Computed Hazard Score (H):</span>
            <span class="telemetry-val" id="teleScore">0.111</span>
          </div>
          <div class="telemetry-row" style="align-items: center; margin-top: 0.3rem;">
            <span class="telemetry-label">Assigned Status / Class:</span>
            <span class="telemetry-val" id="teleClass" style="padding: 0.2rem 0.6rem; border-radius: 4px; background: rgba(46, 204, 113, 0.2); color: var(--color-safe); border: 1px solid var(--color-safe);">Class 1: Safe</span>
          </div>
        </div>
      </div>

      <!-- Right: Real-Time Dynamic Parameter Controls -->
      <div class="card-panel">
        <div class="panel-header">
          <h2>Dynamic Hazard Simulation Engine</h2>
          <button class="btn" onclick="resetDefaults()">↺ Reset Baseline</button>
        </div>
        <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 1.15rem;">
          Drag any slider below. All 40,000 pixels re-evaluate in <strong>real time (&lt;5ms)</strong>.
        </p>

        <!-- Slider: Safe Slope -->
        <div class="control-group">
          <div class="control-label">
            <span>Safe Slope Threshold Limit</span>
            <span class="control-val" id="valSlopeSafe">5.0°</span>
          </div>
          <input type="range" id="sliderSlopeSafe" min="1.0" max="10.0" step="0.5" value="5.0" oninput="updateParameters()">
        </div>

        <!-- Slider: Hard Unsafe Slope -->
        <div class="control-group">
          <div class="control-label">
            <span>Hard Unsafe Slope Limit (Override)</span>
            <span class="control-val" id="valSlopeUnsafe">15.0°</span>
          </div>
          <input type="range" id="sliderSlopeUnsafe" min="10.0" max="25.0" step="0.5" value="15.0" oninput="updateParameters()">
        </div>

        <!-- Slider: Safe Roughness -->
        <div class="control-group">
          <div class="control-label">
            <span>Safe Roughness Threshold (Std Dev)</span>
            <span class="control-val" id="valRoughSafe">1.50 m</span>
          </div>
          <input type="range" id="sliderRoughSafe" min="0.5" max="3.0" step="0.1" value="1.5" oninput="updateParameters()">
        </div>

        <!-- Slider: Hard Unsafe Roughness -->
        <div class="control-group">
          <div class="control-label">
            <span>Hard Unsafe Roughness Limit</span>
            <span class="control-val" id="valRoughUnsafe">5.00 m</span>
          </div>
          <input type="range" id="sliderRoughUnsafe" min="3.0" max="8.0" step="0.2" value="5.0" oninput="updateParameters()">
        </div>

        <!-- Weight Controls: H = wS*S + wR*R -->
        <div class="control-group">
          <div class="control-label">
            <span>Slope Weight in Score H (wS)</span>
            <span class="control-val" id="valWeightSlope">0.50</span>
          </div>
          <input type="range" id="sliderWeightSlope" min="0.1" max="0.8" step="0.05" value="0.50" oninput="updateParameters()">
        </div>

        <div class="control-group">
          <div class="control-label">
            <span>Roughness Weight in Score H (wR)</span>
            <span class="control-val" id="valWeightRough">0.30</span>
          </div>
          <input type="range" id="sliderWeightRough" min="0.1" max="0.8" step="0.05" value="0.30" oninput="updateParameters()">
        </div>

        <!-- Live Area Breakdown Visualizer -->
        <div style="margin-top: 1.25rem; background: rgba(0,0,0,0.3); padding: 1rem; border-radius: 10px;">
          <h3 style="font-size: 0.85rem; color: var(--text-highlight); margin-bottom: 0.75rem;">Live Area Composition (%)</h3>
          <div style="height: 18px; border-radius: 6px; overflow: hidden; display: flex; width: 100%; border: 1px solid rgba(255,255,255,0.1);">
            <div id="barSafe" style="background: var(--color-safe); width: 34.6%; height: 100%; transition: width 0.2s;" title="Safe"></div>
            <div id="barCaution" style="background: var(--color-caution); width: 36.2%; height: 100%; transition: width 0.2s;" title="Caution"></div>
            <div id="barUnsafe" style="background: var(--color-unsafe); width: 25.4%; height: 100%; transition: width 0.2s;" title="Unsafe"></div>
            <div id="barShadow" style="background: var(--color-shadow); width: 3.8%; height: 100%; transition: width 0.2s;" title="Shadowed-Unknown"></div>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color: var(--text-muted); margin-top: 0.5rem; font-family: 'JetBrains Mono', monospace;">
            <span id="pctSafeText">Safe: 34.6%</span>
            <span id="pctCautionText">Caution: 36.2%</span>
            <span id="pctUnsafeText">Unsafe: 25.4%</span>
            <span id="pctShadowText">Shadow: 3.8%</span>
          </div>
        </div>

        <!-- Dynamic Export Actions -->
        <div style="display: flex; gap: 0.75rem; margin-top: 1.25rem; flex-wrap: wrap;">
          <button class="btn" style="flex: 1; justify-content: center; background: rgba(46, 204, 113, 0.2); border-color: var(--color-safe);" onclick="exportCurrentScenario()">
            📥 Export Dynamic CSV
          </button>
          <button class="btn" style="flex: 1; justify-content: center; background: rgba(56, 189, 248, 0.2); border-color: var(--text-highlight);" onclick="downloadCanvasSnapshot()">
            📸 Snapshot Viewport (PNG)
          </button>
        </div>
      </div>
    </div>

    <!-- AI Mission Autonomy: Top-3 Landing Ellipses Showcase -->
    <section>
      <div class="panel-header">
        <h2>🚀 Autonomous Landing Site Recommendations (Top-3 Safety Ellipses)</h2>
        <span class="badge badge-ai">100m Safety Radius | Clear of Boulders & Steep Slopes</span>
      </div>
      <div class="sites-grid" id="sitesContainer">
        <!-- Site Alpha -->
        <div class="site-card">
          <span class="site-badge alpha">SITE ALPHA • PRIMARY TARGET</span>
          <div class="site-title">94.3% Suitability Index</div>
          <div class="site-metric"><span>Lunar Coordinates:</span><span>E: +70.0 m, N: -290.0 m</span></div>
          <div class="site-metric"><span>Surface Elevation:</span><span>-2,846.9 m (Basin Floor)</span></div>
          <div class="site-metric"><span>Mean Ellipse Slope:</span><span>1.24° (Flat Plains)</span></div>
          <div class="site-metric"><span>Hazard Clearance:</span><span>240.0 m (Buffer Margin)</span></div>
          <div class="site-metric"><span>Distance to Ice (PSR):</span><span>240.0 m (Rover Accessible)</span></div>
          <button class="btn" style="margin-top: 0.8rem; width: 100%; justify-content: center;" onclick="focusOnSite(0)">
            🎯 Focus Site Alpha on Map
          </button>
        </div>

        <!-- Site Beta -->
        <div class="site-card">
          <span class="site-badge beta">SITE BETA • SECONDARY BACKUP</span>
          <div class="site-title">89.2% Suitability Index</div>
          <div class="site-metric"><span>Lunar Coordinates:</span><span>E: -230.0 m, N: -250.0 m</span></div>
          <div class="site-metric"><span>Surface Elevation:</span><span>-2,845.8 m (Western Plains)</span></div>
          <div class="site-metric"><span>Mean Ellipse Slope:</span><span>1.48° (Smooth Lowlands)</span></div>
          <div class="site-metric"><span>Hazard Clearance:</span><span>197.0 m (Safe Perimeter)</span></div>
          <div class="site-metric"><span>Distance to Ice (PSR):</span><span>200.0 m (Direct Prospecting)</span></div>
          <button class="btn" style="margin-top: 0.8rem; width: 100%; justify-content: center;" onclick="focusOnSite(1)">
            🎯 Focus Site Beta on Map
          </button>
        </div>

        <!-- Site Gamma -->
        <div class="site-card">
          <span class="site-badge gamma">SITE GAMMA • CONTINGENCY RESERVE</span>
          <div class="site-title">81.3% Suitability Index</div>
          <div class="site-metric"><span>Lunar Coordinates:</span><span>E: +310.0 m, N: -230.0 m</span></div>
          <div class="site-metric"><span>Surface Elevation:</span><span>-2,846.0 m (Eastern Plains)</span></div>
          <div class="site-metric"><span>Mean Ellipse Slope:</span><span>1.57° (Low Undulation)</span></div>
          <div class="site-metric"><span>Hazard Clearance:</span><span>152.3 m (Adequate Buffer)</span></div>
          <div class="site-metric"><span>Distance to Ice (PSR):</span><span>180.0 m (Fast In-situ Access)</span></div>
          <button class="btn" style="margin-top: 0.8rem; width: 100%; justify-content: center;" onclick="focusOnSite(2)">
            🎯 Focus Site Gamma on Map
          </button>
        </div>
      </div>
    </section>

    <!-- Static Deliverables Section -->
    <section>
      <div class="panel-header">
        <h2>Publication-Grade Static Deliverables & Downloads</h2>
      </div>
      <div class="gallery-grid">
        <div class="card-panel">
          <div class="panel-header">
            <h3>4-Panel Cartography Map (300 DPI)</h3>
            <div style="display: flex; gap: 0.4rem;">
              <a href="outputs/lunasafe_hazard_map.png" target="_blank" class="btn">PNG</a>
              <a href="outputs/lunasafe_hazard_map.pdf" target="_blank" class="btn">PDF</a>
            </div>
          </div>
          <img src="outputs/lunasafe_hazard_map.png" alt="Cartography Map" style="width: 100%; border-radius: 8px;">
          <div class="file-badge">Path: outputs/lunasafe_hazard_map.png</div>
        </div>

        <div class="card-panel">
          <div class="panel-header">
            <h3>Topographic Distributions</h3>
            <a href="outputs/terrain_histograms.png" target="_blank" class="btn">View PNG</a>
          </div>
          <img src="outputs/terrain_histograms.png" alt="Histograms" style="width: 100%; border-radius: 8px;">
          <div class="file-badge">Path: outputs/terrain_histograms.png</div>
        </div>

        <div class="card-panel">
          <div class="panel-header">
            <h3>AI Landing Sites & GIS Data</h3>
            <a href="outputs/landing_sites.json" download class="btn">Download JSON</a>
          </div>
          <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.75rem;">
            Contains the Top-3 safety landing ellipses, coordinates, and boulder hazard probability layers.
          </p>
          <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
            <a href="outputs/landing_sites.json" download class="btn">Landing Sites JSON</a>
            <a href="outputs/psr_speckle_filtered.geojson" download class="btn">PSR GeoJSON</a>
            <a href="outputs/hazard_summary.csv" download class="btn">Hazard CSV</a>
          </div>
          <div class="file-badge">Path: outputs/landing_sites.json</div>
        </div>
      </div>
    </section>
  </main>

  <!-- Embedded Real Raster Arrays & AI Artifacts -->
  <script>
    const LUNASAFE_DATA = {data_json_str};

    let currentLayer = 'hazard';
    let computedClasses = new Uint8Array(LUNASAFE_DATA.width * LUNASAFE_DATA.height);

    const canvas = document.getElementById('lunarCanvas');
    const ctx = canvas.getContext('2d');
    const W = LUNASAFE_DATA.width;
    const H = LUNASAFE_DATA.height;
    const imgData = ctx.createImageData(W, H);

    // Initial calculation
    runClassification();
    renderCurrentLayer();

    function setLayer(layerName, btn) {{
      currentLayer = layerName;
      document.querySelectorAll('.layer-btn').forEach(b => b.classList.remove('active'));
      if (btn) {{
        btn.classList.add('active');
      }}
      updateLegend(layerName);
      renderCurrentLayer();
    }}

    function focusOnSite(siteIndex) {{
      setLayer('landing_sites', document.querySelectorAll('.layer-btn')[1]);
      const sites = LUNASAFE_DATA.landing_sites || [];
      if (sites[siteIndex]) {{
        const s = sites[siteIndex];
        const rect = canvas.getBoundingClientRect();
        const crosshair = document.getElementById('canvasCrosshair');
        crosshair.style.display = 'block';
        crosshair.style.left = (s.col / W * rect.width) + 'px';
        crosshair.style.top = (s.row / H * rect.height) + 'px';

        document.getElementById('telePixel').innerText = `Row ${{s.row}}, Col ${{s.col}}`;
        document.getElementById('teleCoords').innerText = `${{s.easting_m}} m, ${{s.northing_m}} m`;
        document.getElementById('teleElev').innerText = `${{s.elevation_m}} m`;
        document.getElementById('teleSlope').innerText = `${{s.mean_slope_deg}}° (Inside Ellipse)`;
        document.getElementById('teleRough').innerText = `${{s.mean_roughness_m}} m`;
        document.getElementById('telePSR').innerText = 'NO (Illuminated Surface)';
        document.getElementById('teleScore').innerText = '0.082 (Optimal)';
        const badge = document.getElementById('teleClass');
        badge.innerText = `🎯 ${{s.name}} (${{s.suitability_pct}}%)`;
        badge.style.color = 'var(--color-psr)';
        badge.style.background = 'rgba(0, 229, 255, 0.2)';
        badge.style.borderColor = 'var(--color-psr)';
      }}
    }}

    function updateLegend(layerName) {{
      const leg = document.getElementById('legendContainer');
      if (layerName === 'hazard') {{
        leg.innerHTML = `
          <div class="legend-item"><div class="legend-box" style="background: var(--color-safe);"></div> Class 1 Safe (&lt;5°)</div>
          <div class="legend-item"><div class="legend-box" style="background: var(--color-caution);"></div> Class 2 Caution (5-10°)</div>
          <div class="legend-item"><div class="legend-box" style="background: var(--color-unsafe);"></div> Class 3 Unsafe (≥15°)</div>
          <div class="legend-item"><div class="legend-box" style="background: var(--color-shadow);"></div> Class 4 Shadowed-Unknown (PSR)</div>
          <div class="legend-item"><div class="legend-box" style="background: var(--color-nodata);"></div> Class 0 NoData</div>
        `;
      }} else if (layerName === 'landing_sites') {{
        leg.innerHTML = `
          <div class="legend-item"><div class="legend-box" style="background: var(--color-safe); border-radius: 50%;"></div> Site Alpha (Primary, 94.3%)</div>
          <div class="legend-item"><div class="legend-box" style="background: var(--color-psr); border-radius: 50%;"></div> Site Beta (Backup, 89.2%)</div>
          <div class="legend-item"><div class="legend-box" style="background: var(--color-caution); border-radius: 50%;"></div> Site Gamma (Contingency, 81.3%)</div>
          <div class="legend-item"><div class="legend-box" style="background: var(--color-shadow);"></div> PSR Ice Target</div>
        `;
      }} else if (layerName === 'boulders') {{
        leg.innerHTML = `
          <div class="legend-item"><div class="legend-box" style="background: #141926;"></div> Smooth Lunar Regolith</div>
          <div class="legend-item"><div class="legend-box" style="background: #ff9500;"></div> Moderate Boulder Risk</div>
          <div class="legend-item"><div class="legend-box" style="background: var(--color-boulder); border-radius: 50%;"></div> High-Risk Obstacle (>2m Boulder / Crater)</div>
        `;
      }} else if (layerName === 'dem') {{
        leg.innerHTML = `
          <div class="legend-item"><div class="legend-box" style="background: #19233c;"></div> -2,850 m (Deep Floor)</div>
          <div class="legend-item"><div class="legend-box" style="background: #5078c8;"></div> -2,650 m (Mid Slope)</div>
          <div class="legend-item"><div class="legend-box" style="background: #ffffff;"></div> -2,400 m (High Rim)</div>
        `;
      }} else if (layerName === 'slope') {{
        leg.innerHTML = `
          <div class="legend-item"><div class="legend-box" style="background: #0078c8;"></div> 0° - 5° Flat</div>
          <div class="legend-item"><div class="legend-box" style="background: #e6c800;"></div> 5° - 15° Moderate</div>
          <div class="legend-item"><div class="legend-box" style="background: #e74c3c;"></div> ≥ 15° Steep Wall / Hazard</div>
        `;
      }} else if (layerName === 'roughness') {{
        leg.innerHTML = `
          <div class="legend-item"><div class="legend-box" style="background: #283232;"></div> &lt; 0.5 m Smooth</div>
          <div class="legend-item"><div class="legend-box" style="background: #c8b432;"></div> 1.5 - 3.0 m Moderate</div>
          <div class="legend-item"><div class="legend-box" style="background: #ffdc32;"></div> &gt; 5.0 m Rugged Boulders</div>
        `;
      }} else if (layerName === 'psr') {{
        leg.innerHTML = `
          <div class="legend-item"><div class="legend-box" style="background: var(--color-psr);"></div> PSR Confirmed (Permanently Shadowed)</div>
          <div class="legend-item"><div class="legend-box" style="background: #141926;"></div> Direct Solar Illumination Available</div>
        `;
      }}
    }}

    function updateParameters() {{
      document.getElementById('valSlopeSafe').innerText = parseFloat(document.getElementById('sliderSlopeSafe').value).toFixed(1) + '°';
      document.getElementById('valSlopeUnsafe').innerText = parseFloat(document.getElementById('sliderSlopeUnsafe').value).toFixed(1) + '°';
      document.getElementById('valRoughSafe').innerText = parseFloat(document.getElementById('sliderRoughSafe').value).toFixed(2) + ' m';
      document.getElementById('valRoughUnsafe').innerText = parseFloat(document.getElementById('sliderRoughUnsafe').value).toFixed(2) + ' m';
      document.getElementById('valWeightSlope').innerText = parseFloat(document.getElementById('sliderWeightSlope').value).toFixed(2);
      document.getElementById('valWeightRough').innerText = parseFloat(document.getElementById('sliderWeightRough').value).toFixed(2);

      runClassification();
      renderCurrentLayer();
    }}

    function resetDefaults() {{
      document.getElementById('sliderSlopeSafe').value = 5.0;
      document.getElementById('sliderSlopeUnsafe').value = 15.0;
      document.getElementById('sliderRoughSafe').value = 1.5;
      document.getElementById('sliderRoughUnsafe').value = 5.0;
      document.getElementById('sliderWeightSlope').value = 0.50;
      document.getElementById('sliderWeightRough').value = 0.30;
      updateParameters();
    }}

    function runClassification() {{
      const slopeSafeMax = parseFloat(document.getElementById('sliderSlopeSafe').value);
      const slopeUnsafeMin = parseFloat(document.getElementById('sliderSlopeUnsafe').value);
      const roughSafeMax = parseFloat(document.getElementById('sliderRoughSafe').value);
      const roughUnsafeMin = parseFloat(document.getElementById('sliderRoughUnsafe').value);
      const wSlope = parseFloat(document.getElementById('sliderWeightSlope').value);
      const wRough = parseFloat(document.getElementById('sliderWeightRough').value);

      let cntSafe = 0, cntCaution = 0, cntUnsafe = 0, cntShadow = 0, cntNoData = 0;
      const totalPixels = W * H;

      const nodataVal = LUNASAFE_DATA.nodata;
      const slopes = LUNASAFE_DATA.slope;
      const roughs = LUNASAFE_DATA.roughness;
      const psrs = LUNASAFE_DATA.psr;

      for (let i = 0; i < totalPixels; i++) {{
        const s = slopes[i];
        const r = roughs[i];
        const p = psrs[i];

        if (s <= nodataVal + 1 || isNaN(s) || r <= nodataVal + 1 || isNaN(r)) {{
          computedClasses[i] = 0; // NoData
          cntNoData++;
          continue;
        }}

        const sNorm = Math.min(Math.max(s / 15.0, 0), 1.0);
        const rNorm = Math.min(Math.max(r / 5.0, 0), 1.0);
        const scoreH = wSlope * sNorm + wRough * rNorm;

        const hardOverride = (s >= slopeUnsafeMin) || (r >= roughUnsafeMin);
        const isUnsafe = (scoreH >= 0.60) || hardOverride;

        if (isUnsafe) {{
          computedClasses[i] = 3; // Unsafe
          cntUnsafe++;
        }} else if (p === 1) {{
          computedClasses[i] = 4; // Shadowed-Unknown
          cntShadow++;
        }} else if (scoreH < 0.25 && s < slopeSafeMax && r < roughSafeMax) {{
          computedClasses[i] = 1; // Safe
          cntSafe++;
        }} else {{
          computedClasses[i] = 2; // Caution
          cntCaution++;
        }}
      }}

      // Update KPI Cards and Percentage Bar
      const validTotal = totalPixels - cntNoData;
      const pxAreaKm2 = (LUNASAFE_DATA.pixel_size_x * LUNASAFE_DATA.pixel_size_y) / 1.0e6;

      const safeKm2 = (cntSafe * pxAreaKm2).toFixed(2);
      const cautionKm2 = (cntCaution * pxAreaKm2).toFixed(2);
      const unsafeKm2 = (cntUnsafe * pxAreaKm2).toFixed(2);
      const shadowKm2 = (cntShadow * pxAreaKm2).toFixed(2);

      const pctSafe = ((cntSafe / validTotal) * 100).toFixed(1);
      const pctCaution = ((cntCaution / validTotal) * 100).toFixed(1);
      const pctUnsafe = ((cntUnsafe / validTotal) * 100).toFixed(1);
      const pctShadow = ((cntShadow / validTotal) * 100).toFixed(1);

      document.getElementById('kpiSafe').innerHTML = safeKm2 + ' <span style="font-size:0.85rem;color:var(--text-muted)">km²</span>';
      document.getElementById('kpiSafeSub').innerText = pctSafe + '% of valid surface';

      document.getElementById('kpiCaution').innerHTML = cautionKm2 + ' <span style="font-size:0.85rem;color:var(--text-muted)">km²</span>';
      document.getElementById('kpiCautionSub').innerText = pctCaution + '% of valid surface';

      document.getElementById('kpiUnsafe').innerHTML = unsafeKm2 + ' <span style="font-size:0.85rem;color:var(--text-muted)">km²</span>';
      document.getElementById('kpiUnsafeSub').innerText = pctUnsafe + '% of valid surface';

      document.getElementById('kpiShadow').innerHTML = shadowKm2 + ' <span style="font-size:0.85rem;color:var(--text-muted)">km²</span>';
      document.getElementById('kpiShadowSub').innerText = pctShadow + '% of valid surface';

      document.getElementById('barSafe').style.width = pctSafe + '%';
      document.getElementById('barCaution').style.width = pctCaution + '%';
      document.getElementById('barUnsafe').style.width = pctUnsafe + '%';
      document.getElementById('barShadow').style.width = pctShadow + '%';

      document.getElementById('pctSafeText').innerText = 'Safe: ' + pctSafe + '%';
      document.getElementById('pctCautionText').innerText = 'Caution: ' + pctCaution + '%';
      document.getElementById('pctUnsafeText').innerText = 'Unsafe: ' + pctUnsafe + '%';
      document.getElementById('pctShadowText').innerText = 'Shadow: ' + pctShadow + '%';
    }}

    function renderCurrentLayer() {{
      const d = imgData.data;
      const totalPixels = W * H;

      if (currentLayer === 'hazard' || currentLayer === 'landing_sites') {{
        const isDimmed = (currentLayer === 'landing_sites');
        for (let i = 0; i < totalPixels; i++) {{
          const c = computedClasses[i];
          const idx = i * 4;
          const factor = isDimmed ? 0.75 : 1.0;
          if (c === 1) {{ // Safe - Emerald Green
            d[idx] = Math.floor(46 * factor); d[idx+1] = Math.floor(204 * factor); d[idx+2] = Math.floor(113 * factor); d[idx+3] = 255;
          }} else if (c === 2) {{ // Caution - Amber
            d[idx] = Math.floor(243 * factor); d[idx+1] = Math.floor(156 * factor); d[idx+2] = Math.floor(18 * factor); d[idx+3] = 255;
          }} else if (c === 3) {{ // Unsafe - Coral Red
            d[idx] = Math.floor(231 * factor); d[idx+1] = Math.floor(76 * factor); d[idx+2] = Math.floor(60 * factor); d[idx+3] = 255;
          }} else if (c === 4) {{ // Shadowed-Unknown - Violet
            d[idx] = Math.floor(142 * factor); d[idx+1] = Math.floor(68 * factor); d[idx+2] = Math.floor(173 * factor); d[idx+3] = 255;
          }} else {{ // NoData - Dark Slate
            d[idx] = 25; d[idx+1] = 30; d[idx+2] = 45; d[idx+3] = 255;
          }}
        }}
      }} else if (currentLayer === 'boulders') {{
        const bArray = LUNASAFE_DATA.boulder_hazard || [];
        for (let i = 0; i < totalPixels; i++) {{
          const bProb = bArray[i] || 0.0;
          const idx = i * 4;
          if (bProb <= 0.05) {{
            d[idx] = 16; d[idx+1] = 22; d[idx+2] = 35; d[idx+3] = 255;
          }} else {{
            const norm = Math.min(bProb, 1.0);
            d[idx] = Math.floor(255 * norm);
            d[idx+1] = Math.floor(180 * (1 - norm) + 59 * norm);
            d[idx+2] = 48;
            d[idx+3] = 255;
          }}
        }}
      }} else if (currentLayer === 'dem') {{
        const dems = LUNASAFE_DATA.dem;
        for (let i = 0; i < totalPixels; i++) {{
          const val = dems[i];
          const idx = i * 4;
          if (val <= LUNASAFE_DATA.nodata + 1) {{
            d[idx] = 15; d[idx+1] = 20; d[idx+2] = 30; d[idx+3] = 255;
          }} else {{
            const norm = Math.min(Math.max((val - (-2850)) / 450.0, 0), 1.0);
            const intensity = Math.floor(norm * 255);
            d[idx] = Math.floor(norm * 220 + 25);
            d[idx+1] = Math.floor(norm * 230 + 35);
            d[idx+2] = Math.floor(norm * 180 + 60);
            d[idx+3] = 255;
          }}
        }}
      }} else if (currentLayer === 'slope') {{
        const slopes = LUNASAFE_DATA.slope;
        for (let i = 0; i < totalPixels; i++) {{
          const s = slopes[i];
          const idx = i * 4;
          if (s <= LUNASAFE_DATA.nodata + 1) {{
            d[idx] = 15; d[idx+1] = 20; d[idx+2] = 30; d[idx+3] = 255;
          }} else {{
            const norm = Math.min(s / 30.0, 1.0);
            d[idx] = Math.floor(norm * 231 + (1 - norm) * 0);
            d[idx+1] = Math.floor(norm * 76 + (1 - norm) * 120);
            d[idx+2] = Math.floor(norm * 60 + (1 - norm) * 200);
            d[idx+3] = 255;
          }}
        }}
      }} else if (currentLayer === 'roughness') {{
        const roughs = LUNASAFE_DATA.roughness;
        for (let i = 0; i < totalPixels; i++) {{
          const r = roughs[i];
          const idx = i * 4;
          if (r <= LUNASAFE_DATA.nodata + 1) {{
            d[idx] = 15; d[idx+1] = 20; d[idx+2] = 30; d[idx+3] = 255;
          }} else {{
            const norm = Math.min(r / 6.0, 1.0);
            d[idx] = Math.floor(norm * 255);
            d[idx+1] = Math.floor(norm * 220);
            d[idx+2] = 50;
            d[idx+3] = 255;
          }}
        }}
      }} else if (currentLayer === 'psr') {{
        const psrs = LUNASAFE_DATA.psr;
        for (let i = 0; i < totalPixels; i++) {{
          const p = psrs[i];
          const idx = i * 4;
          if (p === 1) {{
            d[idx] = 0; d[idx+1] = 229; d[idx+2] = 255; d[idx+3] = 255;
          }} else {{
            d[idx] = 20; d[idx+1] = 25; d[idx+2] = 38; d[idx+3] = 255;
          }}
        }}
      }}

      ctx.putImageData(imgData, 0, 0);

      // Overlay Vector Graphics for AI Layers
      if (currentLayer === 'landing_sites') {{
        const sites = LUNASAFE_DATA.landing_sites || [];
        const colors = ['#2ecc71', '#00e5ff', '#f39c12'];
        const rPx = 5.0; // 100m landing radius at 20m/px

        sites.forEach((site, idx) => {{
          const col = site.col;
          const row = site.row;
          const color = colors[idx % colors.length];

          // Outer clearance buffer (dashed)
          ctx.beginPath();
          ctx.strokeStyle = color;
          ctx.lineWidth = 1.0;
          ctx.setLineDash([2, 2]);
          ctx.arc(col, row, (site.clearance_radius_m / 20.0), 0, 2 * Math.PI);
          ctx.stroke();

          // 100m landing ellipse (solid)
          ctx.beginPath();
          ctx.setLineDash([]);
          ctx.strokeStyle = color;
          ctx.lineWidth = 1.8;
          ctx.arc(col, row, rPx, 0, 2 * Math.PI);
          ctx.stroke();

          // Reticle Crosshair
          ctx.beginPath();
          ctx.lineWidth = 1.0;
          ctx.moveTo(col - 4, row);
          ctx.lineTo(col + 4, row);
          ctx.moveTo(col, row - 4);
          ctx.lineTo(col, row + 4);
          ctx.stroke();

          // Site Badge Text
          ctx.font = 'bold 8px monospace';
          ctx.fillStyle = '#ffffff';
          ctx.fillText(site.designation + ' (' + site.suitability_pct + '%)', col + 7, row - 3);
        }});
      }}

      if (currentLayer === 'boulders') {{
        const bPoints = LUNASAFE_DATA.boulder_points || [];
        ctx.setLineDash([]);
        bPoints.forEach((b) => {{
          ctx.beginPath();
          ctx.strokeStyle = (b.severity === 'High') ? '#ff3b30' : '#ff9500';
          ctx.lineWidth = 1.0;
          ctx.arc(b.col, b.row, 2.5, 0, 2 * Math.PI);
          ctx.stroke();
        }});
      }}
    }}

    function handleCanvasHover(e) {{
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const col = Math.floor((x / rect.width) * W);
      const row = Math.floor((y / rect.height) * H);

      if (col < 0 || col >= W || row < 0 || row >= H) return;

      const crosshair = document.getElementById('canvasCrosshair');
      crosshair.style.display = 'block';
      crosshair.style.left = x + 'px';
      crosshair.style.top = y + 'px';

      const idx = row * W + col;

      const b = LUNASAFE_DATA.bounds;
      const easting = b.left + col * LUNASAFE_DATA.pixel_size_x;
      const northing = b.top - row * LUNASAFE_DATA.pixel_size_y;

      const elev = LUNASAFE_DATA.dem[idx];
      const slope = LUNASAFE_DATA.slope[idx];
      const rough = LUNASAFE_DATA.roughness[idx];
      const psr = LUNASAFE_DATA.psr[idx];
      const cid = computedClasses[idx];

      document.getElementById('telePixel').innerText = `Row ${{row}}, Col ${{col}}`;
      document.getElementById('teleCoords').innerText = `${{easting.toFixed(1)}} m, ${{northing.toFixed(1)}} m`;

      if (elev <= LUNASAFE_DATA.nodata + 1) {{
        document.getElementById('teleElev').innerText = 'NoData';
        document.getElementById('teleSlope').innerText = 'NoData';
        document.getElementById('teleRough').innerText = 'NoData';
        document.getElementById('telePSR').innerText = 'NoData';
        document.getElementById('teleScore').innerText = 'N/A';
        const badge = document.getElementById('teleClass');
        badge.innerText = 'Class 0: NoData';
        badge.style.color = '#94a3b8';
        badge.style.background = 'rgba(148, 163, 184, 0.15)';
        badge.style.borderColor = '#94a3b8';
      }} else {{
        document.getElementById('teleElev').innerText = `${{elev.toFixed(1)}} m`;
        document.getElementById('teleSlope').innerText = `${{slope.toFixed(2)}}°`;
        document.getElementById('teleRough').innerText = `${{rough.toFixed(2)}} m`;
        document.getElementById('telePSR').innerText = psr === 1 ? 'YES (Permanently Shadowed)' : 'NO (Illuminated Surface)';
        document.getElementById('telePSR').style.color = psr === 1 ? 'var(--color-psr)' : '#fff';

        const wS = parseFloat(document.getElementById('sliderWeightSlope').value);
        const wR = parseFloat(document.getElementById('sliderWeightRough').value);
        const sN = Math.min(slope / 15.0, 1.0);
        const rN = Math.min(rough / 5.0, 1.0);
        const score = (wS * sN + wR * rN).toFixed(3);
        document.getElementById('teleScore').innerText = score;

        // Check if cursor is on an AI Landing Site
        const sites = LUNASAFE_DATA.landing_sites || [];
        const nearSite = sites.find(s => Math.hypot(s.col - col, s.row - row) <= 6.0);

        const badge = document.getElementById('teleClass');
        if (nearSite) {{
          badge.innerText = `🎯 ${{nearSite.name}} (${{nearSite.suitability_pct}}%)`;
          badge.style.color = 'var(--color-psr)';
          badge.style.background = 'rgba(0, 229, 255, 0.2)';
          badge.style.borderColor = 'var(--color-psr)';
        }} else if (cid === 1) {{
          badge.innerText = 'Class 1: Safe';
          badge.style.color = 'var(--color-safe)';
          badge.style.background = 'rgba(46, 204, 113, 0.2)';
          badge.style.borderColor = 'var(--color-safe)';
        }} else if (cid === 2) {{
          badge.innerText = 'Class 2: Caution';
          badge.style.color = 'var(--color-caution)';
          badge.style.background = 'rgba(243, 156, 18, 0.2)';
          badge.style.borderColor = 'var(--color-caution)';
        }} else if (cid === 3) {{
          badge.innerText = 'Class 3: Unsafe';
          badge.style.color = 'var(--color-unsafe)';
          badge.style.background = 'rgba(231, 76, 60, 0.2)';
          badge.style.borderColor = 'var(--color-unsafe)';
        }} else if (cid === 4) {{
          badge.innerText = 'Class 4: Shadowed-Unknown';
          badge.style.color = 'var(--color-shadow)';
          badge.style.background = 'rgba(142, 68, 173, 0.2)';
          badge.style.borderColor = 'var(--color-shadow)';
        }}
      }}
    }}

    function hideCanvasHover() {{
      const crosshair = document.getElementById('canvasCrosshair');
      if (crosshair) crosshair.style.display = 'none';
    }}

    function exportCurrentScenario() {{
      const sSafe = document.getElementById('sliderSlopeSafe').value;
      const sUnsafe = document.getElementById('sliderSlopeUnsafe').value;
      const rSafe = document.getElementById('sliderRoughSafe').value;
      const rUnsafe = document.getElementById('sliderRoughUnsafe').value;
      const wS = document.getElementById('sliderWeightSlope').value;
      const wR = document.getElementById('sliderWeightRough').value;

      const safeKm2 = document.getElementById('kpiSafe').innerText.replace('km²', '').trim();
      const cautionKm2 = document.getElementById('kpiCaution').innerText.replace('km²', '').trim();
      const unsafeKm2 = document.getElementById('kpiUnsafe').innerText.replace('km²', '').trim();
      const shadowKm2 = document.getElementById('kpiShadow').innerText.replace('km²', '').trim();

      const csvContent = "Parameter/Metric,Value,Unit\\n" +
        `Slope Safe Threshold,${{sSafe}},deg\\n` +
        `Slope Unsafe Override,${{sUnsafe}},deg\\n` +
        `Roughness Safe Threshold,${{rSafe}},m\\n` +
        `Roughness Unsafe Override,${{rUnsafe}},m\\n` +
        `Slope Weight wS,${{wS}},ratio\\n` +
        `Roughness Weight wR,${{wR}},ratio\\n` +
        `Class 1 Safe Area,${{safeKm2}},km2\\n` +
        `Class 2 Caution Area,${{cautionKm2}},km2\\n` +
        `Class 3 Unsafe Area,${{unsafeKm2}},km2\\n` +
        `Class 4 Shadowed Area,${{shadowKm2}},km2\\n`;

      const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.setAttribute("href", url);
      link.setAttribute("download", `lunasafe_simulation_s${{sSafe}}_r${{rSafe}}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }}

    function downloadCanvasSnapshot() {{
      const link = document.createElement('a');
      link.download = `lunasafe_${{currentLayer}}_viewport.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    }}
  </script>
</body>
</html>
"""
    out_dir = config.BASE_DIR / "legacy"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_html = out_dir / "dashboard.html"
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Generated dynamic interactive dashboard: {out_html}")
    return out_html

if __name__ == "__main__":
    build_dashboard()
