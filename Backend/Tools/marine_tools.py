# Backend/Tools/marine_tools.py
"""
Open-Meteo Marine Weather API tool.

Responsibility: Fetch real marine data from the Open-Meteo Marine API.
This file handles ONLY API communication — no risk calculations, no LLM logic.
"""
import os
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ========== SECURE ENV LOADING ==========
# Open-Meteo public Marine API does NOT require an API key.
BASE_URL = os.getenv("MARINE_API_BASE_URL")

if not BASE_URL:
    raise RuntimeError(
        "MARINE_API_BASE_URL environment variable is not set in .env"
    )

REQUEST_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

# Fields requested from the Open-Meteo Marine API (current conditions)
CURRENT_MARINE_FIELDS = ",".join([
    "wave_height",
    "wave_direction",
    "wave_period",
    "swell_wave_height",
    "ocean_current_velocity",
    "ocean_current_direction",
    "sea_surface_temperature",
])


async def get_marine_data(latitude: float, longitude: float) -> dict:
    """
    Fetch current marine weather data from the Open-Meteo Marine API.

    Uses .env for the base URL and httpx for non-blocking requests.
    Returns the raw JSON response as a dict.

    Args:
        latitude:  Vessel latitude  (-90 to 90).
        longitude: Vessel longitude (-180 to 180).

    Returns:
        dict: Raw JSON response from the Open-Meteo Marine API.

    Raises:
        ValueError: If latitude or longitude are invalid.
        Exception:  On network / HTTP errors (details logged server-side only).
    """
    # ---- Input validation ----
    if not isinstance(latitude, (int, float)):
        raise ValueError("Latitude must be numeric")
    if not isinstance(longitude, (int, float)):
        raise ValueError("Longitude must be numeric")
    if not (-90 <= latitude <= 90):
        raise ValueError("Latitude out of range (-90 to 90)")
    if not (-180 <= longitude <= 180):
        raise ValueError("Longitude out of range (-180 to 180)")

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": CURRENT_MARINE_FIELDS,
        "timezone": "auto",
        "cell_selection": "sea",
    }

    headers = {
        "User-Agent": "KyroX-Marine-AI/1.0",
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(
                BASE_URL, params=params, headers=headers
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException as exc:
        logger.error(
            "Marine API request timed out for (%s, %s): %s",
            latitude, longitude, exc,
        )
        raise Exception("Marine API request timed out") from exc
    except httpx.RequestError as exc:
        # Don't leak upstream error details (may contain reflected parameters)
        logger.error("Marine API request failed: %s", exc)
        raise Exception("Failed to reach Marine API") from exc
    except httpx.HTTPStatusError as exc:
        # Log details server-side only; never echo raw response body to callers
        logger.error(
            "Marine API error %s: %s",
            exc.response.status_code,
            exc.response.text[:200],
        )
        raise Exception(
            f"Marine API request failed with status {exc.response.status_code}"
        ) from exc


# ---------- Example Usage (Test this file directly) ----------
if __name__ == "__main__":
    import asyncio

    async def test():
        try:
            # Test for a location in the Arabian Sea
            result = await get_marine_data(latitude=20.0, longitude=70.0)
            print("Marine API Response:")
            import json
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Error: {e}")

    asyncio.run(test())
