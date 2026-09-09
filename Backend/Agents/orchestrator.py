# backend/agents/orchestrator.py
import asyncio
import logging
import re
from typing import Optional, Union, Tuple

from Agents.conversational_agent import conversational_agent
from Agents.weather_agent import weather_agent
from Agents.marine_agent import marine_agent
from Agents.geospatial_agent import geospatial_agent
from Agents.recommendation_agent import recommendation_agent
from Agents.gps_agent import gps_agent
from Models.schemas import Location

logger = logging.getLogger(__name__)

INTENT_NEXT_ACTION = {
    "CHECK_SAFETY": "weather_marine_geospatial_risk",
    "WEATHER_QUERY": "weather_agent",
    "MARINE_QUERY": "marine_agent",
    "BOUNDARY_WARNING": "geospatial_agent",
    "EMERGENCY": "emergency_alert_service",
    "GENERAL_QUERY": "conversational_response",
}

# Known maritime zone coordinates and bounding centers
KNOWN_ZONES = {
    "zone-danger-se": {
        "latitude": 14.83,
        "longitude": 73.97,
        "name": "Restricted Danger Zone (Red Alert Squall Line)",
        "default_wind_kts": 45.0,
        "default_wave_m": 3.6,
        "lightning": "HIGH",
        "storm": "HIGH",
    },
    "zone-wind-ne": {
        "latitude": 15.43,
        "longitude": 73.73,
        "name": "Caution Area (Rough Swell Sector)",
        "default_wind_kts": 22.0,
        "default_wave_m": 2.8,
        "lightning": "LOW",
        "storm": "LOW",
    },
    "zone-pfz-sw": {
        "latitude": 15.20,
        "longitude": 73.53,
        "name": "INCOIS Potential Fishing Zone (PFZ Alpha)",
        "default_wind_kts": 8.0,
        "default_wave_m": 1.1,
        "lightning": "LOW",
        "storm": "LOW",
    },
}


