# backend/agents/orchestrator.py
"""
Multi-agent orchestrator.

    conversational_agent ─┐
    weather_agent ────────┤
    marine_agent ─────────┼─► consensus_agent ─► calculate_risk ─► recommendation_agent
    geospatial_agent ─────┤      (cross-checks)     (scoring)         (advice + LLM)
    official_alerts ──────┘

Every stage is recorded in `agent_trace` so the UI can show which agent
contributed what, how long it took, and whether it succeeded.
"""
import asyncio
import logging
import re
import time
from typing import Optional, Tuple, Union

from Agents.consensus_agent import build_consensus
from Agents.conversational_agent import conversational_agent
from Agents.ecosystem_agent import ecosystem_agent, ecosystem_summary
from Agents.geospatial_agent import geospatial_agent
from Agents.gps_agent import gps_agent
from Agents.marine_agent import marine_agent
from Agents.recommendation_agent import recommendation_agent
from Agents.weather_agent import weather_agent
from Models.schemas import Location
from Services.http_cache import UpstreamError, cached_get_json
from Tools.official_alerts import get_official_alerts

logger = logging.getLogger(__name__)

INTENT_NEXT_ACTION = {
    "CHECK_SAFETY": "weather_marine_geospatial_risk",
    "WEATHER_QUERY": "weather_agent",
    "MARINE_QUERY": "marine_agent",
    "BOUNDARY_WARNING": "geospatial_agent",
    "EMERGENCY": "emergency_alert_service",
    "GENERAL_QUERY": "conversational_response",
}

# Zone IDs are presentation labels used by the map UI only; they carry no
# coordinates. Analysis always uses a real position.
KNOWN_ZONES = {
    "zone-danger-se": {"name": "Hazard sector (live weather)"},
    "zone-wind-ne": {"name": "Caution sector (live weather)"},
    "zone-pfz-sw": {"name": "Recommended fishing sector (live SST)"},
}

# Fast path for common Indian ports (offline, no geocoding round trip).
# Anything else is resolved globally via geocoding in `resolve_location_from_text`.
_PORTS = [
    (("goa", "panaji", "mormugao"), 15.42, 73.78),
    (("mumbai", "bombay"), 18.92, 72.83),
    (("kochi", "cochin"), 9.97, 76.24),
    (("chennai", "madras"), 13.08, 80.28),
    (("visakhapatnam", "vizag"), 17.68, 83.22),
    (("mangalore", "mangaluru"), 12.87, 74.84),
    (("porbandar",), 21.64, 69.61),
    (("kanyakumari",), 8.08, 77.55),
    (("kolkata", "calcutta"), 22.55, 88.31),
    (("netrani",), 14.01, 74.32),
    (("malvan",), 16.06, 73.47),
    (("karwar",), 14.81, 74.13),
    (("ratnagiri",), 16.99, 73.30),
    (("betul",), 15.14, 73.95),
]

# Lookahead so matches can overlap ("safe to fish near Durban" must yield "Durban").
_PREPOSITIONS = ("near", "at", "in", "off", "around", "from", "to", "outside")
_PLACE_PATTERN = re.compile(
    r"\b(?:" + "|".join(_PREPOSITIONS) + r")\s+(?=([A-Za-z][A-Za-z .'-]{2,40}?)"
    r"(?:[?.!,]|\s+(?:today|tomorrow|now|tonight|coast|harbou?r|port|beach|sea|this|right)\b|$))",
    re.IGNORECASE,
)
_PLACE_STOPWORDS = {"the sea", "sea", "the morning", "the evening", "night", "risk", "danger", "safe"}


def extract_location_and_zone_from_text(text: str) -> Tuple[Optional[Location], Optional[str]]:
    """Synchronous detection of explicit coordinates or known port names."""
    low = (text or "").lower()
    coord_match = re.search(r"(-?\d{1,2}\.\d+)\s*°?\s*([ns])?[,\s]+(-?\d{1,3}\.\d+)\s*°?\s*([ew])?", low)
    if coord_match:
        try:
            lat = float(coord_match.group(1)) * (-1 if coord_match.group(2) == "s" else 1)
            lon = float(coord_match.group(3)) * (-1 if coord_match.group(4) == "w" else 1)
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return Location(latitude=lat, longitude=lon), None
        except ValueError:
            pass
    for names, lat, lon in _PORTS:
        if any(re.search(rf"\b{re.escape(n)}\b", low) for n in names):
            return Location(latitude=lat, longitude=lon), None
    return None, None


