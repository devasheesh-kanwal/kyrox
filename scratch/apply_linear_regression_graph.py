# scratch/apply_linear_regression_graph.py
import re
import os
import sys

# 1. GRAPH CSS
GRAPH_CSS = """
    /* ==========================================================================
       24-HOUR LINEAR REGRESSION PREDICTION MODELLING STUDIO
       Marine Bridge Visual Specification (ZERO BLUE)
       ========================================================================== */
    .graph-viewport {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      background-color: var(--bg-hull);
      color: var(--text-chart);
      z-index: 15;
      overflow: hidden;
    }

    .graph-top-hud {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 10px 14px;
      background: var(--bg-bridge);
      border-bottom: 2px solid var(--border-bezel);
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.55);
      flex-shrink: 0;
      z-index: 20;
    }

    .graph-hud-title-lockup {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .graph-badge-icon {
      width: 32px;
      height: 32px;
      border-radius: var(--radius-subtle);
      background: var(--bg-console);
      border: 1.5px solid var(--border-brass);
      display: grid;
      place-items: center;
      color: var(--brass-bright);
      box-shadow: inset 0 0 5px rgba(0, 0, 0, 0.6);
      font-size: 16px;
    }

    .graph-hud-title {
      font-family: var(--font-nav);
      font-size: 14.5px;
      font-weight: 700;
      color: var(--text-chart);
      letter-spacing: 0.5px;
      line-height: 1.2;
    }

    .graph-hud-subtitle {
      font-family: var(--font-telemetry);
      font-size: 10px;
      color: var(--text-muted);
      letter-spacing: 0.3px;
    }

    .graph-var-pills {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }

    .graph-var-pill {
      padding: 5px 11px;
      border-radius: var(--radius-subtle);
      background: var(--bg-console);
      border: 1px solid var(--border-bezel);
      font-family: var(--font-telemetry);
      font-size: 11px;
      color: var(--text-muted);
      cursor: pointer;
      user-select: none;
      transition: all 0.15s ease;
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }

    .graph-var-pill:hover {
      background: var(--bg-console-raised);
      border-color: var(--border-brass);
      color: var(--text-chart);
    }

    .graph-var-pill.active {
      background: var(--brass-base);
      color: var(--text-inverse);
      border-color: var(--brass-bright);
      font-weight: 700;
      box-shadow: 0 0 10px rgba(200, 138, 62, 0.4);
    }

    .graph-top-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .graph-btn-action {
      padding: 5px 10px;
      background: var(--bg-console);
      border: 1px solid var(--border-brass);
      border-radius: var(--radius-subtle);
      color: var(--text-chart);
      font-family: var(--font-telemetry);
      font-size: 11px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      transition: background-color 0.12s, border-color 0.12s;
    }

    .graph-btn-action:hover {
      background: var(--bg-console-raised);
      border-color: var(--brass-bright);
      color: var(--brass-bright);
    }

    .graph-canvas-container {
      flex: 1;
      position: relative;
      width: 100%;
      min-height: 280px;
      background-color: #0E0C0A;
      background-image:
        linear-gradient(to right, rgba(94, 78, 61, 0.09) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(94, 78, 61, 0.09) 1px, transparent 1px);
      background-size: 36px 36px;
      overflow: hidden;
      cursor: crosshair;
    }

    #regressionCanvas {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      display: block;
    }

    .graph-hover-hud {
      position: absolute;
      display: none;
      pointer-events: none;
      background: rgba(24, 20, 17, 0.96);
      border: 1.5px solid var(--brass-base);
      border-radius: var(--radius-subtle);
      padding: 8px 12px;
      font-family: var(--font-telemetry);
      font-size: 11px;
      color: var(--text-chart);
      box-shadow: 0 6px 20px rgba(0, 0, 0, 0.8);
      z-index: 30;
      transform: translate(-50%, -125%);
      white-space: nowrap;
      line-height: 1.4;
    }

    .graph-hover-hud-row {
      display: flex;
      justify-content: space-between;
      gap: 12px;
    }

    .graph-hover-badge {
      display: inline-block;
      padding: 1px 6px;
      border-radius: 2px;
      font-size: 9.5px;
      font-weight: 700;
      text-transform: uppercase;
      margin-top: 3px;
    }

    .graph-hover-badge.danger { background: var(--danger-base); color: #fff; }
    .graph-hover-badge.caution { background: var(--caution-base); color: #12100E; }
    .graph-hover-badge.safe { background: var(--pfz-base); color: #fff; }

    .graph-bottom-telemetry-bar {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(135px, 1fr));
      gap: 8px;
      padding: 8px 14px;
      background: var(--bg-bridge);
      border-top: 1.5px solid var(--border-bezel);
      flex-shrink: 0;
      z-index: 20;
    }

    .graph-bottom-card {
      background: var(--bg-console);
      border: 1px solid var(--border-bezel);
      border-radius: var(--radius-subtle);
      padding: 6px 10px;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .graph-bottom-card-lbl {
      font-family: var(--font-telemetry);
      font-size: 9.5px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.4px;
    }

    .graph-bottom-card-val {
      font-family: var(--font-telemetry);
      font-size: 15px;
      font-weight: 700;
      color: var(--text-chart);
    }

    .graph-bottom-card-sub {
      font-family: var(--font-telemetry);
      font-size: 10px;
      color: var(--brass-bright);
    }

    /* Side Station Graph Panel */
    .regression-side-container {
      display: flex;
      flex-direction: column;
      gap: 12px;
      padding: 12px;
      height: 100%;
      overflow-y: auto;
    }

    .regression-spec-card {
      background: var(--bg-console);
      border: 1px solid var(--border-brass);
      border-radius: var(--radius-subtle);
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .regression-spec-title {
      font-family: var(--font-nav);
      font-size: 13px;
      font-weight: 700;
      color: var(--brass-bright);
      display: flex;
      align-items: center;
      gap: 6px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .regression-metrics-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }

    .regression-metric-item {
      background: var(--bg-input);
      border: 1px solid var(--border-bezel);
      border-radius: var(--radius-subtle);
      padding: 6px 8px;
    }

    .regression-metric-key {
      font-family: var(--font-telemetry);
      font-size: 9.5px;
      color: var(--text-dim);
    }

    .regression-metric-val {
      font-family: var(--font-telemetry);
      font-size: 13.5px;
      font-weight: 700;
      color: var(--text-chart);
    }

    .regression-advisory-box {
      border-radius: var(--radius-subtle);
      padding: 10px 12px;
      border: 1px solid var(--border-bezel);
      font-size: 11.5px;
      line-height: 1.45;
    }

    .regression-advisory-box.danger {
      background: var(--danger-fill);
      border-color: var(--danger-border);
      color: #FFB3A3;
    }

    .regression-advisory-box.caution {
      background: var(--caution-fill);
      border-color: var(--caution-border);
      color: #FFDF9E;
    }

    .regression-advisory-box.safe {
      background: var(--pfz-fill);
      border-color: var(--pfz-border);
      color: #D2E8B0;
    }

    .regression-table-wrap {
      border: 1px solid var(--border-bezel);
      border-radius: var(--radius-subtle);
      overflow: hidden;
      background: var(--bg-console);
    }

    .regression-table {
      width: 100%;
      border-collapse: collapse;
      font-family: var(--font-telemetry);
      font-size: 11px;
    }

    .regression-table th {
      background: var(--bg-bridge);
      color: var(--text-muted);
      padding: 6px 8px;
      text-align: left;
      border-bottom: 1px solid var(--border-bezel);
      font-weight: 600;
      font-size: 10px;
    }

    .regression-table td {
      padding: 5px 8px;
      border-bottom: 1px solid rgba(58, 48, 39, 0.4);
      color: var(--text-chart);
    }

    .regression-table tr:hover td {
      background: var(--bg-console-raised);
    }

    /* Mobile handling for view-graph */
    .bridge-cockpit.view-graph .tactical-chart-station { display: flex; width: 100%; }
    .bridge-cockpit.view-graph .tactical-side-station { display: none; }
"""