# Comprehensive Indian & International Maritime Ports, Anchorages, and Coastal Regions
COASTAL_LOCATIONS: dict = {
    # Goa Coastal Waters
    "goa": (15.2993, 73.8030, "Goa Coastal Waters", None),
    "panaji": (15.4989, 73.8278, "Panaji (Goa)", None),
    "panjim": (15.4989, 73.8278, "Panaji (Goa)", None),
    "mormugao": (15.4167, 73.7833, "Mormugao Port (Goa)", None),
    "vasco": (15.3982, 73.8113, "Vasco da Gama (Goa)", None),
    "betul": (15.1480, 73.9550, "Betul Estuary (Goa)", None),
    "calangute": (15.5439, 73.7553, "Calangute Offshore (Goa)", None),
    "candolim": (15.5170, 73.7620, "Candolim Coastal Waters (Goa)", None),
    "baga": (15.5560, 73.7510, "Baga Beach Waters (Goa)", None),
    "colva": (15.2780, 73.9120, "Colva Waters (Goa)", None),
    "palolem": (15.0100, 74.0230, "Palolem Bay (Goa)", None),
    "anjuna": (15.5730, 73.7410, "Anjuna Offshore (Goa)", None),
    "malvan": (16.0600, 73.4700, "Malvan Marine Sanctuary (Maharashtra)", None),
    "netrani": (14.0167, 74.3333, "Netrani Island Coral Reserve (Karnataka)", None),

    # Maharashtra & Gujarat (West Coast North)
    "mumbai": (18.9220, 72.8347, "Mumbai Harbour & Offshore", None),
    "bombay": (18.9220, 72.8347, "Mumbai Harbour & Offshore", None),
    "jnpt": (18.9500, 72.9500, "JNPT / Nhava Sheva (Maharashtra)", None),
    "nhava sheva": (18.9500, 72.9500, "JNPT / Nhava Sheva (Maharashtra)", None),
    "alibaug": (18.6414, 72.8722, "Alibaug Coastal Waters", None),
    "alibag": (18.6414, 72.8722, "Alibaug Coastal Waters", None),
    "ratnagiri": (16.9902, 73.3000, "Ratnagiri Port Waters", None),
    "dahanu": (19.9700, 72.7300, "Dahanu Offshore", None),
    "kandla": (23.0033, 70.2186, "Kandla / Deendayal Port (Gujarat)", None),
    "deendayal": (23.0033, 70.2186, "Kandla / Deendayal Port (Gujarat)", None),
    "mundra": (22.8390, 69.7060, "Mundra Port (Gujarat)", None),
    "porbandar": (21.6422, 69.6093, "Porbandar Coastal Waters", None),
    "veraval": (20.9000, 70.3700, "Veraval Fishery Port (Gujarat)", None),
    "okha": (22.4667, 69.0667, "Okha Port (Gujarat)", None),
    "dwarka": (22.2442, 68.9685, "Dwarka Coastal Waters", None),
    "bhavnagar": (21.7645, 72.1519, "Gulf of Khambhat / Bhavnagar", None),
    "surat": (21.1702, 72.8311, "Surat Coastal Waters", None),
    "hazira": (21.1000, 72.6300, "Hazira Industrial Port", None),
    "daman": (20.4283, 72.8397, "Daman Coastal Waters", None),
    "diu": (20.7144, 70.9874, "Diu Island Coastal Waters", None),
    "pipavav": (20.9100, 71.5000, "Port Pipavav (Gujarat)", None),

    # Karnataka & Kerala (West Coast South)
    "karwar": (14.8150, 74.1300, "Karwar Naval & Fishing Port", None),
    "mangalore": (12.9141, 74.8560, "New Mangalore Port Waters", None),
    "mangaluru": (12.9141, 74.8560, "New Mangalore Port Waters", None),
    "bhatkal": (13.9800, 74.5500, "Bhatkal Coastal Waters", None),
    "udupi": (13.3409, 74.7421, "Malpe / Udupi Coastal Waters", None),
    "malpe": (13.3500, 74.7000, "Malpe Fishing Harbour", None),
    "honnavar": (14.2800, 74.4500, "Honnavar Waters", None),
    "cochin": (9.9312, 76.2673, "Cochin / Kochi Port Waters", None),
    "kochi": (9.9312, 76.2673, "Cochin / Kochi Port Waters", None),
    "calicut": (11.2588, 75.7804, "Kozhikode / Calicut Port", None),
    "kozhikode": (11.2588, 75.7804, "Kozhikode / Calicut Port", None),
    "kollam": (8.8932, 76.6141, "Kollam / Quilon Port Waters", None),
    "quilon": (8.8932, 76.6141, "Kollam / Quilon Port Waters", None),
    "alappuzha": (9.4981, 76.3388, "Alappuzha / Alleppey Waters", None),
    "alleppey": (9.4981, 76.3388, "Alappuzha / Alleppey Waters", None),
    "trivandrum": (8.5241, 76.9366, "Thiruvananthapuram Coastal Waters", None),
    "thiruvananthapuram": (8.5241, 76.9366, "Thiruvananthapuram Coastal Waters", None),
    "vizhinjam": (8.3800, 76.9900, "Vizhinjam International Seaport", None),
    "kannur": (11.8745, 75.3704, "Kannur Coastal Waters", None),
    "munambam": (10.1800, 76.1700, "Munambam Fishery Harbour", None),

    # Tamil Nadu & Andhra Pradesh (East Coast South)
    "kanyakumari": (8.0883, 77.5385, "Kanyakumari / Cape Comorin", None),
    "cape comorin": (8.0883, 77.5385, "Kanyakumari / Cape Comorin", None),
    "tuticorin": (8.7642, 78.1348, "V.O. Chidambaranar / Tuticorin Port", None),
    "thoothukudi": (8.7642, 78.1348, "Thoothukudi / Tuticorin Port", None),
    "rameshwaram": (9.2876, 79.3129, "Rameshwaram & Pamban Pass", None),
    "rameswaram": (9.2876, 79.3129, "Rameshwaram & Pamban Pass", None),
    "pamban": (9.2800, 79.2000, "Pamban Strait", None),
    "chennai": (13.0827, 80.2707, "Chennai Port & Coastal Waters", None),
    "madras": (13.0827, 80.2707, "Chennai Port & Coastal Waters", None),
    "ennore": (13.2000, 80.3300, "Kamarajar / Ennore Port", None),
    "pondicherry": (11.9416, 79.8083, "Puducherry / Pondicherry Port", None),
    "puducherry": (11.9416, 79.8083, "Puducherry / Pondicherry Port", None),
    "cuddalore": (11.7500, 79.7700, "Cuddalore Port Waters", None),
    "nagapattinam": (10.7667, 79.8417, "Nagapattinam Fishery Port", None),
    "visakhapatnam": (17.6868, 83.2185, "Visakhapatnam Port & Outer Anchorage", None),
    "vizag": (17.6868, 83.2185, "Visakhapatnam Port & Outer Anchorage", None),
    "kakinada": (16.9891, 82.2475, "Kakinada Deep Water Port", None),
    "machilipatnam": (16.1875, 81.1389, "Machilipatnam Coastal Waters", None),
    "krishnapatnam": (14.2500, 80.1200, "Krishnapatnam Port", None),

    # Odisha & West Bengal (East Coast North)
    "paradip": (20.2644, 86.6698, "Paradip Port Waters", None),
    "paradeep": (20.2644, 86.6698, "Paradip Port Waters", None),
    "dhamra": (20.8000, 86.9700, "Dhamra Port (Odisha)", None),
    "gopalpur": (19.2600, 84.9000, "Gopalpur Port (Odisha)", None),
    "puri": (19.8135, 85.8312, "Puri Coastal Waters", None),
    "kolkata": (22.5726, 88.3639, "Hooghly River / Kolkata Port", None),
    "calcutta": (22.5726, 88.3639, "Hooghly River / Kolkata Port", None),
    "haldia": (22.0257, 88.0583, "Haldia Dock Complex", None),
    "digha": (21.6266, 87.5074, "Digha Coastal Waters", None),

    # Islands & UTs
    "port blair": (11.6234, 92.7265, "Port Blair (Andaman & Nicobar)", None),
    "andaman": (11.6234, 92.7265, "Andaman Sea", None),
    "nicobar": (7.0000, 93.8000, "Great Nicobar Waters", None),
    "kavaratti": (10.5667, 72.6333, "Kavaratti (Lakshadweep)", None),
    "agatti": (10.8500, 72.1833, "Agatti Island (Lakshadweep)", None),
    "lakshadweep": (10.5667, 72.6333, "Lakshadweep Waters", None),

    # Multilingual Names (Hindi / Tamil)
    "मुंबई": (18.9220, 72.8347, "मुंबई (Mumbai Harbour)", None),
    "गोवा": (15.2993, 73.8030, "गोवा (Goa Waters)", None),
    "कोच्चि": (9.9312, 76.2673, "कोच्चि (Kochi Port)", None),
    "चेन्नई": (13.0827, 80.2707, "चेन्नई (Chennai Port)", None),
    "कोलकाता": (22.5726, 88.3639, "कोलकाता (Kolkata Port)", None),
    "मंगलुरु": (12.9141, 74.8560, "मंगलुरु (Mangaluru Port)", None),
    "कारवार": (14.8150, 74.1300, "कारवार (Karwar Port)", None),
    "विशाखापट्टनम": (17.6868, 83.2185, "विशाखापट्टनम (Vizag Port)", None),
    "கொச்சி": (9.9312, 76.2673, "கொச்சி (Kochi)", None),
    "சென்னை": (13.0827, 80.2707, "சென்னை (Chennai)", None),
    "தூத்துக்குடி": (8.7642, 78.1348, "தூத்துக்குடி (Tuticorin)", None),
    "கன்னியாகுமரி": (8.0883, 77.5385, "கன்னியாகுமரி (Kanyakumari)", None),
}

