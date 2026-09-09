# scratch/update_all_9_files.py
import re
import os
import sys
from validate_js import parse_js

html_files = [
    'alerts.html',
    'chat.html',
    'index.html',
    'map.html',
    'map/map.html',
    'Frontend/Alerts/alerts.html',
    'Frontend/Chat/chat.html',
    'Frontend/Map/map.html',
    'Frontend/index.html'
]

# 1. CSS to insert before </style>
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

# 2. HTML to insert inside .tactical-chart-station after #chartViewport
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

# 3. TAB BUTTON
TAB_BTN_HTML = """          <button class="station-tab-btn" id="tabBtnGraph" type="button" role="tab" aria-selected="false" aria-controls="panelGraph">
            <span id="txtTabGraphLabel">📈 24h सांख्यिकीय ग्राफ</span>
          </button>
        </nav>"""

# 4. SIDE PANEL 3
PANEL_3_HTML = """
        <!-- PANEL 3: 24-HOUR LINEAR REGRESSION ANALYTICS PANEL -->
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
      </aside>"""

# 5. MOBILE DOCK BUTTON
MOB_DOCK_BTN_HTML = """      <button class="mobile-dock-btn" id="mobNavGraph" type="button">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="20" x2="18" y2="10"></line>
          <line x1="12" y1="20" x2="12" y2="4"></line>
          <line x1="6" y1="20" x2="6" y2="14"></line>
          <path d="M2 18l6-6 4 4 10-10"></path>
        </svg>
        <span id="txtMobGraph">24h ग्राफ</span>
      </button>
    </nav>"""

# 6. TAB SWITCHING LOGIC TO REPLACE
OLD_SWITCH_TABS_SNIPPET = """    // Sub-Navigation Tab Switching (Alerts <-> Chat) in Companion Station
    const tabBtnAlerts = document.getElementById('tabBtnAlerts');
    const tabBtnChat = document.getElementById('tabBtnChat');
    const panelAlerts = document.getElementById('panelAlerts');
    const panelChat = document.getElementById('panelChat');

    function switchStationTab(target) {
      currentStationTab = target;
      tabBtnAlerts.classList.toggle('active', target === 'alerts');
      tabBtnChat.classList.toggle('active', target === 'chat');
      tabBtnAlerts.setAttribute('aria-selected', target === 'alerts' ? 'true' : 'false');
      tabBtnChat.setAttribute('aria-selected', target === 'chat' ? 'true' : 'false');

      panelAlerts.classList.toggle('active', target === 'alerts');
      panelChat.classList.toggle('active', target === 'chat');

      // Keep mobile bottom dock in sync when switching station tabs
      if (currentDeviceMode === 'phone' || window.innerWidth < 960) {
        mobNavChart.classList.remove('active');
        mobNavAlerts.classList.toggle('active', target === 'alerts');
        mobNavChat.classList.toggle('active', target === 'chat');
      }
    }

    tabBtnAlerts.addEventListener('click', () => switchStationTab('alerts'));
    tabBtnChat.addEventListener('click', () => switchStationTab('chat'));

    // Mobile Dock Tab Switching (< 960px Viewports)
    const bridgeCockpit = document.getElementById('bridgeCockpit');
    const mobNavChart = document.getElementById('mobNavChart');
    const mobNavAlerts = document.getElementById('mobNavAlerts');
    const mobNavChat = document.getElementById('mobNavChat');

    function switchMobileView(view) {
      mobNavChart.classList.toggle('active', view === 'chart');
      mobNavAlerts.classList.toggle('active', view === 'alerts');
      mobNavChat.classList.toggle('active', view === 'chat');

      bridgeCockpit.classList.remove('view-alerts', 'view-chat');
      if (view === 'alerts') {
        bridgeCockpit.classList.add('view-alerts');
        switchStationTab('alerts');
      } else if (view === 'chat') {
        bridgeCockpit.classList.add('view-chat');
        switchStationTab('chat');
      }
    }

    mobNavChart.addEventListener('click', () => switchMobileView('chart'));
    mobNavAlerts.addEventListener('click', () => switchMobileView('alerts'));
    mobNavChat.addEventListener('click', () => switchMobileView('chat'));"""

