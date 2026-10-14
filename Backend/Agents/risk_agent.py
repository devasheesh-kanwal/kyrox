# Backend/Agents/risk_agent.py
"""
Risk Agent - scores many sea cells at once for the heatmap and route planner.

Previously each heatmap refresh made 27 separate upstream calls (9 points x
3 agents), which got the app rate-limited. Cells are now fetched in batched
multi-point requests (2 calls for a whole grid) and scored with the same
deterministic `calculate_risk` used for the chat advisory, including the
12 h look-ahead. Land / no-coverage cells are returned as None - never as
"safe".
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

from Agents.geospatial_agent import geospatial_agent
from Agents.gps_agent import gps_agent
from Agents.orchestrator import calculate_risk
from Models.schemas import Location
from Tools.marine_tools import get_marine_grid
from Tools.openmeteo_weather import get_weather_grid

logger = logging.getLogger(__name__)

GRID_STEP_DEG = 0.035


def generate_3x3_coordinates(center_lat: float, center_lon: float, step: float = GRID_STEP_DEG) -> List[Tuple[float, float]]:
    """3x3 grid with the user at the centre (row-major, north to south, west to east)."""
    points = []
    for d_lat in (step, 0.0, -step):
        for d_lon in (-step, 0.0, step):
            lat = max(-90.0, min(90.0, center_lat + d_lat))
            lon = ((center_lon + d_lon + 180.0) % 360.0) - 180.0
            points.append((round(lat, 6), round(lon, 6)))
    return points


def score_cell(marine: Optional[dict], weather: Optional[dict], geo: Optional[dict] = None) -> Optional[Dict[str, Any]]:
    """Score one grid cell from batched grid data. Returns None for land / no data."""
    if marine is None:
        return None
    weather = weather or {}
    m = {
        "wave_height": marine.get("wave_height"),
        "swell_wave_height": marine.get("swell_wave_height"),
        "sea_surface_temperature": marine.get("sea_surface_temperature"),
        "forecast_12h": {"wave_height_max": marine.get("wave_height_max_12h")},
    }
    w = {
        "wind_speed": weather.get("wind_speed"),
        "wind_gusts": weather.get("wind_gusts"),
        "forecast_12h": {
            "wind_speed_max": weather.get("wind_speed_max_12h"),
            "wind_gusts_max": weather.get("wind_gusts_max_12h"),
        },
    }
    code = weather.get("weather_code")
    if code in (95, 96, 99):
        w["lightning_risk"] = "HIGH"
        w["storm_risk"] = "HIGH"
    risk = calculate_risk(m, w, geo or {})
    return {
        "risk": float(risk["risk_score"]),
        "risk_level": risk["risk_level"],
        "reasons": risk["reasons"],
        "confidence": risk.get("confidence"),
        "wave_height": m["wave_height"],
        "wave_height_max_12h": marine.get("wave_height_max_12h"),
        "swell_height": m["swell_wave_height"],
        "wind_speed": w["wind_speed"],
        "wind_speed_max_12h": weather.get("wind_speed_max_12h"),
        "sst": m["sea_surface_temperature"],
    }


async def score_points(points: List[Tuple[float, float]]) -> List[Optional[Dict[str, Any]]]:
    marine_cells, weather_cells = await asyncio.gather(get_marine_grid(points), get_weather_grid(points))
    return [score_cell(m, w) for m, w in zip(marine_cells, weather_cells)]


async def generate_risk_heatmap(latitude: float, longitude: float, step: float = GRID_STEP_DEG) -> Dict[str, Any]:
    """3x3 risk grid around the verified position; only cells with real data are returned."""
    gps_info = gps_agent(latitude, longitude)
    center_lat, center_lon = gps_info["latitude"], gps_info["longitude"]
    grid = generate_3x3_coordinates(center_lat, center_lon, step=step)

    scored, center_geo = await asyncio.gather(
        score_points(grid),
        geospatial_agent(Location(latitude=center_lat, longitude=center_lon)),
        return_exceptions=True,
    )
    if isinstance(scored, Exception):
        raise scored
    restricted_here = (
        not isinstance(center_geo, Exception)
        and bool(center_geo.get("restricted_zone") or center_geo.get("inside_protected_area"))
    )

    risk_points = []
    for idx, ((lat, lon), cell) in enumerate(zip(grid, scored)):
        if cell is None:
            continue
        restricted = restricted_here and idx == 4
        level = cell["risk_level"]
        wave, swell, wind, sst = cell["wave_height"], cell["swell_height"], cell["wind_speed"], cell["sst"]
        hazard = level in {"HIGH", "CRITICAL"} or (wave or 0) >= 2.0 or (swell or 0) >= 2.0 or (wind or 0) >= 25
        caution = not hazard and (level == "MEDIUM" or (wave or 0) >= 1.2 or (swell or 0) >= 1.2 or (wind or 0) >= 18)
        # "Suitable" = calm and safe now and over the next 12 h. It is a safety
        # suitability flag, NOT a fish-availability (PFZ) forecast.
        suitable = not restricted and not hazard and not caution and sst is not None and wave is not None
        risk_points.append({
            "latitude": lat,
            "longitude": lon,
            **cell,
            "restricted": restricted,
            "zone_type": "hazard" if hazard else ("caution" if caution else ("calm" if suitable else None)),
            "zone_label": "Hazard" if hazard else ("Caution" if caution else ("Calm sea (safety only)" if suitable else None)),
        })

    logger.info("Heatmap at (%.4f, %.4f): %d/9 sea cells", center_lat, center_lon, len(risk_points))
    return {"user_location": {"latitude": center_lat, "longitude": center_lon}, "risk_points": risk_points}
