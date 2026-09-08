# backend/tools/opentopography_tools.py
import os
import logging
import math
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ========== SECURE ENV LOADING (No Hardcoded Keys!) ==========
OPEN_TOPOGRAPHY_KEY = os.getenv("OPEN_TOPOGRAPHY_KEY")
if not OPEN_TOPOGRAPHY_KEY:
    raise RuntimeError(" OPEN_TOPOGRAPHY_KEY environment variable is not set in .env")

OPEN_TOPOGRAPHY_URL = os.getenv("OPEN_TOPOGRAPHY_URL")
if not OPEN_TOPOGRAPHY_URL:
    raise RuntimeError(" OPEN_TOPOGRAPHY_URL environment variable is not set in .env")
#  IMPORTANT: Your .env URL MUST be: https://portal.opentopography.org/API/globaldem
# NOT: https://opentopography.org/developers (that's just the docs page!)

REQUEST_TIMEOUT = httpx.Timeout(15.0, connect=5.0)  # DEM data can be heavy, giving 15s


async def fetch_dem_data(latitude: float, longitude: float):
    """
    Async tool to fetch Digital Elevation Model (DEM) data from OpenTopography.
    Uses .env for API key and URL, and httpx for non-blocking requests.
    Returns elevation metrics useful for hill/landslide risk analysis.
    """
    # --- Input Validation (Security: prevents injection/bad data) ---
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        raise ValueError("Latitude and Longitude must be numeric")
    if not (-90 <= latitude <= 90):
        raise ValueError("Latitude out of range (-90 to 90)")
    if not (-180 <= longitude <= 180):
        raise ValueError("Longitude out of range (-180 to 180)")

    # --- Build Bounding Box (approx 1km x 1km box) ---
    # 0.01 degree ≈ 1.1km, which is great for local hill analysis
    delta = 0.01
    params = {
        "demtype": "SRTMGL3",              # 30m resolution (best for hills)
        "south": latitude - delta,
        "north": latitude + delta,
        "west": longitude - delta,
        "east": longitude + delta,
        "outputFormat": "PointCloud",      # Returns JSON instead of heavy GeoTIFF
        "API_Key": OPEN_TOPOGRAPHY_KEY,    #  Loaded securely from .env
    }

    # Headers to identify ourselves (good API etiquette)
    headers = {
        "User-Agent": "ORCA-Marine-Hill-SIH2026/1.0 (Contact: team@kyrox.ai)"
    }

    try:
        logger.debug(f" Fetching DEM for Lat: {latitude}, Lon: {longitude}")
        
        # Async request with explicit timeout (prevents hanging/DoS)
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(OPEN_TOPOGRAPHY_URL, params=params, headers=headers)

    except httpx.RequestError as exc:
        # Don't leak internal exceptions to the caller; log server-side only
        logger.error("OpenTopography API request failed: %s", exc)
        raise Exception("Failed to reach OpenTopography API") from exc

    # --- Handle Response ---
    if response.is_success:
        try:
            data = response.json()
            logger.debug("Received PointCloud JSON with %d keys", len(data))
            
            # Parse the PointCloud response
            # Usually returns: {"pointcloud": [[lat, lon, elev], ...]}
            points = data.get("pointcloud", [])
            if not points:
                logger.warning("No elevation points returned for this area")
                return {
                    "mean_elevation_m": None,
                    "slope_estimate_deg": None,
                    "point_count": 0,
                    "risk_factor": 0.0
                }

            # Extract elevations (3rd column)
            elevations = [p[2] for p in points if len(p) >= 3]
            if not elevations:
                raise ValueError("Invalid PointCloud format received")

            # Calculate metrics
            mean_elev = sum(elevations) / len(elevations)
            max_elev = max(elevations)
            min_elev = min(elevations)
            elev_range = max_elev - min_elev
            
            # Rough Slope Estimate (if range > 0 and box is ~1km)
            # Slope (degrees) = arctan(Rise / Run). Run ≈ 1.1km
            run_meters = 1100  # ~1km in meters
            slope_rad = math.atan(elev_range / run_meters) if elev_range > 0 else 0
            slope_deg = math.degrees(slope_rad)

            # Simple Risk Factor (0 to 1) for landslides
            # Higher slope = higher risk. Slope > 25° is high risk.
            risk_factor = min(slope_deg / 45.0, 1.0) if slope_deg > 0 else 0.0

            logger.info(f" DEM Fetched: Mean Elev: {mean_elev:.1f}m, Slope: {slope_deg:.1f}°")
            
            return {
                "mean_elevation_m": round(mean_elev, 2),
                "slope_estimate_deg": round(slope_deg, 2),
                "elevation_range_m": round(elev_range, 2),
                "point_count": len(elevations),
                "risk_factor": round(risk_factor, 3)  # 0=low risk, 1=high risk
            }

        except (ValueError, KeyError, IndexError) as parse_err:
            logger.error("Failed to parse OpenTopography JSON response: %s", parse_err)
            raise Exception("Invalid data format received from OpenTopography") from parse_err

    else:
        # Log full details server-side only; NEVER echo raw response body 
        # (might contain error traces or reflected parameters)
        logger.error("OpenTopography API error %s: %s", response.status_code, response.text[:200])
        raise Exception(f"OpenTopography API request failed with status {response.status_code}")


# ---------- Example Usage (Test this file directly) ----------
if __name__ == "__main__":
    import asyncio

    async def test():
        try:
            # Test for Nainital (Uttarakhand hills)
            result = await fetch_dem_data(latitude=29.39, longitude=79.45)
            print("Hill Analysis Result:")
            print(result)
        except Exception as e:
            print(f" Error: {e}")

    asyncio.run(test())