async def geocode_place(name: str) -> Optional[dict]:
    """Global place lookup via Open-Meteo geocoding (cached for a week)."""
    name = (name or "").strip()
    if len(name) < 3:
        return None
    try:
        resp = await cached_get_json(
            "https://geocoding-api.open-meteo.com/v1/search",
            {"name": name, "count": 1, "language": "en"},
            ttl=7 * 24 * 3600,
        )
    except UpstreamError:
        return None
    results = (resp.data or {}).get("results") or []
    if not results:
        return None
    r = results[0]
    label = ", ".join(x for x in (r.get("name"), r.get("admin1"), r.get("country")) if x)
    return {"latitude": float(r["latitude"]), "longitude": float(r["longitude"]), "name": label}


async def resolve_location_from_text(text: str) -> Tuple[Optional[Location], Optional[str]]:
    """Coordinates / known port first, then a geocoded place name ("near Durban")."""
    loc, _ = extract_location_and_zone_from_text(text)
    if loc:
        return loc, None
    candidates = [m.group(1).strip(" .'-") for m in _PLACE_PATTERN.finditer(text or "")]
    for candidate in reversed(candidates):  # the last place mentioned wins
        words = candidate.lower().split()
        if candidate.lower() in _PLACE_STOPWORDS or any(w in _PREPOSITIONS for w in words):
            continue
        place = await geocode_place(candidate)
        if place:
            return Location(latitude=place["latitude"], longitude=place["longitude"]), place["name"]
    return None, None


# A metre figure only counts as a wave height when a wave word sits right next
# to it ("3 m waves", "waves are 4 meters", "swell 2.5 m", "3 मीटर लहरें").
# Boat lengths ("9 m boat"), depths, distances and m/s wind speeds are ignored.
_NUM = r'(\d+(?:\.\d+)?)'
_METRE = r'(?:m|mtr|mtrs|meter|meters|metre|metres|मीटर)(?![/\w])'
_WAVE_WORD = r'(?:waves?|swells?|breakers?|surf|sea\s+state|लहर(?:ें|ों)?)'
_NOT_WAVE_AFTER = (r'(?!\s*(?:long|length|boat|boats|vessel|craft|trawler|ship|canoe|dinghy|'
                   r'deep|depth|offshore|away|from|off|nm|nautical|km|kilomet))')
_WAVE_AFTER_NUMBER = re.compile(
    _NUM + r'\s*' + _METRE + r'\s+(?:(?:high|tall|big|rough|heavy|ki|की|के)\s+)?' + _WAVE_WORD)
_WAVE_BEFORE_NUMBER = re.compile(
    _WAVE_WORD + r'(?:\s+(?!boat|vessel|craft|trawler|ship)[^\s\d]+){0,3}?\s+' + _NUM + r'\s*' + _METRE + _NOT_WAVE_AFTER)


def _extract_wave_height(low: str) -> Optional[float]:
    """Wave height in metres the user described, or None. Expects lowercase text."""
    for pattern in (_WAVE_AFTER_NUMBER, _WAVE_BEFORE_NUMBER):
        for match in pattern.finditer(low):
            value = float(match.group(1))
            # Nothing above 20 m is a plausible wave description.
            if 0 < value <= 20.0:
                return value
    return None


def extract_user_conditions(text: str) -> dict:
    """Extract hypothetical or user-reported conditions (wind, waves, lightning, storms)."""
    conds = {}
    low = (text or "").lower()

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

    wave_height = _extract_wave_height(low)
    if wave_height is not None:
        conds["wave_height"] = wave_height

    if any(k in low for k in ["lightning", "तड़ित", "बिजली", "thunder"]):
        conds["lightning_risk"] = "HIGH"
    if any(k in low for k in ["squall", "cyclone", "storm", "toofan", "तूफान", "झंझावात", "red alert"]):
        conds["storm_risk"] = "HIGH"
    return conds


# ---------------------------------------------------------------------------
# Deterministic risk scoring
# ---------------------------------------------------------------------------
def _wave_tier(h: Optional[float]) -> int:
    if h is None:
        return 0
    return 3 if h >= 3.5 else 2 if h >= 2.5 else 1 if h >= 1.8 else 0


def _wind_tier(w: Optional[float]) -> int:
    if w is None:
        return 0
    return 3 if w >= 35 else 2 if w >= 25 else 1 if w >= 18 else 0


_WAVE_POINTS = {0: 0, 1: 20, 2: 35, 3: 50}
_WIND_POINTS = {0: 0, 1: 15, 2: 30, 3: 45}
_OFFICIAL_POINTS = {0: 5, 1: 15, 2: 40, 3: 60}


