# Backend/Tools/marine_tools.py
"""
Open-Meteo Marine API tool (global coverage, no API key).

One cached request returns:
  * `current`  - best-match analysis for the vessel position;
  * `hourly`   - 12 h look-ahead for the best-match model PLUS two independent
                 wave models (ECMWF WAM and NOAA GFS-Wave) so the agents can
                 cross-check sources instead of trusting a single feed;
  * modelled sea level (tide + surge) used for tide timing.

This file handles ONLY API communication and unit normalisation.
"""
import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from Services.http_cache import cached_get_json

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()

logger = logging.getLogger(__name__)

BASE_URL = os.getenv("MARINE_API_BASE_URL") or "https://marine-api.open-meteo.com/v1/marine"

KMH_TO_KNOTS = 0.539957

# Independent wave models used for cross-validation. best_match is listed
# first so the `current` block comes from Open-Meteo's best blend.
WAVE_MODELS = ("best_match", "ecmwf_wam025", "ncep_gfswave025")
MODEL_LABELS = {
    "marine_best_match": "Open-Meteo best match",
    "ecmwf_wam025": "ECMWF WAM",
    "ncep_gfswave025": "NOAA GFS-Wave",
}

CURRENT_MARINE_FIELDS = ",".join([
    "wave_height",
    "wave_direction",
    "wave_period",
    "swell_wave_height",
    "swell_wave_period",
    "swell_wave_direction",
    "ocean_current_velocity",
    "ocean_current_direction",
    "sea_surface_temperature",
])
HOURLY_MARINE_FIELDS = "wave_height,swell_wave_height,sea_level_height_msl"
FORECAST_HOURS = 12
CACHE_TTL = 900.0  # upstream marine models update hourly at best


class MarineDataUnavailable(Exception):
    """Raised when the position has no marine model coverage (e.g. inland)."""


def _validate(latitude: float, longitude: float) -> None:
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        raise ValueError("Latitude and longitude must be numeric")
    if not (-90 <= latitude <= 90):
        raise ValueError("Latitude out of range (-90 to 90)")
    if not (-180 <= longitude <= 180):
        raise ValueError("Longitude out of range (-180 to 180)")


def _hourly_series(hourly: dict, field: str, model_key: str) -> list:
    return list(hourly.get(f"{field}_{model_key}") or [])


async def get_marine_data(latitude: float, longitude: float) -> dict:
    """
    Fetch marine conditions for a point.

    Returns a dict:
        {
          "current": {... ocean_current_velocity in KNOTS ...},
          "observed_at": "2026-10-10T08:45Z",
          "grid_point": {"latitude": .., "longitude": ..},
          "hourly_time": [...],
          "forecast": {"wave_height": [...], "swell_wave_height": [...]},
          "models": {"ECMWF WAM": [...], "NOAA GFS-Wave": [...]},
          "sea_level": [...],
          "stale": bool, "age_seconds": int,
        }

    Raises MarineDataUnavailable when the point is not covered by any marine
    model (inland). We never substitute another location's data: a fisherman
    must not receive readings for a different coast.
    """
    _validate(latitude, longitude)
    params = {
        "latitude": round(latitude, 3),
        "longitude": round(longitude, 3),
        "current": CURRENT_MARINE_FIELDS,
        "hourly": HOURLY_MARINE_FIELDS,
        "models": ",".join(WAVE_MODELS),
        "forecast_hours": FORECAST_HOURS,
        "timezone": "GMT",
        "cell_selection": "sea",
    }
    response = await cached_get_json(BASE_URL, params, ttl=CACHE_TTL)
    data = response.data or {}
    current = dict(data.get("current") or {})

    if current.get("wave_height") is None and current.get("sea_surface_temperature") is None:
        raise MarineDataUnavailable(
            "No marine model coverage at this position (likely on land or in a closed water body)"
        )

    # Open-Meteo reports ocean currents in km/h; the whole app works in knots.
    velocity = current.get("ocean_current_velocity")
    if isinstance(velocity, (int, float)):
        current["ocean_current_velocity"] = round(velocity * KMH_TO_KNOTS, 2)

    hourly = data.get("hourly") or {}
    models = {}
    for model_key, label in MODEL_LABELS.items():
        if model_key == "marine_best_match":
            continue
        series = _hourly_series(hourly, "wave_height", model_key)
        if any(isinstance(v, (int, float)) for v in series):
            models[label] = series

    observed = current.get("time")
    return {
        "current": current,
        "observed_at": f"{observed}Z" if observed else None,
        "grid_point": {"latitude": data.get("latitude"), "longitude": data.get("longitude")},
        "hourly_time": list(hourly.get("time") or []),
        "forecast": {
            "wave_height": _hourly_series(hourly, "wave_height", "marine_best_match"),
            "swell_wave_height": _hourly_series(hourly, "swell_wave_height", "marine_best_match"),
        },
        "models": models,
        "sea_level": _hourly_series(hourly, "sea_level_height_msl", "marine_best_match"),
        "stale": response.stale,
        "age_seconds": response.age_seconds,
    }


async def get_marine_grid(points: list[tuple[float, float]], hours: int = FORECAST_HOURS) -> list[Optional[dict]]:
    """
    Fetch wave height (now + 12 h max) for many points in batched requests.
    Used by the heatmap and route planner. Returns None for land/no-coverage.
    """
    batch = 60
    sem = asyncio.Semaphore(4)

    async def fetch_chunk(chunk):
        results: list[Optional[dict]] = []
        params = {
            "latitude": ",".join(f"{p[0]:.3f}" for p in chunk),
            "longitude": ",".join(f"{p[1]:.3f}" for p in chunk),
            "current": "wave_height,swell_wave_height,sea_surface_temperature",
            "hourly": "wave_height",
            "forecast_hours": hours,
            "timezone": "GMT",
            # "nearest" (not "sea") so coastal land cells come back empty and
            # the route planner treats them as land instead of snapping to sea.
            "cell_selection": "nearest",
        }
        async with sem:
            response = await cached_get_json(BASE_URL, params, ttl=CACHE_TTL)
        payload = response.data if isinstance(response.data, list) else [response.data]
        for item in payload:
            current = (item or {}).get("current") or {}
            wave = current.get("wave_height")
            if wave is None:
                results.append(None)
                continue
            future = [v for v in ((item.get("hourly") or {}).get("wave_height") or []) if isinstance(v, (int, float))]
            results.append({
                "wave_height": wave,
                "wave_height_max_12h": max(future + [wave]),
                "swell_wave_height": current.get("swell_wave_height"),
                "sea_surface_temperature": current.get("sea_surface_temperature"),
            })
        return results

    chunks = [points[i:i + batch] for i in range(0, len(points), batch)]
    parts = await asyncio.gather(*(fetch_chunk(c) for c in chunks))
    return [cell for part in parts for cell in part]
