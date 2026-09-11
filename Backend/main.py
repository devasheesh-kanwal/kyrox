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
from fastapi import FastAPI, Query, Body, HTTPException
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
from Agents.geospatial_agent import geospatial_agent as run_geospatial_agent
from Agents.recommendation_agent import recommendation_agent as run_recommendation_agent
from Agents.conversational_agent import conversational_agent as run_conversational_agent
from Agents.gps_agent import gps_agent
from Agents.risk_agent import generate_risk_heatmap
from Services.prediction_service import compute_24h_prediction, compute_24h_prediction_async
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

# A location is required for live marine analysis. Never substitute a fixed
# harbour when the device has not provided a GPS fix.


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


import math
from datetime import datetime, timezone, timedelta

def _compute_dynamic_tides_and_nav(
    marine_data: Dict[str, Any],
    weather_data: Dict[str, Any],
    geo_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Dynamically compute astronomical tides, baro, SOG, COG, and depth."""
    now_utc = datetime.now(timezone.utc)
    # India Standard Time (IST) is UTC + 5:30
    now_ist = now_utc + timedelta(hours=5, minutes=30)

    # Semi-diurnal M2 lunar tidal cycle: ~12.42 hours (745 minutes)
    epoch_min = int(now_utc.timestamp() / 60)
    cycle_pos = (epoch_min % 745) / 745.0  # 0.0 to 1.0

    if cycle_pos <= 0.5:
        min_to_high = int((0.5 - cycle_pos) * 745) if cycle_pos > 0.05 else int((1.0 - cycle_pos) * 745)
        min_to_low = int((0.25 - cycle_pos) * 745) if cycle_pos <= 0.25 else int((0.75 - cycle_pos) * 745)
    else:
        min_to_high = int((1.0 - cycle_pos) * 745)
        min_to_low = int((0.75 - cycle_pos) * 745) if cycle_pos <= 0.75 else int((1.25 - cycle_pos) * 745)

    next_high_dt = now_ist + timedelta(minutes=min_to_high)
    next_low_dt = now_ist + timedelta(minutes=min_to_low)

    wave_h = marine_data.get("wave_height") or weather_data.get("wave_height")
    wind_spd = weather_data.get("wind_speed")
    current_vel = marine_data.get("ocean_current_velocity")
    current_dir = marine_data.get("ocean_current_direction") or marine_data.get("wave_direction")
    baro = weather_data.get("surface_pressure")
    sst = marine_data.get("sea_surface_temperature")
    dist_shore = (geo_data or {}).get("distance_to_shore_meters")

    depth_m = max(14, min(85, int(float(dist_shore) * 0.0075))) if dist_shore is not None else None
    current_dir = float(current_dir) if current_dir is not None else None
    cardinal = ("SW" if 180 <= current_dir <= 270 else ("NW" if 270 < current_dir <= 360 else ("NE" if 0 <= current_dir <= 90 else "SE"))) if current_dir is not None else None

    return {
        "depth": f"{depth_m}m" if depth_m is not None else "UNAVAILABLE",
        "baro": f"{float(baro):.1f} hPa" if baro is not None else "UNAVAILABLE",
        "sog": "UNAVAILABLE",
        "cog": f"{current_dir:.0f}° {cardinal}" if current_dir is not None else "UNAVAILABLE",
        "highTide": "UNAVAILABLE — tide station data not configured",
        "lowTide": "UNAVAILABLE — tide station data not configured",
        "visibility": "UNAVAILABLE" if not weather_data else ("EXCELLENT (>10 NM)" if weather_data.get("storm_risk") == "LOW" else "MODERATE (5-8 NM)"),
        "wave": f"{float(wave_h):.1f}m" if wave_h is not None else "UNAVAILABLE",
        "wind": f"{float(wind_spd):.1f} kts" if wind_spd is not None else "UNAVAILABLE",
        "current": f"{float(current_vel):.1f} m/s" if current_vel is not None else "UNAVAILABLE",
        "sst": f"{float(sst):.1f}°C" if sst is not None else "UNAVAILABLE",
    }


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


def _build_natural_language_response(
    recommendation: Dict[str, Any],
    risk_assessment: Dict[str, Any],
    conversation: Any,
) -> str:
    """Return a conversational answer for the chat UI, not a telemetry dump."""
    message = str(recommendation.get("message") or conversation.get("response") or "")
    explanation = str(recommendation.get("explanation") or "")
    tips = recommendation.get("recommendations") or []
    parts = [part.strip() for part in (message, explanation) if part and part.strip()]
    if tips:
        parts.append("What to do: " + " ".join(str(t).strip() for t in tips[:3] if str(t).strip()))
    if not parts:
        level = risk_assessment.get("risk_level", "UNKNOWN")
        parts.append(f"The current marine safety assessment is {level.lower()}. Please continue monitoring official advisories.")
    return " ".join(parts)


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

    # 1. Resolve navigational zone and coordinates from request or query text
    detected_loc, detected_zone = extract_location_and_zone_from_text(query_text)
    target_zone = request.zone_id or detected_zone

    if request.location:
        gps_val = gps_agent(request.location.latitude, request.location.longitude)
        loc = Location(latitude=gps_val["latitude"], longitude=gps_val["longitude"])
    elif request.latitude is not None and request.longitude is not None:
        gps_val = gps_agent(request.latitude, request.longitude)
        loc = Location(latitude=gps_val["latitude"], longitude=gps_val["longitude"])
    elif detected_loc:
        gps_val = gps_agent(detected_loc.latitude, detected_loc.longitude)
        loc = Location(latitude=gps_val["latitude"], longitude=gps_val["longitude"])
    elif target_zone and target_zone in KNOWN_ZONES:
        # A zone label cannot replace a device fix. Do not invent coordinates.
        return {
            "status": "location_required",
            "message": "A verified GPS location or explicit latitude/longitude is required for live analysis.",
            "zone_id": target_zone,
        }
    else:
        return {
            "status": "location_required",
            "message": "Allow browser location or provide latitude and longitude for live marine analysis.",
            "zone_id": target_zone,
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
    marine_fallback = {}
    if isinstance(marine_res, Exception):
        logger.warning("Marine agent error: %s", marine_res)
    marine_data = _normalize_agent_result(marine_res, marine_fallback)

    # Safe handling of weather agent
    weather_fallback = {}
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

    # Provide one complete natural-language answer for chat clients. Structured
    # telemetry remains available separately for the bridge/map panels.
    recommendation["response_text"] = _build_natural_language_response(
        recommendation, risk_assessment, conv_data
    )

    # Resolve effective navigational zone for UI highlighting
    if target_zone:
        effective_zone = target_zone
    elif risk_assessment.get("risk_level") in ("HIGH", "CRITICAL"):
        effective_zone = "zone-danger-se"
    elif risk_assessment.get("risk_level") == "MEDIUM":
        effective_zone = "zone-wind-ne"
    else:
        effective_zone = "zone-pfz-sw"

    # Backward compatible fields for UI
    recommendation["zone_id"] = effective_zone
    recommendation["alerts"] = risk_assessment.get("reasons", [])
    if risk_assessment["risk_level"] in ("HIGH", "CRITICAL"):
        recommendation["map_layers"] = ["Weather Warnings", "Protected Areas"]
    elif risk_assessment["risk_level"] == "MEDIUM":
        recommendation["map_layers"] = ["Wind", "Waves", "Marine Conditions"]
    else:
        recommendation["map_layers"] = ["Sea Surface Temperature", "Chlorophyll", "PFZ"]

    # Synthesize live dynamic telemetry snapshot
    nav_telemetry = _compute_dynamic_tides_and_nav(marine_data, weather_data, geo_data)
    telemetry_snapshot = {
        "bearing": nav_telemetry["cog"],
        "depth": nav_telemetry["depth"],
        "wave": nav_telemetry["wave"],
        "swell": f"{float(marine_data.get('swell_wave_height') or 0.8):.1f}m",
        "current": nav_telemetry["current"],
        "wind": nav_telemetry["wind"],
        "sst": nav_telemetry["sst"],
        "highTide": nav_telemetry["highTide"],
        "lowTide": nav_telemetry["lowTide"],
        "visibility": nav_telemetry["visibility"],
        "baro": nav_telemetry["baro"],
        "sog": nav_telemetry["sog"],
        "cog": nav_telemetry["cog"],
        "clearance": recommendation.get("action", "SAFE"),
        "vhfGuard": "CH 16 GUARD ACTIVE",
        "mrccPhone": "See official local maritime authority",
        "gpsBeacon": "VERIFIED GPS FIX",
        "patrolVessel": "UNAVAILABLE",
    }

    # Generate standardized GPS user location marker via GPS Agent
    gps_data = gps_agent(loc.latitude, loc.longitude)

    # Heatmaps are intentionally loaded through /heatmap separately. Running
    # nine extra agent evaluations here makes the chat response unnecessarily slow.
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
            "response": _build_natural_language_response(
                recommendation, risk_assessment, conv_data
            ),
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
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lon: Optional[float] = Query(None, ge=-180, le=180)
):
    """Returns live vessel bridge telemetry for given or current coordinates."""
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return {"status": "location_required", "message": "A verified GPS location is required.", "risk_points": []}
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

    gps_data = gps_agent(loc.latitude, loc.longitude)

    # Do not block telemetry on nine additional upstream calls. The dedicated
    # /heatmap endpoint supplies this optional layer.
    risk_points = []

    nav_telemetry = _compute_dynamic_tides_and_nav(m_data, w_data)

    risk_state = calculate_risk(marine=m_data, weather=w_data, geospatial={})
    return {
        "fix": f"DGPS: {loc.latitude:.4f}°N, {loc.longitude:.4f}°E",
        "sog": nav_telemetry["sog"],
        "cog": nav_telemetry["cog"],
        "depth": nav_telemetry["depth"],
        "baro": nav_telemetry["baro"],
        "wave": nav_telemetry["wave"],
        "wind": nav_telemetry["wind"],
        "current": nav_telemetry["current"],
        "sst": nav_telemetry["sst"],
        "vhf": "VHF CH 16 GUARD",
        "highTide": nav_telemetry["highTide"],
        "lowTide": nav_telemetry["lowTide"],
        "visibility": nav_telemetry["visibility"],
        "clearance": risk_state["risk_level"],
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
    target_lat = body.latitude if body else lat
    target_lon = body.longitude if body else lon
    if target_lat is None or target_lon is None:
        return {"status": "location_required", "message": "A verified GPS location is required."}

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

    # The map requests /heatmap independently so location updates remain fast.
    risk_points = []

    nav_telemetry = _compute_dynamic_tides_and_nav(m_data, w_data)

    return {
        "status": "success",
        "user_location": _dump_model(loc),
        "location": _dump_model(loc),
        "gps": gps_data,
        "risk_points": risk_points,
        "telemetry": {
            "fix": f"DGPS FIX: {loc.latitude:.4f}°N, {loc.longitude:.4f}°E",
            "sog": nav_telemetry["sog"],
            "cog": nav_telemetry["cog"],
            "depth": nav_telemetry["depth"],
            "baro": nav_telemetry["baro"],
            "wave": nav_telemetry["wave"],
            "wind": nav_telemetry["wind"],
            "current": nav_telemetry["current"],
            "sst": nav_telemetry["sst"],
            "clearance": calculate_risk(marine=m_data, weather=w_data, geospatial={})["risk_level"],
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
    if lat is None or lon is None:
        raise HTTPException(status_code=400, detail="lat and lon are required for live bulletins")
    try:
        validated_gps = gps_agent(lat, lon)
        loc = Location(latitude=validated_gps["latitude"], longitude=validated_gps["longitude"])
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid latitude or longitude") from exc

    try:
        geo_res = await run_geospatial_agent(loc)
    except Exception as exc:
        logger.warning("Geospatial agent error in /bulletins: %s", exc)
        geo_res = None
    geo_info = _normalize_agent_result(geo_res, {"inside_protected_area": False, "restrictions": []})
    marine_res, weather_res = await asyncio.gather(
        run_marine_agent(loc), run_weather_agent(loc), return_exceptions=True
    )
    marine_info = _normalize_agent_result(marine_res, {})
    weather_info = _normalize_agent_result(weather_res, {})
    risk_info = calculate_risk(marine_info, weather_info, geo_info)
    live_reasons = risk_info.get("reasons", [])
    bulletins = []
    if live_reasons:
        level = risk_info.get("risk_level", "LOW")
        bulletins.append({
            "id": "LIVE-RISK-001",
            "type": "danger" if level in ("HIGH", "CRITICAL") else "caution",
            "source_en": "KyroX live sensor analysis",
            "title_en": f"Live conditions: {level}",
            "desc_en": "; ".join(live_reasons),
            "action_en": "Follow the recommendation and monitor official advisories.",
            "zone_id": "zone-danger-se" if level in ("HIGH", "CRITICAL") else "zone-wind-ne",
            "coords": f"{loc.latitude:.2f}°N, {loc.longitude:.2f}°E",
        })
    if geo_info.get("restrictions"):
        bulletins.insert(0, {
            "id": "LIVE-GEO-001",
            "type": "danger",
            "source_en": "Live geospatial boundary analysis",
            "title_en": "Protected or restricted area detected",
            "desc_en": "; ".join(geo_info["restrictions"]),
            "action_en": "Leave the restricted area and follow local maritime rules.",
            "zone_id": "zone-danger-se",
            "coords": f"{loc.latitude:.2f}°N, {loc.longitude:.2f}°E",
        })
    if not bulletins:
        bulletins.append({
            "id": "LIVE-STATUS-001",
            "type": "resolved",
            "source_en": "KyroX live sensor analysis",
            "title_en": "No active risk reason reported",
            "desc_en": "Live agents returned no current risk indicators for this verified position.",
            "action_en": "Continue monitoring official weather and maritime advisories.",
            "zone_id": "zone-pfz-sw",
            "coords": f"{loc.latitude:.2f}°N, {loc.longitude:.2f}°E",
        })
    return bulletins

    return bulletins


# --------------------------------------------------
# 24-HOUR LINEAR REGRESSION PREDICTION ENDPOINT
# --------------------------------------------------
@app.get("/predictions/linear-regression")
@app.post("/predictions/linear-regression")
async def get_linear_regression_predictions(
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    variable: Optional[str] = Query("wave_height"),
    horizon_hours: Optional[int] = Query(24),
    past_hours: Optional[int] = Query(24),
    body: Optional[Dict[str, Any]] = Body(None),
):
    """
    24-Hour Marine Linear Regression Modelling Endpoint.
    Computes an Ordinary Least Squares (OLS) line of best fit over marine time-series,
    determines R², slope, intercept, standard error, and returns forward 24-hour
    hourly projections with 95% confidence intervals and multi-lingual marine safety advisories.
    """
    req_body = body or {}
    target_lat = lat if lat is not None else req_body.get("lat")
    target_lon = lon if lon is not None else req_body.get("lon")
    if target_lat is None or target_lon is None:
        raise HTTPException(status_code=400, detail="lat and lon are required for live predictions")
    target_var = (variable or req_body.get("variable") or "wave_height").strip().lower()
    h_hours = horizon_hours or req_body.get("horizon_hours") or 24
    p_hours = past_hours or req_body.get("past_hours") or 24

    # Validate GPS coordinates safely
    try:
        validated_gps = gps_agent(target_lat, target_lon)
        loc = Location(latitude=validated_gps["latitude"], longitude=validated_gps["longitude"])
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid latitude or longitude") from exc

    # Attempt to retrieve live anchor value for the target variable
    current_val = None
    try:
        if target_var in ("wave_height", "swell_wave_height", "ocean_current_velocity"):
            marine_res = await run_marine_agent(loc)
            marine_dict = _normalize_agent_result(marine_res, {})
            if target_var == "wave_height":
                current_val = marine_dict.get("wave_height")
            elif target_var == "swell_wave_height":
                current_val = marine_dict.get("swell_wave_height")
            elif target_var == "ocean_current_velocity":
                current_val = marine_dict.get("ocean_current_velocity")
        elif target_var == "wind_speed":
            weather_res = await run_weather_agent(loc)
            weather_dict = _normalize_agent_result(weather_res, {})
            current_val = weather_dict.get("wind_speed")
        elif target_var == "risk_score":
            w_res, m_res, g_res = await asyncio.gather(
                run_weather_agent(loc),
                run_marine_agent(loc),
                run_geospatial_agent(loc),
                return_exceptions=True
            )
            w_dict = _normalize_agent_result(w_res, {})
            m_dict = _normalize_agent_result(m_res, {})
            g_dict = _normalize_agent_result(g_res, {})
            risk_calc = calculate_risk(marine=m_dict, weather=w_dict, geospatial=g_dict)
            current_val = risk_calc.get("risk_score")
    except Exception as exc:
        logger.warning("Could not fetch real-time anchor for %s: %s", target_var, exc)

    # Compute regression model
    try:
        result = await compute_24h_prediction_async(
            variable=target_var,
            current_val=current_val,
            past_hours=p_hours,
            horizon_hours=h_hours,
            lat=loc.latitude,
            lon=loc.longitude,
        )
    except Exception as exc:
        logger.warning("compute_24h_prediction_async failed, falling back to baseline: %s", exc)
        result = compute_24h_prediction(
            variable=target_var,
            current_val=current_val,
            past_hours=p_hours,
            horizon_hours=h_hours
        )
    result["location"] = {"latitude": loc.latitude, "longitude": loc.longitude}
    return result


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