def _as_dict(obj) -> dict:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj if isinstance(obj, dict) else {}


def calculate_risk(
    marine: dict,
    weather: dict,
    geospatial: dict,
    intent: Optional[str] = None,
    user_message: Optional[str] = None,
    zone_id: Optional[str] = None,
    consensus: Optional[dict] = None,
) -> dict:
    """
    Deterministic, explainable marine risk score (0-100).

    Uses the consensus agent's conservative `effective` values, the 12 h
    outlook, pressure trend, official alerts and protected areas. Missing data
    is never scored as calm: if wind and waves are both unknown the level is
    at least MEDIUM and confidence is "low".
    """
    marine, weather, geospatial = _as_dict(marine), _as_dict(weather), _as_dict(geospatial)
    low_msg = (user_message or "").lower()

    is_emergency = intent == "EMERGENCY" or any(k in low_msg for k in [
        "mayday", "sinking", "man overboard", "engine failure", "sos", "distress",
        "boat sinking", "fire on board", "डूब", "आपातकाल", "जान जोखिम", "नाव डूब",
    ])
    if is_emergency:
        return {
            "risk_score": 100,
            "risk_level": "CRITICAL",
            "reasons": [
                "EMERGENCY DISTRESS DETECTED: Immediate threat to vessel/crew life",
                "Transmit MAYDAY on VHF Channel 16 / DSC distress and activate your EPIRB if fitted",
                "Contact the nearest Maritime Rescue Coordination Centre (India Coast Guard: 1554)",
            ],
            "confidence": "high",
            "data_gaps": [],
            "findings": [],
            "outlook": {},
        }

    consensus = consensus or build_consensus(marine, weather)
    eff = consensus.get("effective") or {}
    user_conds = extract_user_conditions(user_message or "")
    score = 0
    reasons: list[str] = []

    # --- Current sea state (conservative consensus values, or a what-if) ---
    # A condition the user describes is scored only when it is worse than the
    # measured value (conservative), and the reason says where it came from.
    wave_h = eff.get("wave_height")
    wave_note = ""
    if user_conds.get("wave_height") is not None and user_conds["wave_height"] > (wave_h or 0.0):
        wave_h = user_conds["wave_height"]
        wave_note = ", as you described"
    wave_t = _wave_tier(wave_h)
    score += _WAVE_POINTS[wave_t]
    if wave_t == 3:
        reasons.append(f"Severe waves ({wave_h:.1f} m{wave_note}) - dangerous for all small craft")
    elif wave_t == 2:
        reasons.append(f"Rough sea ({wave_h:.1f} m{wave_note}) - vessels under 20 m use extreme caution")
    elif wave_t == 1:
        reasons.append(f"Moderate waves ({wave_h:.1f} m{wave_note})")

    wind = eff.get("wind_speed")
    wind_note = ""
    if user_conds.get("wind_speed_kts") is not None and user_conds["wind_speed_kts"] > (wind or 0.0):
        wind = user_conds["wind_speed_kts"]
        wind_note = ", as you described"
    wind_t = _wind_tier(wind)
    score += _WIND_POINTS[wind_t]
    if wind_t == 3:
        reasons.append(f"Gale-force wind ({wind:.0f} kt{wind_note}) - extreme capsize hazard")
    elif wind_t == 2:
        reasons.append(f"Strong wind ({wind:.0f} kt{wind_note}) - open boats unsafe")
    elif wind_t == 1:
        reasons.append(f"Fresh wind ({wind:.0f} kt{wind_note})")

    gust = eff.get("wind_gusts")
    if gust is not None and gust >= 40:
        score += 25
        reasons.append(f"Dangerous gusts up to {gust:.0f} kt")
    elif gust is not None and gust >= 30 and wind_t < 2:
        score += 12
        reasons.append(f"Strong gusts up to {gust:.0f} kt")

    lightning = user_conds.get("lightning_risk") or weather.get("lightning_risk")
    storm = user_conds.get("storm_risk") or weather.get("storm_risk")
    if lightning == "HIGH":
        score += 40
        reasons.append("Thunderstorm / lightning reported at this position")
    if storm == "HIGH":
        score += 40
        reasons.append("Squall or storm conditions")
    elif storm == "MEDIUM":
        score += 8

    # --- 12 h outlook: only counts when worse than now ---
    wave_ahead_t = _wave_tier(eff.get("wave_height_max_12h"))
    wind_ahead_t = _wind_tier(eff.get("wind_speed_max_12h"))
    outlook_points = 0
    if wave_ahead_t > wave_t:
        outlook_points += (_WAVE_POINTS[wave_ahead_t] - _WAVE_POINTS[wave_t]) * 0.7
        reasons.append(f"Forecast: waves building to {eff['wave_height_max_12h']:.1f} m within 12 h")
    if wind_ahead_t > wind_t:
        outlook_points += (_WIND_POINTS[wind_ahead_t] - _WIND_POINTS[wind_t]) * 0.7
        reasons.append(f"Forecast: wind rising to {eff['wind_speed_max_12h']:.0f} kt within 12 h")
    if eff.get("storm_expected_12h") and lightning != "HIGH":
        outlook_points += 20
        reasons.append("Forecast: thunderstorms expected within 12 h")
    score += int(round(outlook_points))

    if eff.get("pressure_trend") == "severe":
        score += 25
        reasons.append("Barometric pressure falling rapidly - approaching weather system")
    elif eff.get("pressure_trend") == "falling":
        score += 10
        reasons.append("Barometric pressure falling - weather may deteriorate")

    # --- Official warnings (INCOIS / GDACS) ---
    official = consensus.get("official_alerts") or []
    if official:
        top = official[0]
        points = _OFFICIAL_POINTS.get(int(top.get("severity", 1)), 15)
        if any(a.get("kind") == "Tsunami" for a in official):
            points = max(points, 80)
        score += points
        for alert in official[:3]:
            where = f" - {alert['district']}" if alert.get("district") else ""
            reasons.append(f"OFFICIAL {alert['source']}: {alert.get('alert') or alert['kind']} ({alert['level']}){where}, {alert['distance_km']:.0f} km away")

    # --- Protected / restricted areas ---
    if geospatial.get("inside_protected_area") or geospatial.get("restricted_zone"):
        score += 50
        notes = geospatial.get("restrictions") or ["Vessel is inside a restricted or protected marine area"]
        reasons.extend(n for n in notes if n not in reasons)
    elif geospatial.get("near_boundary"):
        score += 25
        reasons.append("Vessel is close to a protected or restricted boundary")

    # --- Missing data must never read as "safe" ---
    gaps = consensus.get("data_gaps") or []
    if consensus.get("no_sea_coverage"):
        reasons.append("Position is on land or outside marine model coverage - no sea-state assessment possible")
        gaps = ["sea state (not at sea)"]
    elif len(gaps) == 2:
        score = max(score, 30)
        reasons.append("Live wind and wave data unavailable - safety cannot be confirmed; check official forecasts")
    elif gaps:
        score += 15
        reasons.append(f"Live {gaps[0]} unavailable - assessment is incomplete")

    score = min(int(round(score)), 100)
    if score >= 80:
        level = "CRITICAL"
    elif score >= 55:
        level = "HIGH"
    elif score >= 30:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "risk_score": score,
        "risk_level": level,
        "reasons": reasons,
        "confidence": consensus.get("confidence", "medium"),
        "data_gaps": gaps,
        "findings": consensus.get("findings", []),
        "outlook": {
            "wave_height_max_12h": eff.get("wave_height_max_12h"),
            "wind_speed_max_12h": eff.get("wind_speed_max_12h"),
            "wind_gusts_max_12h": eff.get("wind_gusts_max_12h"),
            "storm_expected_12h": eff.get("storm_expected_12h"),
            "pressure_trend": eff.get("pressure_trend"),
        },
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
async def _timed(name: str, coro, trace: list):
    start = time.perf_counter()
    try:
        result = await coro
        trace.append({"agent": name, "status": "ok", "ms": int((time.perf_counter() - start) * 1000)})
        return result
    except Exception as exc:
        trace.append({"agent": name, "status": "failed", "error": str(exc)[:160],
                      "ms": int((time.perf_counter() - start) * 1000)})
        logger.warning("%s failed: %s", name, exc)
        return exc