_GEOCODE_CACHE: dict = {}


def _lookup_external_geocoding(text: str) -> Optional[Tuple[Location, str]]:
    """Fast geocoding lookup for explicitly mentioned ports/harbours with in-memory caching."""
    patterns = [
        r'\b(?:port|harbour|harbor|beach|island|coast|bay|gulf)\s+of\s+([A-Za-z\s]{3,24})\b',
        r'\b([A-Za-z\s]{3,24})\s+(?:port|harbour|harbor|beach|island|coast|bay|gulf)\b',
        r'\b(?:city|town|coastal\s+waters)\s+of\s+([A-Za-z\s]{3,24})\b',
    ]
    stoplist = {
        "sail", "sailing", "fish", "fishing", "swim", "swimming",
        "navigate", "navigation", "go", "going", "proceed", "proceeding",
        "leave", "leaving", "dock", "docking", "anchor", "anchoring",
        "safety", "danger", "caution", "weather", "marine", "wind",
        "waves", "status", "report", "the", "now", "today", "tomorrow",
        "water", "sea", "ocean", "here", "port", "beach", "island", "coast"
    }

    candidates = []
    for pat in patterns:
        m = re.search(pat, text or "", re.IGNORECASE)
        if m:
            cand = m.group(1).strip()
            cand_low = cand.lower()
            if cand_low not in stoplist and not any(w in stoplist for w in cand_low.split()):
                candidates.append(cand)

    if not candidates:
        return None

    import httpx
    for place in candidates:
        ckey = place.lower()
        if ckey in _GEOCODE_CACHE:
            lat, lon, name = _GEOCODE_CACHE[ckey]
            return Location(latitude=lat, longitude=lon), name

        try:
            resp = httpx.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": place, "count": 1, "language": "en", "format": "json"},
                timeout=2.0
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results")
                if results and len(results) > 0:
                    top = results[0]
                    lat = float(top["latitude"])
                    lon = float(top["longitude"])
                    name = f"{top.get('name', place)} ({top.get('country', '')})"
                    _GEOCODE_CACHE[ckey] = (lat, lon, name)
                    return Location(latitude=lat, longitude=lon), name
        except Exception as exc:
            logger.debug("External geocoding lookup failed for '%s': %s", place, exc)

    return None


