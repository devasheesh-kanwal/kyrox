# Backend/Tools/official_alerts.py
"""
Official / authoritative hazard feeds.

* INCOIS (India) - High Wave Alerts (HWA) and Swell Surge Alerts (SSA) per
  coastal district. Source: the public JSON feed used by INCOIS's own mobile
  app. It is undocumented, so it may change without notice; failures are
  reported as "feed unavailable", never hidden.
* GDACS (global, UN/EC JRC) - active tropical cyclones and tsunamis.

INCOIS publishes districts by name only, so districts are geocoded with the
Open-Meteo geocoding API and cached. Districts that cannot be geocoded are
reported as `unlocated` instead of being guessed.
"""
import asyncio
import json
import logging
import math
import re
from typing import Optional

from Services.http_cache import UpstreamError, cached_get_json

logger = logging.getLogger(__name__)

INCOIS_ALERTS_URL = "https://sarat.incois.gov.in/incoismobileappdata/rest/incois/hwassalatestdata"
GDACS_EVENTS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

INCOIS_RADIUS_KM = 150.0       # district alerts apply to the adjoining coastal sea
GDACS_CYCLONE_RADIUS_KM = 1000.0
GDACS_TSUNAMI_RADIUS_KM = 2000.0

COLOR_SEVERITY = {"red": 3, "orange": 2, "yellow": 1, "green": 0}

_geocode_cache: dict[str, Optional[tuple[float, float]]] = {}
_geocode_lock = asyncio.Semaphore(4)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _name_candidates(district: str) -> list[str]:
    """'KASARAGOD, KANNUR' -> ['Kasaragod', 'Kannur']; 'JUNAGADH NORTH' -> ['Junagadh North', 'Junagadh']."""
    parts = re.split(r",|&| AND ", district.upper())
    out = []
    for part in parts:
        name = part.strip().title()
        if not name:
            continue
        out.append(name)
        trimmed = re.sub(r"\b(North|South|East|West|Island|Islands)\b", "", name).strip()
        if trimmed and trimmed != name:
            out.append(trimmed)
    return out


def _norm(text: str) -> str:
    return re.sub(r"[^a-z]", "", (text or "").lower())


async def _geocode_district(district: str, state: str) -> Optional[tuple[float, float]]:
    key = f"{district}|{state}"
    if key in _geocode_cache:
        return _geocode_cache[key]
    result = None
    async with _geocode_lock:
        for name in _name_candidates(district):
            try:
                resp = await cached_get_json(
                    GEOCODE_URL,
                    {"name": name, "count": 10, "countryCode": "IN", "language": "en"},
                    ttl=7 * 24 * 3600,
                )
            except UpstreamError:
                continue
            matches = (resp.data or {}).get("results") or []
            # Prefer a match in the same state; never accept a different state.
            state_n = _norm(state)
            same_state = [m for m in matches if state_n and (state_n in _norm(m.get("admin1", "")) or _norm(m.get("admin1", "")) in state_n)]
            if same_state:
                m = same_state[0]
                result = (float(m["latitude"]), float(m["longitude"]))
                break
    _geocode_cache[key] = result
    return result


def _parse_incois_list(raw) -> list[dict]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return []
    return [r for r in raw if isinstance(r, dict)] if isinstance(raw, list) else []


