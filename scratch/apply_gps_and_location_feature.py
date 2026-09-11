# scratch/apply_gps_and_location_feature.py
import os
import re
import sys

INDEX_PATH = r"c:\Users\devas\OneDrive\Documents\KyroX\Frontend\index.html"

with open(INDEX_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. ADD CSS FOR GPS TOGGLE & LOCATION SEARCH BAR
CSS_ADDITION = """
    /* ==========================================================================
       GPS TRACKING TOGGLE & TACTICAL LOCATION SEARCH BAR
       ========================================================================== */
    .gps-led-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: #55c759;
      box-shadow: 0 0 8px #55c759;
      display: inline-block;
      transition: all 0.2s ease;
      flex-shrink: 0;
    }

    .bezel-btn.gps-active {
      border-color: #55c759;
      color: var(--text-chart);
    }

    .bezel-btn.gps-disabled {
      opacity: 0.85;
      border-color: var(--border-bezel);
      color: var(--text-muted);
    }

    .bezel-btn.gps-disabled .gps-led-dot {
      background-color: #786D5F;
      box-shadow: none;
    }

    .tactical-location-search-bar {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      background: var(--bg-bridge);
      border-bottom: 1.5px solid var(--border-bezel);
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.45);
      z-index: 24;
      flex-shrink: 0;
    }

    .loc-search-input-wrapper {
      position: relative;
      flex: 1;
      min-width: 220px;
      display: flex;
      align-items: center;
    }

    .loc-search-icon {
      position: absolute;
      left: 10px;
      font-size: 13px;
      color: var(--brass-bright);
      pointer-events: none;
    }

    #inputCustomLocation {
      width: 100%;
      padding: 6px 28px 6px 30px;
      background: var(--bg-input);
      border: 1px solid var(--border-brass);
      border-radius: var(--radius-subtle);
      color: var(--text-chart);
      font-family: var(--font-telemetry);
      font-size: 11.5px;
      outline: none;
      transition: border-color 0.15s, box-shadow 0.15s;
    }

    #inputCustomLocation:focus {
      border-color: var(--brass-bright);
      box-shadow: 0 0 6px rgba(200, 138, 62, 0.35);
    }

    .loc-search-clear {
      position: absolute;
      right: 8px;
      background: none;
      border: none;
      color: var(--text-dim);
      font-size: 16px;
      line-height: 1;
      cursor: pointer;
      display: none;
      padding: 0;
    }

    .loc-search-clear:hover {
      color: var(--text-chart);
    }

    .loc-search-submit {
      padding: 6px 14px;
      background: var(--brass-base);
      color: var(--text-inverse);
      font-family: var(--font-telemetry);
      font-size: 11px;
      font-weight: 700;
      border: 1px solid var(--brass-bright);
      border-radius: var(--radius-subtle);
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      white-space: nowrap;
      transition: background-color 0.12s, box-shadow 0.12s;
    }

    .loc-search-submit:hover {
      background: var(--brass-bright);
      box-shadow: 0 0 8px rgba(220, 155, 74, 0.4);
    }

    .loc-search-gps {
      padding: 6px 11px;
      background: var(--bg-console);
      color: var(--text-chart);
      font-family: var(--font-telemetry);
      font-size: 11px;
      border: 1px solid var(--border-bezel);
      border-radius: var(--radius-subtle);
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      white-space: nowrap;
      transition: background-color 0.12s, border-color 0.12s;
    }

    .loc-search-gps:hover {
      background: var(--bg-console-raised);
      border-color: var(--border-brass);
      color: var(--brass-bright);
    }

    .loc-quick-chips {
      display: flex;
      align-items: center;
      gap: 5px;
      flex-wrap: wrap;
      width: 100%;
      padding-top: 4px;
      border-top: 1px dashed rgba(58, 48, 39, 0.5);
    }

    .loc-quick-lbl {
      font-family: var(--font-telemetry);
      font-size: 9.5px;
      color: var(--text-dim);
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }

    .loc-chip {
      padding: 2px 7px;
      background: var(--bg-console);
      border: 1px solid var(--border-bezel);
      border-radius: 2px;
      color: var(--text-muted);
      font-family: var(--font-telemetry);
      font-size: 10px;
      cursor: pointer;
      transition: all 0.12s ease;
    }

    .loc-chip:hover {
      background: var(--bg-console-raised);
      border-color: var(--border-brass);
      color: var(--brass-bright);
    }
"""

# Insert CSS before </style>
if "/* GPS TRACKING TOGGLE & TACTICAL LOCATION SEARCH BAR */" not in content:
    content = content.replace("</style>", CSS_ADDITION + "\n  </style>", 1)

# 2. INSERT GPS TOGGLE BUTTON IN MASTHEAD
OLD_MASTHEAD_BTNS = """        <div class="masthead-controls">
          <!-- Sunlight Deck Mode Button -->"""

NEW_MASTHEAD_BTNS = """        <div class="masthead-controls">
          <!-- GPS Real-Time Tracking Toggle Button -->
          <button id="btnGpsToggle" class="bezel-btn gps-active" type="button" title="Toggle Real-time GPS Tracking ON / OFF">
            <span class="gps-led-dot"></span>
            <span id="txtGpsToggle">📡 GPS: ON</span>
          </button>

          <!-- Sunlight Deck Mode Button -->"""

content = content.replace(OLD_MASTHEAD_BTNS, NEW_MASTHEAD_BTNS, 1)

# 3. INSERT LOCATION SEARCH BAR IN TACTICAL CHART STATION
OLD_CHART_STATION_START = """      <!-- LEFT / CENTER: TACTICAL NAVIGATIONAL CHART -->
      <section class="tactical-chart-station" aria-label="Nautical Navigation Chart">
        
        <div class="chart-viewport" id="chartViewport">"""

NEW_CHART_STATION_START = """      <!-- LEFT / CENTER: TACTICAL NAVIGATIONAL CHART -->
      <section class="tactical-chart-station" aria-label="Nautical Navigation Chart">
        
        <!-- DEDICATED MANUAL LOCATION INPUT & QUERY STATION -->
        <div class="tactical-location-search-bar" id="locSearchBar">
          <div class="loc-search-input-wrapper">
            <span class="loc-search-icon">🔍</span>
            <input type="text" id="inputCustomLocation" placeholder="Type port, coastal zone or Lat, Lon (e.g. Mumbai, Kochi, Chennai, 18.92, 72.83)..." autocomplete="off" spellcheck="false">
            <button type="button" id="btnClearLocSearch" class="loc-search-clear" title="Clear Search">×</button>
          </div>
          <button type="button" id="btnSubmitLocation" class="loc-search-submit">
            <span id="txtBtnSubmitLoc">📍 विवरण देखें (Show Details)</span>
          </button>
          <button type="button" id="btnCurrentGpsLocation" class="loc-search-gps" title="Reset to Device GPS Location">
            <span id="txtBtnCurrentGps">🎯 मेरा जीपीएस (My GPS)</span>
          </button>
          <div class="loc-quick-chips" id="locQuickChips">
            <span class="loc-quick-lbl" id="txtQuickPortsLbl">त्वरित बंदरगाह:</span>
            <button type="button" class="loc-chip" data-loc="Mumbai">मुंबई</button>
            <button type="button" class="loc-chip" data-loc="Kochi">कोच्चि</button>
            <button type="button" class="loc-chip" data-loc="Chennai">चेन्नई</button>
            <button type="button" class="loc-chip" data-loc="Visakhapatnam">विशाखापट्टनम</button>
            <button type="button" class="loc-chip" data-loc="Mangalore">मंगलुरु</button>
            <button type="button" class="loc-chip" data-loc="Porbandar">पोरबंदर</button>
            <button type="button" class="loc-chip" data-loc="Kanyakumari">कन्याकुमारी</button>
            <button type="button" class="loc-chip" data-loc="Kolkata">कोलकाता</button>
          </div>
        </div>

        <div class="chart-viewport" id="chartViewport">"""

content = content.replace(OLD_CHART_STATION_START, NEW_CHART_STATION_START, 1)

# 4. REPLACE GOA SECTOR HEADINGS & LABELS
content = content.replace("COMMERCIAL MARINE BRIDGE TERMINAL • GOA–KARWAR SECTOR", "COMMERCIAL MARINE BRIDGE TERMINAL • REAL-TIME GPS NAVIGATION")
content = content.replace("COMMERCIAL MARINE BRIDGE TERMINAL \u2022 GOA\u2013KARWAR SECTOR", "COMMERCIAL MARINE BRIDGE TERMINAL • REAL-TIME GPS NAVIGATION")
content = content.replace("SECTOR: GOA-KARWAR", "SECTOR: LIVE GPS TRACKING")

# Bulletins stations & rescue mentions
content = content.replace('"INCOIS-HYD / MRCC-GOA"', '"INCOIS-HYD / MRCC NATIONAL"')
content = content.replace('"MRCC-MUMBAI / COASTGUARD-GOA"', '"MRCC NATIONAL / INDIAN COAST GUARD"')
content = content.replace("MRCC Goa Bearing 085° E", "MRCC Coastal Station Bearing 085° E")
content = content.replace("Your position 15°24.6'N, 73°48.2'E is logged at MRCC Goa.", "Your GPS position is continuously logged with Maritime Rescue Coordination Centre (MRCC).")

# Replace default 'Goa Offshore' fallbacks
content = content.replace("'Goa Offshore'", "'Live Navigational Position'")

print("Phase 1 replacements applied successfully.")
with open(INDEX_PATH, "w", encoding="utf-8") as f:
    f.write(content)