def extract_location_and_zone_from_text(
    text: str
) -> Tuple[Optional[Location], Optional[str], Optional[str]]:
    """
    Detect user-mentioned geographical points, coastal ports, explicit coordinates, or safety zones.
    Returns: (Location, zone_id, location_display_name)
    """
    low = (text or "").lower()

    # 1. Check for explicit DMS coordinates e.g. 15°26'N, 73°44'E or 15 26 N 73 44 E
    dms_match = re.search(
        r'(\d{1,2})[°\s]+(\d{1,2}(?:\.\d+)?)\'?\s*([NSns])[,\s]+(\d{1,3})[°\s]+(\d{1,2}(?:\.\d+)?)\'?\s*([EWew])',
        text or ""
    )
    if dms_match:
        lat_deg, lat_min, lat_dir, lon_deg, lon_min, lon_dir = dms_match.groups()
        lat_val = float(lat_deg) + float(lat_min) / 60.0
        if lat_dir.upper() == 'S':
            lat_val = -lat_val
        lon_val = float(lon_deg) + float(lon_min) / 60.0
        if lon_dir.upper() == 'W':
            lon_val = -lon_val
        if -90 <= lat_val <= 90 and -180 <= lon_val <= 180:
            name_str = f"Coordinates {round(lat_val, 4)}°{lat_dir.upper()}, {round(lon_val, 4)}°{lon_dir.upper()}"
            return Location(latitude=round(lat_val, 6), longitude=round(lon_val, 6)), None, name_str

    # 2. Check for explicit decimal coordinates e.g. "18.92, 72.83" or "lat: 18.92, lon: 72.83"
    coord_match = re.search(r'(?:lat(?:itude)?[:\s]*)?(-?\d{1,2}\.\d+)[,\s]+(?:lon(?:gitude)?[:\s]*)?(-?\d{1,3}\.\d+)', low)
    if coord_match:
        try:
            lat = float(coord_match.group(1))
            lon = float(coord_match.group(2))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                name_str = f"Waypoint ({lat:.4f}°N, {lon:.4f}°E)"
                return Location(latitude=lat, longitude=lon), None, name_str
        except ValueError:
            pass

    # 3. Check tactical simulation keywords ONLY when the user clearly
    # refers to the demo Goa chart overlays — never for generic safety words.
    if any(k in low for k in ["zone-danger-se", "14°50", "14.83"]):
        return Location(latitude=14.83, longitude=73.97), "zone-danger-se", "Restricted Danger Zone (SE Squall)"
    if any(k in low for k in ["zone-wind-ne", "15°26", "15.43"]):
        return Location(latitude=15.43, longitude=73.73), "zone-wind-ne", "Caution Area (Rough Swell Sector)"
    if any(k in low for k in ["zone-pfz-sw", "15°12"]):
        return Location(latitude=15.20, longitude=73.53), "zone-pfz-sw", "INCOIS Potential Fishing Zone (PFZ Alpha)"

    # 4. Check curated dictionary of coastal locations
    # Sort keys by length descending to match multi-word phrases first (e.g. "port blair" before "port")
    sorted_keys = sorted(COASTAL_LOCATIONS.keys(), key=lambda k: len(k), reverse=True)
    for key in sorted_keys:
        # Match as whole word or boundary-enclosed phrase
        pattern = r'\b' + re.escape(key) + r'\b'
        if re.search(pattern, low):
            lat, lon, display_name, zone = COASTAL_LOCATIONS[key]
            return Location(latitude=lat, longitude=lon), zone, display_name

    # 5. Geocoding fallback for non-catalogued places told by the user
    geo_res = _lookup_external_geocoding(text or "")
    if geo_res:
        loc, display_name = geo_res
        return loc, None, display_name

    return None, None, None