NEW_SWITCH_TABS_SNIPPET = """    // Sub-Navigation Tab Switching (Alerts <-> Chat <-> Graph) in Companion Station
    const tabBtnAlerts = document.getElementById('tabBtnAlerts');
    const tabBtnChat = document.getElementById('tabBtnChat');
    const tabBtnGraph = document.getElementById('tabBtnGraph');
    const panelAlerts = document.getElementById('panelAlerts');
    const panelChat = document.getElementById('panelChat');
    const panelGraph = document.getElementById('panelGraph');
    const mobNavGraph = document.getElementById('mobNavGraph');
    const graphViewport = document.getElementById('graphViewport');
    const chartViewport = document.getElementById('chartViewport');

    function switchStationTab(target) {
      currentStationTab = target;
      tabBtnAlerts.classList.toggle('active', target === 'alerts');
      tabBtnChat.classList.toggle('active', target === 'chat');
      if (tabBtnGraph) tabBtnGraph.classList.toggle('active', target === 'graph');
      tabBtnAlerts.setAttribute('aria-selected', target === 'alerts' ? 'true' : 'false');
      tabBtnChat.setAttribute('aria-selected', target === 'chat' ? 'true' : 'false');
      if (tabBtnGraph) tabBtnGraph.setAttribute('aria-selected', target === 'graph' ? 'true' : 'false');

      panelAlerts.classList.toggle('active', target === 'alerts');
      panelChat.classList.toggle('active', target === 'chat');
      if (panelGraph) panelGraph.classList.toggle('active', target === 'graph');

      // REPLACE MAP WITH GRAPH WHEN GRAPH SECTION IS ACTIVE
      if (chartViewport && graphViewport) {
        if (target === 'graph') {
          chartViewport.style.display = 'none';
          graphViewport.style.display = 'flex';
          if (typeof renderRegressionStudio === 'function') {
            renderRegressionStudio();
          }
        } else {
          graphViewport.style.display = 'none';
          chartViewport.style.display = '';
          if (leafletMap) {
            setTimeout(function() { leafletMap.invalidateSize(); }, 60);
          }
        }
      }

      // Keep mobile bottom dock in sync when switching station tabs
      if (currentDeviceMode === 'phone' || window.innerWidth < 960) {
        mobNavChart.classList.toggle('active', target === 'chart');
        mobNavAlerts.classList.toggle('active', target === 'alerts');
        mobNavChat.classList.toggle('active', target === 'chat');
        if (mobNavGraph) mobNavGraph.classList.toggle('active', target === 'graph');
      }
    }

    tabBtnAlerts.addEventListener('click', () => switchStationTab('alerts'));
    tabBtnChat.addEventListener('click', () => switchStationTab('chat'));
    if (tabBtnGraph) tabBtnGraph.addEventListener('click', () => switchStationTab('graph'));

    // Mobile Dock Tab Switching (< 960px Viewports)
    const bridgeCockpit = document.getElementById('bridgeCockpit');
    const mobNavChart = document.getElementById('mobNavChart');
    const mobNavAlerts = document.getElementById('mobNavAlerts');
    const mobNavChat = document.getElementById('mobNavChat');

    function switchMobileView(view) {
      mobNavChart.classList.toggle('active', view === 'chart');
      mobNavAlerts.classList.toggle('active', view === 'alerts');
      mobNavChat.classList.toggle('active', view === 'chat');
      if (mobNavGraph) mobNavGraph.classList.toggle('active', view === 'graph');

      bridgeCockpit.classList.remove('view-alerts', 'view-chat', 'view-graph');
      if (view === 'alerts') {
        bridgeCockpit.classList.add('view-alerts');
        switchStationTab('alerts');
      } else if (view === 'chat') {
        bridgeCockpit.classList.add('view-chat');
        switchStationTab('chat');
      } else if (view === 'graph') {
        bridgeCockpit.classList.add('view-graph');
        switchStationTab('graph');
      } else {
        switchStationTab('alerts');
        if (chartViewport) chartViewport.style.display = '';
        if (graphViewport) graphViewport.style.display = 'none';
        if (leafletMap) setTimeout(function() { leafletMap.invalidateSize(); }, 60);
      }
    }

    mobNavChart.addEventListener('click', () => switchMobileView('chart'));
    mobNavAlerts.addEventListener('click', () => switchMobileView('alerts'));
    mobNavChat.addEventListener('click', () => switchMobileView('chat'));
    if (mobNavGraph) mobNavGraph.addEventListener('click', () => switchMobileView('graph'));"""

