# Backend/Tools/marine_tools.py
"""
Open-Meteo Marine Weather API tool.

Responsibility: Fetch real marine data from the Open-Meteo Marine API.
This file handles ONLY API communication — no risk calculations, no LLM logic.
"""
import os
import logging
from pathlib import Path
import httpx
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()

logger = logging.getLogger(__name__)

# ========== SECURE ENV LOADING ==========
# Open-Meteo public Marine API does NOT require an API key.
BASE_URL = os.getenv("MARINE_API_BASE_URL") or "https://marine-api.open-meteo.com/v1/marine"

REQUEST_TIMEOUT = httpx.Timeout(15.0, connect=8.0)

CURRENT_MARINE_FIELDS = ",".join([
    "wave_height",
    "wave_direction",
    "wave_period",
    "swell_wave_height",
    "ocean_current_velocity",
    "ocean_current_direction",
    "sea_surface_temperature",
])

# Reference maritime coastal stations across Indian littoral waters
COASTAL_SECTOR_ANCHORS = [
    ("Central West Coast Offshore", 15.25, 73.75),
    ("Karwar Marine Sector", 14.80, 74.05),
    ("Mormugao Channel", 15.42, 73.74),
    ("Betul South Waters", 15.12, 73.90),
    ("Mumbai High", 19.10, 72.60),
    ("Gujarat Saurashtra", 21.10, 70.00),
    ("Mangalore Sector", 12.85, 74.75),
    ("Kochi Offshore", 9.95, 76.15),
    ("Kanyakumari Cape", 8.05, 77.55),
    ("Chennai East", 13.10, 80.35),
    ("Visakhapatnam Deep", 17.65, 83.35),
    ("Odisha Paradip", 20.25, 86.70),
    ("Digha Bengal", 21.55, 87.55),
    ("Andaman Sea", 11.65, 92.75),
]


def _find_nearest_coastal_anchor(lat: float, lon: float) -> tuple[float, float]:
    """Find the nearest coastal marine anchor point for inland coordinates."""
    best = min(COASTAL_SECTOR_ANCHORS, key=lambda a: (a[1] - lat) ** 2 + (a[2] - lon) ** 2)
    return best[1], best[2]


async def get_marine_data(latitude: float, longitude: float) -> dict:
    """
    Fetch current marine weather data from the Open-Meteo Marine API.

    Uses .env for the base URL and httpx for non-blocking requests.
    If the requested coordinates are inland and return null marine conditions,
    automatically resolves conditions for the nearest coastal sector.
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

    headers = {
        "User-Agent": "KyroX-Marine-AI/2.0",
    }

    async def _fetch(lat: float, lon: float) -> dict:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": CURRENT_MARINE_FIELDS,
            "timezone": "auto",
            "cell_selection": "nearest",
        }
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(BASE_URL, params=params, headers=headers)
            response.raise_for_status()
            return response.json()

    try:
        data = await _fetch(latitude, longitude)
        current = data.get("current") or {}
        # If open-meteo returned null values (coordinate is inland / non-marine)
        if current.get("wave_height") is None:
            c_lat, c_lon = _find_nearest_coastal_anchor(latitude, longitude)
            logger.info("Coordinates (%.4f, %.4f) are inland; fetching nearest coastal anchor (%.4f, %.4f)",
                        latitude, longitude, c_lat, c_lon)
            coastal_data = await _fetch(c_lat, c_lon)
            if (coastal_data.get("current") or {}).get("wave_height") is not None:
                return coastal_data
        return data
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