def extract_user_conditions(text: str) -> dict:
    """Extract hypothetical or user-reported conditions (wind, waves, lightning, storms)."""
    conds = {}
    low = (text or "").lower()

    # Wind speed extraction (knots, km/h, m/s)
    wind_kt = re.search(r'(\d+(?:\.\d+)?)\s*(?:knot|knots|kt|kts)\b', low)
    if wind_kt:
        conds["wind_speed_kts"] = float(wind_kt.group(1))
    else:
        wind_kmh = re.search(r'(\d+(?:\.\d+)?)\s*(?:km/h|kmph|kph|किमी)\b', low)
        if wind_kmh:
            conds["wind_speed_kts"] = float(wind_kmh.group(1)) * 0.539957
        else:
            wind_ms = re.search(r'(\d+(?:\.\d+)?)\s*(?:m/s|mps)\b', low)
            if wind_ms:
                conds["wind_speed_kts"] = float(wind_ms.group(1)) * 1.94384

    # Wave height extraction (e.g. 3m wave, 3.5 meter, 4.0m)
    wave_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:m|meter|meters|metre|metres|मीटर)\b(?:\s*(?:wave|waves|swell|लहर))?', low)
    if wave_match:
        val = float(wave_match.group(1))
        # Ignore values > 20m as they typically refer to depths, distance, or craft length (e.g. 34m depth)
        if val <= 20.0 and "depth" not in low[max(0, wave_match.start() - 10):wave_match.end()]:
            conds["wave_height"] = val

    # Thunderstorm & Lightning indicators
    if any(k in low for k in ["lightning", "तड़ित", "बिजली", "thunder"]):
        conds["lightning_risk"] = "HIGH"
    if any(k in low for k in ["squall", "cyclone", "storm", "toofan", "तूफान", "झंझावात", "red alert"]):
        conds["storm_risk"] = "HIGH"

    return conds


