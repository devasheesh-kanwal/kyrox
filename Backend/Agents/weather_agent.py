# Backend/Agents/weather_agent.py
"""
Weather Agent — Fetches real-time atmospheric conditions.
Integrates OpenWeather (if configured) with automatic failover to Open-Meteo Weather API
(which requires no API key, providing 100% reliable live telemetry).
"""
import logging
from typing import Optional

from Models.schemas import Location, WeatherData
from Tools.openweather import get_weather
from Tools.openmeteo_weather import get_openmeteo_weather

logger = logging.getLogger(__name__)


class WeatherAgentError(Exception):
    """Raised when weather data cannot be retrieved or parsed."""


STORM_CONDITIONS = {"thunderstorm", "squall", "tornado"}


async def weather_agent(location: Location) -> WeatherData:
    """
    Fetch weather for a location and map it into our internal WeatherData model.
    Attempts OpenWeather first; falls back seamlessly to Open-Meteo Weather API.
    """
    data = None
    source = None

    # 1. Attempt OpenWeather if API key is present
    try:
        data = await get_weather(
            latitude=location.latitude,
            longitude=location.longitude,
        )
        source = "openweather"
    except Exception as exc:
        logger.info(
            "OpenWeather unavailable for (%.4f, %.4f) (%s), falling back to Open-Meteo Weather API",
            location.latitude, location.longitude, exc
        )

    # 2. Fallback to Open-Meteo Weather API (free, keyless, reliable)
    if not data or source != "openweather":
        try:
            data = await get_openmeteo_weather(
                latitude=location.latitude,
                longitude=location.longitude,
            )
            source = "openmeteo"
        except Exception as exc:
            logger.error("All weather sources failed for (%.4f, %.4f): %s",
                         location.latitude, location.longitude, exc)
            raise WeatherAgentError("Unable to retrieve live weather data") from exc

    if source == "openmeteo":
        return _parse_openmeteo(data)
    else:
        return _parse_openweather(data)


def _parse_openmeteo(data: dict) -> WeatherData:
    """Parse Open-Meteo Weather API response into WeatherData model."""
    current = data.get("current") or {}
    wind_speed = float(current.get("wind_speed_10m") or 0.0)
    wind_direction = current.get("wind_direction_10m")
    temperature = current.get("temperature_2m")
    surface_pressure = current.get("surface_pressure")
    weather_code = int(current.get("weather_code") or 0)

    # WMO Weather Code Classification:
    # 95, 96, 99 = Thunderstorm
    # 80, 81, 82 = Rain showers / Squall line
    # 61, 63, 65 = Rain
    is_lightning = weather_code in (95, 96, 99)
    is_squall = weather_code in (81, 82) or (wind_speed >= 30.0)
    is_storm = is_lightning or is_squall or weather_code in (95, 96, 99)

    lightning_risk = "HIGH" if is_lightning else "LOW"
    storm_risk = "HIGH" if is_storm else ("MEDIUM" if wind_speed >= 20.0 or weather_code in (63, 65, 80) else "LOW")

    return WeatherData(
        wind_speed=round(wind_speed, 1),
        wave_height=0.0,
        lightning_risk=lightning_risk,
        storm_risk=storm_risk,
        temperature=round(float(temperature), 1) if temperature is not None else None,
        surface_pressure=round(float(surface_pressure), 1) if surface_pressure is not None else None,
        wind_direction=round(float(wind_direction), 1) if wind_direction is not None else None,
    )


def _parse_openweather(data: dict) -> WeatherData:
    """Parse OpenWeather response into WeatherData model."""
    weather_conditions = _extract_conditions(data)
    raw_wind = _safe_get(data, ["wind", "speed"], default=0.0)
    # OpenWeather default metric units are m/s -> convert to knots (1 m/s ≈ 1.94384 knots)
    wind_speed_kts = float(raw_wind) * 1.94384 if raw_wind < 30.0 else float(raw_wind)

    temp_c = _safe_get(data, ["main", "temp"], default=None)
    pressure_hpa = _safe_get(data, ["main", "pressure"], default=None)
    wind_deg = _safe_get(data, ["wind", "deg"], default=None)

    is_storm = bool(STORM_CONDITIONS & weather_conditions)
    lightning_risk = "HIGH" if "thunderstorm" in weather_conditions else "LOW"
    storm_risk = "HIGH" if is_storm else ("MEDIUM" if wind_speed_kts >= 20.0 else "LOW")

    return WeatherData(
        wind_speed=round(wind_speed_kts, 1),
        wave_height=0.0,
        lightning_risk=lightning_risk,
        storm_risk=storm_risk,
        temperature=round(float(temp_c), 1) if temp_c is not None else None,
        surface_pressure=round(float(pressure_hpa), 1) if pressure_hpa is not None else None,
        wind_direction=round(float(wind_deg), 1) if wind_deg is not None else None,
    )


def _extract_conditions(data: dict) -> set[str]:
    """Safely extract lowercased condition names from an OpenWeather-style payload."""
    try:
        return {
            item.get("main", "").lower()
            for item in data.get("weather", [])
            if isinstance(item, dict)
        }
    except (AttributeError, TypeError):
        logger.warning("Unexpected 'weather' field shape in API response")
        return set()


def _safe_get(data: dict, path: list[str], default=None):
    """Walk a nested dict safely, returning `default` if any key is missing/wrong-typed."""
    current = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current if isinstance(current, (int, float)) else default
