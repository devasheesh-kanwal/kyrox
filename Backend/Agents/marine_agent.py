# Backend/Agents/marine_agent.py
"""
Marine Agent — processes raw Open-Meteo Marine API data into clean structured output.

Responsibility: Accept a location, call the marine API tool, and return
a clean dictionary of marine conditions. No risk calculations, no LLM logic.
"""
import logging

from Models.schemas import Location
from Tools.marine_tools import get_marine_data

logger = logging.getLogger(__name__)


class MarineAgentError(Exception):
    """Raised when marine data cannot be retrieved or parsed."""


# Marine fields we extract from the API response.
# Maps API field name → our output key (they happen to match in this case).
_MARINE_FIELDS = [
    "wave_height",
    "wave_direction",
    "wave_period",
    "swell_wave_height",
    "ocean_current_velocity",
    "ocean_current_direction",
    "sea_surface_temperature",
]


async def marine_agent(location: Location) -> dict:
    """
    Fetch marine conditions for a vessel location and return clean structured data.

    Args:
        location: A Location object with latitude and longitude.

    Returns:
        dict: Structured marine data, e.g.:
            {
                "wave_height": 1.8,
                "wave_direction": 220,
                "wave_period": 7.5,
                "swell_wave_height": 1.2,
                "ocean_current_velocity": 2.1,
                "ocean_current_direction": 180,
                "sea_surface_temperature": 28.4
            }

    Raises:
        MarineAgentError: On any failure to retrieve or parse marine data.
    """
    # ---- Fetch raw data from the Marine API tool ----
    try:
        raw_data = await get_marine_data(
            latitude=location.latitude,
            longitude=location.longitude,
        )
    except Exception as exc:
        # Don't leak raw upstream error details
        logger.error(
            "Marine data fetch failed for (%s, %s): %s",
            location.latitude, location.longitude, exc,
        )
        raise MarineAgentError("Unable to retrieve marine data") from exc

    # ---- Extract the "current" block from the API response ----
    current_data = raw_data.get("current")
    if not isinstance(current_data, dict):
        logger.error(
            "Missing or invalid 'current' block in Marine API response: %s",
            type(current_data),
        )
        raise MarineAgentError(
            "Marine API returned an unexpected response format"
        )

    # ---- Build clean structured output ----
    marine_conditions = {}
    for field in _MARINE_FIELDS:
        value = current_data.get(field)
        if isinstance(value, (int, float)):
            marine_conditions[field] = value
        else:
            # Missing or non-numeric — log a warning but default to None
            logger.warning(
                "Marine field '%s' missing or invalid in API response "
                "(got %r), defaulting to None",
                field, value,
            )
            marine_conditions[field] = None

    logger.info(
        "Marine data processed for (%s, %s): %s",
        location.latitude, location.longitude, marine_conditions,
    )

    return marine_conditions


# ---------- Example Usage (Test this file directly) ----------
if __name__ == "__main__":
    import asyncio

    async def test():
        try:
            loc = Location(latitude=20.0, longitude=70.0)
            result = await marine_agent(loc)
            print("Structured Marine Data:")
            for key, val in result.items():
                print(f"  {key}: {val}")
        except MarineAgentError as e:
            print(f"Agent Error: {e}")

    asyncio.run(test())