def calculate_risk(
    marine: dict,
    weather: dict,
    geospatial: dict,
    intent: Optional[str] = None,
    user_message: Optional[str] = None,
    zone_id: Optional[str] = None,
) -> dict:
    """
    Calculate comprehensive marine risk deterministically.
    Considers:
      1. Emergency distress intent (immediate 100/100 Critical override).
      2. Target / active nautical safety zones (e.g. Red Alert squall zone).
      3. Live sensor readings (normalized units: m/s -> knots).
      4. Inquired / hypothetical conditions in user query (what-if evaluation).
      5. Marine sanctuaries and restricted maritime boundaries.
    """
    score = 0
    reasons = []

    # Safe conversion if inputs are Pydantic models or None
    m_dict = marine.model_dump() if hasattr(marine, "model_dump") else (marine if isinstance(marine, dict) else {})
    w_dict = weather.model_dump() if hasattr(weather, "model_dump") else (weather if isinstance(weather, dict) else {})
    g_dict = geospatial.model_dump() if hasattr(geospatial, "model_dump") else (geospatial if isinstance(geospatial, dict) else {})

    marine = m_dict
    weather = w_dict
    geospatial = g_dict

    low_msg = (user_message or "").lower()

    # 1. EMERGENCY DISTRESS OVERRIDE
    is_emergency = (
        intent == "EMERGENCY" or
        any(k in low_msg for k in [
            "mayday", "sinking", "man overboard", "engine failure",
            "sos", "distress", "boat sinking", "fire on board",
            "डूब", "आपातकाल", "जान जोखिम", "नाव डूब"
        ])
    )
    if is_emergency:
        return {
            "risk_score": 100,
            "risk_level": "CRITICAL",
            "reasons": [
                "EMERGENCY DISTRESS DETECTED: Immediate threat to vessel/crew life",
                "Stand by on VHF Channel 16 immediately",
                "Alerting Coast Guard MRCC Goa (+91-832-2520511 / toll-free 1554)"
            ]
        }

    # 2. Extract hypothetical/queried conditions from user message
    user_conds = extract_user_conditions(user_message or "")

    # 3. Zone-based hazard assessment
    effective_zone = zone_id or ""
    if not effective_zone:
        if any(k in low_msg for k in ["danger", "squall", "red alert", "तूफान"]):
            effective_zone = "zone-danger-se"
        elif any(k in low_msg for k in ["caution", "rough swell", "2.8m", "सावधानी"]):
            effective_zone = "zone-wind-ne"

    if effective_zone == "zone-danger-se":
        score += 70
        reasons.append("Restricted Danger Zone (Red Alert): 45 knot gusts & active lightning squall line")
    elif effective_zone == "zone-wind-ne":
        score += 40
        reasons.append("Caution Area: 2.8m rough cross-swells & 35 km/h winds")

    # 4. Wave height evaluation (Douglas scale)
    raw_wave = float(marine.get("wave_height") or weather.get("wave_height") or 0.0)
    queried_wave = float(user_conds.get("wave_height") or 0.0)
    wave_h = max(raw_wave, queried_wave)

    if wave_h >= 3.5:
        score += 50
        reasons.append(f"Severe wave height ({wave_h:.1f}m) - dangerous for all small craft")
    elif wave_h >= 2.5:
        score += 35
        reasons.append(f"Rough sea swell ({wave_h:.1f}m) - vessels < 20m advised extreme caution")
    elif wave_h >= 1.8:
        score += 20
        reasons.append(f"Moderate wave swell ({wave_h:.1f}m)")

    # 5. Wind speed evaluation (convert OpenWeather m/s to knots)
    raw_wind = float(weather.get("wind_speed") or 0.0)
    wind_kts_sensor = (raw_wind * 1.94384) if raw_wind < 30.0 else raw_wind
    queried_wind = float(user_conds.get("wind_speed_kts") or 0.0)
    wind_spd = max(wind_kts_sensor, queried_wind)

    if wind_spd >= 35.0:
        score += 45
        reasons.append(f"Severe gale wind speed ({wind_spd:.1f} kts) - extreme capsize hazard")
    elif wind_spd >= 25.0:
        score += 30
        reasons.append(f"Strong sustained winds ({wind_spd:.1f} kts) - open canoes unsafe")
    elif wind_spd >= 18.0:
        score += 15
        reasons.append(f"Brisk winds ({wind_spd:.1f} kts)")

    # 6. Lightning & Storm evaluation
    lightning = user_conds.get("lightning_risk") or weather.get("lightning_risk")
    storm = user_conds.get("storm_risk") or weather.get("storm_risk")

    if lightning == "HIGH":
        score += 40
        reasons.append("Active lightning cell lock in sector")

    if storm == "HIGH":
        score += 50
        reasons.append("Squall or storm front detected")

    # 7. Geospatial protected area & boundary evaluation
    if geospatial.get("inside_protected_area") or geospatial.get("restricted_zone"):
        score += 50
        sanctuary_notes = geospatial.get("restrictions", [])
        if sanctuary_notes:
            for sn in sanctuary_notes:
                if sn not in reasons:
                    reasons.append(sn)
        else:
            reasons.append("Vessel is inside a restricted or marine sanctuary zone")
    elif geospatial.get("near_boundary"):
        score += 25
        reasons.append("Vessel is operating close to restricted boundary")

    # 8. Final Risk Tier Mapping
    if score >= 80:
        risk_level = "CRITICAL"
    elif score >= 55:
        risk_level = "HIGH"
    elif score >= 30:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "risk_score": min(score, 100),
        "risk_level": risk_level,
        "reasons": reasons,
    }


