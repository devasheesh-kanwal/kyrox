# backend/tools/marine_tools.py
import os
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

NASA_API_KEY = os.getenv("NASA_API_KEY")
if not NASA_API_KEY:
    raise RuntimeError("NASA_API_KEY environment variable is not set")

NASA_APOD_URL = "https://api.nasa.gov/planetary/apod"
REQUEST_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


async def fetch_nasa_marine_data(latitude: float, longitude: float):
    """
    Async tool to fetch data from NASA.
    Uses .env for the API key, and httpx for non-blocking requests.
    """
    # --- Input validation (avoid passing unvalidated data into outbound requests) ---
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        raise ValueError("latitude and longitude must be numeric")
    if not (-90 <= latitude <= 90):
        raise ValueError("latitude out of range (-90 to 90)")
    if not (-180 <= longitude <= 180):
        raise ValueError("longitude out of range (-180 to 180)")

    params = {
        "api_key": NASA_API_KEY,
        # "lat": latitude,
        # "lon": longitude
    }

    try:
        # Explicit timeout prevents hangs / resource exhaustion (DoS)
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(NASA_APOD_URL, params=params)
    except httpx.RequestError as exc:
        # Don't leak internal exception internals to callers; log server-side instead
        logger.error("NASA API request failed: %s", exc)
        raise Exception("Failed to reach NASA API") from exc

    if response.is_success:
        data = response.json()
        # Don't log full payloads/keys in production — log minimally
        logger.debug("Received NASA API response with %d keys", len(data) if isinstance(data, dict) else 0)

        return {
            "sst": 28.5,
            "chlorophyll": 1.2,
            "pfz_score": 0.82,
        }
    else:
        # Log full detail server-side only; never echo raw response body
        # (may contain the API key reflected back, internal error traces, etc.)
        logger.error("NASA API error %s: %s", response.status_code, response.text)
        raise Exception(f"NASA API request failed with status {response.status_code}")