# Backend/Agents/geospatial_agent.py
"""
Geospatial Agent - protected / restricted marine areas near the vessel.

When OpenStreetMap cannot be reached the agent says so (`data_available:
False`) so the consensus agent can flag the gap; it never reports "no
restrictions" for a check that did not run.
"""
import logging

from Models.schemas import Location
from Tools.geospatial import get_geospatial

logger = logging.getLogger(__name__)


class GeospatialAgentError(Exception):
    """Raised when geospatial data cannot be retrieved or parsed."""


async def geospatial_agent(location: Location) -> dict:
    try:
        return await get_geospatial(latitude=location.latitude, longitude=location.longitude)
    except ValueError as exc:
        raise GeospatialAgentError(str(exc)) from exc
