# scratch/apply_js_features.py
import re

INDEX_PATH = r"c:\Users\devas\OneDrive\Documents\KyroX\Frontend\index.html"

with open(INDEX_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update initial map coordinates and fallback coordinates
content = content.replace("const initLat = vesselLocation ? vesselLocation.latitude : 15.25;", "const initLat = vesselLocation ? vesselLocation.latitude : 18.92;")
content = content.replace("const initLon = vesselLocation ? vesselLocation.longitude : 73.80;", "const initLon = vesselLocation ? vesselLocation.longitude : 72.83;")
content = content.replace("const targetLat = (typeof lat === 'number') ? lat : (vesselLocation ? vesselLocation.latitude : 15.25);", "const targetLat = (typeof lat === 'number') ? lat : (vesselLocation ? vesselLocation.latitude : 18.92);")
content = content.replace("const targetLon = (typeof lon === 'number') ? lon : (vesselLocation ? vesselLocation.longitude : 73.80);", "const targetLon = (typeof lon === 'number') ? lon : (vesselLocation ? vesselLocation.longitude : 72.83);")
content = content.replace("const targetLat = (vesselLocation && typeof vesselLocation.latitude === 'number') ? vesselLocation.latitude : 15.246;", "const targetLat = (vesselLocation && typeof vesselLocation.latitude === 'number') ? vesselLocation.latitude : 18.922;")
content = content.replace("const targetLon = (vesselLocation && typeof vesselLocation.longitude === 'number') ? vesselLocation.longitude : 73.803;", "const targetLon = (vesselLocation && typeof vesselLocation.longitude === 'number') ? vesselLocation.longitude : 72.834;")

# 2. Add GPS State and Location Management Code
TARGET_BEFORE = "    let isBackendConnected = false;"

JS_ADDITIONS = """    let isBackendConnected = false;

    // --- Live GPS Tracking & Manual Location Management ---
    let isGpsTrackingEnabled = true;
    let customLocationName = null;

    // Comprehensive Coastal Ports & Maritime Hubs Directory for instant 0ms lookup
    const MARITIME_PORTS_CATALOG = {
      "mumbai": { name: "Mumbai Port & Offshore Sector", lat: 18.922, lon: 72.834 },
      "bombay": { name: "Mumbai Port & Offshore Sector", lat: 18.922, lon: 72.834 },
      "navi mumbai": { name: "Jawaharlal Nehru Port (JNPT)", lat: 18.950, lon: 72.950 },
      "jnpt": { name: "JNPT Nhava Sheva", lat: 18.950, lon: 72.950 },
      "kochi": { name: "Kochi Marine Terminal & Offshore", lat: 9.967, lon: 76.242 },
      "cochin": { name: "Kochi Marine Terminal & Offshore", lat: 9.967, lon: 76.242 },
      "chennai": { name: "Chennai Port & East Coast Waters", lat: 13.085, lon: 80.298 },
      "madras": { name: "Chennai Port & East Coast Waters", lat: 13.085, lon: 80.298 },
      "visakhapatnam": { name: "Visakhapatnam Deepwater Harbour", lat: 17.686, lon: 83.218 },
      "vizag": { name: "Visakhapatnam Deepwater Harbour", lat: 17.686, lon: 83.218 },
      "kolkata": { name: "Kolkata Marine Approaches", lat: 22.550, lon: 88.310 },
      "calcutta": { name: "Kolkata Marine Approaches", lat: 22.550, lon: 88.310 },
      "haldia": { name: "Haldia Dock Complex", lat: 22.020, lon: 88.060 },
      "mangalore": { name: "New Mangalore Port Waters", lat: 12.870, lon: 74.840 },
      "karwar": { name: "Karwar Marine Sanctuary Waters", lat: 14.810, lon: 74.130 },
      "porbandar": { name: "Porbandar Marine Coast", lat: 21.642, lon: 69.609 },
      "kandla": { name: "Deendayal Port (Kandla)", lat: 23.003, lon: 70.218 },
      "veraval": { name: "Veraval Commercial Fishery Sector", lat: 20.900, lon: 70.360 },
      "surat": { name: "Hazira Surat Maritime Terminal", lat: 21.116, lon: 72.635 },
      "hazira": { name: "Hazira Surat Maritime Terminal", lat: 21.116, lon: 72.635 },
      "ratnagiri": { name: "Ratnagiri Coastal Anchorage", lat: 16.990, lon: 73.300 },
      "malvan": { name: "Malvan Marine Sanctuary Waters", lat: 16.060, lon: 73.470 },
      "kanyakumari": { name: "Kanyakumari Cape Waters", lat: 8.078, lon: 77.555 },
      "tuticorin": { name: "VO Chidambaranar Port (Tuticorin)", lat: 8.764, lon: 78.134 },
      "thoothukudi": { name: "VO Chidambaranar Port (Tuticorin)", lat: 8.764, lon: 78.134 },
      "rameswaram": { name: "Pamban & Rameswaram Channel", lat: 9.287, lon: 79.312 },
      "cuddalore": { name: "Cuddalore Coastal Fairway", lat: 11.750, lon: 79.770 },
      "pondicherry": { name: "Puducherry Coastal Waters", lat: 11.930, lon: 79.830 },
      "puducherry": { name: "Puducherry Coastal Waters", lat: 11.930, lon: 79.830 },
      "machilipatnam": { name: "Machilipatnam Bay", lat: 16.180, lon: 81.130 },
      "kakinada": { name: "Kakinada Deep Sea Port", lat: 16.980, lon: 82.240 },
      "paradip": { name: "Paradip Major Marine Port", lat: 20.260, lon: 86.670 },
      "digha": { name: "Digha Fishery Coastal Waters", lat: 21.626, lon: 87.510 },
      "port blair": { name: "Port Blair Andaman Marine Waters", lat: 11.667, lon: 92.733 },
      "alappuzha": { name: "Alappuzha Coastal Waters", lat: 9.498, lon: 76.326 },
      "alleppey": { name: "Alappuzha Coastal Waters", lat: 9.498, lon: 76.326 },
      "bhavnagar": { name: "Bhavnagar Anchorage", lat: 21.764, lon: 72.150 },
      "daman": { name: "Daman Coastal Fairway", lat: 20.417, lon: 72.833 },
      "diu": { name: "Diu Head Marine Anchorage", lat: 20.714, lon: 70.987 },
      "jamnagar": { name: "Gulf of Kutch Jamnagar Waters", lat: 22.470, lon: 70.070 },
      "mormugao": { name: "Mormugao Port Fairway", lat: 15.420, lon: 73.780 },
      "betul": { name: "Betul South Marine Sector", lat: 15.140, lon: 73.950 }
    };

    // Update GPS Toggle Button UI
    function updateGpsToggleUI(enabled) {
      const btn = document.getElementById('btnGpsToggle');
      const txt = document.getElementById('txtGpsToggle');
      if (!btn || !txt) return;

      if (enabled) {
        btn.classList.add('gps-active');
        btn.classList.remove('gps-disabled');
        txt.textContent = (currentLang === 'hi') ? '📡 जीपीएस: चालू' : (currentLang === 'ta' ? '📡 GPS: ஆன்' : '📡 GPS: ON');
        btn.setAttribute('title', 'GPS Tracking Active • Click to Pause');
      } else {
        btn.classList.remove('gps-active');
        btn.classList.add('gps-disabled');
        txt.textContent = (currentLang === 'hi') ? '📡 जीपीएस: बंद' : (currentLang === 'ta' ? '📡 GPS: ஆஃப்' : '📡 GPS: OFF');
        btn.setAttribute('title', 'GPS Tracking Paused • Click to Resume');
      }
    }

    // Toggle Real-time GPS Tracking System
    function toggleGpsTracking(forceState) {
      if (typeof forceState === 'boolean') {
        isGpsTrackingEnabled = forceState;
      } else {
        isGpsTrackingEnabled = !isGpsTrackingEnabled;
      }

      updateGpsToggleUI(isGpsTrackingEnabled);

      if (isGpsTrackingEnabled) {
        console.log('[KyroX GPS] Resuming real-time GPS tracking watch...');
        customLocationName = null;
        initVesselLocation();
        const elFix = document.getElementById('txtTelemetryFix');
        if (elFix) {
          elFix.innerHTML = '<span style="color:var(--pfz-bright);">📡 GPS TRACKING RESUMED • ACQUIRING FIX...</span>';
        }
      } else {
        console.log('[KyroX GPS] Pausing real-time GPS tracking watch...');
        if (gpsWatchId !== null) {
          try {
            navigator.geolocation.clearWatch(gpsWatchId);
          } catch (e) {}
          gpsWatchId = null;
        }
        const elFix = document.getElementById('txtTelemetryFix');
        if (elFix && vesselLocation) {
          const lat = vesselLocation.latitude;
          const lon = vesselLocation.longitude;
          elFix.innerHTML = `<span style="color:var(--caution-border);">📍 MANUAL LOCATION MODE: ${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E (GPS PAUSED)</span>`;
        }
      }
    }

    // Attach GPS Toggle Event Listener
    const btnGpsToggle = document.getElementById('btnGpsToggle');
    if (btnGpsToggle) {
      btnGpsToggle.addEventListener('click', () => toggleGpsTracking());
    }

    // Geocode or Parse Coordinates from User Input
    async function resolveLocationQuery(queryStr) {
      const q = (queryStr || '').trim();
      if (!q) return null;

      // 1. Check for explicit decimal coordinates: e.g. "18.92, 72.83" or "18.92 72.83"
      const coordMatch = q.match(/^(-?\\d{1,2}(?:\\.\\d+)?)[,\\s]+(-?\\d{1,3}(?:\\.\\d+)?)$/);
      if (coordMatch) {
        const lat = parseFloat(coordMatch[1]);
        const lon = parseFloat(coordMatch[2]);
        if (lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
          return {
            name: `Coordinates (${lat.toFixed(4)}°, ${lon.toFixed(4)}°)`,
            latitude: lat,
            longitude: lon
          };
        }
      }

      // 2. Check Fast Built-in Maritime Ports Catalog
      const cleanKey = q.toLowerCase().replace(/^(port of|port|harbour|beach|island)\\s+/i, '').trim();
      if (MARITIME_PORTS_CATALOG[cleanKey]) {
        const item = MARITIME_PORTS_CATALOG[cleanKey];
        return {
          name: item.name,
          latitude: item.lat,
          longitude: item.lon
        };
      }

      // Check partial matches in catalog
      for (const key of Object.keys(MARITIME_PORTS_CATALOG)) {
        if (cleanKey.includes(key) || key.includes(cleanKey)) {
          const item = MARITIME_PORTS_CATALOG[key];
          return {
            name: item.name,
            latitude: item.lat,
            longitude: item.lon
          };
        }
      }

      // 3. Online OpenStreetMap Nominatim Geocoding Fallback
      try {
        const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q)}&limit=1`;
        const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) {
            const first = data[0];
            const lat = parseFloat(first.lat);
            const lon = parseFloat(first.lon);
            if (!isNaN(lat) && !isNaN(lon)) {
              return {
                name: first.display_name.split(',')[0].trim() || q,
                latitude: lat,
                longitude: lon
              };
            }
          }
        }
      } catch (err) {
        console.warn('[KyroX Geocoder] Nominatim lookup failed:', err);
      }

      return null;
    }

    // Execute Manual Location Search and Detailed Briefing
    async function handleManualLocationSearch(queryStr) {
      const q = (queryStr || '').trim();
      if (!q) return;

      const submitBtn = document.getElementById('btnSubmitLocation');
      const originalBtnHtml = submitBtn ? submitBtn.innerHTML : '';
      if (submitBtn) {
        submitBtn.innerHTML = '<span>⏳ SEARCHING...</span>';
        submitBtn.disabled = true;
      }

      try {
        const resolved = await resolveLocationQuery(q);
        if (!resolved) {
          alert((currentLang === 'hi') ? 
            `स्थान "${q}" नहीं मिला। कृपया बंदरगाह का नाम (उदा. Mumbai, Kochi) या अक्षांश/देशांतर (उदा. 18.92, 72.83) दर्ज करें।` : 
            `Location "${q}" could not be resolved. Please enter a recognized port name (e.g. Mumbai, Kochi) or Lat, Lon coordinates.`);
          return;
        }

        console.log('[KyroX Location Search] Resolved:', resolved);
        customLocationName = resolved.name;

        // Automatically pause device GPS watch so the manual location is preserved
        if (isGpsTrackingEnabled) {
          toggleGpsTracking(false);
        }

        const lat = resolved.latitude;
        const lon = resolved.longitude;
        vesselLocation = { latitude: lat, longitude: lon, name: resolved.name };

        // Pin on chart and focus
        pinUserLocationOnMap({
          id: 'manual_location',
          name: resolved.name,
          latitude: lat,
          longitude: lon,
          type: 'MANUAL_LOCATION',
          marker_type: 'USER'
        });

        // Update Backend and Telemetry
        sendLocationToBackend(lat, lon);
        fetchRiskHeatmap(lat, lon);

        // Fetch Telemetry specifically for this location
        try {
          const telemRes = await fetch(`${BACKEND_API_BASE}/telemetry?lat=${lat}&lon=${lon}`);
          if (telemRes.ok) {
            const telemData = await telemRes.json();
            updateBridgeTelemetryUI(telemData);
            displayLocationDetailsDrawer(resolved.name, lat, lon, telemData);
          } else {
            displayLocationDetailsDrawer(resolved.name, lat, lon, null);
          }
        } catch (e) {
          displayLocationDetailsDrawer(resolved.name, lat, lon, null);
        }

        // Recalculate 24-hour predictions for this specific location
        if (typeof loadRegressionData === 'function') {
          loadRegressionData(activeRegVar);
        }

      } finally {
        if (submitBtn) {
          submitBtn.innerHTML = originalBtnHtml;
          submitBtn.disabled = false;
        }
      }
    }

    // Display Comprehensive Details Drawer for the Selected Location
    function displayLocationDetailsDrawer(name, lat, lon, telemData) {
      const latDeg = Math.floor(Math.abs(lat));
      const latMin = ((Math.abs(lat) - latDeg) * 60).toFixed(1);
      const lonDeg = Math.floor(Math.abs(lon));
      const lonMin = ((Math.abs(lon) - lonDeg) * 60).toFixed(1);
      const coordsStr = `${latDeg}°${latMin}'${lat >= 0 ? 'N' : 'S'}, ${lonDeg}°${lonMin}'${lon >= 0 ? 'E' : 'W'}`;

      const wave = (telemData && telemData.wave) ? telemData.wave : '1.3m';
      const wind = (telemData && telemData.wind) ? telemData.wind : '12.4 kts';
      const current = (telemData && telemData.current) ? telemData.current : '1.1 kts';
      const depth = (telemData && telemData.depth) ? telemData.depth : '32m';
      const baro = (telemData && telemData.baro) ? telemData.baro : '1008.6 hPa';
      const sst = (telemData && telemData.sst) ? telemData.sst : '28.2°C';
      const clearance = (telemData && telemData.clearance === 'SAFE') ? 'SAFE (सुरक्षित)' : 'CAUTION (सतर्कता आवश्यक)';

      const title = `📍 ${name}`;
      const reason = (currentLang === 'hi') ? 
        `समुद्री स्थिति: तरंग ऊंचाई ${wave}, पवन ${wind}, जलधारा ${current}, गहराई ${depth}, वायुदाब ${baro}, जल तापमान ${sst}। नेविगेशन स्थिति: ${clearance}। 24-घंटे सांख्यिकीय पूर्वानुमान इस स्थान से अपडेट हैं।` : 
        `Marine Conditions: Wave ${wave}, Wind ${wind}, Current ${current}, Depth ${depth}, Baro ${baro}, SST ${sst}. Clearance Status: ${clearance}. 24-hour regression prediction model synchronized to this position.`;

      showTacticalDrawer(title, reason, coordsStr, 'vessel', 'manual_location');
    }

    // Location Search Bar Controls Setup
    const inputCustomLocation = document.getElementById('inputCustomLocation');
    const btnSubmitLocation = document.getElementById('btnSubmitLocation');
    const btnClearLocSearch = document.getElementById('btnClearLocSearch');
    const btnCurrentGpsLocation = document.getElementById('btnCurrentGpsLocation');

    if (inputCustomLocation) {
      inputCustomLocation.addEventListener('input', () => {
        if (btnClearLocSearch) {
          btnClearLocSearch.style.display = inputCustomLocation.value.trim() ? 'block' : 'none';
        }
      });

      inputCustomLocation.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          handleManualLocationSearch(inputCustomLocation.value);
        }
      });
    }

    if (btnSubmitLocation && inputCustomLocation) {
      btnSubmitLocation.addEventListener('click', () => {
        handleManualLocationSearch(inputCustomLocation.value);
      });
    }

    if (btnClearLocSearch && inputCustomLocation) {
      btnClearLocSearch.addEventListener('click', () => {
        inputCustomLocation.value = '';
        btnClearLocSearch.style.display = 'none';
        inputCustomLocation.focus();
      });
    }

    if (btnCurrentGpsLocation) {
      btnCurrentGpsLocation.addEventListener('click', () => {
        if (inputCustomLocation) {
          inputCustomLocation.value = '';
          if (btnClearLocSearch) btnClearLocSearch.style.display = 'none';
        }
        toggleGpsTracking(true);
      });
    }

    // Quick Port Chips Listeners
    document.querySelectorAll('.loc-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const portName = chip.getAttribute('data-loc');
        if (inputCustomLocation) {
          inputCustomLocation.value = portName;
          if (btnClearLocSearch) btnClearLocSearch.style.display = 'block';
        }
        handleManualLocationSearch(portName);
      });
    });
"""

if "MARITIME_PORTS_CATALOG" not in content:
    content = content.replace(TARGET_BEFORE, JS_ADDITIONS, 1)

with open(INDEX_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print("Phase 2 JS features successfully integrated into Frontend/index.html")