# 2. GRAPH VIEWPORT HTML
GRAPH_VIEWPORT_HTML = """
        <!-- 24-HOUR LINEAR REGRESSION PREDICTION MODELLING STUDIO (Replaces Nautical Map in Graph Mode) -->
        <div class="graph-viewport" id="graphViewport" style="display: none;">
          <div class="graph-top-hud">
            <div class="graph-hud-title-lockup">
              <div class="graph-badge-icon">📈</div>
              <div>
                <div class="graph-hud-title" id="txtGraphHeaderTitle">24-Hour Linear Regression Prediction Modelling</div>
                <div class="graph-hud-subtitle" id="txtGraphHeaderSubtitle">सांख्यिकीय रिग्रेशन पूर्वानुमान • OLS Best-Fit Trend Analysis</div>
              </div>
            </div>

            <!-- Target Variable Pills -->
            <div class="graph-var-pills" role="radiogroup" aria-label="Prediction Variables">
              <button class="graph-var-pill active" data-var="wave_height" id="btnVarWave" type="button">
                <span>🌊 <span id="txtVarWave">तरंग ऊंचाई (Wave)</span></span>
              </button>
              <button class="graph-var-pill" data-var="wind_speed" id="btnVarWind" type="button">
                <span>💨 <span id="txtVarWind">पवन गति (Wind)</span></span>
              </button>
              <button class="graph-var-pill" data-var="swell_wave_height" id="btnVarSwell" type="button">
                <span>🌊 <span id="txtVarSwell">स्वेल्ल (Swell)</span></span>
              </button>
              <button class="graph-var-pill" data-var="ocean_current_velocity" id="btnVarCurrent" type="button">
                <span>🧭 <span id="txtVarCurrent">जलधारा (Current)</span></span>
              </button>
              <button class="graph-var-pill" data-var="risk_score" id="btnVarRisk" type="button">
                <span>⚡ <span id="txtVarRisk">जोखिम इंडेक्स (Risk)</span></span>
              </button>
            </div>

            <!-- Graph Actions -->
            <div class="graph-top-actions">
              <button class="graph-btn-action" id="btnRecalcRegression" type="button" title="Recalculate Regression Model">
                <span>🔄</span> <span id="txtBtnRecalc">पुनर्गणना (Recalculate)</span>
              </button>
              <button class="graph-btn-action" id="btnToggleCI" type="button" title="Toggle 95% Confidence Interval Band">
                <span>🎯</span> <span id="txtBtnCI">95% CI बैंड</span>
              </button>
            </div>
          </div>

          <!-- Interactive High-DPI Canvas Stage -->
          <div class="graph-canvas-container" id="graphCanvasContainer">
            <canvas id="regressionCanvas"></canvas>
            <div class="graph-hover-hud" id="graphHoverHud">
              <div class="graph-hover-hud-row">
                <span id="hoverHudTime" style="font-weight: 700; color: var(--brass-bright);">+0h</span>
                <span id="hoverHudVal" style="font-weight: 700; font-size: 13px;">1.45m</span>
              </div>
              <div class="graph-hover-hud-row" style="font-size: 9.5px; color: var(--text-muted);">
                <span>CI [95%]:</span>
                <span id="hoverHudCI">1.25m - 1.65m</span>
              </div>
              <div class="graph-hover-hud-row" style="font-size: 9.5px; color: var(--text-muted);">
                <span>24h Delta:</span>
                <span id="hoverHudDelta">+0.00m</span>
              </div>
              <div class="graph-hover-badge safe" id="hoverHudBadge">SAFE</div>
            </div>
          </div>

          <!-- Bottom Instrument Telemetry Bar -->
          <div class="graph-bottom-telemetry-bar">
            <div class="graph-bottom-card">
              <span class="graph-bottom-card-lbl" id="lblBtmCurrent">वर्तमान प्रेक्षण (0h)</span>
              <span class="graph-bottom-card-val" id="valBtmCurrent">1.45 m</span>
              <span class="graph-bottom-card-sub" id="subBtmCurrent">DGPS Live</span>
            </div>
            <div class="graph-bottom-card">
              <span class="graph-bottom-card-lbl" id="lblBtmMid">+6h मध्याह्न अनुमान</span>
              <span class="graph-bottom-card-val" id="valBtmMid">1.62 m</span>
              <span class="graph-bottom-card-sub" id="subBtmMid">+0.17m Delta</span>
            </div>
            <div class="graph-bottom-card">
              <span class="graph-bottom-card-lbl" id="lblBtmNight">+12h रात्रि अनुमान</span>
              <span class="graph-bottom-card-val" id="valBtmNight">1.84 m</span>
              <span class="graph-bottom-card-sub" id="subBtmNight">+0.39m Delta</span>
            </div>
            <div class="graph-bottom-card">
              <span class="graph-bottom-card-lbl" id="lblBtmDawn">+24h क्षितिज अनुमान</span>
              <span class="graph-bottom-card-val" id="valBtmDawn">2.25 m</span>
              <span class="graph-bottom-card-sub" id="subBtmDawn">+0.80m Surge</span>
            </div>
            <div class="graph-bottom-card" style="border-color: var(--border-brass);">
              <span class="graph-bottom-card-lbl" id="lblBtmPeak">24h अधिकतम चरम</span>
              <span class="graph-bottom-card-val" id="valBtmPeak" style="color: var(--caution-border);">2.25 m</span>
              <span class="graph-bottom-card-sub" id="subBtmPeak">घंटा +24 पर</span>
            </div>
          </div>
        </div>
"""

