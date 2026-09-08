# Backend/Agents/gps_agent.py
"""
GPS Agent for KyroX Marine Safety AI
Handles and validates the user's actual device GPS coordinates.
Strictly checks latitude (-90 to 90) and longitude (-180 to 180).
Produces a clean structured user location pin for frontend cartography.
Does not hardcode any city, default location, or fake coordinates.
"""
import logging
from typing import Union, Dict, Any

logger = logging.getLogger(__name__)


def gps_agent(
    latitude: Union[float, int],
    longitude: Union[float, int]
) -> Dict[str, Any]:
    """
    Validate device GPS coordinates and return standardized marker object.

    Args:
        latitude: float or int between -90.0 and 90.0
        longitude: float or int between -180.0 and 180.0

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
        ValueError: If coordinates are missing, non-numeric, or out of geographical bounds.
    """
    if latitude is None or longitude is None:
        raise ValueError("Latitude and longitude must be provided.")

    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid coordinate format: latitude='{latitude}', longitude='{longitude}' must be numeric.") from exc

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
