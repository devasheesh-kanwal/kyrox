# Backend/Agents/weather_agent.py
import logging

from Models.schemas import Location, WeatherData
from Tools.openweather import get_weather

logger = logging.getLogger(__name__)


class WeatherAgentError(Exception):
    """Raised when weather data cannot be retrieved or parsed."""


STORM_CONDITIONS = {"thunderstorm"}


async def weather_agent(location: Location) -> WeatherData:
    """
    Fetch weather for a location and map it into our internal WeatherData model.
    Raises WeatherAgentError on any failure so callers can handle it explicitly.
    """
    try:
        data = await get_weather(
            latitude=location.latitude,
            longitude=location.longitude,
        )
    except Exception as exc:
        # Don't leak raw upstream error details (may include API key echoes, etc.)
        logger.error("Weather fetch failed for (%s, %s): %s",
                     location.latitude, location.longitude, exc)
        raise WeatherAgentError("Unable to retrieve weather data") from exc

    weather_conditions = _extract_conditions(data)
    wind_speed = _safe_get(data, ["wind", "speed"], default=0.0)

    is_storm = bool(STORM_CONDITIONS & weather_conditions)
    risk = "HIGH" if is_storm else "LOW"

    return WeatherData(
        wind_speed=wind_speed,
        wave_height=0.0,  # TODO: not provided by this API — source separately
        lightning_risk=risk,
        storm_risk=risk,
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

