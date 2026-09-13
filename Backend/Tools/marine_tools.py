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
    ("Port Blair Offshore", 11.62, 92.73),
    ("Great Nicobar Sector", 7.03, 93.79),
]

# Regional baseline intelligence for the Indian maritime boundary. SSH values
# are sea-surface-height anomalies from the latest configured reference grid;
# they are intentionally labeled as baseline data until an altimetry feed is configured.
MARITIME_SECTOR_DATA = [
    {"sector": "Gujarat Saurashtra", "lat": 21.10, "lon": 70.00, "species": ["Whale shark", "Indian mackerel"], "oil_slick": {"status": "clear", "area_km2": 0.0}, "ssh_anomaly_cm": 4.2},
    {"sector": "Mumbai High", "lat": 19.10, "lon": 72.60, "species": ["Indo-Pacific bottlenose dolphin", "Blue whale"], "oil_slick": {"status": "watch", "area_km2": 0.6}, "ssh_anomaly_cm": 5.8},
    {"sector": "Konkan and Goa", "lat": 15.25, "lon": 73.75, "species": ["Olive Ridley turtle", "Whale shark"], "oil_slick": {"status": "detected", "area_km2": 1.2}, "ssh_anomaly_cm": 3.6},
    {"sector": "Karwar and Mangalore", "lat": 13.85, "lon": 74.40, "species": ["Blue whale", "Spinner dolphin"], "oil_slick": {"status": "clear", "area_km2": 0.0}, "ssh_anomaly_cm": 2.9},
    {"sector": "Kochi Offshore", "lat": 9.95, "lon": 76.15, "species": ["Dugong", "Whale shark"], "oil_slick": {"status": "clear", "area_km2": 0.0}, "ssh_anomaly_cm": 1.7},
    {"sector": "Gulf of Mannar", "lat": 9.05, "lon": 79.10, "species": ["Dugong", "Green sea turtle"], "oil_slick": {"status": "watch", "area_km2": 0.3}, "ssh_anomaly_cm": 1.1},
    {"sector": "Kanyakumari", "lat": 8.05, "lon": 77.55, "species": ["Sperm whale", "Indian Ocean tuna"], "oil_slick": {"status": "clear", "area_km2": 0.0}, "ssh_anomaly_cm": 0.8},
    {"sector": "Chennai and Pulicat", "lat": 13.10, "lon": 80.35, "species": ["Olive Ridley turtle", "Finless porpoise"], "oil_slick": {"status": "watch", "area_km2": 0.4}, "ssh_anomaly_cm": 2.4},
    {"sector": "Visakhapatnam Deep", "lat": 17.65, "lon": 83.35, "species": ["Olive Ridley turtle", "Bryde's whale"], "oil_slick": {"status": "clear", "area_km2": 0.0}, "ssh_anomaly_cm": 3.0},
    {"sector": "Odisha Paradip", "lat": 20.25, "lon": 86.70, "species": ["Olive Ridley turtle", "Irrawaddy dolphin"], "oil_slick": {"status": "watch", "area_km2": 0.5}, "ssh_anomaly_cm": 4.6},
    {"sector": "Digha Bengal", "lat": 21.55, "lon": 87.55, "species": ["Gangetic dolphin", "Olive Ridley turtle"], "oil_slick": {"status": "clear", "area_km2": 0.0}, "ssh_anomaly_cm": 4.9},
    {"sector": "Lakshadweep Sea", "lat": 10.57, "lon": 72.64, "species": ["Green sea turtle", "Manta ray"], "oil_slick": {"status": "clear", "area_km2": 0.0}, "ssh_anomaly_cm": 2.2},
    {"sector": "Andaman Sea", "lat": 11.62, "lon": 92.73, "species": ["Dugong", "Hawksbill turtle", "Manta ray"], "oil_slick": {"status": "clear", "area_km2": 0.0}, "ssh_anomaly_cm": 6.4},
    {"sector": "Great Nicobar", "lat": 7.03, "lon": 93.79, "species": ["Leatherback turtle", "Blue whale"], "oil_slick": {"status": "clear", "area_km2": 0.0}, "ssh_anomaly_cm": 7.1},
]


def _find_nearest_coastal_anchor(lat: float, lon: float) -> tuple[float, float]:
    """Find the nearest coastal marine anchor point for inland coordinates."""
    best = min(COASTAL_SECTOR_ANCHORS, key=lambda a: (a[1] - lat) ** 2 + (a[2] - lon) ** 2)
    return best[1], best[2]


def get_nearest_maritime_sector(latitude: float, longitude: float) -> dict:
    """Return the nearest Indian maritime sector intelligence baseline."""
    sector = min(
        MARITIME_SECTOR_DATA,
        key=lambda item: (item["lat"] - latitude) ** 2 + (item["lon"] - longitude) ** 2,
    )
    return {
        **sector,
        "source": "KyroX Indian maritime reference grid",
        "ssh_status": "baseline_anomaly",
        "ssh_unit": "cm",
    }


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