# 7. REGRESSION JS ENGINE
REGRESSION_JS_BLOCK = """
    /* ==========================================================================
       24-HOUR LINEAR REGRESSION PREDICTION MODELLING ENGINE (JavaScript Engine)
       ========================================================================== */
    const regressionCanvas = document.getElementById('regressionCanvas');
    const graphCanvasContainer = document.getElementById('graphCanvasContainer');
    const graphHoverHud = document.getElementById('graphHoverHud');

    // Prediction Variable Specifications & Maritime Threshold Limits
    const REG_VARIABLE_CONFIGS = {
      wave_height: {
        unit: 'm',
        label: 'Significant Wave Height',
        labelHi: 'तरंग ऊंचाई',
        labelTa: 'அலை உயரம்',
        safeMax: 1.5,
        cautionMax: 2.5,
        dangerMin: 2.5,
        minPhys: 0.2,
        maxPhys: 6.0,
        defaultAnchor: 1.45,
        slopeSim: 0.033
      },
      wind_speed: {
        unit: 'kts',
        label: 'Wind Speed',
        labelHi: 'पवन गति',
        labelTa: 'காற்று வேகம்',
        safeMax: 15.0,
        cautionMax: 25.0,
        dangerMin: 25.0,
        minPhys: 2.0,
        maxPhys: 55.0,
        defaultAnchor: 18.2,
        slopeSim: 0.38
      },
      swell_wave_height: {
        unit: 'm',
        label: 'Swell Wave Height',
        labelHi: 'स्वेल्ल तरंग ऊंचाई',
        labelTa: 'சுழல் அலை உயரம்',
        safeMax: 1.2,
        cautionMax: 2.0,
        dangerMin: 2.0,
        minPhys: 0.1,
        maxPhys: 5.0,
        defaultAnchor: 1.15,
        slopeSim: 0.024
      },
      ocean_current_velocity: {
        unit: 'm/s',
        label: 'Ocean Current Velocity',
        labelHi: 'जलधारा गति',
        labelTa: 'நீரோட்ட வேகம்',
        safeMax: 0.8,
        cautionMax: 1.5,
        dangerMin: 1.5,
        minPhys: 0.1,
        maxPhys: 3.5,
        defaultAnchor: 0.85,
        slopeSim: 0.016
      },
      risk_score: {
        unit: 'idx',
        label: 'Marine Risk Index',
        labelHi: 'सामरिक जोखिम इंडेक्स',
        labelTa: 'கடல் ஆபத்து குறியீடு',
        safeMax: 35.0,
        cautionMax: 70.0,
        dangerMin: 70.0,
        minPhys: 5.0,
        maxPhys: 100.0,
        defaultAnchor: 42.0,
        slopeSim: 1.15
      }
    };

    let activeRegVar = 'wave_height';
    let regShowCI = true;
    let regressionDataCache = null;
    let hoverActiveIndex = null;

    // Mathematical Ordinary Least Squares (OLS) Solver
    function computeClientOLS(xArr, yArr) {
      const n = xArr.length;
      if (n < 2) {
        return { slope: 0, intercept: yArr[0] || 0, rSquared: 0, stdError: 0, equation: 'y = 0.00x + 0.00' };
      }
      let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, sumY2 = 0;
      for (let i = 0; i < n; i++) {
        sumX += xArr[i];
        sumY += yArr[i];
        sumXY += xArr[i] * yArr[i];
        sumX2 += xArr[i] * xArr[i];
        sumY2 += yArr[i] * yArr[i];
      }
      const denom = (n * sumX2) - (sumX * sumX);
      const slope = Math.abs(denom) > 1e-9 ? ((n * sumXY) - (sumX * sumY)) / denom : 0;
      const intercept = (sumY - (slope * sumX)) / n;

      const yMean = sumY / n;
      let ssTot = 0, ssRes = 0;
      for (let i = 0; i < n; i++) {
        const yPred = (slope * xArr[i]) + intercept;
        ssTot += Math.pow(yArr[i] - yMean, 2);
        ssRes += Math.pow(yArr[i] - yPred, 2);
      }
      const rSquared = ssTot > 1e-9 ? Math.max(0, Math.min(1, 1 - (ssRes / ssTot))) : 0.85;
      const stdError = Math.sqrt(Math.max(0, ssRes / Math.max(1, n - 2)));
      const eqSign = intercept >= 0 ? '+' : '-';
      const equation = 'y = ' + slope.toFixed(4) + 'x ' + eqSign + ' ' + Math.abs(intercept).toFixed(3);

      return {
        slope: slope,
        intercept: intercept,
        rSquared: rSquared,
        stdError: stdError,
        equation: equation
      };
    }

    // Generate Synthesized Marine History anchored at current telemetry
    function generateSyntheticHistory(varKey, anchorVal, pastHours) {
      const cfg = REG_VARIABLE_CONFIGS[varKey];
      const anchor = (anchorVal !== undefined && anchorVal !== null) ? anchorVal : cfg.defaultAnchor;
      const history = [];
      const now = new Date();

      for (let h = -pastHours; h <= 0; h++) {
        const dt = new Date(now.getTime() + h * 3600 * 1000);
        const tidalOsc = Math.sin(h * (2 * Math.PI / 12.4)) * (anchor * 0.12);
        const gustJitter = Math.cos(h * (2 * Math.PI / 6.0)) * (anchor * 0.05);
        const trend = cfg.slopeSim * h;
        let val = anchor + trend + tidalOsc + gustJitter;
        val = Math.max(cfg.minPhys, Math.min(cfg.maxPhys, val));
        history.push({
          hour_offset: h,
          timestamp: dt.toISOString(),
          time_label: (dt.getUTCHours() < 10 ? '0' : '') + dt.getUTCHours() + ':00 UTC',
          value: parseFloat(val.toFixed(2)),
          is_historical: true,
          is_current: (h === 0)
        });
      }
      history[history.length - 1].value = parseFloat(anchor.toFixed(2));
      return history;
    }

    // Local 24-Hour Prediction Engine (offline-resilient fallback)
    function computeLocal24hPrediction(varKey) {
      const cfg = REG_VARIABLE_CONFIGS[varKey];
      const history = generateSyntheticHistory(varKey, null, 24);
      const xHist = history.map(function(pt) { return pt.hour_offset; });
      const yHist = history.map(function(pt) { return pt.value; });

      const metrics = computeClientOLS(xHist, yHist);
      const slope = metrics.slope;
      const intercept = metrics.intercept;
      const se = metrics.stdError;

      const xMean = xHist.reduce(function(a, b) { return a + b; }, 0) / xHist.length;
      const sumXDiffSq = Math.max(1e-6, xHist.reduce(function(acc, x) { return acc + Math.pow(x - xMean, 2); }, 0));
      const n = xHist.length;

      const predictions = [];
      const now = new Date();
      let maxVal = -1e9;
      let maxValHour = 0;

      for (let h = 1; h <= 24; h++) {
        const dt = new Date(now.getTime() + h * 3600 * 1000);
        let predVal = (slope * h) + intercept;
        predVal = Math.max(cfg.minPhys, Math.min(cfg.maxPhys, predVal));

        const leverage = Math.sqrt(1.0 + (1.0 / n) + (Math.pow(h - xMean, 2) / sumXDiffSq));
        const margin = 1.96 * se * leverage;
        const ciLower = Math.max(cfg.minPhys, predVal - margin);
        const ciUpper = Math.min(cfg.maxPhys, predVal + margin);

        let safetyStatus = 'safe';
        if (predVal >= cfg.dangerMin) {
          safetyStatus = 'danger';
        } else if (predVal >= cfg.cautionMax || (predVal >= cfg.safeMax && slope > 0)) {
          safetyStatus = 'caution';
        }

        if (predVal > maxVal) {
          maxVal = predVal;
          maxValHour = h;
        }

        const hStr = (dt.getHours() < 10 ? '0' : '') + dt.getHours() + ':' + (dt.getMinutes() < 10 ? '0' : '') + dt.getMinutes();
        predictions.push({
          hour_offset: h,
          timestamp: dt.toISOString(),
          time_label: '+' + h + 'h (' + hStr + ')',
          predicted_value: parseFloat(predVal.toFixed(2)),
          ci_lower: parseFloat(ciLower.toFixed(2)),
          ci_upper: parseFloat(ciUpper.toFixed(2)),
          safety_status: safetyStatus,
          delta_from_now: parseFloat((predVal - yHist[yHist.length - 1]).toFixed(2))
        });
      }

      const valNow = yHist[yHist.length - 1];
      const val24h = predictions[predictions.length - 1].predicted_value;
      const delta24h = parseFloat((val24h - valNow).toFixed(2));

      let overallStatus = 'safe';
      if (maxVal >= cfg.dangerMin) overallStatus = 'danger';
      else if (maxVal >= cfg.safeMax) overallStatus = 'caution';

      return {
        success: true,
        variable: varKey,
        unit: cfg.unit,
        label: cfg.label,
        thresholds: {
          safe_max: cfg.safeMax,
          caution_max: cfg.cautionMax,
          danger_min: cfg.dangerMin
        },
        current_value: valNow,
        horizon_hours: 24,
        past_hours: 24,
        metrics: metrics,
        summary: {
          trend: slope > 0.02 ? 'SHARP_INCREASE' : (slope > 0.005 ? 'MODERATE_RISE' : 'STABLE'),
          trend_label: slope > 0.005 ? 'वृद्धि (Rising)' : 'स्थिर (Stable)',
          overall_status: overallStatus,
          val_now: valNow,
          val_24h: val24h,
          delta_24h: delta24h,
          peak_val: parseFloat(maxVal.toFixed(2)),
          peak_hour: maxValHour,
          advisory_hi: overallStatus === 'danger'
            ? ('चेतावनी: अगले 24 घंटों में ' + cfg.labelHi + ' ' + maxVal.toFixed(1) + cfg.unit + ' तक पहुंचने का अनुमान है। छोटी नौकाएं बंदरगाह लौटें।')
            : ('सतर्कता: ' + cfg.labelHi + ' में अगले 24 घंटों में ' + (delta24h >= 0 ? '+' : '') + delta24h.toFixed(1) + cfg.unit + ' परिवर्तन का अनुमान है।'),
          advisory_en: overallStatus === 'danger'
            ? ('Warning: 24h regression projects ' + cfg.label + ' reaching hazardous ' + maxVal.toFixed(1) + cfg.unit + ' peak. Craft <20m stay inshore.')
            : ('Advisory: Linear trend projects ' + cfg.label + ' shifting ' + (delta24h >= 0 ? '+' : '') + delta24h.toFixed(1) + cfg.unit + ' over 24h.'),
          advisory_ta: overallStatus === 'danger'
            ? ('எச்சரிக்கை: அடுத்த 24 மணி நேரத்தில் ' + cfg.labelTa + ' ' + maxVal.toFixed(1) + cfg.unit + ' வரை எட்ட வாய்ப்புள்ளது.')
            : ('கவனம்: அடுத்த 24 மணி நேரத்தில் ' + cfg.labelTa + ' ' + (delta24h >= 0 ? '+' : '') + delta24h.toFixed(1) + cfg.unit + ' மாறுபட வாய்ப்புள்ளது.')
        },
        history: history,
        predictions: predictions
      };
    }

    // Asynchronously fetch from Backend API or compute locally
    async function loadRegressionData(varKey) {
      activeRegVar = varKey;
      const cfg = REG_VARIABLE_CONFIGS[varKey];
      const targetLat = (typeof currentLat !== 'undefined' && currentLat) ? currentLat : 15.246;
      const targetLon = (typeof currentLon !== 'undefined' && currentLon) ? currentLon : 73.803;

      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(function() { controller.abort(); }, 3500);
        const resp = await fetch('http://127.0.0.1:8000/predictions/linear-regression?variable=' + encodeURIComponent(varKey) + '&lat=' + targetLat + '&lon=' + targetLon, {
          signal: controller.signal
        });
        clearTimeout(timeoutId);
        if (resp.ok) {
          const data = await resp.json();
          if (data && data.predictions && data.predictions.length > 0) {
            regressionDataCache = data;
            renderRegressionStudio();
            return;
          }
        }
      } catch (e) {
        // API offline or request timed out, proceed with deterministic calculation
      }

      regressionDataCache = computeLocal24hPrediction(varKey);
      renderRegressionStudio();
    }

    // High-DPI Canvas Rendering Engine
    function drawRegressionCanvas() {
      if (!regressionCanvas || !graphCanvasContainer || !regressionDataCache) return;

      const container = graphCanvasContainer;
      const w = container.clientWidth;
      const h = container.clientHeight;
      if (w <= 0 || h <= 0) return;

      const dpr = window.devicePixelRatio || 1;
      regressionCanvas.width = w * dpr;
      regressionCanvas.height = h * dpr;

      const ctx = regressionCanvas.getContext('2d');
      ctx.resetTransform();
      ctx.scale(dpr, dpr);

      ctx.clearRect(0, 0, w, h);

      const data = regressionDataCache;
      const cfg = REG_VARIABLE_CONFIGS[activeRegVar] || REG_VARIABLE_CONFIGS.wave_height;
      const history = data.history || [];
      const predictions = data.predictions || [];

      const padLeft = 60;
      const padRight = 30;
      const padTop = 35;
      const padBottom = 45;
      const plotW = Math.max(10, w - padLeft - padRight);
      const plotH = Math.max(10, h - padTop - padBottom);

      const tMin = -24;
      const tMax = 24;

      // Determine dynamic Y bounds
      let yMinVal = 0;
      let yMaxVal = Math.max(cfg.dangerMin * 1.25, 4.0);
      history.forEach(function(pt) {
        if (pt.value > yMaxVal) yMaxVal = pt.value * 1.15;
      });
      predictions.forEach(function(pt) {
        if (pt.predicted_value > yMaxVal) yMaxVal = pt.predicted_value * 1.15;
        if (pt.ci_upper > yMaxVal) yMaxVal = pt.ci_upper * 1.1;
      });

      function toX(t) {
        return padLeft + ((t - tMin) / (tMax - tMin)) * plotW;
      }

      function toY(val) {
        return padTop + plotH - ((val - yMinVal) / (yMaxVal - yMinVal)) * plotH;
      }

      // 1. Shaded Threshold Background Bands
      const ySafeMax = toY(cfg.safeMax);
      const yCautionMax = toY(cfg.cautionMax);
      const yZero = toY(0);

      // Safe band
      ctx.fillStyle = 'rgba(116, 128, 78, 0.07)';
      ctx.fillRect(padLeft, ySafeMax, plotW, yZero - ySafeMax);

      // Caution band
      ctx.fillStyle = 'rgba(212, 144, 59, 0.08)';
      ctx.fillRect(padLeft, yCautionMax, plotW, ySafeMax - yCautionMax);

      // Danger band
      ctx.fillStyle = 'rgba(196, 84, 58, 0.12)';
      ctx.fillRect(padLeft, padTop, plotW, yCautionMax - padTop);

      // 2. Threshold Reference Lines
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);

      // Danger line
      ctx.strokeStyle = 'rgba(222, 99, 71, 0.55)';
      ctx.beginPath();
      ctx.moveTo(padLeft, yCautionMax);
      ctx.lineTo(padLeft + plotW, yCautionMax);
      ctx.stroke();

      ctx.fillStyle = 'rgba(255, 133, 107, 0.85)';
      ctx.font = '10px monospace';
      ctx.fillText('DANGER THRESHOLD (' + cfg.dangerMin + cfg.unit + ')', padLeft + 8, yCautionMax - 4);

      // Safe line
      ctx.strokeStyle = 'rgba(140, 155, 94, 0.55)';
      ctx.beginPath();
      ctx.moveTo(padLeft, ySafeMax);
      ctx.lineTo(padLeft + plotW, ySafeMax);
      ctx.stroke();

      ctx.fillStyle = 'rgba(169, 187, 115, 0.85)';
      ctx.fillText('SAFE OPERATIONAL LIMIT (' + cfg.safeMax + cfg.unit + ')', padLeft + 8, ySafeMax - 4);

      ctx.setLineDash([]);

      // 3. Grid Lines & Axis Labels
      ctx.strokeStyle = 'rgba(94, 78, 61, 0.35)';
      ctx.fillStyle = '#A89B88';
      ctx.font = '10.5px monospace';

      // Horizontal Value Grid
      const yTicks = 5;
      for (let i = 0; i <= yTicks; i++) {
        const val = yMinVal + (i / yTicks) * (yMaxVal - yMinVal);
        const yPos = toY(val);
        ctx.beginPath();
        ctx.moveTo(padLeft, yPos);
        ctx.lineTo(padLeft + plotW, yPos);
        ctx.stroke();
        ctx.fillText(val.toFixed(1) + ' ' + cfg.unit, 8, yPos + 3.5);
      }

      // Vertical Time Grid
      const tHours = [-24, -18, -12, -6, 0, 6, 12, 18, 24];
      tHours.forEach(function(h) {
        const xPos = toX(h);
        ctx.beginPath();
        ctx.moveTo(xPos, padTop);
        ctx.lineTo(xPos, padTop + plotH);
        ctx.stroke();

        let label = h === 0 ? 'NOW (0h)' : (h > 0 ? '+' + h + 'h' : h + 'h');
        ctx.fillText(label, xPos - (h === 0 ? 22 : 12), padTop + plotH + 18);
      });

      // 4. Shaded 95% Confidence Interval Band (Future Horizon)
      if (regShowCI && predictions.length > 0) {
        ctx.fillStyle = 'rgba(200, 138, 62, 0.16)';
        ctx.strokeStyle = 'rgba(220, 155, 74, 0.45)';
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 3]);

        ctx.beginPath();
        ctx.moveTo(toX(0), toY(history[history.length - 1].value));
        predictions.forEach(function(pt) {
          ctx.lineTo(toX(pt.hour_offset), toY(pt.ci_upper));
        });
        for (let i = predictions.length - 1; i >= 0; i--) {
          ctx.lineTo(toX(predictions[i].hour_offset), toY(predictions[i].ci_lower));
        }
        ctx.lineTo(toX(0), toY(history[history.length - 1].value));
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // 5. Historical Observed Telemetry Curve (-24h to 0h)
      if (history.length > 1) {
        ctx.strokeStyle = 'rgba(239, 234, 225, 0.85)';
        ctx.lineWidth = 2.2;
        ctx.beginPath();
        history.forEach(function(pt, idx) {
          const px = toX(pt.hour_offset);
          const py = toY(pt.value);
          if (idx === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        });
        ctx.stroke();

        ctx.fillStyle = '#EFEAE1';
        history.forEach(function(pt) {
          const px = toX(pt.hour_offset);
          const py = toY(pt.value);
          ctx.beginPath();
          ctx.arc(px, py, 3, 0, Math.PI * 2);
          ctx.fill();
        });
      }

      // 6. Vertical "PRESENT TIME (0h)" Marker
      const xZero = toX(0);
      ctx.strokeStyle = '#DC9B4A';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(xZero, padTop);
      ctx.lineTo(xZero, padTop + plotH);
      ctx.stroke();

      const curY = toY(history[history.length - 1].value);
      ctx.fillStyle = '#FFD152';
      ctx.beginPath();
      ctx.arc(xZero, curY, 6, 0, Math.PI * 2);
      ctx.fill();

      // 7. Linear Regression Trendline (y = mx + c)
      const slope = data.metrics.slope;
      const intercept = data.metrics.intercept;

      ctx.strokeStyle = '#C88A3E';
      ctx.lineWidth = 2.5;
      ctx.setLineDash([6, 4]);
      ctx.beginPath();
      ctx.moveTo(toX(-24), toY((slope * -24) + intercept));
      ctx.lineTo(toX(24), toY((slope * 24) + intercept));
      ctx.stroke();
      ctx.setLineDash([]);

      // 8. Future 24 Hourly Prediction Nodes
      predictions.forEach(function(pt) {
        const px = toX(pt.hour_offset);
        const py = toY(pt.predicted_value);

        let nodeColor = '#8C9B5E';
        if (pt.safety_status === 'danger') nodeColor = '#DE6347';
        else if (pt.safety_status === 'caution') nodeColor = '#E8A44C';

        ctx.fillStyle = nodeColor;
        ctx.beginPath();
        ctx.arc(px, py, 4, 0, Math.PI * 2);
        ctx.fill();

        ctx.strokeStyle = '#12100E';
        ctx.lineWidth = 1.2;
        ctx.stroke();
      });

      // 9. Interactive Crosshair and Inspection Tooltip
      if (hoverActiveIndex !== null) {
        let hoverPt = null;
        let isFuture = false;

        if (hoverActiveIndex <= 0) {
          const histIdx = hoverActiveIndex + 24;
          if (histIdx >= 0 && histIdx < history.length) {
            hoverPt = history[histIdx];
          }
        } else {
          const predIdx = hoverActiveIndex - 1;
          if (predIdx >= 0 && predIdx < predictions.length) {
            hoverPt = predictions[predIdx];
            isFuture = true;
          }
        }

        if (hoverPt) {
          const hX = toX(hoverPt.hour_offset);
          const hVal = isFuture ? hoverPt.predicted_value : hoverPt.value;
          const hY = toY(hVal);

          ctx.strokeStyle = 'rgba(220, 155, 74, 0.75)';
          ctx.lineWidth = 1;
          ctx.setLineDash([2, 2]);

          ctx.beginPath();
          ctx.moveTo(hX, padTop);
          ctx.lineTo(hX, padTop + plotH);
          ctx.stroke();

          ctx.beginPath();
          ctx.moveTo(padLeft, hY);
          ctx.lineTo(padLeft + plotW, hY);
          ctx.stroke();
          ctx.setLineDash([]);

          ctx.strokeStyle = '#FFF';
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(hX, hY, 8, 0, Math.PI * 2);
          ctx.stroke();

          if (graphHoverHud) {
            graphHoverHud.style.display = 'block';
            graphHoverHud.style.left = hX + 'px';
            graphHoverHud.style.top = hY + 'px';

            document.getElementById('hoverHudTime').textContent = hoverPt.time_label || ('Hour ' + hoverPt.hour_offset);
            document.getElementById('hoverHudVal').textContent = hVal.toFixed(2) + ' ' + cfg.unit;

            if (isFuture) {
              document.getElementById('hoverHudCI').textContent = hoverPt.ci_lower + ' - ' + hoverPt.ci_upper + ' ' + cfg.unit;
              document.getElementById('hoverHudDelta').textContent = (hoverPt.delta_from_now >= 0 ? '+' : '') + hoverPt.delta_from_now + ' ' + cfg.unit;
              const badge = document.getElementById('hoverHudBadge');
              badge.className = 'graph-hover-badge ' + hoverPt.safety_status;
              badge.textContent = hoverPt.safety_status.toUpperCase();
            } else {
              document.getElementById('hoverHudCI').textContent = 'Observed';
              document.getElementById('hoverHudDelta').textContent = (hoverPt.hour_offset === 0 ? 'Anchor' : (hoverPt.hour_offset + 'h past'));
              const badge = document.getElementById('hoverHudBadge');
              badge.className = 'graph-hover-badge safe';
              badge.textContent = hoverPt.hour_offset === 0 ? 'LIVE FIX' : 'LOGGED';
            }
          }
        }
      } else if (graphHoverHud) {
        graphHoverHud.style.display = 'none';
      }
    }

    // Update Bottom Instrument Readouts and Side Panel
    function updateRegressionHUD() {
      if (!regressionDataCache) return;
      const d = regressionDataCache;
      const s = d.summary;
      const m = d.metrics;
      const p = d.predictions || [];

      // Bottom Instrument Telemetry
      const valCurrentEl = document.getElementById('valBtmCurrent');
      const valMidEl = document.getElementById('valBtmMid');
      const valNightEl = document.getElementById('valBtmNight');
      const valDawnEl = document.getElementById('valBtmDawn');
      const valPeakEl = document.getElementById('valBtmPeak');

      if (valCurrentEl) valCurrentEl.textContent = s.val_now.toFixed(2) + ' ' + d.unit;
      if (valMidEl && p.length >= 6) valMidEl.textContent = p[5].predicted_value.toFixed(2) + ' ' + d.unit;
      if (valNightEl && p.length >= 12) valNightEl.textContent = p[11].predicted_value.toFixed(2) + ' ' + d.unit;
      if (valDawnEl && p.length >= 24) valDawnEl.textContent = p[23].predicted_value.toFixed(2) + ' ' + d.unit;
      if (valPeakEl) valPeakEl.textContent = s.peak_val.toFixed(2) + ' ' + d.unit;

      const subMid = document.getElementById('subBtmMid');
      const subNight = document.getElementById('subBtmNight');
      const subDawn = document.getElementById('subBtmDawn');
      const subPeak = document.getElementById('subBtmPeak');

      if (subMid && p.length >= 6) subMid.textContent = (p[5].delta_from_now >= 0 ? '+' : '') + p[5].delta_from_now.toFixed(2) + d.unit + ' Delta';
      if (subNight && p.length >= 12) subNight.textContent = (p[11].delta_from_now >= 0 ? '+' : '') + p[11].delta_from_now.toFixed(2) + d.unit + ' Delta';
      if (subDawn && p.length >= 24) subDawn.textContent = (p[23].delta_from_now >= 0 ? '+' : '') + p[23].delta_from_now.toFixed(2) + d.unit + ' Net';
      if (subPeak) subPeak.textContent = 'Hour +' + s.peak_hour;

      // Side Station Specs
      const eqEl = document.getElementById('txtRegEquation');
      const r2El = document.getElementById('txtRegR2');
      const slopeEl = document.getElementById('txtRegSlope');
      const seEl = document.getElementById('txtRegSE');

      if (eqEl) eqEl.textContent = m.equation;
      if (r2El) r2El.textContent = (m.r_squared !== undefined ? m.r_squared : m.rSquared).toFixed(3);
      if (slopeEl) slopeEl.textContent = (m.slope >= 0 ? '+' : '') + m.slope.toFixed(4) + ' ' + d.unit + '/h';
      if (seEl) seEl.textContent = (m.standard_error !== undefined ? m.standard_error : m.stdError).toFixed(3);

      // Side Station Advisory Box
      const advBox = document.getElementById('boxRegAdvisory');
      const advBody = document.getElementById('txtRegAdvisoryBody');
      if (advBox && advBody) {
        advBox.className = 'regression-advisory-box ' + s.overall_status;
        const lang = (typeof currentLang !== 'undefined') ? currentLang : 'hi';
        if (lang === 'en') advBody.textContent = s.advisory_en;
        else if (lang === 'ta') advBody.textContent = s.advisory_ta;
        else advBody.textContent = s.advisory_hi;
      }

      // Populate Hour-by-Hour Forecast Table
      const tbody = document.getElementById('tblRegressionRows');
      if (tbody) {
        let html = '';
        p.forEach(function(row) {
          const badgeClass = row.safety_status === 'danger' ? 'station-badge-danger' : (row.safety_status === 'caution' ? 'station-badge-caution' : 'station-badge-safe');
          const statusText = row.safety_status === 'danger' ? 'खतरा (Danger)' : (row.safety_status === 'caution' ? 'सावधानी (Caution)' : 'सामान्य (Safe)');
          html += '<tr>' +
            '<td><strong>' + row.time_label + '</strong></td>' +
            '<td>' + row.predicted_value.toFixed(2) + ' ' + d.unit + '</td>' +
            '<td style="color: var(--text-dim);">' + row.ci_lower.toFixed(2) + ' - ' + row.ci_upper.toFixed(2) + '</td>' +
            '<td><span class="' + badgeClass + '" style="font-size: 9.5px; padding: 1px 5px;">' + statusText + '</span></td>' +
          '</tr>';
        });
        tbody.innerHTML = html;
      }
    }

    function renderRegressionStudio() {
      drawRegressionCanvas();
      updateRegressionHUD();
    }

    // Hover Interaction on Canvas
    if (graphCanvasContainer) {
      graphCanvasContainer.addEventListener('mousemove', function(e) {
        const rect = graphCanvasContainer.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const padLeft = 60;
        const padRight = 30;
        const plotW = Math.max(10, rect.width - padLeft - padRight);

        const relX = mouseX - padLeft;
        const t = Math.round(-24 + (relX / plotW) * 48);
        if (t >= -24 && t <= 24) {
          hoverActiveIndex = t;
        } else {
          hoverActiveIndex = null;
        }
        drawRegressionCanvas();
      });

      graphCanvasContainer.addEventListener('mouseleave', function() {
        hoverActiveIndex = null;
        drawRegressionCanvas();
      });
    }

    // Variable Selection Buttons Listener
    const varPills = document.querySelectorAll('.graph-var-pill');
    varPills.forEach(function(pill) {
      pill.addEventListener('click', function() {
        varPills.forEach(function(p) { p.classList.remove('active'); });
        pill.classList.add('active');
        const v = pill.getAttribute('data-var');
        loadRegressionData(v);
      });
    });

    // Recalculate Button Listener
    const btnRecalc = document.getElementById('btnRecalcRegression');
    if (btnRecalc) {
      btnRecalc.addEventListener('click', function() {
        btnRecalc.style.transform = 'scale(0.95)';
        setTimeout(function() { btnRecalc.style.transform = ''; }, 150);
        loadRegressionData(activeRegVar);
      });
    }

    // Toggle 95% Confidence Interval Band Listener
    const btnToggleCI = document.getElementById('btnToggleCI');
    if (btnToggleCI) {
      btnToggleCI.addEventListener('click', function() {
        regShowCI = !regShowCI;
        btnToggleCI.classList.toggle('active', regShowCI);
        drawRegressionCanvas();
      });
    }

    // Handle Window Resizing for High-DPI Canvas
    window.addEventListener('resize', function() {
      if (typeof currentStationTab !== 'undefined' && currentStationTab === 'graph') {
        drawRegressionCanvas();
      }
    });

    // Initial Load of Regression Telemetry
    loadRegressionData('wave_height');
"""

