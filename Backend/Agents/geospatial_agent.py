# Backend/Agents/geospatial_Agent.py
import logging

from Models.schemas import Location, GeoData
from Tools.geospatial import get_geospatial

logger = logging.getLogger(__name__)


class GeospatialAgentError(Exception):
    """Raised when geospatial data cannot be retrieved or parsed."""


async def geospatial_agent(location: Location) -> dict:
    """
    Fetch protected-area / shoreline context for a location.

    Returns a dict compatible with the orchestrator in main.py, after validating
    the core fields against GeoData.
    """
    try:
        data = await get_geospatial(
            latitude=location.latitude,
            longitude=location.longitude,
        )
    except Exception as exc:
        logger.warning(
            "Geospatial remote fetch failed for (%s, %s): %s; falling back to local sanctuary & boundary rules",
            location.latitude,
            location.longitude,
            exc,
        )
        return _local_geospatial_check(location.latitude, location.longitude)

    geo = GeoData(
        near_boundary=bool(data.get("near_boundary")),
        distance_to_boundary_meters=float(data.get("distance_to_boundary_meters", 0.0)),
        restricted_zone=bool(data.get("restricted_zone")),
        distance_to_shore_meters=data.get("distance_to_shore_meters"),
    )

    restrictions = data.get("restrictions") or []
    if geo.restricted_zone and not restrictions:
        restrictions = ["Location is inside a restricted or protected area"]
    elif geo.near_boundary and not restrictions:
        restrictions = ["Location is near a protected-area boundary"]

    return {
        "inside_protected_area": bool(
            data.get("inside_protected_area") or geo.restricted_zone
        ),
        "restrictions": restrictions,
        "near_boundary": geo.near_boundary,
        "distance_to_boundary_meters": geo.distance_to_boundary_meters,
        "restricted_zone": geo.restricted_zone,
        "distance_to_shore_meters": geo.distance_to_shore_meters,
    }


def _local_geospatial_check(lat: float, lon: float) -> dict:
    restrictions = []
    inside_protected_area = False
    restricted_zone = False
    near_boundary = False
    dist_boundary = 10000.0

    # Malvan Marine Sanctuary (Lat 16.02 - 16.10, Lon 73.42 - 73.52)
    if 16.02 <= lat <= 16.10 and 73.42 <= lon <= 73.52:
        inside_protected_area = True
        restricted_zone = True
        dist_boundary = 0.0
        restrictions.append("Malvan Marine Sanctuary: Bottom trawling strictly prohibited")
    # Netrani Island Reserve (Lat 13.98 - 14.06, Lon 74.28 - 74.37)
    elif 13.98 <= lat <= 14.06 and 74.28 <= lon <= 74.37:
        inside_protected_area = True
        restricted_zone = True
        dist_boundary = 0.0
        restrictions.append("Netrani Island Coral Reserve: Protected marine area")
    # Mormugao Port Fairway (Lat 15.39 - 15.45, Lon 73.74 - 73.83)
    elif 15.39 <= lat <= 15.45 and 73.74 <= lon <= 73.83:
        restrictions.append("Commercial Shipping Channel: Keep continuous VHF CH 16 watch")

    return {
        "inside_protected_area": inside_protected_area,
        "restrictions": restrictions,
        "near_boundary": near_boundary,
        "distance_to_boundary_meters": dist_boundary,
        "restricted_zone": restricted_zone,
        "distance_to_shore_meters": 5000.0,
    }

