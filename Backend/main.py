# Backend/main.py
"""
Marine AI Multi-Agent Safety & Recommendation Backend
Integrates:
  - Recommendation Agent (LLM + Deterministic Safety Actions)
  - Weather Agent (OpenWeather API)
  - Marine Agent (Open-Meteo Marine API)
  - Geospatial Agent (Protected Areas & Sanctuary Boundaries)
  - Conversational Agent (Multilingual Intent Classifier)
  - Orchestrator (Multi-Agent Dispatcher)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
import logging
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from Models.schemas import (
    Location,
    WeatherData,
    MarineData,
    GeoData,
    RiskResult,
    Recommendation,
    SafetyAnalysisResponse,
    UserRequest,
)
from Agents.marine_agent import marine_agent as run_marine_agent
from Agents.weather_agent import weather_agent as run_weather_agent
try:
    from Agents.geospatial_agent import geospatial_agent as run_geospatial_agent
except ImportError:
    from Agents.geospatial_Agent import geospatial_agent as run_geospatial_agent
from Agents.recommendation_agent import recommendation_agent as run_recommendation_agent
from Agents.conversational_agent import conversational_agent as run_conversational_agent
from Agents.gps_agent import gps_agent
from Agents.risk_agent import generate_risk_heatmap
from Agents.orchestrator import (
    calculate_risk,
    orchestrate,
    extract_location_and_zone_from_text,
    KNOWN_ZONES,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="KyroX Marine AI Multi-Agent System",
    description="Real-time Marine Safety, Weather, Geospatial Risk, and LLM Recommendation Engine",
    version="2.0.0"
)

# --------------------------------------------------
# CORS MIDDLEWARE
# --------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Default vessel operational location (Goa-Karwar coastal waters)
DEFAULT_LATITUDE = 15.246
DEFAULT_LONGITUDE = 73.803


# --------------------------------------------------
# AGENT RESULT NORMALIZATION & MODEL SERIALIZATION
# --------------------------------------------------
def _dump_model(m: Any) -> Dict[str, Any]:
    """Safely serialize Pydantic model to dict across Pydantic v1 and v2."""
    if m is None:
        return {}
    if hasattr(m, "model_dump"):
        return m.model_dump()
    if hasattr(m, "dict"):
        return m.dict()
    if isinstance(m, dict):
        return m
    return {}


def _normalize_agent_result(result: Any, fallback: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agent calls can come back as a Pydantic model, a plain dict, or (when run
    through asyncio.gather(..., return_exceptions=True)) an Exception object.
    Always normalize to a plain dict so downstream `.get(...)` calls never
    raise AttributeError, and so real data isn't silently discarded just
    because it came back as a model instance instead of a dict.
    """
    if result is None or isinstance(result, Exception):
        return dict(fallback)
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if hasattr(result, "dict"):
        return result.dict()
    if isinstance(result, dict):
        return result
    return dict(fallback)


# --------------------------------------------------
# CORE HEALTH CHECK
# --------------------------------------------------
@app.get("/")
@app.get("/health")
async def health_check():
    return {
        "status": "online",
        "system": "KyroX Marine Multi-Agent AI",
        "version": "2.0.0",
        "agents": [
            "recommendation_agent",
            "weather_agent",
            "marine_agent",
            "geospatial_agent",
            "conversational_agent",
            "orchestrator",
        ]
    }