async def orchestrate(
    user_message: str,
    location: Optional[Union[Location, dict]] = None,
    zone_id: Optional[str] = None,
) -> dict:
    """
    Full end-to-end multi-agent orchestrator:
    1. Runs conversational_agent to extract user intent.
    2. Dynamically extracts landmarks, coordinates, or zones from message.
    3. Runs weather_agent, marine_agent, and geospatial_agent concurrently.
    4. Calculates comprehensive context-aware risk assessment.
    5. Runs recommendation_agent for safety action, actionable tips, and LLM advice.
    6. Returns fully unified multi-agent telemetry and recommendation response.
    """
    conversation = conversational_agent(user_message)
    intent = conversation.get("intent") or "GENERAL_QUERY"

    # Contextual Location Extraction
    detected_loc, detected_zone, detected_name = extract_location_and_zone_from_text(user_message)
    effective_zone = zone_id or detected_zone

    # Location told by user in message takes precedence over passive/stored location!
    if detected_loc is not None:
        loc_obj = detected_loc
        loc_name = detected_name or "Queried Location"
    elif location is not None:
        if isinstance(location, dict):
            loc_obj = Location(**location)
        else:
            loc_obj = location
        loc_name = "Your Current Location"
    elif effective_zone and effective_zone in KNOWN_ZONES:
        loc_obj = Location(
            latitude=KNOWN_ZONES[effective_zone]["latitude"],
            longitude=KNOWN_ZONES[effective_zone]["longitude"]
        )
        loc_name = KNOWN_ZONES[effective_zone]["name"]
    else:
        # Default vessel operational location (Goa coastal waters)
        loc_obj = Location(latitude=15.246, longitude=73.803)
        loc_name = "Default Vessel Station"

    # Process validated GPS pin via GPS Agent
    gps_data = gps_agent(loc_obj.latitude, loc_obj.longitude, name=loc_name)

    # Run domain agents concurrently
    marine_task = marine_agent(loc_obj)
    weather_task = weather_agent(loc_obj)
    geo_task = geospatial_agent(loc_obj)

    results = await asyncio.gather(
        marine_task,
        weather_task,
        geo_task,
        return_exceptions=True,
    )

    marine_data = results[0] if not isinstance(results[0], Exception) else {
        "wave_height": 1.2,
        "sea_surface_temperature": 28.2,
        "ocean_current_velocity": 1.1,
    }
    weather_res = results[1] if not isinstance(results[1], Exception) else None
    geo_data = results[2] if not isinstance(results[2], Exception) else {
        "inside_protected_area": False,
        "restricted_zone": False,
        "near_boundary": False,
        "restrictions": [],
    }

    if hasattr(weather_res, "model_dump"):
        weather_data = weather_res.model_dump()
    elif isinstance(weather_res, dict):
        weather_data = weather_res
    else:
        weather_data = {
            "wind_speed": 12.0,
            "wave_height": float(marine_data.get("wave_height") or 1.2),
            "lightning_risk": "LOW",
            "storm_risk": "LOW",
        }

    # Cross-fill wave height from marine if weather had 0.0
    if not weather_data.get("wave_height") and marine_data.get("wave_height"):
        weather_data["wave_height"] = marine_data["wave_height"]

    # Calculate Contextual Risk
    risk_assessment = calculate_risk(
        marine=marine_data,
        weather=weather_data,
        geospatial=geo_data,
        intent=intent,
        user_message=user_message,
        zone_id=effective_zone,
    )

    # Recommendation Agent Integration
    recommendation = await recommendation_agent(
        risk_data=risk_assessment,
        weather_data=weather_data,
        marine_data=marine_data,
        geo_data=geo_data,
    )

    # Attach UI helper fields
    recommendation["alerts"] = risk_assessment.get("reasons", [])
    if risk_assessment["risk_level"] in ("HIGH", "CRITICAL"):
        recommendation["map_layers"] = ["Weather Warnings", "Protected Areas"]
    elif risk_assessment["risk_level"] == "MEDIUM":
        recommendation["map_layers"] = ["Wind", "Waves", "Marine Conditions"]
    else:
        recommendation["map_layers"] = ["Sea Surface Temperature", "Chlorophyll", "PFZ"]

    logger.info(
        "Orchestrator completed: intent=%s, risk_level=%s, score=%d, action=%s",
        intent,
        risk_assessment["risk_level"],
        risk_assessment["risk_score"],
        recommendation.get("action"),
    )

    return {
        "user_message": user_message,
        "intent": intent,
        "conversation": conversation,
        "location": {"latitude": loc_obj.latitude, "longitude": loc_obj.longitude},
        "gps": gps_data,
        "zone_id": effective_zone,
        "marine_data": marine_data,
        "weather_data": weather_data,
        "geospatial_data": geo_data,
        "risk_assessment": risk_assessment,
        "recommendation": recommendation,
    }


def orchestrator(
    user_message: str,
    location: Optional[Union[Location, dict]] = None,
    zone_id: Optional[str] = None,
) -> dict:
    """Synchronous entry point that runs the async orchestrate coroutine."""
    try:
        return asyncio.run(orchestrate(user_message, location, zone_id))
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(orchestrate(user_message, location, zone_id))
