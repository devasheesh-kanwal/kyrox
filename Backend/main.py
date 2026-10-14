# Backend/main.py
"""
ORCA / KyroX - Marine Ecosystem Reasoning with Collaborative Agents.

Agents:  weather, marine, geospatial, official alerts (INCOIS + GDACS),
         conversational, consensus (cross-validation), recommendation,
         risk grid / route planner.
Sources: Open-Meteo (ECMWF + NOAA models, global), INCOIS high-wave & swell
         surge alerts (India), GDACS cyclones & tsunamis (global),
         OpenStreetMap protected areas.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from Models.schemas import Location, UserRequest
from Agents.gps_agent import gps_agent
from Agents.ecosystem_agent import ecosystem_agent
from Agents.orchestrator import (
    geocode_place,
    calculate_risk,
    orchestrate,
    resolve_location_from_text,
    run_agents,
)
from Agents.risk_agent import generate_risk_heatmap
from Services.http_cache import UpstreamError, close_client
from Services.prediction_service import PredictionUnavailable, compute_forecast
from Services.route_planner import VESSEL_LIMITS, RouteError, plan_route
from Services.translation_service import (
    LANGUAGE_CODE_TO_NAME,
    MAX_TRANSLATE_BATCH,
    is_supported_language,
    translate_batch,
    translate_text,
    translate_to_all_indian_languages,
)
from Tools.official_alerts import get_incois_alerts, get_official_alerts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

APP_VERSION = "3.0.0"
DATA_SOURCES = [
    {"name": "Open-Meteo Marine", "provides": "waves, swell, currents, SST, modelled sea level", "models": ["ECMWF WAM", "NOAA GFS-Wave"], "coverage": "global"},
    {"name": "Open-Meteo Weather", "provides": "wind, gusts, pressure, thunderstorms", "models": ["ECMWF IFS", "NOAA GFS"], "coverage": "global"},
    {"name": "INCOIS", "provides": "official High Wave & Swell Surge alerts", "coverage": "Indian coast"},
    {"name": "GDACS (UN / EC JRC)", "provides": "active tropical cyclones & tsunamis", "coverage": "global"},
    {"name": "OpenStreetMap / Overpass", "provides": "protected & restricted areas", "coverage": "global"},
    {"name": "OBIS (UNESCO-IOC)", "provides": "threatened species occurrence records", "coverage": "global"},
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Warm the INCOIS district geocoding cache so the first user is not slow.
    warm = asyncio.create_task(get_incois_alerts(15.0, 74.0))
    yield
    warm.cancel()
    await close_client()


app = FastAPI(
    title="ORCA Marine Multi-Agent System",
    description="Marine safety advisories from collaborating AI agents over fused ocean & weather data",
    version=APP_VERSION,
    lifespan=lifespan,
)

_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Simple per-IP sliding-window rate limit. Protects the free upstream APIs and
# the server when publicly deployed; tune with RATE_LIMIT_PER_MINUTE.
RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
_hits: Dict[str, deque] = defaultdict(deque)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if RATE_LIMIT > 0 and request.method != "OPTIONS":
        ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?")).split(",")[0].strip()
        now = time.time()
        q = _hits[ip]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            return JSONResponse({"detail": "Too many requests - please slow down."}, status_code=429)
        q.append(now)
    return await call_next(request)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _dump_model(m: Any) -> Dict[str, Any]:
    if m is None:
        return {}
    if hasattr(m, "model_dump"):
        return m.model_dump()
    return m if isinstance(m, dict) else {}


def format_coords(lat: float, lon: float) -> str:
    return f"{abs(lat):.2f}°{'N' if lat >= 0 else 'S'}, {abs(lon):.2f}°{'E' if lon >= 0 else 'W'}"


def _fmt(value, unit: str, digits: int = 1) -> str:
    return f"{float(value):.{digits}f}{unit}" if isinstance(value, (int, float)) else "UNAVAILABLE"


def _cardinal(deg: Optional[float]) -> str:
    if deg is None:
        return ""
    return ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][int(((deg % 360) + 22.5) // 45) % 8]


def _visibility_text(vis_m: Optional[float]) -> str:
    if vis_m is None:
        return "UNAVAILABLE"
    nm = vis_m / 1852
    quality = "GOOD" if nm >= 5 else "MODERATE" if nm >= 2 else "POOR"
    return f"{quality} ({nm:.0f} NM)"


def _tide_text(event: Optional[dict]) -> str:
    if not event:
        return "UNAVAILABLE"
    return f"{event['time'][11:16]} UTC ({event['level_m']:+.2f} m, model)"


def build_telemetry(marine: dict, weather: dict, risk: dict, loc: Location) -> Dict[str, Any]:
    """Bridge-panel telemetry. Only measured/modelled values; never synthesised."""
    tide = marine.get("tide") or {}
    cur_dir = marine.get("ocean_current_direction")
    wind_dir = weather.get("wind_direction")
    return {
        "fix": f"GPS: {format_coords(loc.latitude, loc.longitude)}",
        "sog": "UNAVAILABLE",
        "cog": "UNAVAILABLE",
        "depth": "UNAVAILABLE",
        "current_direction": f"{cur_dir:.0f}° {_cardinal(cur_dir)}" if cur_dir is not None else "UNAVAILABLE",
        "bearing": f"{cur_dir:.0f}° {_cardinal(cur_dir)}" if cur_dir is not None else "UNAVAILABLE",
        "baro": _fmt(weather.get("pressure_msl") or weather.get("surface_pressure"), " hPa"),
        "pressure_tendency_3h": weather.get("pressure_tendency_3h"),
        "wave": _fmt(marine.get("wave_height"), " m"),
        "wave_height": marine.get("wave_height"),
        "wave_period": marine.get("wave_period"),
        "wave_direction": marine.get("wave_direction"),
        "swell": _fmt(marine.get("swell_wave_height"), " m"),
        "swell_height": marine.get("swell_wave_height"),
        "swell_period": marine.get("swell_wave_period"),
        "swell_direction": marine.get("swell_wave_direction"),
        "wind": (_fmt(weather.get("wind_speed"), " kt", 0) + (f" {_cardinal(wind_dir)}" if wind_dir is not None else "")) if weather.get("wind_speed") is not None else "UNAVAILABLE",
        "wind_speed": weather.get("wind_speed"),
        "wind_gusts": weather.get("wind_gusts"),
        "current": _fmt(marine.get("ocean_current_velocity"), " kt"),
        "sst": _fmt(marine.get("sea_surface_temperature"), " °C"),
        "highTide": _tide_text(tide.get("next_high")),
        "lowTide": _tide_text(tide.get("next_low")),
        "tide_source": tide.get("source"),
        "visibility": _visibility_text(weather.get("visibility_m")),
        "sea_surface_height_anomaly": "N/A",
        "sea_surface_height_unit": "",
        "vhf": "VHF CH 16",
        "clearance": risk.get("risk_level"),
        "risk_level": risk.get("risk_level"),
        "risk_score": risk.get("risk_score"),
        "confidence": risk.get("confidence"),
        "outlook": risk.get("outlook"),
        "observed_at": marine.get("observed_at") or weather.get("observed_at"),
        "sources": [s for s in (marine.get("source"), weather.get("source")) if s],
        "stale": bool(marine.get("stale") or weather.get("stale")),
    }


def _build_natural_language_response(recommendation: Dict[str, Any], risk: Dict[str, Any]) -> str:
    parts = [p.strip() for p in (str(recommendation.get("message") or ""), str(recommendation.get("explanation") or "")) if p.strip()]
    tips = [str(t).strip() for t in (recommendation.get("recommendations") or [])[:3] if str(t).strip()]
    if tips:
        parts.append("What to do: " + " ".join(tips))
    if not parts:
        parts.append(f"The current marine safety assessment is {risk.get('risk_level', 'unknown').lower()}.")
    return " ".join(parts)


async def _noop() -> None:
    return None


async def _localized_text(text: str, language: str) -> str:
    if not text or not language or language == "en":
        return text
    result = await translate_text(text, language, "en")
    return result.get("translated_text") if result.get("success") and result.get("translated_text") else text


def _alerts_from_risk(risk: Dict[str, Any], action: str, zone: str, loc: Location) -> List[Dict[str, Any]]:
    level = risk.get("risk_level", "LOW")
    kind = "danger" if level in ("HIGH", "CRITICAL") else ("caution" if level == "MEDIUM" else "resolved")
    return [{
        "id": f"ALERT-{i + 1:03d}",
        "type": kind,
        "risk_level": level,
        "title": f"Advisory ({level})",
        "description": reason,
        "action": action,
        "zone_id": zone,
        "coords": format_coords(loc.latitude, loc.longitude),
    } for i, reason in enumerate(risk.get("reasons", []))]


def _zone_for(level: str, requested: Optional[str]) -> str:
    if requested:
        return requested
    if level in ("HIGH", "CRITICAL"):
        return "zone-danger-se"
    if level == "MEDIUM":
        return "zone-wind-ne"
    return "zone-pfz-sw"


def _location_or_none(lat, lon) -> Optional[Location]:
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return None
    try:
        gps = gps_agent(lat, lon)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Location(latitude=gps["latitude"], longitude=gps["longitude"])


# --------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------
@app.get("/")
@app.get("/health")
async def health_check():
    return {
        "status": "online",
        "system": "ORCA Marine Multi-Agent AI",
        "version": APP_VERSION,
        "agents": [
            "weather_agent", "marine_agent", "geospatial_agent", "official_alerts_agent",
            "conversational_agent", "ecosystem_agent", "consensus_agent", "recommendation_agent", "risk_grid_agent", "route_planner",
        ],
        "data_sources": DATA_SOURCES,
        "llm_configured": bool(os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_KEY")),
    }


# --------------------------------------------------------------------------
# Main query: full agent pipeline
# --------------------------------------------------------------------------
@app.post("/query")
async def process_query(request: UserRequest):
    query_text = (request.message or "").strip() or "What is the current safety status?"
    language = (request.language or "en").lower()
    if language != "en" and not is_supported_language(language):
        logger.warning("Unsupported response language requested: %s", language)
        language = "en"

    place_name = None
    if request.location:
        loc = _location_or_none(request.location.latitude, request.location.longitude)
    elif request.latitude is not None and request.longitude is not None:
        loc = _location_or_none(request.latitude, request.longitude)
    else:
        loc = None
    # A place named in the question ("near Durban") overrides the device position.
    named_loc, named_place = await resolve_location_from_text(query_text)
    if named_loc is not None:
        loc, place_name = named_loc, named_place

    if loc is None:
        return {
            "status": "location_required",
            "message": await _localized_text(
                "Allow location access, or name a port / give latitude and longitude, for live marine analysis.", language),
            "language": language,
            "zone_id": request.zone_id,
        }

    result = await orchestrate(query_text, location=loc, zone_id=request.zone_id, place_name=place_name)
    risk = result["risk_assessment"]
    recommendation = result["recommendation"]
    marine, weather, geo = result["marine_data"], result["weather_data"], result["geospatial_data"]

    response_text = _build_natural_language_response(recommendation, risk)
    if place_name:
        response_text = f"[{place_name}] " + response_text
    recommendation["response_text"] = response_text

    wants_bundle = language != "en"
    language_result, all_languages = await asyncio.gather(
        translate_text(response_text, language, "en"),
        translate_to_all_indian_languages(response_text, "en") if wants_bundle else _noop(),
    )
    localized = language_result.get("translated_text") or response_text
    translation_success = bool(language_result.get("success"))
    if wants_bundle and isinstance(all_languages, dict) and all_languages.get("translations"):
        translations = all_languages["translations"]
        entry = translations.get(LANGUAGE_CODE_TO_NAME.get(language, ""))
        if entry is not None and translation_success:
            entry["text"], entry["success"] = localized, True
        recommendation["translations"] = translations

    zone = _zone_for(risk["risk_level"], request.zone_id)
    recommendation["zone_id"] = zone
    recommendation["alerts"] = risk.get("reasons", [])
    recommendation["map_layers"] = (["Weather Warnings", "Protected Areas"] if risk["risk_level"] in ("HIGH", "CRITICAL")
                                    else ["Wind", "Waves", "Marine Conditions"] if risk["risk_level"] == "MEDIUM"
                                    else ["Sea Surface Temperature"])
    telemetry = build_telemetry(marine, weather, risk, loc)
    telemetry["clearance"] = recommendation.get("action", risk["risk_level"])

    return {
        "status": "success",
        "location": _dump_model(loc),
        "place_name": place_name,
        "chat": {
            "user_message": query_text,
            "intent": result["intent"],
            "response": localized,
            "language": language,
            "translation_success": translation_success,
            "translations": recommendation.get("translations", {}),
        },
        "weather": weather,
        "marine": marine,
        "geospatial": geo,
        "risk": {
            "risk_score": risk["risk_score"],
            "risk_level": risk["risk_level"],
            "reasons": risk["reasons"],
            "confidence": risk.get("confidence"),
            "data_gaps": risk.get("data_gaps", []),
            "outlook": risk.get("outlook", {}),
        },
        "consensus": result["consensus"],
        "official_alerts": result["official_alerts"],
        "ecosystem": result["ecosystem"],
        "agent_trace": result["agent_trace"],
        "recommendation": recommendation,
        "heatmap": {"user_location": _dump_model(loc), "risk_points": []},
        "alerts": _alerts_from_risk(risk, recommendation.get("action", ""), zone, loc),
        # Backward-compatible aliases used by existing UI bindings
        "user_query": query_text,
        "intent": result["intent"],
        "conversation": result["conversation"],
        "gps": result["gps"],
        "risk_points": [],
        "zone_id": zone,
        "marine_data": marine,
        "weather_data": weather,
        "geospatial_data": geo,
        "risk_assessment": risk,
        "telemetry": telemetry,
    }


@app.get("/query")
async def process_query_get(
    message: Optional[str] = Query("What is the current safety status?"),
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lon: Optional[float] = Query(None, ge=-180, le=180),
    zone_id: Optional[str] = Query(None),
    language: str = Query("en"),
):
    return await process_query(UserRequest(message=message or "", latitude=lat, longitude=lon,
                                           zone_id=zone_id, language=language))


# --------------------------------------------------------------------------
# Telemetry / location
# --------------------------------------------------------------------------
async def _live_snapshot(loc: Location) -> Dict[str, Any]:
    agents = await run_agents(loc)
    risk = calculate_risk(agents["marine"], agents["weather"], agents["geospatial"], consensus=agents["consensus"])
    return {"agents": agents, "risk": risk, "telemetry": build_telemetry(agents["marine"], agents["weather"], risk, loc)}


@app.get("/telemetry")
@app.post("/telemetry")
async def get_live_telemetry(lat: Optional[float] = Query(None, ge=-90, le=90),
                             lon: Optional[float] = Query(None, ge=-180, le=180)):
    loc = _location_or_none(lat, lon)
    if loc is None:
        return {"status": "location_required", "message": "A verified GPS location is required.", "risk_points": []}
    snap = await _live_snapshot(loc)
    agents, risk = snap["agents"], snap["risk"]
    return {
        **snap["telemetry"],
        "location": _dump_model(loc),
        "gps": gps_agent(loc.latitude, loc.longitude),
        "risk_points": [],
        "reasons": risk["reasons"],
        "consensus": agents["consensus"],
        "official_alerts": agents["official"]["alerts"],
        "official_feeds": agents["official"].get("feeds", {}),
        "ecosystem": {k: v for k, v in agents["ecosystem"].items() if k != "species"},
        "agent_trace": agents["trace"],
        "marine_available": bool(agents["marine"].get("data_available")),
        "weather_available": bool(agents["weather"].get("data_available")),
    }


class LocationUpdateRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


@app.post("/location")
@app.get("/location")
async def update_user_location(body: Optional[LocationUpdateRequest] = Body(None),
                               lat: Optional[float] = Query(None), lon: Optional[float] = Query(None)):
    loc = _location_or_none(body.latitude if body else lat, body.longitude if body else lon)
    if loc is None:
        return {"status": "location_required", "message": "A verified GPS location is required."}
    snap = await _live_snapshot(loc)
    return {
        "status": "success",
        "user_location": _dump_model(loc),
        "location": _dump_model(loc),
        "gps": gps_agent(loc.latitude, loc.longitude),
        "risk_points": [],
        "telemetry": snap["telemetry"],
    }


# --------------------------------------------------------------------------
# Heatmap
# --------------------------------------------------------------------------
class HeatmapRequest(BaseModel):
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    step: Optional[float] = Field(0.035, ge=0.005, le=0.5)


@app.post("/heatmap")
@app.get("/heatmap")
@app.post("/api/v1/risk-analysis")
@app.get("/api/v1/risk-analysis")
async def get_risk_heatmap(body: Optional[HeatmapRequest] = Body(None), lat: Optional[float] = Query(None),
                           lon: Optional[float] = Query(None), step: Optional[float] = Query(0.035)):
    t_lat = body.latitude if body and body.latitude is not None else lat
    t_lon = body.longitude if body and body.longitude is not None else lon
    t_step = body.step if body and body.step is not None else (step or 0.035)
    if t_lat is None or t_lon is None:
        return {"error": "latitude and longitude are required", "user_location": None, "risk_points": []}
    try:
        data = await generate_risk_heatmap(t_lat, t_lon, step=t_step)
    except Exception as exc:
        logger.error("Heatmap generation failed: %s", exc)
        return {"user_location": {"latitude": t_lat, "longitude": t_lon}, "risk_points": [],
                "error": "Unable to compute risk heatmap right now", "has_data": False}
    data["has_data"] = bool(data.get("risk_points"))
    if not data["has_data"]:
        data["message"] = "No marine model coverage around this location (on land?)"
    return data


# --------------------------------------------------------------------------
# Safe route planner
# --------------------------------------------------------------------------
class RouteRequest(BaseModel):
    start_latitude: float = Field(..., ge=-90, le=90)
    start_longitude: float = Field(..., ge=-180, le=180)
    end_latitude: float = Field(..., ge=-90, le=90)
    end_longitude: float = Field(..., ge=-180, le=180)
    vessel: str = Field("small", description="small | medium | large")


@app.post("/route")
async def safe_route(body: RouteRequest):
    try:
        return await plan_route(body.start_latitude, body.start_longitude,
                                body.end_latitude, body.end_longitude, vessel=body.vessel)
    except RouteError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except UpstreamError as exc:
        raise HTTPException(status_code=503, detail="Forecast provider is busy or unreachable - try again in a minute.") from exc


@app.get("/route/vessels")
async def route_vessels():
    return VESSEL_LIMITS


@app.get("/ecosystem")
async def ecosystem(lat: float = Query(..., ge=-90, le=90), lon: float = Query(..., ge=-180, le=180)):
    return await ecosystem_agent(lat, lon)


@app.get("/geocode")
async def geocode(q: str = Query(..., min_length=2, max_length=80)):
    place = await geocode_place(q)
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")
    return place


# --------------------------------------------------------------------------
# Official alerts & bulletins
# --------------------------------------------------------------------------
@app.get("/alerts/official")
async def official_alerts(lat: float = Query(..., ge=-90, le=90), lon: float = Query(..., ge=-180, le=180)):
    return await get_official_alerts(lat, lon)


@app.get("/bulletins")
@app.post("/bulletins")
async def get_bulletins(lat: Optional[float] = Query(None), lon: Optional[float] = Query(None)):
    """Bulletins = official warnings near the position + the live agent assessment."""
    if lat is None or lon is None:
        raise HTTPException(status_code=400, detail="lat and lon are required for live bulletins")
    loc = _location_or_none(lat, lon)
    snap = await _live_snapshot(loc)
    agents, risk = snap["agents"], snap["risk"]
    coords = format_coords(loc.latitude, loc.longitude)
    bulletins = []

    for i, alert in enumerate(agents["official"]["alerts"][:6]):
        level = alert.get("level", "")
        where = alert.get("district") or f"{alert['distance_km']:.0f} km away"
        bulletins.append({
            "id": f"OFFICIAL-{alert['source']}-{i + 1}",
            "type": "danger" if alert.get("severity", 0) >= 2 else "caution",
            "source_en": f"{alert['source']} (official)",
            "title_en": f"{alert.get('alert') or alert['kind']} - {where}",
            "desc_en": alert.get("message") or "",
            "action_en": "Follow the official advisory and local authority instructions.",
            "zone_id": "zone-danger-se" if alert.get("severity", 0) >= 2 else "zone-wind-ne",
            "coords": coords,
            "official": True,
            "issued": alert.get("issued"),
            "level": level,
            "url": alert.get("url"),
        })

    if agents["geospatial"].get("restrictions"):
        bulletins.append({
            "id": "LIVE-GEO-001", "type": "danger", "source_en": "Geospatial agent (OpenStreetMap)",
            "title_en": "Protected or restricted area nearby",
            "desc_en": "; ".join(agents["geospatial"]["restrictions"]),
            "action_en": "Check local rules before fishing here.",
            "zone_id": "zone-danger-se", "coords": coords,
        })

    live_reasons = [r for r in risk["reasons"] if not r.startswith("OFFICIAL")]
    level = risk["risk_level"]
    bulletins.append({
        "id": "LIVE-RISK-001",
        "type": "danger" if level in ("HIGH", "CRITICAL") else ("caution" if level == "MEDIUM" else "resolved"),
        "source_en": f"ORCA agents ({risk.get('confidence', 'medium')} confidence)",
        "title_en": f"Live assessment: {level}",
        "desc_en": "; ".join(live_reasons) if live_reasons else "No hazards in current conditions or the 12 h forecast.",
        "action_en": {"LOW": "Normal precautions; re-check before departure.",
                      "MEDIUM": "Stay near the coast and plan an early return.",
                      "HIGH": "Return to shore / do not depart.",
                      "CRITICAL": "Do not go to sea."}.get(level, "Monitor official advisories."),
        "zone_id": _zone_for(level, None),
        "coords": coords,
    })
    for name, meta in agents["official"].get("feeds", {}).items():
        if meta.get("available") is False:
            bulletins.append({
                "id": f"FEED-{name}", "type": "caution", "source_en": "ORCA system",
                "title_en": f"{name} official feed unavailable",
                "desc_en": f"Could not reach {name}. Check official channels directly.",
                "action_en": "Do not assume there are no official warnings.",
                "zone_id": "zone-wind-ne", "coords": coords,
            })
    return bulletins


# --------------------------------------------------------------------------
# Forecast (kept at the legacy linear-regression path for the UI)
# --------------------------------------------------------------------------
@app.get("/predictions/forecast")
@app.get("/predictions/linear-regression")
@app.post("/predictions/linear-regression")
async def get_forecast(lat: Optional[float] = Query(None), lon: Optional[float] = Query(None),
                       variable: Optional[str] = Query("wave_height"), horizon_hours: Optional[int] = Query(24),
                       past_hours: Optional[int] = Query(24), body: Optional[Dict[str, Any]] = Body(None)):
    req = body or {}
    t_lat = lat if lat is not None else req.get("lat")
    t_lon = lon if lon is not None else req.get("lon")
    if t_lat is None or t_lon is None:
        raise HTTPException(status_code=400, detail="lat and lon are required for live predictions")
    loc = _location_or_none(float(t_lat), float(t_lon))
    try:
        result = await compute_forecast((variable or req.get("variable") or "wave_height").strip().lower(),
                                        loc.latitude, loc.longitude,
                                        horizon_hours=horizon_hours or req.get("horizon_hours") or 24,
                                        past_hours=past_hours or req.get("past_hours") or 24)
    except PredictionUnavailable as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=404)
    except Exception as exc:
        logger.warning("Forecast failed: %s", exc)
        return JSONResponse({"success": False, "error": "Forecast service temporarily unavailable"}, status_code=503)
    result["location"] = {"latitude": loc.latitude, "longitude": loc.longitude}
    return result


# --------------------------------------------------------------------------
# Translation
# --------------------------------------------------------------------------
class TranslationRequest(BaseModel):
    text: str = Field(..., max_length=5000)
    target_lang: str = Field("hi")
    source_lang: str = Field("en")


@app.post("/translate")
@app.get("/translate")
async def translate_endpoint(body: Optional[TranslationRequest] = Body(None), text: Optional[str] = Query(None),
                             target_lang: Optional[str] = Query("hi"), source_lang: Optional[str] = Query("en")):
    target_text = body.text if body else text
    if not target_text:
        raise HTTPException(status_code=400, detail="text is required")
    return await translate_text(target_text, body.target_lang if body else target_lang,
                                body.source_lang if body else source_lang)


class BatchTranslationRequest(BaseModel):
    texts: List[str]
    target_lang: str = Field("hi")
    source_lang: str = Field("en")


@app.post("/translate/batch")
async def translate_batch_endpoint(body: BatchTranslationRequest):
    if not body.texts:
        return {"translations": [], "count": 0}
    if len(body.texts) > MAX_TRANSLATE_BATCH:
        raise HTTPException(status_code=400, detail=f"At most {MAX_TRANSLATE_BATCH} texts can be translated per request")
    results = await translate_batch(body.texts, body.target_lang, body.source_lang)
    return {"source_language": (body.source_lang or "en").lower(), "target_language": (body.target_lang or "hi").lower(),
            "translations": results, "count": len(results)}


class MultiLanguageTranslationRequest(BaseModel):
    text: str = Field(..., max_length=5000)
    source_lang: str = Field("en")


@app.post("/translate/all")
@app.get("/translate/all")
async def translate_all_endpoint(body: Optional[MultiLanguageTranslationRequest] = Body(None),
                                 text: Optional[str] = Query(None), source_lang: Optional[str] = Query("en")):
    target_text = body.text if body else text
    if not target_text:
        raise HTTPException(status_code=400, detail="text is required")
    return await translate_to_all_indian_languages(target_text, body.source_lang if body else source_lang)


@app.get("/translate/languages")
async def get_supported_languages():
    from Services.translation_service import INDIAN_LANGUAGES
    return {"languages": INDIAN_LANGUAGES}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