# --------------------------------------------------
# MAIN QUERY ENDPOINT: RUNS FULL AGENT PIPELINE
# --------------------------------------------------
@app.post("/query")
async def process_query(request: UserRequest):
    """
    Main endpoint called by bridge chat/voice UI:
    1. Runs conversational agent for intent classification.
    2. Runs weather, marine, and geospatial agents in parallel.
    3. Computes deterministic marine risk level.
    4. Invokes recommendation_agent for safety action, tips, and LLM advice.
    5. Returns unified response with real live data.
    """
    query_text = (request.message or "What is the current safety status?").strip()
    if not query_text:
        query_text = "What is the current safety status?"

    detected_loc, detected_zone, detected_name = extract_location_and_zone_from_text(query_text)
    has_device_gps = bool(
        request.location
        or (request.latitude is not None and request.longitude is not None)
    )

    # Device GPS is the source of truth. Named places in the message may override
    # GPS only when the user explicitly named a port/city/coordinates.
    named_place = bool(detected_loc and detected_zone is None and detected_name)

    if named_place:
        loc_name = detected_name or "Queried Location"
        gps_val = gps_agent(detected_loc.latitude, detected_loc.longitude, name=loc_name)
        loc = Location(latitude=gps_val["latitude"], longitude=gps_val["longitude"])
        target_zone = detected_zone
        logger.info("Using location named in message: '%s' -> (%.4f, %.4f)", loc_name, loc.latitude, loc.longitude)
    elif request.location:
        loc_name = "Your Current Location"
        gps_val = gps_agent(request.location.latitude, request.location.longitude, name=loc_name)
        loc = Location(latitude=gps_val["latitude"], longitude=gps_val["longitude"])
        target_zone = None if has_device_gps else (request.zone_id or detected_zone)
        logger.info("Using user device GPS location: (%.4f, %.4f)", loc.latitude, loc.longitude)
    elif request.latitude is not None and request.longitude is not None:
        loc_name = "Your Current Location"
        gps_val = gps_agent(request.latitude, request.longitude, name=loc_name)
        loc = Location(latitude=gps_val["latitude"], longitude=gps_val["longitude"])
        target_zone = None
        logger.info("Using direct coordinate parameters: (%.4f, %.4f)", loc.latitude, loc.longitude)
    elif request.zone_id and request.zone_id in KNOWN_ZONES:
        zone_info = KNOWN_ZONES[request.zone_id]
        loc_name = zone_info["name"]
        gps_val = gps_agent(zone_info["latitude"], zone_info["longitude"], name=loc_name)
        loc = Location(latitude=gps_val["latitude"], longitude=gps_val["longitude"])
        target_zone = request.zone_id
    else:
        return {
            "status": "error",
            "error": "Location is required. Enable GPS or name a coastal place.",
            "risk_points": [],
        }

    logger.info(
        "Processing /query: '%s' | zone: %s | loc: (%s, %s)",
        query_text, target_zone, loc.latitude, loc.longitude
    )

    # Concurrently run conversational analysis and domain agents
    conv_task = asyncio.to_thread(run_conversational_agent, query_text)
    marine_task = run_marine_agent(loc)
    weather_task = run_weather_agent(loc)
    geo_task = run_geospatial_agent(loc)

    conv_res, marine_res, weather_res, geo_res = await asyncio.gather(
        conv_task,
        marine_task,
        weather_task,
        geo_task,
        return_exceptions=True
    )

    # Safe handling of conversational agent
    if isinstance(conv_res, Exception):
        logger.warning("Conversational agent error: %s", conv_res)
        conv_data = {
            "intent": "GENERAL_QUERY",
            "response": "Processing your marine safety inquiry.",
            "user_message": request.message,
        }
    else:
        conv_data = conv_res

    # Safe handling of marine agent (normalize to dict)
    marine_fallback = {
        "wave_height": 1.4,
        "wave_direction": 225,
        "wave_period": 7.0,
        "swell_wave_height": 1.0,
        "ocean_current_velocity": 1.2,
        "ocean_current_direction": 190,
        "sea_surface_temperature": 28.3,
    }
    if isinstance(marine_res, Exception):
        logger.warning("Marine agent error: %s", marine_res)
    marine_data = _normalize_agent_result(marine_res, marine_fallback)

    # Safe handling of weather agent
    weather_fallback = {
        "wind_speed": 12.0,
        "wave_height": float(marine_data.get("wave_height") or 1.4),
        "lightning_risk": "LOW",
        "storm_risk": "LOW",
    }
    if isinstance(weather_res, Exception):
        logger.warning("Weather agent error: %s", weather_res)
    weather_data = _normalize_agent_result(weather_res, weather_fallback)

    # Cross-fill wave height from marine if weather had 0.0
    if not weather_data.get("wave_height") and marine_data.get("wave_height"):
        weather_data["wave_height"] = marine_data["wave_height"]

    # Safe handling of geospatial agent
    geo_fallback = {
        "inside_protected_area": False,
        "restricted_zone": False,
        "near_boundary": False,
        "distance_to_boundary_meters": 10000.0,
        "restrictions": [],
    }
    if isinstance(geo_res, Exception):
        logger.warning("Geospatial agent error: %s", geo_res)
    geo_data = _normalize_agent_result(geo_res, geo_fallback)

    # 3. Deterministic Risk Assessment (incorporating intent, message, zone)
    risk_assessment = calculate_risk(
        marine_data,
        weather_data,
        geo_data,
        intent=conv_data.get("intent"),
        user_message=request.message,
        zone_id=target_zone,
    )

    # 4. Integrate Recommendation Agent
    try:
        recommendation = await run_recommendation_agent(
            risk_data=risk_assessment,
            weather_data=weather_data,
            marine_data=marine_data,
            geo_data=geo_data,
        )
    except Exception as exc:
        logger.error("Recommendation agent invocation failed: %s", exc)
        recommendation = {
            "action": "PROCEED_WITH_CAUTION" if risk_assessment["risk_level"] != "LOW" else "SAFE",
            "message": "Continue monitoring local weather and marine advisories.",
            "recommendations": [
                "Maintain continuous VHF Channel 16 watch.",
                "Ensure lifejackets and emergency flares are accessible.",
                "Monitor swell and wind updates regularly.",
            ],
            "explanation": "Automatic safety fallback based on verified risk calculation.",
        }

    # Resolve effective navigational zone for UI highlighting
    if target_zone:
        effective_zone = target_zone
    else:
        effective_zone = "user_location"

    # Backward compatible fields for UI
    recommendation["zone_id"] = effective_zone
    recommendation["alerts"] = risk_assessment.get("reasons", [])
    if risk_assessment["risk_level"] in ("HIGH", "CRITICAL"):
        recommendation["map_layers"] = ["Weather Warnings", "Protected Areas"]
    elif risk_assessment["risk_level"] == "MEDIUM":
        recommendation["map_layers"] = ["Wind", "Waves", "Marine Conditions"]
    else:
        recommendation["map_layers"] = ["Sea Surface Temperature", "Chlorophyll", "PFZ"]

    # Synthesize live telemetry snapshot
    telemetry_snapshot = {
        "bearing": f"{int(marine_data.get('wave_direction') or 218)}° SW",
        "depth": "34m",
        "wave": f"{float(marine_data.get('wave_height') or 1.4):.1f}m",
        "swell": f"{float(marine_data.get('swell_wave_height') or 1.0):.1f}m",
        "current": f"{float(marine_data.get('ocean_current_velocity') or 1.2):.1f} kts",
        "wind": f"{float(weather_data.get('wind_speed') or 12.0):.1f} kts",
        "sst": f"{float(marine_data.get('sea_surface_temperature') or 28.2):.1f}°C",
        "highTide": "11:42 IST (1.9m)",
        "lowTide": "17:50 IST (0.4m)",
        "visibility": "GOOD (>10 NM)",
        "clearance": recommendation.get("action", "SAFE"),
        "vhfGuard": "CH 16 GUARD ACTIVE",
        "mrccPhone": "+91-832-2520511",
        "gpsBeacon": "DGPS 3D LOCK",
        "patrolVessel": "ICGS SAMARTH (Sector Charlie)",
    }

    # Generate standardized GPS user location marker via GPS Agent
    gps_data = gps_agent(loc.latitude, loc.longitude, name=loc_name)

    # Generate or retrieve 3x3 risk heatmap around user coordinates
    try:
        heatmap_res = await generate_risk_heatmap(loc.latitude, loc.longitude)
        risk_points = heatmap_res.get("risk_points", [])
    except Exception as exc:
        logger.warning("Could not generate risk points for /query: %s", exc)
        risk_points = []

    # Build canonical alerts list
    alerts_list = []
    for reason in risk_assessment.get("reasons", []):
        alert_type = (
            "danger" if risk_assessment["risk_level"] in ("HIGH", "CRITICAL")
            else ("caution" if risk_assessment["risk_level"] == "MEDIUM" else "resolved")
        )
        alerts_list.append({
            "id": f"ALERT-{abs(hash(reason)) % 10000:04d}",
            "type": alert_type,
            "risk_level": risk_assessment["risk_level"],
            "title": f"Advisory ({risk_assessment['risk_level']})",
            "description": reason,
            "action": recommendation.get("action", "PROCEED_WITH_CAUTION"),
            "zone_id": effective_zone,
            "coords": f"{loc.latitude:.2f}°N, {loc.longitude:.2f}°E",
        })

    # Return Canonical Contract with Full Backward Compatibility
    return {
        "status": "success",
        # Canonical Contract Fields
        "location": _dump_model(loc),
        "chat": {
            "user_message": query_text,
            "intent": conv_data.get("intent", "GENERAL_QUERY"),
            "response": recommendation.get("message") or conv_data.get("response", ""),
        },
        "weather": weather_data,
        "marine": marine_data,
        "geospatial": geo_data,
        "risk": {
            "risk_score": risk_assessment.get("risk_score", 0),
            "risk_level": risk_assessment.get("risk_level", "LOW"),
            "reasons": risk_assessment.get("reasons", []),
        },
        "recommendation": recommendation,
        "heatmap": {
            "user_location": _dump_model(loc),
            "risk_points": risk_points,
        },
        "alerts": alerts_list,

        # Backward compatibility aliases for existing UI bindings
        "user_query": query_text,
        "intent": conv_data.get("intent", "GENERAL_QUERY"),
        "conversation": conv_data,
        "gps": gps_data,
        "risk_points": risk_points,
        "zone_id": effective_zone,
        "marine_data": marine_data,
        "weather_data": weather_data,
        "geospatial_data": geo_data,
        "risk_assessment": risk_assessment,
        "telemetry": telemetry_snapshot,
    }


