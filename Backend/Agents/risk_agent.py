# Backend/Agents/risk_agent.py
"""
Risk Agent & Dynamic Heatmap Generator for KyroX Marine Safety AI.
Constructs a geographic 3x3 risk grid centered around the user's verified GPS coordinates.
For each grid point:
    Location -> Weather Agent + Marine Agent + Geospatial Agent -> Deterministic Risk Calculation -> Risk Score (0-100)
Does not generate fake or random risk scores.
Evaluates all grid cells concurrently and caches evaluations to optimize API throughput.
"""
import asyncio
import logging
import time
import os
import sys
from typing import List, Dict, Any, Tuple, Optional

# Ensure Backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Models.schemas import Location
from Agents.gps_agent import gps_agent
from Agents.marine_agent import marine_agent
from Agents.weather_agent import weather_agent
from Agents.geospatial_Agent import geospatial_agent
from Agents.orchestrator import calculate_risk

logger = logging.getLogger(__name__)

# Default geographic step distance for 3x3 grid (~0.035 degrees ≈ 3.8 km at coastal latitudes)
GRID_STEP_DEG = 0.035

# In-memory TTL Cache for evaluated coordinates to avoid redundant upstream calls
# Key: "round(lat, 3)_round(lon, 3)" -> (timestamp, evaluation_result)
_RISK_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 600.0  # 10 minutes


def _cache_key(lat: float, lon: float) -> str:
    return f"{round(lat, 3):.3f}_{round(lon, 3):.3f}"


def generate_3x3_coordinates(
    center_lat: float,
    center_lon: float,
    step: float = GRID_STEP_DEG
) -> List[Tuple[float, float]]:
    """
    Generate 3x3 geographic coordinates with the user at the exact center (P5).

    Layout:
        P1 (North-West)    P2 (North)    P3 (North-East)
        P4 (West)          USER (Center) P6 (East)
        P7 (South-West)    P8 (South)    P9 (South-East)
    """
    lat_offsets = [step, 0.0, -step]
    lon_offsets = [-step, 0.0, step]

    points = []
    for d_lat in lat_offsets:
        for d_lon in lon_offsets:
            pt_lat = max(-90.0, min(90.0, center_lat + d_lat))
            pt_lon = max(-180.0, min(180.0, center_lon + d_lon))
            points.append((round(pt_lat, 6), round(pt_lon, 6)))

    return points


async def evaluate_risk_point(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Concurrently query real Weather, Marine, and Geospatial APIs for a coordinate,
    and compute deterministic risk via calculate_risk.
    """
    ckey = _cache_key(latitude, longitude)
    now = time.time()

    if ckey in _RISK_CACHE:
        cached_time, cached_data = _RISK_CACHE[ckey]
        if now - cached_time < CACHE_TTL_SECONDS:
            return cached_data

    loc = Location(latitude=latitude, longitude=longitude)

    # Concurrently evaluate real environment conditions for this location
    try:
        marine_res, weather_res, geo_res = await asyncio.gather(
            marine_agent(loc),
            weather_agent(loc),
            geospatial_agent(loc),
            return_exceptions=True
        )
    except Exception as exc:
        logger.warning("Agent gather error for point (%.4f, %.4f): %s", latitude, longitude, exc)
        marine_res, weather_res, geo_res = {}, {}, {}

    if isinstance(marine_res, Exception):
        logger.warning("Marine agent failed for (%.4f, %.4f): %s", latitude, longitude, marine_res)
        m_data = {}
    elif hasattr(marine_res, "model_dump"):
        m_data = marine_res.model_dump()
    elif isinstance(marine_res, dict):
        m_data = marine_res
    else:
        m_data = {}

    if isinstance(weather_res, Exception):
        logger.warning("Weather agent failed for (%.4f, %.4f): %s", latitude, longitude, weather_res)
        w_data = {}
    elif hasattr(weather_res, "model_dump"):
        w_data = weather_res.model_dump()
    elif isinstance(weather_res, dict):
        w_data = weather_res
    else:
        w_data = {}

    if isinstance(geo_res, Exception):
        logger.warning("Geospatial agent failed for (%.4f, %.4f): %s", latitude, longitude, geo_res)
        g_data = {}
    elif hasattr(geo_res, "model_dump"):
        g_data = geo_res.model_dump()
    elif isinstance(geo_res, dict):
        g_data = geo_res
    else:
        g_data = {}

    # Cross-fill wave height from marine if weather has 0
    if not w_data.get("wave_height") and m_data.get("wave_height"):
        w_data["wave_height"] = m_data["wave_height"]

    # Calculate deterministic risk using verified rules
    risk_assessment = calculate_risk(
        marine=m_data,
        weather=w_data,
        geospatial=g_data,
        intent="CHECK_SAFETY",
        user_message=""
    )

    risk_score = float(risk_assessment.get("risk_score", 0))
    risk_level = risk_assessment.get("risk_level", "LOW")

    result = {
        "latitude": latitude,
        "longitude": longitude,
        "risk": round(risk_score, 1),
        "risk_level": risk_level,
    }

    _RISK_CACHE[ckey] = (now, result)
    return result


async def generate_risk_heatmap(
    latitude: float,
    longitude: float,
    step: float = GRID_STEP_DEG
) -> Dict[str, Any]:
    """
    Generate the complete 3x3 risk heatmap centered on user's verified GPS position.

    Returns:
        {
            "user_location": {"latitude": ..., "longitude": ...},
            "risk_points": [
                {"latitude": ..., "longitude": ..., "risk": ..., "risk_level": ...},
                ... (9 points)
            ]
        }
    """
    # 1. Validate coordinates strictly with GPS Agent
    gps_info = gps_agent(latitude, longitude)
    center_lat = gps_info["latitude"]
    center_lon = gps_info["longitude"]

    # 2. Build 3x3 grid coordinates
    grid_coords = generate_3x3_coordinates(center_lat, center_lon, step=step)

    # 3. Concurrently evaluate all 9 points across domain agents
    tasks = [evaluate_risk_point(pt_lat, pt_lon) for pt_lat, pt_lon in grid_coords]
    evaluated = await asyncio.gather(*tasks, return_exceptions=True)

    risk_points = []
    for idx, result in enumerate(evaluated):
        if isinstance(result, dict) and "risk" in result:
            risk_points.append(result)
        else:
            logger.warning(
                "Skipping heatmap cell %s at %s: %s",
                idx + 1,
                grid_coords[idx],
                result,
            )

    logger.info(
        "Generated 3x3 risk heatmap for user at (%.4f, %.4f) with %d points",
        center_lat,
        center_lon,
        len(risk_points)
    )

    return {
        "user_location": {
            "latitude": center_lat,
            "longitude": center_lon
        },
        "risk_points": list(risk_points)
    }