def _ok(result, fallback: dict) -> dict:
    if result is None or isinstance(result, Exception):
        return dict(fallback)
    return _as_dict(result) or dict(fallback)


async def run_agents(location: Location, include_conversation: Optional[str] = None,
                     include_official: bool = True) -> dict:
    """Run the domain agents concurrently and build the consensus."""
    trace: list[dict] = []
    tasks = [
        _timed("weather_agent", weather_agent(location), trace),
        _timed("marine_agent", marine_agent(location), trace),
        _timed("geospatial_agent", geospatial_agent(location), trace),
    ]
    if include_official:
        tasks.append(_timed("official_alerts_agent", get_official_alerts(location.latitude, location.longitude), trace))
    tasks.append(_timed("ecosystem_agent", ecosystem_agent(location.latitude, location.longitude), trace))
    if include_conversation is not None:
        tasks.append(_timed("conversational_agent", asyncio.to_thread(conversational_agent, include_conversation), trace))

    results = await asyncio.gather(*tasks)
    weather = _ok(results[0], {})
    marine = _ok(results[1], {})
    if isinstance(results[1], Exception) and "coverage" in str(results[1]):
        marine = {"data_available": False, "no_coverage": True}
    geo = _ok(results[2], {"inside_protected_area": False, "restricted_zone": False,
                           "near_boundary": False, "restrictions": []})
    official = _ok(results[3], {"alerts": [], "feeds": {}}) if include_official else {"alerts": [], "feeds": {}}
    ecosystem = _ok(results[4 if include_official else 3], {"available": False, "species": [], "total": 0})
    conversation = None
    if include_conversation is not None:
        conversation = _ok(results[-1], {"intent": "GENERAL_QUERY", "response": ""})

    start = time.perf_counter()
    consensus = build_consensus(marine, weather, official, geo)
    eco_note = ecosystem_summary(ecosystem)
    if eco_note:
        consensus["findings"].append({"agents": ["ecosystem_agent"], "type": "ecosystem", "message": eco_note, "impact": "info"})
    trace.append({"agent": "consensus_agent", "status": "ok", "ms": int((time.perf_counter() - start) * 1000),
                  "confidence": consensus["confidence"],
                  "conflicts": sum(1 for f in consensus["findings"] if f["type"] == "conflict")})
    return {
        "weather": weather,
        "marine": marine,
        "geospatial": geo,
        "official": official,
        "ecosystem": ecosystem,
        "conversation": conversation,
        "consensus": consensus,
        "trace": trace,
    }