def update_html_file(file_path):
    print(f"Updating {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Insert CSS before </style> if not already there
    if '24-HOUR LINEAR REGRESSION PREDICTION MODELLING STUDIO' not in content:
        style_idx = content.find('</style>')
        if style_idx != -1:
            content = content[:style_idx] + GRAPH_CSS + "\n  " + content[style_idx:]
        else:
            print(f"ERROR: </style> not found in {file_path}")
            return False

    # 2. Insert graphViewport in .tactical-chart-station after #chartViewport closing tag
    if 'id="graphViewport"' not in content:
        target_pat = re.compile(r'(</div>\s*</div>\s*</section>\s*<!-- RIGHT / COMPANION STATION)', re.DOTALL)
        # Find closing of chart-viewport
        # Look for the tactical detail drawer and its following closing divs
        # In all files, the pattern before </section> is:
        #           </div>\n        </div>\n      </section>
        # Let's inspect exact pattern:
        chart_viewport_end_pat = re.compile(
            r'(\s*</div>\s*</div>\s*</section>\s*<!-- RIGHT / COMPANION STATION: BULLETINS & RADIO COMMUNICATOR -->)',
            re.DOTALL
        )
        m = chart_viewport_end_pat.search(content)
        if m:
            insert_point = m.start()
            # We want to insert inside the section, after the inner </div>
            # Let's match:
            #             </div>
            #           </div>
            #         </div>
            #       </section>
            # Specifically:
            sub_pat = re.compile(r'(<div class="tactical-detail-drawer"[^>]*>.*?</div>\s*</div>\s*)(\s*</section>)', re.DOTALL)
            m2 = sub_pat.search(content)
            if m2:
                content = content[:m2.end(1)] + GRAPH_VIEWPORT_HTML + content[m2.start(2):]
            else:
                print(f"ERROR: detail drawer closing not found in {file_path}")
                return False
        else:
            print(f"ERROR: chart-station closing not found in {file_path}")
            return False

    # 3. Insert tab button #tabBtnGraph if not present
    if 'id="tabBtnGraph"' not in content:
        tab_nav_pat = re.compile(r'(<nav class="station-tab-bar" role="tablist">.*?</nav>)', re.DOTALL)
        m_tab = tab_nav_pat.search(content)
        if m_tab:
            old_nav = m_tab.group(0)
            if '</nav>' in old_nav:
                new_nav = old_nav.replace('</nav>', TAB_BTN_HTML)
                content = content[:m_tab.start()] + new_nav + content[m_tab.end():]
        else:
            print(f"ERROR: station-tab-bar not found in {file_path}")
            return False

    # 4. Insert side station panel 3 (#panelGraph) before </aside>
    if 'id="panelGraph"' not in content:
        aside_pat = re.compile(r'(\s*</aside>\s*</main>)', re.DOTALL)
        m_aside = aside_pat.search(content)
        if m_aside:
            content = content[:m_aside.start()] + PANEL_3_HTML + content[m_aside.start():]
        else:
            print(f"ERROR: </aside> not found in {file_path}")
            return False

    # 5. Insert mobile dock button #mobNavGraph if not present
    if 'id="mobNavGraph"' not in content:
        dock_nav_pat = re.compile(r'(<nav class="mobile-bridge-dock"[^>]*>.*?</nav>)', re.DOTALL)
        m_dn = dock_nav_pat.search(content)
        if m_dn:
            old_dn = m_dn.group(0)
            new_dn = old_dn.replace('</nav>', MOB_DOCK_BTN_HTML)
            content = content[:m_dn.start()] + new_dn + content[m_dn.end():]
        else:
            print(f"ERROR: mobile-bridge-dock not found in {file_path}")
            return False

    # 6. Replace switchStationTab and switchMobileView
    if 'Sub-Navigation Tab Switching (Alerts <-> Chat <-> Graph)' not in content:
        if OLD_SWITCH_TABS_SNIPPET in content:
            content = content.replace(OLD_SWITCH_TABS_SNIPPET, NEW_SWITCH_TABS_SNIPPET)
        else:
            # Let's search with regex
            switch_pat = re.compile(
                r'// Sub-Navigation Tab Switching \(Alerts <-> Chat\) in Companion Station.*?'
                r'mobNavChat\.addEventListener\(\'click\', \(\) => switchMobileView\(\'chat\'\)\);',
                re.DOTALL
            )
            m_sw = switch_pat.search(content)
            if m_sw:
                content = content[:m_sw.start()] + NEW_SWITCH_TABS_SNIPPET + content[m_sw.end():]
            else:
                print(f"ERROR: Tab switching code block not matched in {file_path}")
                return False

    # 7. Add REGRESSION_JS_BLOCK before the closing </script> tag
    if '24-HOUR LINEAR REGRESSION PREDICTION MODELLING ENGINE' not in content:
        last_script_idx = content.rfind('</script>')
        if last_script_idx != -1:
            content = content[:last_script_idx] + "\n" + REGRESSION_JS_BLOCK + "\n  " + content[last_script_idx:]
        else:
            print(f"ERROR: closing </script> not found in {file_path}")
            return False

    # 8. Add I18N language support in setLanguage
    if 'txtTabGraphLabel' not in content:
        lang_target = "document.getElementById('txtTabChatLabel').textContent = t.tabChat;"
        lang_replacement = """document.getElementById('txtTabChatLabel').textContent = t.tabChat;
      if (document.getElementById('txtTabGraphLabel')) document.getElementById('txtTabGraphLabel').textContent = (lang === 'hi' ? '📈 24h सांख्यिकीय ग्राफ' : (lang === 'ta' ? '📈 24h வரைபடம்' : '📈 24h Statistical Graph'));
      if (document.getElementById('txtMobGraph')) document.getElementById('txtMobGraph').textContent = (lang === 'hi' ? '24h ग्राफ' : (lang === 'ta' ? '24h வரைபடம்' : '24h Graph'));
      if (document.getElementById('txtGraphHeaderTitle')) document.getElementById('txtGraphHeaderTitle').textContent = (lang === 'hi' ? '24-घंटे लीनियर रिग्रेशन प्रेडिक्शन मॉडलिंग' : (lang === 'ta' ? '24 மணி நேர நேரியல் பின்னடைவு முன்கணிப்பு' : '24-Hour Linear Regression Prediction Modelling'));
      if (document.getElementById('txtGraphHeaderSubtitle')) document.getElementById('txtGraphHeaderSubtitle').textContent = (lang === 'hi' ? 'सांख्यिकीय रिग्रेशन पूर्वानुमान • OLS Best-Fit Trend Analysis' : (lang === 'ta' ? 'புள்ளியியல் கடல் முன்கணிப்பு • OLS Best-Fit Trend Analysis' : 'Statistical Marine Forecast • OLS Best-Fit Trend Analysis'));
      if (typeof updateRegressionHUD === 'function') updateRegressionHUD();"""
        if lang_target in content:
            content = content.replace(lang_target, lang_replacement)

    # Validate JavaScript before writing!
    script_start = content.find('<script>')
    script_end = content.rfind('</script>')
    script_code = content[script_start+8:script_end]
    parse_js(script_code)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"SUCCESS: {file_path} successfully updated and validated!")
    return True

# Test on chat.html first
print("--- TESTING ON chat.html ---")
if update_html_file('chat.html'):
    print("chat.html passed validation! Now updating all remaining files...")
    for p in html_files:
        if p != 'chat.html':
            update_html_file(p)
    print("\nALL 9 FILES PROCESSED!")
else:
    print("Failed on chat.html, aborting batch.")