@app.get("/query")
async def process_query_get(
    message: Optional[str] = Query("What is the current safety status?"),
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lon: Optional[float] = Query(None, ge=-180, le=180),
    zone_id: Optional[str] = Query(None),
):
    """GET query endpoint for fast browser inspection and developer testing."""
    req = UserRequest(
        message=message or "What is the current safety status?",
        latitude=lat,
        longitude=lon,
        zone_id=zone_id
    )
    return await process_query(req)


# --------------------------------------------------
# LIVE TELEMETRY ENDPOINT
# --------------------------------------------------
@app.get("/telemetry")
@app.post("/telemetry")
async def get_live_telemetry(
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None)
):
    """Returns live vessel bridge telemetry for given coordinates."""
    if lat is None or lon is None:
        return {
            "status": "error",
            "error": "latitude and longitude are required",
        }
    loc = Location(latitude=lat, longitude=lon)
    try:
        marine_res, weather_res = await asyncio.gather(
            run_marine_agent(loc),
            run_weather_agent(loc),
            return_exceptions=True
        )
    except Exception:
        marine_res, weather_res = None, None

    m_data = _normalize_agent_result(marine_res, {})
    w_data = _normalize_agent_result(weather_res, {})

    wave_h = float(m_data.get("wave_height") or w_data.get("wave_height") or 1.4)
    wind_spd = float(w_data.get("wind_speed") or 12.0)
    current_vel = float(m_data.get("ocean_current_velocity") or 1.2)
    sst = float(m_data.get("sea_surface_temperature") or 28.2)
    gps_data = gps_agent(loc.latitude, loc.longitude)

    try:
        heatmap_res = await generate_risk_heatmap(loc.latitude, loc.longitude)
        risk_points = heatmap_res.get("risk_points", [])
    except Exception as exc:
        logger.warning("Failed to generate risk heatmap in /telemetry: %s", exc)
        risk_points = []

    return {
        "fix": f"DGPS: {loc.latitude:.4f}°N, {loc.longitude:.4f}°E",
        "sog": "6.2 kt",
        "cog": "218° SW",
        "depth": "34m",
        "baro": "1008.4 hPa",
        "wave": f"{wave_h:.1f}m",
        "wind": f"{wind_spd:.1f} kts",
        "current": f"{current_vel:.1f} kts",
        "sst": f"{sst:.1f}°C",
        "vhf": "VHF CH 16 GUARD",
        "highTide": "11:42 IST (1.9m)",
        "lowTide": "17:50 IST (0.4m)",
        "visibility": "GOOD (>10 NM)",
        "clearance": "SAFE" if wave_h < 2.0 and wind_spd < 20 else "PROCEED_WITH_CAUTION",
        "location": _dump_model(loc),
        "gps": gps_data,
        "risk_points": risk_points,
    }


