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
        logger.error(
            "Geospatial fetch failed for (%s, %s): %s",
            location.latitude,
            location.longitude,
            exc,
        )
        raise GeospatialAgentError("Unable to retrieve geospatial data") from exc

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
