import re
import os

with open('Frontend/Alerts/alerts.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add Leaflet styling to CSS before </style>
leaflet_css = """
    /* ==========================================================================
       LEAFLET NAUTICAL DARK ENGINE & PULSING GPS BEACON STYLES
       ========================================================================== */
    #marineMapLeaflet {
      width: 100%;
      height: 100%;
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: #12100E;
      z-index: 1;
    }

    .chart-viewport {
      position: relative !important;
      overflow: hidden !important;
    }

    .chart-hud-overlay {
      z-index: 1000 !important;
    }

    .chart-legend-container {
      z-index: 1000 !important;
    }

    .tactical-detail-drawer {
      z-index: 1010 !important;
    }

    /* Dark Nautical Leaflet Controls */
    .leaflet-control-zoom {
      border: 1px solid var(--border-bezel) !important;
      border-radius: var(--radius-subtle) !important;
      overflow: hidden;
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.7) !important;
    }

    .leaflet-control-zoom a {
      background-color: rgba(24, 20, 17, 0.94) !important;
      color: var(--brass-bright) !important;
      border-bottom: 1px solid var(--border-bezel) !important;
      transition: background-color 0.15s, color 0.15s;
    }

    .leaflet-control-zoom a:hover {
      background-color: var(--bg-console-raised) !important;
      color: #FFF !important;
    }

    .leaflet-container {
      background: #12100E !important;
      font-family: var(--font-telemetry) !important;
    }

    .leaflet-tile-pane {
      filter: brightness(0.92) contrast(1.08);
    }

    /* Tactical Map Tooltip */
    .tactical-map-tooltip {
      background: rgba(24, 20, 17, 0.94) !important;
      color: var(--text-chart) !important;
      border: 1px solid var(--border-brass) !important;
      border-radius: 2px !important;
      font-family: var(--font-telemetry) !important;
      font-size: 10.5px !important;
      font-weight: 700 !important;
      padding: 3px 7px !important;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.7) !important;
    }
    .tactical-map-tooltip:before {
      border-top-color: var(--border-brass) !important;
    }

    /* Pulsing GPS Location Beacon */
    .leaflet-user-beacon {
      position: relative;
      width: 28px;
      height: 28px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .user-beacon-core {
      width: 14px;
      height: 14px;
      background: #FFD152;
      border: 2.5px solid #12100E;
      border-radius: 50%;
      box-shadow: 0 0 10px #FFD152, 0 0 20px rgba(255, 209, 82, 0.6);
      z-index: 2;
      position: relative;
    }

    .user-beacon-pulse {
      position: absolute;
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: rgba(255, 209, 82, 0.4);
      animation: userBeaconRings 2.2s infinite cubic-bezier(0.2, 0.8, 0.4, 1);
      z-index: 1;
    }

    @keyframes userBeaconRings {
      0% {
        transform: scale(0.4);
        opacity: 1;
      }
      100% {
        transform: scale(2.4);
        opacity: 0;
      }
    }
  </style>
"""

content = content.replace("  </style>", leaflet_css, 1)

# 2. Replace the SVG element with the Leaflet map container div
svg_pattern = r'<!-- THE AUTHENTIC NAUTICAL CHART SVG -->\s*<svg class="nautical-svg-chart" id="marineSvgChart".*?</svg>'
leaflet_div = """<!-- LEAFLET INTERACTIVE GEOGRAPHIC GPS & NAUTICAL CHART -->
          <div id="marineMapLeaflet"></div>"""

new_content, count = re.subn(svg_pattern, leaflet_div, content, flags=re.DOTALL)
print(f"SVG replacement count: {count}")
assert count == 1, "Failed to replace SVG element"

# 3. Update MAP_ZONES and MAP_MARKERS with geo coordinates
old_zones_markers_pattern = r'const MAP_ZONES = \[.*?\n    const ADVISORY_RESPONSES ='

new_zones_markers = """const MAP_ZONES = [
      {
        id: "zone-pfz-sw",
        type: "pfz",
        center: [15.20, 73.53],
        latLngs: [
          [15.28, 73.45],
          [15.26, 73.62],
          [15.12, 73.65],
          [15.08, 73.48]
        ],
        label_hi: "INCOIS PFZ (उत्तम मत्स्य क्षेत्र)",
        label_en: "INCOIS PFZ (Optimal Fishing)",
        label_ta: "INCOIS PFZ (சிறந்த மீன்பிடி பகுதி)",
        sub_hi: "SST 28.2°C • Chlorophyll 0.42mg/m³",
        sub_en: "SST 28.2°C • Chlorophyll 0.42mg/m³",
        sub_ta: "SST 28.2°C • Chlorophyll 0.42mg/m³",
        reason_hi: "उच्च क्लोरोफिल व अनुकूल तापीय प्रवणता। बांगड़ा और सुरमई के झुंड सक्रिय। हवा मात्र 12 किमी/घंटा, समुद्र पूर्णतः शांत।",
        reason_en: "High chlorophyll density with thermal front. Strong pelagic fish schools (Mackerel & Kingfish). Winds light at 6 kts.",
        reason_ta: "அதிக குளோரோபில் மற்றும் சாதகமான வெப்பநிலை. கானாங்கெளுத்தி மற்றும் வஞ்சிரம் மீன் கூட்டங்கள் அதிகம். காற்று 12 கிமீ/மணி, கடல் அமைதி.",
        coords: "15°12'N, 73°32'E (Bearing 215° SW, 14 NM)"
      },
      {
        id: "zone-wind-ne",
        type: "caution",
        center: [15.43, 73.74],
        latLngs: [
          [15.48, 73.68],
          [15.49, 73.80],
          [15.38, 73.82],
          [15.37, 73.70]
        ],
        label_hi: "सावधानी क्षेत्र (तीव्र लहर)",
        label_en: "Caution Area (Rough Swell)",
        label_ta: "எச்சரிக்கை பகுதி (உயர்ந்த அலைகள்)",
        sub_hi: "Swell 2.8m • Winds 35 km/h",
        sub_en: "Swell 2.8m • Winds 19 kts",
        sub_ta: "Swell 2.8m • Winds 35 km/h",
        reason_hi: "दोपहर 2:00 बजे के बाद 35 किमी/घंटे की हवाएं और 2.8m ऊंची लहरें संभव। छोटी डोंगियों के लिए असुरक्षित।",
        reason_en: "Wind picking up to 19 kts with 2.8m cross-swells after 14:00 IST. Unsafe for open motorized canoes.",
        reason_ta: "மதியம் 2:00 மணிக்கு மேல் 35 கிமீ/மணி வேக காற்று மற்றும் 2.8 மீ உயரமான அலைகள் எழலாம். சிறிய படகுகளுக்கு பாதுகாப்பற்றது.",
        coords: "15°26'N, 73°44'E (Bearing 030° NE, 8 NM)"
      },
      {
        id: "zone-danger-se",
        type: "danger",
        center: [14.83, 73.96],
        latLngs: [
          [14.92, 73.90],
          [14.90, 74.05],
          [14.78, 74.02],
          [14.80, 73.88]
        ],
        label_hi: "प्रतिबंधित खतरा क्षेत्र (रेड अलर्ट)",
        label_en: "Restricted Danger Zone (Red Alert)",
        label_ta: "தடைசெய்யப்பட்ட ஆபத்து பகுதி (ரெட் அலர்ட்)",
        sub_hi: "Squall 45 kt • Lightning Radar Lock",
        sub_en: "Squall 45 kt • Lightning Radar Lock",
        sub_ta: "Squall 45 kt • Lightning Radar Lock",
        reason_hi: "तटरक्षक बल व मौसम विभाग द्वारा रेड अलर्ट जारी। 45 नॉट की तूफानी हवाएं और सक्रिय आकाशीय बिजली का केंद्र। नौका संचालन प्रतिबंधित।",
        reason_en: "IMD / Coast Guard Red Alert squall line. Active lightning strikes and 45 knot cyclonic gusts. Entry strictly prohibited.",
        reason_ta: "கடலோர காவல்படை ரெட் அலர்ட் விடுத்துள்ளது. 45 நாட் சூறாவளி காற்று மற்றும் தீவிர மின்னல் அபாயம். படகு செல்ல தடை.",
        coords: "14°50'N, 73°58'E (Bearing 140° SE, 18 NM)"
      }
    ];

    const MAP_MARKERS = [
      {
        id: "mkr-pfz-target",
        kind: "pfz",
        latLng: [15.20, 73.53],
        zone_id: "zone-pfz-sw",
        label_hi: "PFZ-ALPHA (उत्तम बिंदु)",
        label_en: "PFZ-ALPHA (Target Waypoint)",
        label_ta: "PFZ-ALPHA (இலக்கு புள்ளி)",
        coords: "15°12'N, 73°32'E",
        reason_hi: "अनुशंसित जाल डालने का बिंदु। बांगड़ा और सुरमई के भारी झुंड। गहराई: 42 मीटर।",
        reason_en: "Optimal net casting coordinates. Heavy Mackerel schools detected at 42m depth.",
        reason_ta: "வலை வீசுவதற்கு உகந்த இடம். அதிக கானாங்கெளுத்தி மற்றும் வஞ்சிரம் மீன்கள். ஆழம்: 42 மீட்டர்."
      },
      {
        id: "mkr-squall-center",
        kind: "danger",
        latLng: [14.83, 73.96],
        zone_id: "zone-danger-se",
        label_hi: "तूफान केंद्र (Doppler Eye)",
        label_en: "Squall Core (Doppler Eye)",
        label_ta: "புயல் மையம் (Doppler Eye)",
        coords: "14°50'N, 73°58'E",
        reason_hi: "डॉपलर रडार द्वारा ट्रैक किया गया चक्रवाती केंद्र। उत्तर-पूर्व दिशा में 18 नॉट की गति से बढ़ रहा है।",
        reason_en: "Doppler tracked cyclonic squall core propagating 045° NE at 18 knots.",
        reason_ta: "டாப்ளர் ரேடார் மூலம் கண்காணிக்கப்பட்ட புயல் மையம். வடகிழக்கு நோக்கி 18 நாட் வேகத்தில் நகர்கிறது."
      }
    ];

    const ADVISORY_RESPONSES ="""

new_content, count = re.subn(old_zones_markers_pattern, new_zones_markers, new_content, flags=re.DOTALL)
print(f"MAP_ZONES & MARKERS replacement count: {count}")
assert count == 1, "Failed to replace MAP_ZONES"

# 4. Replace renderMapZones and renderMapMarkers with Leaflet implementations
old_render_pattern = r'    // Render Marine Zones on SVG Chart.*?    // Select and focus zone on map\n    function selectMapZone\(zoneId\) \{.*?    \}'

new_render_code = """    // Leaflet Geographic Map Engine State
    let leafletMap = null;
    let tileLayer = null;
    let userGpsMarker = null;
    let riskHeatmapLayer = null;
    let tacticalZonesLayer = null;
    let waypointsLayer = null;

    function initLeafletMap() {
      if (leafletMap) return;
      const mapContainer = document.getElementById('marineMapLeaflet');
      if (!mapContainer) return;

      const initLat = vesselLocation ? vesselLocation.latitude : 15.25;
      const initLon = vesselLocation ? vesselLocation.longitude : 73.80;

      leafletMap = L.map('marineMapLeaflet', {
        center: [initLat, initLon],
        zoom: 11,
        minZoom: 3,
        maxZoom: 18,
        zoomControl: false
      });

      L.control.zoom({ position: 'bottomright' }).addTo(leafletMap);

      // CartoDB DarkMatter nautical tiles
      tileLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; CARTO &copy; OpenStreetMap',
        subdomains: 'abcd',
        maxZoom: 19
      }).addTo(leafletMap);

      tacticalZonesLayer = L.layerGroup().addTo(leafletMap);
      riskHeatmapLayer = L.layerGroup().addTo(leafletMap);
      waypointsLayer = L.layerGroup().addTo(leafletMap);

      renderLeafletTacticalZones();
      renderLeafletWaypoints();

      leafletMap.on('click', () => {
        closeTacticalDrawer();
      });

      // Synchronize initial heatmap visibility
      updateHeatmapVisuals();
    }

    function renderLeafletTacticalZones() {
      if (!tacticalZonesLayer) return;
      tacticalZonesLayer.clearLayers();

      MAP_ZONES.forEach(z => {
        if (!z.latLngs) return;
        const color = z.type === 'pfz' ? '#8C9B5E' : (z.type === 'caution' ? '#E8A44C' : '#DE6347');
        const fillColor = z.type === 'pfz' ? '#74804E' : (z.type === 'caution' ? '#D4903B' : '#C4543A');

        const polygon = L.polygon(z.latLngs, {
          color: color,
          weight: 1.5,
          fillColor: fillColor,
          fillOpacity: 0.24
        });

        const label = (currentLang === 'hi') ? z.label_hi : (currentLang === 'ta' ? (z.label_ta || z.label_en) : z.label_en);
        polygon.bindTooltip(label, { permanent: false, direction: 'center', className: 'tactical-map-tooltip' });

        polygon.on('click', (e) => {
          L.DomEvent.stopPropagation(e);
          selectMapZone(z.id);
        });

        tacticalZonesLayer.addLayer(polygon);
      });
    }

    function renderLeafletWaypoints() {
      if (!waypointsLayer) return;
      waypointsLayer.clearLayers();

      MAP_MARKERS.forEach(m => {
        if (!m.latLng) return;
        const isPfz = m.kind === 'pfz';
        const markerColor = isPfz ? '#74804E' : '#C4543A';
        const iconChar = isPfz ? '🐟' : '⚡';

        const waypointHtml = `
          <div style="background:${markerColor}; border:2px solid #EFEAE1; border-radius:50%; width:24px; height:24px; display:flex; align-items:center; justify-content:center; font-size:12px; box-shadow:0 2px 8px rgba(0,0,0,0.6); cursor:pointer;">
            ${iconChar}
          </div>
        `;

        const icon = L.divIcon({
          className: 'custom-tactical-waypoint',
          html: waypointHtml,
          iconSize: [24, 24],
          iconAnchor: [12, 12]
        });

        const marker = L.marker(m.latLng, { icon: icon });
        const label = (currentLang === 'hi') ? m.label_hi : (currentLang === 'ta' ? (m.label_ta || m.label_en) : m.label_en);
        marker.bindTooltip(label, { permanent: false, direction: 'top', className: 'tactical-map-tooltip' });

        marker.on('click', (e) => {
          L.DomEvent.stopPropagation(e);
          const theme = m.kind === 'danger' ? 'danger' : 'pfz';
          const reason = (currentLang === 'hi') ? m.reason_hi : (currentLang === 'ta' ? (m.reason_ta || m.reason_en) : m.reason_en);
          showTacticalDrawer(label, reason, m.coords, theme, m.zone_id || 'zone-pfz-sw');
        });

        waypointsLayer.addLayer(marker);
      });
    }

    // Select and focus zone on map
    function selectMapZone(zoneId) {
      activeZoneId = zoneId;
      const z = MAP_ZONES.find(item => item.id === zoneId);
      if (z) {
        const title = (currentLang === 'hi') ? z.label_hi : (currentLang === 'ta' ? (z.label_ta || z.label_en) : z.label_en);
        const reason = (currentLang === 'hi') ? z.reason_hi : (currentLang === 'ta' ? (z.reason_ta || z.reason_en) : z.reason_en);
        showTacticalDrawer(title, reason, z.coords, z.type, z.id);
        if (leafletMap && z.center) {
          leafletMap.flyTo(z.center, 12, { duration: 1.2 });
        }
      }
    }"""

new_content, count = re.subn(old_render_pattern, new_render_code, new_content, flags=re.DOTALL)
print(f"renderMapZones/Markers replacement count: {count}")
assert count == 1, "Failed to replace renderMapZones"

# 5. Update GPS pinning and dynamic risk heatmap functions
old_gps_pattern = r'    // Cartographic Projection: Map Latitude & Longitude to SVG Chart.*?\n    // Transmit User GPS Location to Backend'

new_gps_code = """    // Pin User Location on Leaflet GPS Navigational Chart
    function pinUserLocationOnMap(gpsData) {
      if (!gpsData || typeof gpsData.latitude !== 'number' || typeof gpsData.longitude !== 'number') return;
      const lat = gpsData.latitude;
      const lon = gpsData.longitude;

      const latDeg = Math.floor(Math.abs(lat));
      const latMin = ((Math.abs(lat) - latDeg) * 60).toFixed(1);
      const lonDeg = Math.floor(Math.abs(lon));
      const lonMin = ((Math.abs(lon) - lonDeg) * 60).toFixed(1);
      const coordsStr = `${latDeg}°${latMin}'${lat >= 0 ? 'N' : 'S'}, ${lonDeg}°${lonMin}'${lon >= 0 ? 'E' : 'W'}`;

      // Update masthead telemetry bar
      const elFix = document.getElementById('txtTelemetryFix');
      if (elFix) elFix.textContent = `DGPS FIX: ${coordsStr}`;

      if (!leafletMap) {
        initLeafletMap();
      }

      // Create or update live pulsing beacon icon
      const beaconHtml = `
        <div class="leaflet-user-beacon" title="📍 Your Current Location (${coordsStr})">
          <div class="user-beacon-pulse"></div>
          <div class="user-beacon-core"></div>
        </div>
      `;
      const beaconIcon = L.divIcon({
        className: 'custom-user-beacon-icon',
        html: beaconHtml,
        iconSize: [28, 28],
        iconAnchor: [14, 14]
      });

      if (userGpsMarker) {
        userGpsMarker.setLatLng([lat, lon]);
        userGpsMarker.setIcon(beaconIcon);
      } else {
        userGpsMarker = L.marker([lat, lon], {
          icon: beaconIcon,
          zIndexOffset: 1000
        }).addTo(leafletMap);

        userGpsMarker.on('click', (e) => {
          L.DomEvent.stopPropagation(e);
          const title = (currentLang === 'hi') ? '📍 आपकी वर्तमान स्थिति' : (currentLang === 'ta' ? '📍 உங்கள் தற்போதைய அமைவிடம்' : '📍 Your Current Location');
          const reason = (currentLang === 'hi') ? 
            `जीपीएस सत्यापित लाइव स्थिति (${coordsStr})। मौसम, समुद्री स्थिति और सुरक्षा विश्लेषण इस बिंदु से सिंक हैं।` : 
            (currentLang === 'ta' ? 
              `நேரலை GPS மூலம் பெறப்பட்ட படகு அமைவிடம் (${coordsStr}).` : 
              `Live GPS-verified device coordinates (${coordsStr}). Weather, marine conditions, and risk analyses synced to this position.`);
          showTacticalDrawer(title, reason, coordsStr, 'vessel', 'user_location');
        });
      }

      // Fly and center map to user coordinates
      focusMapOnUserLocation(lat, lon);
    }

    // Center or Move Map Viewport to User Location
    function focusMapOnUserLocation(lat, lon) {
      if (!leafletMap) return;
      const targetLat = (typeof lat === 'number') ? lat : (vesselLocation ? vesselLocation.latitude : 15.25);
      const targetLon = (typeof lon === 'number') ? lon : (vesselLocation ? vesselLocation.longitude : 73.80);
      leafletMap.flyTo([targetLat, targetLon], 12, { duration: 1.2 });
    }

    // Update Bridge Telemetry Strip UI
    function updateBridgeTelemetryUI(data) {
      if (!data) return;
      if (data.sog) {
        const el = document.getElementById('txtTelemSog');
        if (el) el.innerHTML = `SOG: <strong>${data.sog}</strong>`;
      }
      if (data.cog) {
        const el = document.getElementById('txtTelemCog');
        if (el) el.innerHTML = `COG: <strong>${data.cog}</strong>`;
      }
      if (data.depth) {
        const el = document.getElementById('txtTelemDepth');
        if (el) el.innerHTML = `DEPTH: <strong>${data.depth}</strong>`;
      }
      if (data.wave) {
        const el = document.getElementById('txtTelemBaro');
        if (el) el.innerHTML = `WAVE: <strong>${data.wave}</strong> • BARO: <strong>${data.baro || '1008.4 hPa'}</strong>`;
      }
      if (data.fix) {
        const el = document.getElementById('txtTelemetryFix');
        if (el) el.textContent = data.fix;
      }
    }

    // Render Dynamic 3x3 Risk Heatmap around User GPS
    function renderDynamicRiskHeatmap(riskPoints, userLocation) {
      if (!riskHeatmapLayer) return;
      riskHeatmapLayer.clearLayers();

      if (!Array.isArray(riskPoints) || riskPoints.length === 0) return;

      riskPoints.forEach((pt, idx) => {
        const risk = Number(pt.risk) || 0;
        const isCenterUser = (idx === 4);

        let fillColor = '#27AE60'; // Low Risk Green
        let strokeColor = '#2ECC71';
        let fillOpacity = 0.38;

        if (pt.risk_level === 'CRITICAL' || risk >= 80) {
          fillColor = '#C4543A'; // Critical Rust Red
          strokeColor = '#DE6347';
          fillOpacity = 0.55;
        } else if (pt.risk_level === 'HIGH' || risk >= 55) {
          fillColor = '#E67E22'; // High Orange
          strokeColor = '#F39C12';
          fillOpacity = 0.48;
        } else if (pt.risk_level === 'MEDIUM' || risk >= 30) {
          fillColor = '#D4903B'; // Caution Amber
          strokeColor = '#F1C40F';
          fillOpacity = 0.42;
        }

        const circle = L.circle([pt.latitude, pt.longitude], {
          radius: isCenterUser ? 3200 : 2800,
          color: strokeColor,
          weight: isCenterUser ? 2 : 1,
          dashArray: isCenterUser ? null : '4, 4',
          fillColor: fillColor,
          fillOpacity: fillOpacity
        });

        const cellLabel = isCenterUser ? `📍 User GPS (${risk}% ${pt.risk_level})` : `P${idx + 1}: ${risk}% Risk (${pt.risk_level})`;
        circle.bindTooltip(cellLabel, {
          permanent: false,
          direction: 'top',
          className: 'tactical-map-tooltip'
        });

        circle.on('click', (e) => {
          L.DomEvent.stopPropagation(e);
          const theme = (pt.risk_level === 'CRITICAL' || pt.risk_level === 'HIGH') ? 'danger' : (pt.risk_level === 'MEDIUM' ? 'caution' : 'pfz');
          const title = `${cellLabel} • [${pt.latitude.toFixed(4)}°, ${pt.longitude.toFixed(4)}°]`;
          const reason = `Live multi-agent risk assessment: ${risk}% composite risk score. Marine swell: ${pt.wave_height || '1.1m'}, Wind: ${pt.wind_speed || '12 kt'}. Status: ${pt.risk_level}.`;
          showTacticalDrawer(title, reason, `${pt.latitude.toFixed(4)}°N, ${pt.longitude.toFixed(4)}°E`, theme, `risk_point_${idx+1}`);
        });

        riskHeatmapLayer.addLayer(circle);
      });

      // Update legend labels for 3x3 Risk Heatmap
      const legScaleLow = document.getElementById('heatScaleLow');
      const legScaleHigh = document.getElementById('heatScaleHigh');
      const legHeatmap = document.getElementById('legHeatmap');
      if (legScaleLow) legScaleLow.textContent = '0% (कम जोखिम / SAFE)';
      if (legScaleHigh) legScaleHigh.textContent = '100% (गंभीर / CRITICAL)';
      if (legHeatmap) legHeatmap.textContent = '3×3 जीपीएस जोखिम हीटमैप (Live Risk Grid)';
    }

    // Query 3x3 Risk Heatmap from Backend
    async function fetchRiskHeatmap(lat, lon) {
      try {
        const res = await fetch(`${BACKEND_API_BASE}/heatmap`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ latitude: lat, longitude: lon })
        });
        if (!res.ok) return;
        const data = await res.json();
        if (data && Array.isArray(data.risk_points)) {
          renderDynamicRiskHeatmap(data.risk_points, data.user_location);
        }
      } catch (err) {
        console.warn('[KyroX] Heatmap fetch failed:', err);
      }
    }

    // Transmit User GPS Location to Backend"""

new_content, count = re.subn(old_gps_pattern, new_gps_code, new_content, flags=re.DOTALL)
print(f"GPS & Heatmap replacement count: {count}")
assert count == 1, "Failed to replace GPS logic"

# 6. Update updateHeatmapVisuals to toggle riskHeatmapLayer on Leaflet map
old_heatmap_toggle_pattern = r'    function updateHeatmapVisuals\(\) \{.*?    \}'
new_heatmap_toggle_code = """    function updateHeatmapVisuals() {
      const t = I18N[currentLang] || I18N.en;
      if (leafletMap && riskHeatmapLayer) {
        if (isHeatmapActive) {
          if (!leafletMap.hasLayer(riskHeatmapLayer)) leafletMap.addLayer(riskHeatmapLayer);
        } else {
          if (leafletMap.hasLayer(riskHeatmapLayer)) leafletMap.removeLayer(riskHeatmapLayer);
        }
      }
      if (btnToggleHeatmap) {
        btnToggleHeatmap.classList.toggle('off', !isHeatmapActive);
        btnToggleHeatmap.setAttribute('aria-pressed', isHeatmapActive ? 'true' : 'false');
        const txtEl = document.getElementById('txtHeatmapToggle');
        if (txtEl) txtEl.textContent = isHeatmapActive ? t.heatmapBtnOn : t.heatmapBtnOff;
      }
      if (heatmapLegendScale) {
        heatmapLegendScale.style.opacity = isHeatmapActive ? '1' : '0.4';
      }
    }"""

new_content, count = re.subn(old_heatmap_toggle_pattern, new_heatmap_toggle_code, new_content, flags=re.DOTALL)
print(f"updateHeatmapVisuals replacement count: {count}")
assert count == 1, "Failed to replace updateHeatmapVisuals"

# 7. In setLanguage(lang), update render calls to use Leaflet methods
new_content = new_content.replace("renderMapZones();\n      renderMapMarkers();", "renderLeafletTacticalZones();\n      renderLeafletWaypoints();")

# 8. In initBridge(), initialize Leaflet map and update DGPS click handler
old_init_pattern = r'      // Click on DGPS fix in masthead to recenter on user location.*?      fetchLiveTelemetry\(\);'
new_init_code = """      // Initialize Leaflet Map
      initLeafletMap();

      // Click on DGPS fix in masthead to recenter on user location
      const elFix = document.getElementById('txtTelemetryFix');
      if (elFix) {
        elFix.style.cursor = 'pointer';
        elFix.title = 'Click to focus chart on current GPS location';
        elFix.addEventListener('click', () => {
          if (vesselLocation) {
            focusMapOnUserLocation(vesselLocation.latitude, vesselLocation.longitude);
          }
        });
      }

      fetchLiveTelemetry();"""

new_content, count = re.subn(old_init_pattern, new_init_code, new_content, flags=re.DOTALL)
print(f"initBridge replacement count: {count}")
assert count == 1, "Failed to replace initBridge"

# Write out the updated file
with open('Frontend/Alerts/alerts.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Frontend/Alerts/alerts.html updated successfully!")
