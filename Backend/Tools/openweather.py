import os
import logging
from pathlib import Path
import httpx
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()  # Fallback to current working directory if present

logger = logging.getLogger(__name__)

# ========== SECURE ENV LOADING (No Hardcoded Keys!) ==========
API_KEY = os.getenv("WEATHER_KEY", "").strip().removesuffix("git")
BASE_URL = os.getenv("WEATHER_URL")

if not API_KEY:
    raise RuntimeError("WEATHER_KEY environment variable is not set in .env")
if not BASE_URL:
    raise RuntimeError("WEATHER_URL environment variable is not set in .env")

REQUEST_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


async def get_weather(latitude: float, longitude: float) -> dict:
    """
    Fetch current weather data from OpenWeatherMap API.
    Uses .env for API key and URL, and httpx for non-blocking requests.
    Returns the raw JSON response as a dict.
    """
    # Input validation (prevents injection / bad data)
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        raise ValueError("Latitude and longitude must be numeric")
    if not (-90 <= latitude <= 90):
        raise ValueError("Latitude out of range (-90 to 90)")
    if not (-180 <= longitude <= 180):
        raise ValueError("Longitude out of range (-180 to 180)")

    params = {
        "lat": latitude,
        "lon": longitude,
        "appid": API_KEY,
        "units": "metric",
    }

    headers = {
        "User-Agent": "Marine-AI/1.0",
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(BASE_URL, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as exc:
        # Don't leak upstream error details (may contain API key echoes)
        logger.error("Weather API request failed: %s", exc)
        raise Exception("Failed to reach weather API") from exc
    except httpx.HTTPStatusError as exc:
        # Log details server-side only; never echo raw response body to callers
        logger.error("Weather API error %s: %s",
                     exc.response.status_code, exc.response.text[:200])
        raise Exception(
            f"Weather API request failed with status {exc.response.status_code}"
        ) from exc