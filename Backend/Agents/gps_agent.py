# Backend/Agents/gps_agent.py
"""
GPS Agent for KyroX Marine Safety AI
Handles and validates the user's actual device GPS coordinates.
Strictly checks latitude (-90 to 90) and longitude (-180 to 180).
Produces a clean structured user location pin for frontend cartography.
Does not hardcode any city, default location, or fake coordinates.
"""
import math
import logging
from typing import Union, Dict, Any

logger = logging.getLogger(__name__)


def gps_agent(
    latitude: Union[float, int, Any] = None,
    longitude: Union[float, int] = None
) -> Dict[str, Any]:
    """
    Validate device GPS coordinates and return standardized marker object.

    Can be called as:
      - gps_agent(latitude, longitude)
      - gps_agent(location_object)  (e.g., Location model or dict with latitude/longitude)

    Args:
        latitude: float or int between -90.0 and 90.0, or a Location/dict object
        longitude: float or int between -180.0 and 180.0 (if latitude is numeric)

    Returns:
        Structured dictionary representing the user's current location pin:
        {
            "id": "user_location",
            "name": "Your Current Location",
            "latitude": float,
            "longitude": float,
            "type": "CURRENT_LOCATION",
            "marker_type": "USER"
        }

    Raises:
        ValueError: If coordinates are missing, non-numeric, non-finite, or out of geographical bounds.
    """
    raw_lat = latitude
    raw_lon = longitude

    # Support Location object or dict passed as first positional parameter
    if hasattr(raw_lat, "latitude") and hasattr(raw_lat, "longitude"):
        raw_lon = getattr(raw_lat, "longitude")
        raw_lat = getattr(raw_lat, "latitude")
    elif isinstance(raw_lat, dict) and "latitude" in raw_lat and "longitude" in raw_lat:
        raw_lon = raw_lat.get("longitude")
        raw_lat = raw_lat.get("latitude")

    if raw_lat is None or raw_lon is None:
        raise ValueError("Latitude and longitude must be provided.")

    try:
        lat = float(raw_lat)
        lon = float(raw_lon)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid coordinate format: latitude='{raw_lat}', longitude='{raw_lon}' must be numeric.") from exc

    if not math.isfinite(lat) or not math.isfinite(lon):
        raise ValueError(f"Coordinates must be finite numbers (got lat={lat}, lon={lon}).")

    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"Latitude {lat} out of range. Must be between -90.0 and 90.0.")

    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"Longitude {lon} out of range. Must be between -180.0 and 180.0.")

    location_data = {
        "id": "user_location",
        "name": "Your Current Location",
        "latitude": round(lat, 6),
        "longitude": round(lon, 6),
        "type": "CURRENT_LOCATION",
        "marker_type": "USER"
    }

    logger.info("GPS Agent verified coordinates: lat=%.6f, lon=%.6f", lat, lon)
    return location_data