# 3. TAB BUTTON HTML
TAB_BUTTON_GRAPH = """          <button class="station-tab-btn" id="tabBtnGraph" type="button" role="tab" aria-selected="false" aria-controls="panelGraph">
            <span id="txtTabGraphLabel">📈 24h सांख्यिकीय ग्राफ</span>
          </button>"""

# 4. PANEL 3 HTML
PANEL_GRAPH_HTML = """        <!-- PANEL 3: 24-HOUR LINEAR REGRESSION ANALYTICS PANEL -->
        <div class="station-content-panel" id="panelGraph" role="tabpanel" aria-labelledby="tabBtnGraph">
          <div class="regression-side-container">

            <div class="regression-spec-card">
              <div class="regression-spec-title">
                <span>📐 OLS मॉडल सांख्यिकी (Model Specs)</span>
              </div>
              <div class="regression-metrics-grid">
                <div class="regression-metric-item">
                  <div class="regression-metric-key">रिग्रेशन समीकरण (Equation)</div>
                  <div class="regression-metric-val" id="txtRegEquation" style="font-size: 11px;">y = 0.033x + 1.45</div>
                </div>
                <div class="regression-metric-item">
                  <div class="regression-metric-key">निर्धारण गुणांक (R² Fit)</div>
                  <div class="regression-metric-val" id="txtRegR2">0.863</div>
                </div>
                <div class="regression-metric-item">
                  <div class="regression-metric-key">ढाल / दर (Slope m)</div>
                  <div class="regression-metric-val" id="txtRegSlope">+0.033/h</div>
                </div>
                <div class="regression-metric-item">
                  <div class="regression-metric-key">मानक त्रुटि (Std Error)</div>
                  <div class="regression-metric-val" id="txtRegSE">0.098</div>
                </div>
              </div>
            </div>

            <!-- Tactical Advisory based on linear regression -->
            <div class="regression-advisory-box caution" id="boxRegAdvisory">
              <div style="font-weight: 700; margin-bottom: 4px; display: flex; align-items: center; gap: 5px;">
                <span>⚠️</span> <span id="txtRegAdvisoryTitle">24-घंटे सांख्यिकीय समुद्री सलाह</span>
              </div>
              <div id="txtRegAdvisoryBody">
                सतर्कता: तरंग ऊंचाई में अगले 24 घंटों में +0.7m की वृद्धि का रुझान है। मौसम पर सतत निगरानी रखें।
              </div>
            </div>

            <!-- Hour-by-Hour Forecast Table -->
            <div class="regression-spec-card">
              <div class="regression-spec-title">
                <span>⏱️ 24-घंटे घंटावार पूर्वानुमान लॉग</span>
              </div>
              <div class="regression-table-wrap" style="max-height: 240px; overflow-y: auto;">
                <table class="regression-table">
                  <thead>
                    <tr>
                      <th>समय</th>
                      <th>अनुमानित मान</th>
                      <th>95% CI रेंज</th>
                      <th>सुरक्षा स्थिति</th>
                    </tr>
                  </thead>
                  <tbody id="tblRegressionRows">
                    <!-- Dynamic rows from +1h to +24h -->
                  </tbody>
                </table>
              </div>
            </div>

          </div>
        </div>
"""

# 5. MOBILE DOCK BUTTON HTML
MOB_DOCK_GRAPH_HTML = """      <button class="mobile-dock-btn" id="mobNavGraph" type="button">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="20" x2="18" y2="10"></line>
          <line x1="12" y1="20" x2="12" y2="4"></line>
          <line x1="6" y1="20" x2="6" y2="14"></line>
          <path d="M2 18l6-6 4 4 10-10"></path>
        </svg>
        <span id="txtMobGraph">24h ग्राफ</span>
      </button>"""

print("HTML modules prepared successfully.")