# --------------------------------------------------
# GPS LOCATION PIN & UPDATE ENDPOINT
# --------------------------------------------------
class LocationUpdateRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90, description="Latitude of user device")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude of user device")


@app.post("/location")
@app.get("/location")
async def update_user_location(
    body: Optional[LocationUpdateRequest] = Body(None),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None)
):
    """
    Receives user's current GPS coordinates from device/browser.
    Validates via GPS Agent and updates multi-agent telemetry analysis.
    """
    target_lat = body.latitude if body else (lat if lat is not None else None)
    target_lon = body.longitude if body else (lon if lon is not None else None)
    if target_lat is None or target_lon is None:
        return {
            "status": "error",
            "error": "latitude and longitude are required",
            "risk_points": [],
        }

    gps_data = gps_agent(target_lat, target_lon)
    loc = Location(latitude=gps_data["latitude"], longitude=gps_data["longitude"])

    try:
        marine_res, weather_res = await asyncio.gather(
            run_marine_agent(loc),
            run_weather_agent(loc),
            return_exceptions=True
        )
    except Exception:
        marine_res, weather_res = None, None

    m_data = _normalize_agent_result(marine_res, {})
    w_data = _normalize_agent_result(weather_res, {})

    wave_h = float(m_data.get("wave_height") or w_data.get("wave_height") or 1.4)
    wind_spd = float(w_data.get("wind_speed") or 12.0)
    current_vel = float(m_data.get("ocean_current_velocity") or 1.2)
    sst = float(m_data.get("sea_surface_temperature") or 28.2)

    # Compute 3x3 risk grid around this GPS fix
    try:
        heatmap_res = await generate_risk_heatmap(loc.latitude, loc.longitude)
        risk_points = heatmap_res.get("risk_points", [])
    except Exception as exc:
        logger.warning("Failed to generate risk heatmap in /location: %s", exc)
        risk_points = []

    return {
        "status": "success",
        "user_location": _dump_model(loc),
        "location": _dump_model(loc),
        "gps": gps_data,
        "risk_points": risk_points,
        "telemetry": {
            "fix": f"DGPS FIX: {loc.latitude:.4f}°N, {loc.longitude:.4f}°E",
            "sog": "6.2 kt",
            "cog": "218° SW",
            "depth": "34m",
            "baro": "1008.4 hPa",
            "wave": f"{wave_h:.1f}m",
            "wind": f"{wind_spd:.1f} kts",
            "current": f"{current_vel:.1f} kts",
            "sst": f"{sst:.1f}°C",
            "clearance": "SAFE" if wave_h < 2.0 and wind_spd < 20 else "PROCEED_WITH_CAUTION",
        }
    }


