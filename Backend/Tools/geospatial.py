import asyncio
import math
import os
import logging
from pathlib import Path
import httpx
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()

logger = logging.getLogger(__name__)

_raw_geo_url = os.getenv("GEOSPATIAL_URL", "").strip()
if not _raw_geo_url or "geoapify" in _raw_geo_url.lower():
    GEOSPATIAL_URL = "https://overpass-api.de/api/interpreter"
else:
    GEOSPATIAL_URL = _raw_geo_url
GEOSPATIAL_KEY = os.getenv("GEOSPATIAL_KEY")

REQUEST_TIMEOUT = httpx.Timeout(25.0, connect=5.0)

PROTECTED_SEARCH_M = 10_000
SHORE_SEARCH_M = 50_000


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


def _element_coords(element: dict) -> tuple[float, float] | None:
    if "lat" in element and "lon" in element:
        return float(element["lat"]), float(element["lon"])
    center = element.get("center")
    if isinstance(center, dict) and "lat" in center and "lon" in center:
        return float(center["lat"]), float(center["lon"])
    bounds = element.get("bounds")
    if isinstance(bounds, dict):
        try:
            lat = (float(bounds["minlat"]) + float(bounds["maxlat"])) / 2
            lon = (float(bounds["minlon"]) + float(bounds["maxlon"])) / 2
            return lat, lon
        except (KeyError, TypeError, ValueError):
            return None
    return None


def _restriction_label(tags: dict) -> str | None:
    if not isinstance(tags, dict):
        return None
    name = tags.get("name") or tags.get("protection_title") or tags.get("official_name")
    kind = (
        tags.get("protect_class")
        or tags.get("protection_object")
        or tags.get("boundary")
        or tags.get("leisure")
        or tags.get("military")
        or tags.get("fishing")
    )
    if name and kind:
        return f"{name} ({kind})"
    return name or (f"Restricted zone ({kind})" if kind else None)


async def _overpass_query(client: httpx.AsyncClient, query: str) -> dict:
    headers = {
        "User-Agent": "KyroX-Marine-AI/1.0",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    is_overpass = "overpass" in GEOSPATIAL_URL.lower()
    if GEOSPATIAL_KEY and not is_overpass:
        headers["X-API-Key"] = GEOSPATIAL_KEY

    params = {}
    if GEOSPATIAL_KEY and not is_overpass:
        params["key"] = GEOSPATIAL_KEY

    try:
        response = await client.post(
            GEOSPATIAL_URL,
            data={"data": query},
            params=params,
            headers=headers,
        )
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as exc:
        logger.error("Geospatial API request failed: %s", exc)
        raise Exception("Failed to reach geospatial API") from exc
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Geospatial API error %s: %s",
            exc.response.status_code,
            exc.response.text[:200],
        )
        raise Exception(
            f"Geospatial API request failed with status {exc.response.status_code}"
        ) from exc
    except ValueError as exc:
        logger.error("Geospatial API returned invalid JSON: %s", exc)
        raise Exception("Invalid data format received from geospatial API") from exc


async def get_geospatial(latitude: float, longitude: float) -> dict:
    """
    Query nearby protected / restricted marine areas and approximate shore distance.
    Uses Overpass (OSM) via GEOSPATIAL_URL, with optional GEOSPATIAL_KEY from .env.
    """
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        raise ValueError("Latitude and longitude must be numeric")
    if not (-90 <= latitude <= 90):
        raise ValueError("Latitude out of range (-90 to 90)")
    if not (-180 <= longitude <= 180):
        raise ValueError("Longitude out of range (-180 to 180)")

    inside_query = f"""
[out:json][timeout:25];
is_in({latitude},{longitude})->.a;
(
  area.a["boundary"="protected_area"];
  area.a["leisure"="nature_reserve"];
  area.a["protect_class"];
  area.a["military"];
  area.a["fishing"="no"];
  area.a["access"="no"];
);
out tags;
"""

    nearby_query = f"""
[out:json][timeout:25];
(
  nwr["boundary"="protected_area"](around:{PROTECTED_SEARCH_M},{latitude},{longitude});
  nwr["leisure"="nature_reserve"](around:{PROTECTED_SEARCH_M},{latitude},{longitude});
  nwr["protect_class"](around:{PROTECTED_SEARCH_M},{latitude},{longitude});
  nwr["military"](around:{PROTECTED_SEARCH_M},{latitude},{longitude});
  nwr["fishing"="no"](around:{PROTECTED_SEARCH_M},{latitude},{longitude});
);
out center tags;
"""

    shore_query = f"""
[out:json][timeout:25];
(
  way["natural"="coastline"](around:{SHORE_SEARCH_M},{latitude},{longitude});
  nwr["natural"="beach"](around:{SHORE_SEARCH_M},{latitude},{longitude});
  nwr["place"="island"](around:{min(SHORE_SEARCH_M, 20_000)},{latitude},{longitude});
);
out center;
"""

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        inside_data, nearby_data, shore_data = await _gather_queries(
            client, inside_query, nearby_query, shore_query
        )

    inside_elements = inside_data.get("elements") or []
    nearby_elements = nearby_data.get("elements") or []
    shore_elements = shore_data.get("elements") or []

    restrictions: list[str] = []
    seen: set[str] = set()
    for element in list(inside_elements) + list(nearby_elements):
        label = _restriction_label(element.get("tags") or {})
        if label and label not in seen:
            seen.add(label)
            restrictions.append(label)

    inside_protected_area = any(
        (el.get("tags") or {}).get("boundary") == "protected_area"
        or (el.get("tags") or {}).get("leisure") == "nature_reserve"
        or "protect_class" in (el.get("tags") or {})
        for el in inside_elements
        if isinstance(el, dict)
    )

    restricted_zone = inside_protected_area or any(
        (el.get("tags") or {}).get("military")
        or (el.get("tags") or {}).get("fishing") == "no"
        or (el.get("tags") or {}).get("access") == "no"
        for el in inside_elements
        if isinstance(el, dict)
    )

    min_boundary_m = None
    for element in nearby_elements:
        coords = _element_coords(element)
        if not coords:
            continue
        dist = _haversine_m(latitude, longitude, coords[0], coords[1])
        if min_boundary_m is None or dist < min_boundary_m:
            min_boundary_m = dist

    if restricted_zone or inside_protected_area:
        distance_to_boundary_meters = 0.0
    elif min_boundary_m is not None:
        distance_to_boundary_meters = round(min_boundary_m, 1)
    else:
        distance_to_boundary_meters = float(PROTECTED_SEARCH_M)

    shore_m = None
    for element in shore_elements:
        coords = _element_coords(element)
        if not coords:
            continue
        dist = _haversine_m(latitude, longitude, coords[0], coords[1])
        if shore_m is None or dist < shore_m:
            shore_m = dist

    return {
        "inside_protected_area": bool(inside_protected_area or restricted_zone),
        "restricted_zone": bool(restricted_zone or inside_protected_area),
        "restrictions": restrictions,
        "distance_to_boundary_meters": distance_to_boundary_meters,
        "near_boundary": distance_to_boundary_meters <= 2_000,
        "distance_to_shore_meters": round(shore_m, 1) if shore_m is not None else None,
    }


async def _gather_queries(client, inside_query, nearby_query, shore_query):
    return await asyncio.gather(
        _overpass_query(client, inside_query),
        _overpass_query(client, nearby_query),
        _overpass_query(client, shore_query),
    )


if __name__ == "__main__":
    import asyncio

    async def test():
        result = await get_geospatial(latitude=11.685, longitude=92.720)
        print(result)

    asyncio.run(test())
