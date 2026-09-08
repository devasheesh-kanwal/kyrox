# backend/agents/orchestrator.py
import asyncio
import logging
import re
from typing import Optional, Union, Tuple

from Agents.conversational_agent import conversational_agent
from Agents.weather_agent import weather_agent
from Agents.marine_agent import marine_agent
from Agents.geospatial_Agent import geospatial_agent
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


def extract_location_and_zone_from_text(text: str) -> Tuple[Optional[Location], Optional[str]]:
    """Detect mentioned geographical points, sanctuaries, or tactical zones in text."""
    low = (text or "").lower()

    if any(k in low for k in ["danger", "squall", "red alert", "14°50", "14.83", "तूफान"]):
        return Location(latitude=14.83, longitude=73.97), "zone-danger-se"
    if any(k in low for k in ["caution", "rough swell", "2.8m", "15°26", "15.43", "सावधानी"]):
        return Location(latitude=15.43, longitude=73.73), "zone-wind-ne"
    if any(k in low for k in ["pfz", "machli", "fishing spot", "alpha", "15°12", "15.20"]):
        return Location(latitude=15.20, longitude=73.53), "zone-pfz-sw"
    if "netrani" in low:
        return Location(latitude=14.01, longitude=74.32), None
    if "malvan" in low:
        return Location(latitude=16.06, longitude=73.47), None
    if any(k in low for k in ["mormugao", "fairway", "shipping channel"]):
        return Location(latitude=15.42, longitude=73.78), None
    if "betul" in low:
        return Location(latitude=15.14, longitude=73.95), None

    # Regex search for explicit decimal coordinates e.g. "15.42, 73.81"
    coord_match = re.search(r'(-?\d{1,2}\.\d+)[,\s]+(-?\d{1,3}\.\d+)', low)
    if coord_match:
        try:
            lat = float(coord_match.group(1))
            lon = float(coord_match.group(2))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return Location(latitude=lat, longitude=lon), None
        except ValueError:
            pass

    return None, None


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
    detected_loc, detected_zone = extract_location_and_zone_from_text(user_message)
    effective_zone = zone_id or detected_zone

    if location is not None:
        if isinstance(location, dict):
            loc_obj = Location(**location)
        else:
            loc_obj = location
    elif detected_loc is not None:
        loc_obj = detected_loc
    elif effective_zone and effective_zone in KNOWN_ZONES:
        loc_obj = Location(
            latitude=KNOWN_ZONES[effective_zone]["latitude"],
            longitude=KNOWN_ZONES[effective_zone]["longitude"]
        )
    else:
        # Default vessel operational location (Goa coastal waters)
        loc_obj = Location(latitude=15.246, longitude=73.803)

    # Process validated GPS pin via GPS Agent
    gps_data = gps_agent(loc_obj.latitude, loc_obj.longitude)

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