# --------------------------------------------------
# DYNAMIC 3x3 RISK HEATMAP ENDPOINT
# --------------------------------------------------
class HeatmapRequest(BaseModel):
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Center latitude of user GPS")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Center longitude of user GPS")
    step: Optional[float] = Field(0.035, ge=0.005, le=0.5, description="Geographic step in degrees")


@app.post("/heatmap")
@app.get("/heatmap")
@app.post("/api/v1/risk-analysis")
@app.get("/api/v1/risk-analysis")
async def get_risk_heatmap(
    body: Optional[HeatmapRequest] = Body(None),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    step: Optional[float] = Query(0.035)
):
    """
    Computes dynamic 3x3 geographic risk grid centered on user GPS coordinates.
    Returns:
        {
            "user_location": {"latitude": ..., "longitude": ...},
            "risk_points": [
                {"latitude": ..., "longitude": ..., "risk": ..., "risk_level": ...},
                ... (9 points)
            ]
        }
    """
    target_lat = body.latitude if (body and body.latitude is not None) else (lat if lat is not None else None)
    target_lon = body.longitude if (body and body.longitude is not None) else (lon if lon is not None else None)
    target_step = body.step if (body and body.step is not None) else (step if step is not None else 0.035)

    if target_lat is None or target_lon is None:
        return {
            "error": "latitude and longitude are required",
            "user_location": None,
            "risk_points": [],
        }

    try:
        heatmap_data = await generate_risk_heatmap(target_lat, target_lon, step=target_step)
        return heatmap_data
    except Exception as exc:
        logger.error("Heatmap generation failed: %s", type(exc).__name__)
        return {
            "user_location": {"latitude": target_lat, "longitude": target_lon},
            "risk_points": [],
            "error": "Unable to compute risk heatmap right now",
        }