async def orchestrate(
    user_message: str,
    location: Optional[Union[Location, dict]] = None,
    zone_id: Optional[str] = None,
    place_name: Optional[str] = None,
) -> dict:
    """Full pipeline: agents -> consensus -> risk -> recommendation."""
    if location is None:
        location, place_name = await resolve_location_from_text(user_message)
    if isinstance(location, dict):
        location = Location(**location)
    if location is None:
        conversation = conversational_agent(user_message)
        return {
            "status": "location_required",
            "user_message": user_message,
            "intent": conversation.get("intent") or "GENERAL_QUERY",
            "conversation": conversation,
        }

    gps_data = gps_agent(location.latitude, location.longitude)
    agents = await run_agents(location, include_conversation=user_message)
    conversation = agents["conversation"] or {"intent": "GENERAL_QUERY"}
    intent = conversation.get("intent") or "GENERAL_QUERY"

    risk = calculate_risk(
        agents["marine"], agents["weather"], agents["geospatial"],
        intent=intent, user_message=user_message, zone_id=zone_id,
        consensus=agents["consensus"],
    )

    start = time.perf_counter()
    recommendation = await recommendation_agent(
        risk_data=risk,
        weather_data=agents["weather"],
        marine_data=agents["marine"],
        geo_data=agents["geospatial"],
    )
    eco_tips = (agents["ecosystem"] or {}).get("bycatch_tips") or []
    if eco_tips and risk["risk_level"] in ("LOW", "MEDIUM"):
        recommendation["recommendations"] = list(recommendation.get("recommendations") or []) + [f"Protected species recorded here: {eco_tips[0]}"]
    agents["trace"].append({"agent": "recommendation_agent", "status": "ok",
                            "ms": int((time.perf_counter() - start) * 1000),
                            "mode": recommendation.get("mode", "rules")})

    logger.info("Orchestrator: intent=%s level=%s score=%s confidence=%s",
                intent, risk["risk_level"], risk["risk_score"], risk.get("confidence"))
    return {
        "status": "success",
        "user_message": user_message,
        "intent": intent,
        "conversation": conversation,
        "location": {"latitude": location.latitude, "longitude": location.longitude},
        "place_name": place_name,
        "gps": gps_data,
        "zone_id": zone_id,
        "marine_data": agents["marine"],
        "weather_data": agents["weather"],
        "geospatial_data": agents["geospatial"],
        "official_alerts": agents["official"],
        "ecosystem": agents["ecosystem"],
        "consensus": agents["consensus"],
        "risk_assessment": risk,
        "recommendation": recommendation,
        "agent_trace": agents["trace"],
    }


def orchestrator(user_message: str, location=None, zone_id=None) -> dict:
    """Synchronous entry point that runs the async orchestrate coroutine."""
    return asyncio.run(orchestrate(user_message, location, zone_id))
