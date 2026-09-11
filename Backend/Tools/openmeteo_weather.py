# Backend/Tools/openmeteo_weather.py
"""
Open-Meteo Weather API tool.
Provides free, keyless, real-time atmospheric telemetry and storm classification.
"""
import logging
import httpx

logger = logging.getLogger(__name__)

OPENMETEO_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


async def get_openmeteo_weather(latitude: float, longitude: float) -> dict:
    """
    Fetch current atmospheric weather conditions from Open-Meteo Weather API.
    Does not require any API key. Returns standard weather dict with wind speed in knots.
    """
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        raise ValueError("Latitude and longitude must be numeric")
    if not (-90 <= latitude <= 90):
        raise ValueError("Latitude out of range (-90 to 90)")
    if not (-180 <= longitude <= 180):
        raise ValueError("Longitude out of range (-180 to 180)")

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m,weather_code,precipitation",
        "wind_speed_unit": "kn",
        "timezone": "auto",
    }

    headers = {
        "User-Agent": "KyroX-Marine-AI/2.0",
    }

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(OPENMETEO_WEATHER_URL, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