async def get_incois_alerts(latitude: float, longitude: float) -> dict:
    """INCOIS HWA/SSA alerts within INCOIS_RADIUS_KM of the position."""
    try:
        resp = await cached_get_json(INCOIS_ALERTS_URL, None, ttl=1800, stale_ttl=6 * 3600)
    except UpstreamError as exc:
        return {"available": False, "error": str(exc), "alerts": [], "unlocated": 0}

    data = resp.data or {}
    records = []
    for kind, field, date_field in (("High Wave", "HWAJson", "LatestHWADate"), ("Swell Surge", "SSAJson", "LatestSSADate")):
        for rec in _parse_incois_list(data.get(field)):
            records.append((kind, data.get(date_field), rec))

    # Fast exit: INCOIS only covers Indian coasts; skip geocoding far away.
    if not (-5.0 <= latitude <= 30.0 and 60.0 <= longitude <= 100.0):
        return {"available": True, "alerts": [], "unlocated": 0, "stale": resp.stale, "coverage": "outside INCOIS region"}

    coords = await asyncio.gather(*[_geocode_district(r.get("District", ""), r.get("STATE", "")) for _, _, r in records])
    nearby, unlocated = [], 0
    for (kind, issued, rec), pos in zip(records, coords):
        if pos is None:
            unlocated += 1
            continue
        dist = haversine_km(latitude, longitude, pos[0], pos[1])
        if dist > INCOIS_RADIUS_KM:
            continue
        color = (rec.get("Color") or "").strip().lower()
        nearby.append({
            "source": "INCOIS",
            "kind": kind,
            "alert": rec.get("Alert"),
            "level": color or "unknown",
            "severity": COLOR_SEVERITY.get(color, 1),
            "district": rec.get("District"),
            "state": rec.get("STATE"),
            "message": rec.get("Message"),
            "issued": rec.get("Issue Date") or issued,
            "distance_km": round(dist, 1),
        })
    nearby.sort(key=lambda a: (-a["severity"], a["distance_km"]))
    return {"available": True, "alerts": nearby, "unlocated": unlocated, "stale": resp.stale}


async def get_gdacs_alerts(latitude: float, longitude: float) -> dict:
    """Active GDACS tropical cyclones / tsunamis within range of the position."""
    features, stale = [], False
    try:
        for event_type in ("TC", "TS"):
            resp = await cached_get_json(GDACS_EVENTS_URL, {"eventlist": event_type}, ttl=1800, stale_ttl=6 * 3600)
            stale = stale or resp.stale
            if isinstance(resp.data, dict):
                features.extend(resp.data.get("features") or [])
    except UpstreamError as exc:
        return {"available": False, "error": str(exc), "alerts": []}

    alerts = []
    for feature in features:
        props = feature.get("properties") or {}
        if str(props.get("iscurrent", "")).lower() != "true":
            continue
        coords = (feature.get("geometry") or {}).get("coordinates") or []
        if len(coords) < 2:
            continue
        ev_lon, ev_lat = float(coords[0]), float(coords[1])
        dist = haversine_km(latitude, longitude, ev_lat, ev_lon)
        etype = props.get("eventtype")
        radius = GDACS_TSUNAMI_RADIUS_KM if etype == "TS" else GDACS_CYCLONE_RADIUS_KM
        if dist > radius:
            continue
        level = (props.get("alertlevel") or "").lower()
        alerts.append({
            "source": "GDACS",
            "kind": "Tropical Cyclone" if etype == "TC" else "Tsunami",
            "alert": props.get("name") or props.get("eventname"),
            "level": level or "unknown",
            "severity": COLOR_SEVERITY.get(level, 1),
            "message": (props.get("severitydata") or {}).get("severitytext") or props.get("description"),
            "issued": props.get("fromdate"),
            "valid_until": props.get("todate"),
            "distance_km": round(dist, 1),
            "event_position": {"latitude": ev_lat, "longitude": ev_lon},
            "url": ((props.get("url") or {}).get("report")),
        })
    alerts.sort(key=lambda a: (-a["severity"], a["distance_km"]))
    return {"available": True, "alerts": alerts, "stale": stale}


async def get_official_alerts(latitude: float, longitude: float) -> dict:
    incois, gdacs = await asyncio.gather(
        get_incois_alerts(latitude, longitude),
        get_gdacs_alerts(latitude, longitude),
    )
    alerts = sorted(incois["alerts"] + gdacs["alerts"], key=lambda a: (-a["severity"], a["distance_km"]))
    return {
        "alerts": alerts,
        "feeds": {
            "INCOIS": {k: v for k, v in incois.items() if k != "alerts"},
            "GDACS": {k: v for k, v in gdacs.items() if k != "alerts"},
        },
    }
