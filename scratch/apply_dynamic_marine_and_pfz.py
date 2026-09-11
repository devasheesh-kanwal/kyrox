# scratch/apply_dynamic_marine_and_pfz.py
import re

INDEX_PATH = r"c:\Users\devas\OneDrive\Documents\KyroX\Frontend\index.html"

with open(INDEX_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. ADD GOA TO QUICK CHIPS IN HTML
OLD_QUICK_CHIPS = """          <div class="loc-quick-chips" id="locQuickChips">
            <span class="loc-quick-lbl" id="txtQuickPortsLbl">त्वरित बंदरगाह:</span>
            <button type="button" class="loc-chip" data-loc="Mumbai">मुंबई</button>
            <button type="button" class="loc-chip" data-loc="Kochi">कोच्चि</button>"""

NEW_QUICK_CHIPS = """          <div class="loc-quick-chips" id="locQuickChips">
            <span class="loc-quick-lbl" id="txtQuickPortsLbl">त्वरित बंदरगाह:</span>
            <button type="button" class="loc-chip" data-loc="Goa">गोवा (Goa)</button>
            <button type="button" class="loc-chip" data-loc="Mumbai">मुंबई (Mumbai)</button>
            <button type="button" class="loc-chip" data-loc="Kochi">कोच्चि (Kochi)</button>"""

content = content.replace(OLD_QUICK_CHIPS, NEW_QUICK_CHIPS, 1)

# 2. REMOVE FIXED zone_id FROM QUICK QUERIES SO THEY ALWAYS USE ACTIVE LOCATION
content = re.sub(
    r'\{ label: "([^"]+)", query: "([^"]+)", zone_id: "zone-pfz-sw" \}',
    r'{ label: "\1", query: "\2", zone_id: null }',
    content
)
content = re.sub(
    r'\{ label: "([^"]+)", query: "([^"]+)", zone_id: "zone-wind-ne" \}',
    r'{ label: "\1", query: "\2", zone_id: null }',
    content
)
content = re.sub(
    r'\{ label: "([^"]+)", query: "([^"]+)", zone_id: "zone-danger-se" \}',
    r'{ label: "\1", query: "\2", zone_id: null }',
    content
)

# 3. ADD GOA TO MARITIME_PORTS_CATALOG IF MISSING
if '"goa"' not in content:
    content = content.replace(
        'const MARITIME_PORTS_CATALOG = {',
        'const MARITIME_PORTS_CATALOG = {\n      "goa": { name: "Goa Coastal Waters & Panaji Sector", lat: 15.420, lon: 73.780 },\n      "panaji": { name: "Goa Panaji Coastal Waters", lat: 15.420, lon: 73.780 },',
        1
    )

# 4. REPLACE STATIC MAP_ZONES AND MAP_MARKERS WITH DYNAMIC FUNCTIONS
DYNAMIC_ZONES_ENGINE = """
    // --- Dynamic Multi-Location Marine Zones & PFZ Fishing Advice Engine ---
    window.lastBridgeTelemetry = {};

    function updateDynamicMarineZones(lat, lon, locName, liveData) {
      if (typeof lat !== 'number' || typeof lon !== 'number') return;
      const isEastCoast = lon >= 78.0;
      const lonOffset = isEastCoast ? 0.18 : -0.18;
      const pfzLat = Number((lat - 0.04).toFixed(4));
      const pfzLon = Number((lon + lonOffset).toFixed(4));

      const cautionLat = Number((lat + 0.10).toFixed(4));
      const cautionLon = Number((lon + (isEastCoast ? 0.06 : -0.06)).toFixed(4));

      const dangerLat = Number((lat - 0.15).toFixed(4));
      const dangerLon = Number((lon + (isEastCoast ? 0.22 : -0.22)).toFixed(4));

      const displayName = locName || customLocationName || (vesselLocation && vesselLocation.name) || 'Active Coastal Sector';
      const telem = liveData || window.lastBridgeTelemetry || {};
      const sst = telem.sst || '28.2°C';
      const wave = telem.wave || '1.1m';
      const wind = telem.wind || '11.5 kts';

      MAP_ZONES = [
        {
          id: "zone-pfz-sw",
          type: "pfz",
          center: [pfzLat, pfzLon],
          latLngs: [
            [Number((pfzLat + 0.06).toFixed(4)), Number((pfzLon - 0.06).toFixed(4))],
            [Number((pfzLat + 0.05).toFixed(4)), Number((pfzLon + 0.06).toFixed(4))],
            [Number((pfzLat - 0.06).toFixed(4)), Number((pfzLon + 0.07).toFixed(4))],
            [Number((pfzLat - 0.08).toFixed(4)), Number((pfzLon - 0.05).toFixed(4))]
          ],
          label_hi: `INCOIS PFZ मत्स्य क्षेत्र (${displayName})`,
          label_en: `INCOIS PFZ Fishing Zone (${displayName})`,
          label_ta: `INCOIS PFZ மீன்பிடி பகுதி (${displayName})`,
          sub_hi: `SST ${sst} • अनुकूल क्लोरोफिल सीमा`,
          sub_en: `SST ${sst} • Optimal Chlorophyll Front`,
          sub_ta: `SST ${sst} • உகந்த குளோரோபில் எல்லை`,
          reason_hi: `${displayName} के लिए उच्च क्लोरोफिल व तापीय प्रवणता। बांगड़ा, सुरमई और टूना मछली के झुंड सक्रिय। शांत समुद्र (${wave})।`,
          reason_en: `Active pelagic thermal front for ${displayName}. Indian Mackerel, Kingfish and Tuna feeding schools active. Calm sea state (${wave}).`,
          reason_ta: `${displayName} பகுதிக்கான அதிக குளோரோபில் மற்றும் சாதகமான வெப்பநிலை. மீன் கூட்டங்கள் அதிகம். அலை உயரம் (${wave}).`,
          coords: `${pfzLat.toFixed(2)}°N, ${pfzLon.toFixed(2)}°E (${isEastCoast ? 'Bearing 095° E' : 'Bearing 215° SW'}, 12 NM)`
        },
        {
          id: "zone-wind-ne",
          type: "caution",
          center: [cautionLat, cautionLon],
          latLngs: [
            [Number((cautionLat + 0.05).toFixed(4)), Number((cautionLon - 0.05).toFixed(4))],
            [Number((cautionLat + 0.06).toFixed(4)), Number((cautionLon + 0.06).toFixed(4))],
            [Number((cautionLat - 0.05).toFixed(4)), Number((cautionLon + 0.07).toFixed(4))],
            [Number((cautionLat - 0.06).toFixed(4)), Number((cautionLon - 0.05).toFixed(4))]
          ],
          label_hi: `सावधानी क्षेत्र (${displayName})`,
          label_en: `Caution Area (${displayName})`,
          label_ta: `எச்சரிக்கை பகுதி (${displayName})`,
          sub_hi: `Swell 2.4m • मध्यम धारा`,
          sub_en: `Swell 2.4m • Moderate Drift`,
          sub_ta: `Swell 2.4m • மிதமான நீரோட்டம்`,
          reason_hi: `तटीय जलक्षेत्र में 2.4m ऊंची लहरें और हवाएं। छोटी नौकाएं सतर्कता बरतें।`,
          reason_en: `Moderate swell reaching 2.4m with gusty winds in inshore approaches. Small craft exercise vigilance.`,
          reason_ta: `2.4 மீ உயரமான அலைகள் மற்றும் பலத்த காற்று. சிறிய படகுகள் கவனமாக இருக்கவும்.`,
          coords: `${cautionLat.toFixed(2)}°N, ${cautionLon.toFixed(2)}°E (8 NM Inshore)`
        },
        {
          id: "zone-danger-se",
          type: "danger",
          center: [dangerLat, dangerLon],
          latLngs: [
            [Number((dangerLat + 0.07).toFixed(4)), Number((dangerLon - 0.06).toFixed(4))],
            [Number((dangerLat + 0.06).toFixed(4)), Number((dangerLon + 0.08).toFixed(4))],
            [Number((dangerLat - 0.07).toFixed(4)), Number((dangerLon + 0.06).toFixed(4))],
            [Number((dangerLat - 0.06).toFixed(4)), Number((dangerLon - 0.07).toFixed(4))]
          ],
          label_hi: `प्रतिबंधित खतरा क्षेत्र (Squall Alert)`,
          label_en: `Restricted Hazard Zone (Squall Alert)`,
          label_ta: `தடைசெய்யப்பட்ட ஆபத்து பகுதி (Squall Alert)`,
          sub_hi: `Squall 40+ kt • Lightning Radar`,
          sub_en: `Squall 40+ kt • Lightning Radar`,
          sub_ta: `Squall 40+ kt • Lightning Radar`,
          reason_hi: `तटीय रडार द्वारा ट्रैक किया गया स्क्वॉल क्षेत्र। 40+ नॉट की झंझावाती हवाएं और आकाशीय बिजली का खतरा।`,
          reason_en: `Radar tracked squall line with 40+ knot cyclonic gusts and lightning strikes. Entry prohibited.`,
          reason_ta: `40+ நாட் சூறாவளி காற்று மற்றும் மின்னல் ஆபத்து. இப்பகுதியில் செல்ல தடை.`,
          coords: `${dangerLat.toFixed(2)}°N, ${dangerLon.toFixed(2)}°E (16 NM Offshore)`
        }
      ];

      MAP_MARKERS = [
        {
          id: "mkr-pfz-target",
          kind: "pfz",
          latLng: [pfzLat, pfzLon],
          zone_id: "zone-pfz-sw",
          label_hi: `PFZ लक्ष्य बिंदु (${displayName})`,
          label_en: `PFZ Target Waypoint (${displayName})`,
          label_ta: `PFZ இலக்கு புள்ளி (${displayName})`,
          coords: `${pfzLat.toFixed(2)}°N, ${pfzLon.toFixed(2)}°E`,
          reason_hi: `अनुशंसित जाल डालने का बिंदु (${displayName} से 12 NM)। बांगड़ा और सुरमई के झुंड सक्रिय। गहराई: 38-45 मीटर।`,
          reason_en: `Optimal net casting waypoint (12 NM offshore ${displayName}). Pelagic Mackerel and Tuna schools detected. Depth: 38-45m.`,
          reason_ta: `வலை வீசுவதற்கு உகந்த புள்ளி (${displayName} கரையில் இருந்து 12 கடல் மைல்). கானாங்கெளுத்தி மற்றும் சூரை மீன்கள் அதிகம்.`
        },
        {
          id: "mkr-squall-center",
          kind: "danger",
          latLng: [dangerLat, dangerLon],
          zone_id: "zone-danger-se",
          label_hi: `तूफान केंद्र (${displayName})`,
          label_en: `Squall Core (${displayName})`,
          label_ta: `புயல் மையம் (${displayName})`,
          coords: `${dangerLat.toFixed(2)}°N, ${dangerLon.toFixed(2)}°E`,
          reason_hi: `सक्रिय झंझावात केंद्र। उत्तर-पूर्व दिशा में आगे बढ़ रहा है।`,
          reason_en: `Active offshore squall cell moving northeast.`,
          reason_ta: `தீவிர புயல் மையம் வடகிழக்கு நோக்கி நகர்கிறது.`
        }
      ];

      if (typeof renderLeafletTacticalZones === 'function') renderLeafletTacticalZones();
      if (typeof renderLeafletWaypoints === 'function') renderLeafletWaypoints();
    }

    function getDynamicAdvisoryResponse(category) {
      const loc = vesselLocation || { latitude: 18.922, longitude: 72.834, name: 'Active Sector' };
      const displayName = loc.name || customLocationName || 'Active Coastal Sector';
      const isEastCoast = (loc.longitude || 72.83) >= 78.0;
      const lonOffset = isEastCoast ? 0.18 : -0.18;
      const pfzLat = (loc.latitude - 0.04).toFixed(2);
      const pfzLon = (loc.longitude + lonOffset).toFixed(2);
      const coordsStr = `${pfzLat}°N, ${pfzLon}°E`;

      const telem = window.lastBridgeTelemetry || {};
      const sst = telem.sst || '28.2°C';
      const wave = telem.wave || '1.1m';
      const wind = telem.wind || '11.5 kts';
      const current = telem.current || '0.9 kts';
      const depth = telem.depth || '36m';
      const highTide = telem.highTide || '06:45 IST (+2.0m)';

      if (category === 'fishing') {
        return {
          station: "INCOIS-HYD / NATIONAL PFZ SERVICE",
          text_en: `Satellite and oceanographic telemetry confirms active **Potential Fishing Zone (PFZ)** for **${displayName}** at **${coordsStr}** (12 NM offshore). Sea surface temperature is **${sst}** with optimal thermal front and chlorophyll boundary. High density of Indian Mackerel, Sardines, and Kingfish. Wave swell is ${wave} with ${current} current.`,
          text_hi: `उपग्रह व महासागरीय टेलीमेट्री के अनुसार **${displayName}** के लिए **उत्तम मत्स्य क्षेत्र (PFZ)** बिंदु **${coordsStr}** (12 समुद्री मील दूर) पर सक्रिय है। समुद्री सतह तापमान **${sst}** और अनुकूल क्लोरोफिल सीमा मौजूद है। बांगड़ा, सुरमई और टूना मछली मिलने की 85% संभावना है। लहरें ${wave} और शांत बहाव ${current} है।`,
          text_ta: `செயற்கைக்கோள் தகவலின்படி **${displayName}** பகுதிக்கான **சிறந்த மீன்பிடி மண்டலம் (PFZ)** **${coordsStr}** புள்ளியில் செயல்படுகிறது. கடல் வெப்பநிலை **${sst}** மற்றும் சாதகமான குளோரோபில் உள்ளது. கானாங்கெளுத்தி மற்றும் வஞ்சிரம் மீன் கிடைக்க 85% வாய்ப்பு உண்டு. அலை உயரம் ${wave}, நீரோட்டம் ${current}.`,
          telemetry_en: { bearing: isEastCoast ? "095° E (12 NM)" : "220° SW (12 NM)", depth: depth, wave: `${wave} (Calm)`, current: current, sst: sst },
          telemetry_hi: { bearing: isEastCoast ? "095° E (12 समुद्री मील)" : "220° SW (12 समुद्री मील)", depth: depth, wave: `${wave} (शांत लहरें)`, current: current, sst: sst },
          telemetry_ta: { bearing: isEastCoast ? "095° E (12 கடல் மைல்)" : "220° SW (12 கடல் மைல்)", depth: depth, wave: `${wave} (அமைதியான அலை)`, current: current, sst: sst },
          zone_id: "zone-pfz-sw"
        };
      } else if (category === 'weather') {
        return {
          station: "IMD-COASTAL / COASTGUARD RADAR",
          text_en: `Doppler marine radar for **${displayName}**: Sustained winds of ${wind} with waves at ${wave}. Swell conditions are currently manageable inshore, but offshore squalls may generate 2.5m+ seas. Maintain continuous watch on VHF Ch 16.`,
          text_hi: `**${displayName}** के लिए समुद्री मौसम: वर्तमान में हवाएं ${wind} और लहरें ${wave} हैं। तटीय क्षेत्र में स्थिति सामान्य है किंतु खुले समुद्र में 2.5m तक ऊंची लहरें उठ सकती हैं। वीएचएफ चैनल 16 पर सतत निगरानी रखें।`,
          text_ta: `**${displayName}** பகுதிக்கான வானிலை: காற்றின் வேகம் ${wind}, அலை உயரம் ${wave}. கரையோர பகுதியில் நிலைமை சாதகமாக உள்ளது. VHF Ch 16-ல் தொடர் கண்காணிப்பில் இருக்கவும்.`,
          telemetry_en: { bearing: "Offshore Sector (15 NM)", depth: depth, wave: wave, wind: wind, current: current },
          telemetry_hi: { bearing: "तटीय समुद्री क्षेत्र (15 समुद्री मील)", depth: depth, wave: wave, wind: wind, current: current },
          telemetry_ta: { bearing: "கடற்பகுதி (15 கடல் மைல்)", depth: depth, wave: wave, wind: wind, current: current },
          zone_id: "zone-wind-ne"
        };
      } else if (category === 'safety') {
        return {
          station: "NATIONAL HYDROGRAPHIC OFFICE",
          text_en: `Safe return tide window for **${displayName}**: Next High Tide peaks at **${highTide}**, providing maximum bar depth for harbor transit. Sea swell is ${wave}, suitable for safe entry into designated shelters.`,
          text_hi: `**${displayName}** के लिए सुरक्षित बंदरगाह वापसी समय: अगला उच्च ज्वार (High Tide) **${highTide}** पर रहेगा जो बंदरगाह में सुरक्षित प्रवेश के लिए सर्वोत्तम है। लहरें ${wave} शांत हैं।`,
          text_ta: `**${displayName}** துறைமுகம் திரும்புவதற்கான நேரம்: அடுத்த உயர் அலை (High Tide) **${highTide}** மணிக்கு இருக்கும். அலை உயரம் ${wave}, பாதுகாப்பான வழிசெலுத்தலுக்கு உகந்தது.`,
          telemetry_en: { bearing: "Harbor Channel Course", depth: "Bar Depth Nominal", wave: wave, current: current, highTide: highTide },
          telemetry_hi: { bearing: "बंदरगाह चैनल दिशा", depth: "सुरक्षित गहराई", wave: wave, current: current, highTide: highTide },
          telemetry_ta: { bearing: "துறைமுக கால்வாய்", depth: "போதுமான ஆழம்", wave: wave, current: current, highTide: highTide },
          zone_id: "zone-pfz-sw"
        };
      } else {
        const vesselCoordsStr = `${loc.latitude.toFixed(4)}°N, ${loc.longitude.toFixed(4)}°E`;
        return {
          station: "MRCC NATIONAL / INDIAN COAST GUARD",
          text_en: `Emergency distress protocol for **${displayName}**: Standby on **VHF Channel 16 (156.800 MHz)** or toll-free **1554**. Your position **${vesselCoordsStr}** is logged with the nearest Coast Guard rescue station.`,
          text_hi: `**${displayName}** के लिए आपातकालीन बचाव प्रोटोकॉल: **VHF Channel 16 (156.800 MHz)** या टोल-फ्री **1554** पर संपर्क करें। आपकी स्थिति **${vesselCoordsStr}** तटरक्षक बचाव केंद्र में दर्ज है।`,
          text_ta: `**${displayName}** அவசர மீட்பு நடைமுறை: **VHF Channel 16 (156.800 MHz)** அல்லது கட்டணமில்லா எண் **1554**-ஐ அழைக்கவும். உங்கள் அமைவிடம் **${vesselCoordsStr}** கடலோர காவல்படையால் பதிவு செய்யப்பட்டுள்ளது.`,
          telemetry_en: { bearing: "MRCC Station 085° E", depth: depth, wave: wave, current: current, vhfGuard: "CH 16 / 08 Active" },
          telemetry_hi: { bearing: "तटरक्षक दिशा 085° E", depth: depth, wave: wave, current: current, vhfGuard: "CH 16 / 08 सक्रिय" },
          telemetry_ta: { bearing: "காவல்படை திசை 085° E", depth: depth, wave: wave, current: current, vhfGuard: "CH 16 / 08 செயலில் உள்ளது" },
          zone_id: "zone-danger-se"
        };
      }
    }
"""

if "updateDynamicMarineZones" not in content:
    content = content.replace("let MAP_ZONES = [", DYNAMIC_ZONES_ENGINE + "\n    let MAP_ZONES = [", 1)

# 5. UPDATE updateBridgeTelemetryUI TO SAVE LATEST TELEMETRY & SYNC ZONES
OLD_TELEM_UI = """    function updateBridgeTelemetryUI(data) {
      if (!data) return;"""

NEW_TELEM_UI = """    function updateBridgeTelemetryUI(data) {
      if (!data) return;
      window.lastBridgeTelemetry = Object.assign(window.lastBridgeTelemetry || {}, data);
      if (vesselLocation && typeof updateDynamicMarineZones === 'function') {
        updateDynamicMarineZones(vesselLocation.latitude, vesselLocation.longitude, vesselLocation.name, data);
      }"""

content = content.replace(OLD_TELEM_UI, NEW_TELEM_UI, 1)

# 6. UPDATE pinUserLocationOnMap TO CALL updateDynamicMarineZones
OLD_PIN_USER = """      // Update vesselLocation cache
      vesselLocation = { latitude: lat, longitude: lon };"""

NEW_PIN_USER = """      // Update vesselLocation cache
      vesselLocation = { latitude: lat, longitude: lon, name: gpsData.name || (vesselLocation ? vesselLocation.name : null) };
      if (typeof updateDynamicMarineZones === 'function') {
        updateDynamicMarineZones(lat, lon, gpsData.name, window.lastBridgeTelemetry);
      }"""

content = content.replace(OLD_PIN_USER, NEW_PIN_USER, 1)

# 7. UPDATE OFFLINE ADVISORY DISPATCH TO USE getDynamicAdvisoryResponse
OLD_OFFLINE_ADVISORY = """        const lower = text.toLowerCase();
        let matchedKey = 'fishing';
        let matched = ADVISORY_RESPONSES.fishing;
        if (ADVISORY_RESPONSES.emergency.keywords.some(k => lower.includes(k))) {
          matchedKey = 'emergency';
          matched = ADVISORY_RESPONSES.emergency;
        } else if (ADVISORY_RESPONSES.safety.keywords.some(k => lower.includes(k))) {
          matchedKey = 'safety';
          matched = ADVISORY_RESPONSES.safety;
        } else if (ADVISORY_RESPONSES.weather.keywords.some(k => lower.includes(k))) {
          matchedKey = 'weather';
          matched = ADVISORY_RESPONSES.weather;
        }"""

NEW_OFFLINE_ADVISORY = """        const lower = text.toLowerCase();
        let matchedKey = 'fishing';
        if (ADVISORY_RESPONSES.emergency.keywords.some(k => lower.includes(k))) {
          matchedKey = 'emergency';
        } else if (ADVISORY_RESPONSES.safety.keywords.some(k => lower.includes(k))) {
          matchedKey = 'safety';
        } else if (ADVISORY_RESPONSES.weather.keywords.some(k => lower.includes(k))) {
          matchedKey = 'weather';
        }
        let matched = typeof getDynamicAdvisoryResponse === 'function' ? 
          getDynamicAdvisoryResponse(matchedKey) : 
          ADVISORY_RESPONSES[matchedKey];"""

content = content.replace(OLD_OFFLINE_ADVISORY, NEW_OFFLINE_ADVISORY, 1)

with open(INDEX_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print("Dynamic marine zones and location-specific fishing advice applied to Frontend/index.html")
