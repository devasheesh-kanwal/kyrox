# Backend/Tools/geospatial.py
"""
Protected / restricted marine area lookup (OpenStreetMap via Overpass, global).

The public Overpass service is often slow (5-10 s) or overloaded, so:
  * one light query per ~5 km tile, cached for 24 h (boundaries rarely change);
  * failures are cached briefly and reported as `data_available: False`,
    never as "no restrictions";
  * a small offline list of known Indian marine sanctuaries is always
    checked, so a few critical areas work even when Overpass is down.

"Inside" is computed against each area's bounding box, which is
conservative (may flag a point near an irregular boundary as inside).
"""
import asyncio
import logging
import math
import os
import time
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()

logger = logging.getLogger(__name__)

GEOSPATIAL_URL = os.getenv("GEOSPATIAL_URL", "").strip()
if not GEOSPATIAL_URL or "geoapify" in GEOSPATIAL_URL.lower():
    GEOSPATIAL_URL = "https://overpass-api.de/api/interpreter"

REQUEST_TIMEOUT = httpx.Timeout(15.0, connect=5.0)
SEARCH_RADIUS_M = 10_000
NEAR_BOUNDARY_M = 2_000
TILE_DEG = 0.05            # ~5 km cache tiles
CACHE_TTL = 24 * 3600.0
FAILURE_TTL = 300.0

_tile_cache: dict[tuple, tuple[float, Optional[list]]] = {}
_tile_inflight: dict[tuple, asyncio.Task] = {}

# Offline list (lat_min, lat_max, lon_min, lon_max, label). Verified bounding
# boxes of notified Indian marine protected areas used by the original app.
KNOWN_AREAS = [
    (16.02, 16.10, 73.42, 73.52, "Malvan Marine Sanctuary: bottom trawling prohibited"),
    (13.98, 14.06, 74.28, 74.37, "Netrani Island coral reef: protected marine area"),
]


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _restriction_label(tags: dict) -> Optional[str]:
    if not isinstance(tags, dict):
        return None
    name = tags.get("name:en") or tags.get("name") or tags.get("protection_title")
    if tags.get("military"):
        kind = "military area"
    elif tags.get("protect_class") or tags.get("boundary") == "protected_area":
        kind = "protected area"
    elif tags.get("leisure") == "nature_reserve":
        kind = "nature reserve"
    else:
        kind = "restricted area"
    return f"{name} ({kind})" if name else kind.capitalize()


def _bbox_distance_m(lat: float, lon: float, b: dict) -> float:
    """0 when inside the box, else distance to the nearest box edge point."""
    clat = min(max(lat, b["minlat"]), b["maxlat"])
    clon = min(max(lon, b["minlon"]), b["maxlon"])
    return 0.0 if (clat == lat and clon == lon) else _haversine_m(lat, lon, clat, clon)


async def _fetch_tile(tile: tuple) -> Optional[list]:
    lat = (tile[0] + 0.5) * TILE_DEG
    lon = (tile[1] + 0.5) * TILE_DEG
    radius = SEARCH_RADIUS_M + 4000  # cover the whole tile
    query = f"""
[out:json][timeout:12];
(
  nwr["boundary"="protected_area"](around:{radius},{lat},{lon});
  nwr["leisure"="nature_reserve"](around:{radius},{lat},{lon});
  nwr["military"](around:{radius},{lat},{lon});
  nwr["fishing"="no"](around:{radius},{lat},{lon});
);
out tags bb;
"""
    headers = {"User-Agent": "KyroX-ORCA-Marine-AI/3.0 (marine safety)", "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=headers) as client:
            resp = await client.post(GEOSPATIAL_URL, data={"data": query})
            resp.raise_for_status()
            elements = resp.json().get("elements") or []
    except Exception as exc:
        logger.info("Overpass unavailable for tile %s: %s", tile, type(exc).__name__)
        _tile_cache[tile] = (time.time(), None)
        return None
    areas = []
    for el in elements:
        b = el.get("bounds")
        if not b:
            continue
        areas.append({"label": _restriction_label(el.get("tags") or {}), "bounds": b,
                      "military": bool((el.get("tags") or {}).get("military"))})
    _tile_cache[tile] = (time.time(), areas)
    return areas


async def _areas_for(lat: float, lon: float, wait_s: float) -> Optional[list]:
    tile = (math.floor(lat / TILE_DEG), math.floor(lon / TILE_DEG))
    cached = _tile_cache.get(tile)
    if cached:
        age = time.time() - cached[0]
        if cached[1] is not None and age < CACHE_TTL:
            return cached[1]
        if cached[1] is None and age < FAILURE_TTL:
            return None
    task = _tile_inflight.get(tile)
    if task is None or task.done():
        task = asyncio.create_task(_fetch_tile(tile))
        _tile_inflight[tile] = task
    try:
        # shield: if we stop waiting, the fetch keeps going and fills the cache.
        return await asyncio.wait_for(asyncio.shield(task), timeout=wait_s)
    except asyncio.TimeoutError:
        return None


async def get_geospatial(latitude: float, longitude: float, wait_s: float = 4.0) -> dict:
    """Protected / restricted areas within 10 km of the position."""
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        raise ValueError("Latitude and longitude must be numeric")
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        raise ValueError("Coordinates out of range")

    restrictions: list[str] = []
    inside = restricted = False
    nearest = None

    for lat_min, lat_max, lon_min, lon_max, label in KNOWN_AREAS:
        b = {"minlat": lat_min, "maxlat": lat_max, "minlon": lon_min, "maxlon": lon_max}
        d = _bbox_distance_m(latitude, longitude, b)
        if d <= SEARCH_RADIUS_M:
            nearest = d if nearest is None else min(nearest, d)
            if d == 0:
                inside = restricted = True
                restrictions.append(label)

    areas = await _areas_for(latitude, longitude, wait_s)
    for area in areas or []:
        d = _bbox_distance_m(latitude, longitude, area["bounds"])
        if d > SEARCH_RADIUS_M:
            continue
        nearest = d if nearest is None else min(nearest, d)
        if d == 0:
            inside = True
            restricted = True
            if area["label"] and area["label"] not in restrictions:
                restrictions.append(area["label"])
        elif d <= NEAR_BOUNDARY_M and area["label"] and f"Near {area['label']}" not in restrictions:
            restrictions.append(f"Near {area['label']} ({d / 1000:.1f} km)")

    return {
        "inside_protected_area": inside,
        "restricted_zone": restricted,
        "restrictions": restrictions,
        "distance_to_boundary_meters": round(nearest, 1) if nearest is not None else float(SEARCH_RADIUS_M),
        "near_boundary": nearest is not None and 0 < nearest <= NEAR_BOUNDARY_M,
        "distance_to_shore_meters": None,
        "data_available": areas is not None,
        "source": "OpenStreetMap (Overpass)" if areas is not None else "offline sanctuary list only (OpenStreetMap unavailable)",
    }