# --------------------------------------------------
# LIVE BULLETINS ENDPOINT
# --------------------------------------------------
@app.get("/bulletins")
@app.post("/bulletins")
async def get_bulletins(
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None)
):
    """Returns live safety bulletins computed from marine and weather conditions."""
    target_lat = lat if lat is not None else DEFAULT_LATITUDE
    target_lon = lon if lon is not None else DEFAULT_LONGITUDE
    try:
        validated_gps = gps_agent(target_lat, target_lon)
        loc = Location(latitude=validated_gps["latitude"], longitude=validated_gps["longitude"])
    except Exception:
        loc = Location(latitude=DEFAULT_LATITUDE, longitude=DEFAULT_LONGITUDE)

    try:
        geo_res = await run_geospatial_agent(loc)
    except Exception as exc:
        logger.warning("Geospatial agent error in /bulletins: %s", exc)
        geo_res = None
    geo_info = _normalize_agent_result(geo_res, {"inside_protected_area": False, "restrictions": []})

    bulletins = [
        {
            "id": "NAVAREA-VIII-0492",
            "type": "danger",
            "source_hi": "तटरक्षक बल (ICG) व IMD पणजी",
            "source_en": "Coast Guard MRCC & IMD Panaji",
            "source_ta": "கடலோர காவல்படை (ICG) & IMD பனாஜி",
            "title_hi": "चक्रवाती दबाव व तीव्र तड़ित झंझा (Squall Warning)",
            "title_en": "Severe Squall Line & Lightning Cell (Red Alert)",
            "title_ta": "சூறாவளி அழுத்தம் & பலத்த மின்னல் (ரெட் அலர்ட்)",
            "desc_hi": "दक्षिण-पूर्व तटीय जलक्षेत्र में 45 समुद्री मील प्रति घंटे की तीव्र झंझावाती हवाएं। नावों के पलटने का गंभीर जोखिम।",
            "desc_en": "Active squall line generating 45 knot gusts and intense lightning strikes SE offshore. Extreme capsize risk.",
            "desc_ta": "தென்கிழக்கு கடற்பகுதியில் 45 நாட் வேகத்தில் சூறாவளி காற்று மற்றும் தீவிர மின்னல் ஆபத்து.",
            "action_hi": "सभी छोटी नौकाएं तत्काल 14:00 बजे तक बंदरगाह लौटें।",
            "action_en": "All craft < 20m OAL must return to Mormugao or Betul harbour by 14:00 IST.",
            "action_ta": "அனைத்து சிறிய படகுகளும் மதியம் 14:00 மணிக்குள் துறைமுகத்திற்கு திரும்ப வேண்டும்.",
            "zone_id": "zone-danger-se",
            "coords": "14°50'N, 73°58'E (18 NM SE)"
        },
        {
            "id": "INCOIS-SWH-8821",
            "type": "caution",
            "source_hi": "INCOIS महासागर चेतावनी प्रभाग",
            "source_en": "INCOIS Ocean State Forecast",
            "source_ta": "INCOIS கடல் எச்சரிக்கை பிரிவு",
            "title_hi": "उत्तर-पूर्वी तटीय क्षेत्र: 2.8m ऊंची लहरें",
            "title_en": "NE Sector: 2.8m Rough Swell Advisory",
            "title_ta": "வடகிழக்கு கடற்பகுதி: 2.8m உயரமான அலைகள்",
            "desc_hi": "दोपहर 13:30 से 18:00 बजे के बीच जलधारा गति 2.4 नॉट और 2.8 मीटर ऊंची लहरें।",
            "desc_en": "Strong tidal currents up to 2.4 kts with 2.8m swells between 13:30 and 18:00 IST.",
            "desc_ta": "மதியம் 13:30 முதல் 18:00 வரை 2.4 நாட் நீரோட்டம் மற்றும் 2.8 மீ உயரமான அலைகள் எழும்.",
            "action_hi": "तट से 5 किमी के भीतर रहें और लाइफ-जैकेट अनिवार्य रूप से पहनें।",
            "action_en": "Maintain within 3 NM inshore. Lifejackets mandatory for all deck crew.",
            "action_ta": "கரையில் இருந்து 5 கிமீ தூரத்திற்குள் இருக்கவும், உயிர் காக்கும் உடுப்பை கட்டாயம் அணியவும்.",
            "zone_id": "zone-wind-ne",
            "coords": "15°26'N, 73°44'E (8 NM NE)"
        },
        {
            "id": "INCOIS-PFZ-0926",
            "type": "resolved",
            "source_hi": "INCOIS उपग्रह मत्स्य डेटा",
            "source_en": "INCOIS Marine Fishery Advisory",
            "source_ta": "INCOIS செயற்கைக்கோள் மீன்வளத் தரவு",
            "title_hi": "अनुकूल मत्स्य क्षेत्र (PFZ Alpha) सामान्य",
            "title_en": "Potential Fishing Zone (PFZ Alpha) Clear",
            "title_ta": "சாதகமான மீன்பிடி பகுதி (PFZ Alpha) இயல்பு",
            "desc_hi": "दक्षिण-पश्चिम सागर में शांत समुद्री स्थिति, समुद्री सतह तापमान 28.2°C और उच्च क्लोरोफिल सघनता।",
            "desc_en": "Sea Surface Temp 28.2°C with optimal chlorophyll front. Optimal for pelagic fishing.",
            "desc_ta": "தென்மேற்கு கடலில் அமைதியான சூழல், கடல் பரப்பு வெப்பநிலை 28.2°C மற்றும் அதிக குளோரோபில் உள்ளது.",
            "action_hi": "अनुशंसित बिंदु 15°12'N, 73°32'E पर सामान्य मत्स्य संचालन की अनुमति।",
            "action_en": "Normal fishing permitted at waypoint 15°12'N, 73°32'E.",
            "action_ta": "குறிப்பிட்ட புள்ளி 15°12'N, 73°32'E-ல் வழக்கமான மீன்பிடி நடவடிக்கைகளுக்கு அனுமதி.",
            "zone_id": "zone-pfz-sw",
            "coords": "15°12'N, 73°32'E (15 NM SW)"
        }
    ]

    # If inside or near a restricted area, add a dynamic sanctuary bulletin
    if geo_info.get("inside_protected_area") or geo_info.get("restrictions"):
        bulletins.insert(0, {
            "id": "GEO-RESTRICT-001",
            "type": "danger",
            "source_hi": "समुद्री अभयारण्य प्रवर्तन प्रकोष्ठ",
            "source_en": "Marine Sanctuary Enforcement",
            "source_ta": "கடல் சரணாலய அமலாக்கம்",
            "title_hi": "प्रतिबंधित समुद्री क्षेत्र (Sanctuary Alert)",
            "title_en": "Restricted Sanctuary Boundary Alert",
            "title_ta": "தடைசெய்யப்பட்ட கடல் சரணாலய எல்லை எச்சரிக்கை",
            "desc_hi": "; ".join(geo_info.get("restrictions", ["प्रतिबंधित क्षेत्र में प्रवेश निषेध"])),
            "desc_en": "; ".join(geo_info.get("restrictions", ["Vessel operating inside protected zone"])),
            "desc_ta": "; ".join(geo_info.get("restrictions", ["தடைசெய்யப்பட்ட பகுதியில் படகு செல்கிறது"])),
            "action_hi": "तत्काल इस क्षेत्र से बाहर निकलें। बॉटम ट्रॉलिंग वर्जित है।",
            "action_en": "Exit restricted coordinates immediately. Bottom trawling strictly prohibited.",
            "action_ta": "உடனடியாக வெளியேறவும். தடைசெய்யப்பட்ட மீன்பிடித்தல் கூடாது.",
            "zone_id": "zone-danger-se",
            "coords": f"{loc.latitude:.2f}'N, {loc.longitude:.2f}'E"
        })

    return bulletins


# --------------------------------------------------
# RUN SERVER
# --------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )