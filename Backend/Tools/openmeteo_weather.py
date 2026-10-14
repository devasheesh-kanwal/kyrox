# Backend/Tools/openmeteo_weather.py
"""
Open-Meteo Weather API tool (global coverage, no API key).

One cached request returns current conditions plus a 3 h history and 12 h
look-ahead from two independent NWP models (ECMWF IFS and NOAA GFS). The
agents use the history for pressure tendency and the two models to
cross-validate wind before advising a fisherman.
"""
import asyncio
import logging
from typing import Optional

from Services.http_cache import cached_get_json

logger = logging.getLogger(__name__)

OPENMETEO_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_MODELS = ("ecmwf_ifs025", "gfs_seamless")
MODEL_LABELS = {"ecmwf_ifs025": "ECMWF IFS", "gfs_seamless": "NOAA GFS"}
PAST_HOURS = 3
FORECAST_HOURS = 12
CACHE_TTL = 600.0


def _validate(latitude: float, longitude: float) -> None:
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        raise ValueError("Latitude and longitude must be numeric")
    if not (-90 <= latitude <= 90):
        raise ValueError("Latitude out of range (-90 to 90)")
    if not (-180 <= longitude <= 180):
        raise ValueError("Longitude out of range (-180 to 180)")


async def get_openmeteo_weather(latitude: float, longitude: float) -> dict:
    """
    Fetch current weather and multi-model hourly series. Wind is in knots.

    Returns the raw Open-Meteo payload with `stale` / `age_seconds` added.
    Hourly fields are suffixed by model, e.g. `wind_speed_10m_ecmwf_ifs025`.
    """
    _validate(latitude, longitude)
    params = {
        "latitude": round(latitude, 3),
        "longitude": round(longitude, 3),
        "current": "temperature_2m,surface_pressure,pressure_msl,wind_speed_10m,"
                   "wind_direction_10m,wind_gusts_10m,weather_code,precipitation,visibility",
        "hourly": "wind_speed_10m,wind_gusts_10m,pressure_msl,weather_code,visibility",
        "models": ",".join(WEATHER_MODELS),
        "wind_speed_unit": "kn",
        "past_hours": PAST_HOURS,
        "forecast_hours": FORECAST_HOURS,
        "timezone": "GMT",
    }
    response = await cached_get_json(OPENMETEO_WEATHER_URL, params, ttl=CACHE_TTL)
    data = dict(response.data or {})
    data["stale"] = response.stale
    data["age_seconds"] = response.age_seconds
    return data


async def get_weather_grid(points: list[tuple[float, float]], hours: int = FORECAST_HOURS) -> list[Optional[dict]]:
    """Batched current + 12 h max wind/gust for many points (heatmap / routing)."""
    batch = 60
    sem = asyncio.Semaphore(4)

    async def fetch_chunk(chunk):
        results: list[Optional[dict]] = []
        params = {
            "latitude": ",".join(f"{p[0]:.3f}" for p in chunk),
            "longitude": ",".join(f"{p[1]:.3f}" for p in chunk),
            "current": "wind_speed_10m,wind_gusts_10m,weather_code",
            "hourly": "wind_speed_10m,wind_gusts_10m",
            "wind_speed_unit": "kn",
            "forecast_hours": hours,
            "timezone": "GMT",
        }
        async with sem:
            response = await cached_get_json(OPENMETEO_WEATHER_URL, params, ttl=CACHE_TTL)
        payload = response.data if isinstance(response.data, list) else [response.data]
        for item in payload:
            current = (item or {}).get("current") or {}
            wind = current.get("wind_speed_10m")
            if wind is None:
                results.append(None)
                continue
            hourly = (item or {}).get("hourly") or {}
            winds = [v for v in (hourly.get("wind_speed_10m") or []) if isinstance(v, (int, float))]
            gusts = [v for v in (hourly.get("wind_gusts_10m") or []) if isinstance(v, (int, float))]
            results.append({
                "wind_speed": wind,
                "wind_gusts": current.get("wind_gusts_10m"),
                "wind_speed_max_12h": max(winds + [wind]),
                "wind_gusts_max_12h": max(gusts) if gusts else current.get("wind_gusts_10m"),
                "weather_code": current.get("weather_code"),
            })
        return results

    chunks = [points[i:i + batch] for i in range(0, len(points), batch)]
    parts = await asyncio.gather(*(fetch_chunk(c) for c in chunks))
    return [cell for part in parts for cell in part]
