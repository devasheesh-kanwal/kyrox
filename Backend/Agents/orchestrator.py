# backend/agents/orchestrator.py
import asyncio
import logging
from typing import Optional, Union

from Agents.conversational_agent import conversational_agent
from Agents.weather_agent import weather_agent
from Agents.marine_agent import marine_agent
from Agents.geospatial_Agent import geospatial_agent
from Agents.recommendation_agent import recommendation_agent
from Models.schemas import Location

logger = logging.getLogger(__name__)

INTENT_NEXT_ACTION = {
    "CHECK_SAFETY": "weather_marine_geospatial_risk",
    "WEATHER_QUERY": "weather_agent",
    "MARINE_QUERY": "marine_agent",
    "BOUNDARY_WARNING": "geospatial_agent",
    "EMERGENCY": "emergency_alert_service",
    "GENERAL_QUERY": "conversational_response",
}


def calculate_risk(marine: dict, weather: dict, geospatial: dict) -> dict:
    """Calculate marine risk score and reasons deterministically."""
    score = 0
    reasons = []

    wave_h = float(marine.get("wave_height") or weather.get("wave_height") or 0.0)
    wind_spd = float(weather.get("wind_speed") or 0.0)

    # Wave height risk
    if wave_h >= 3.5:
        score += 50
        reasons.append(f"Severe wave height ({wave_h:.1f}m)")
    elif wave_h >= 2.5:
        score += 35
        reasons.append(f"Rough sea swell ({wave_h:.1f}m)")
    elif wave_h >= 1.8:
        score += 20
        reasons.append(f"Moderate wave height ({wave_h:.1f}m)")

    # Wind speed risk
    if wind_spd >= 35.0:
        score += 45
        reasons.append(f"Severe gale wind speed ({wind_spd:.1f} kts)")
    elif wind_spd >= 25.0:
        score += 30
        reasons.append(f"Strong sustained winds ({wind_spd:.1f} kts)")
    elif wind_spd >= 18.0:
        score += 15
        reasons.append(f"Brisk winds ({wind_spd:.1f} kts)")

    # Lightning & storm risk
    if weather.get("lightning_risk") == "HIGH":
        score += 40
        reasons.append("Active lightning detected in sector")

    if weather.get("storm_risk") == "HIGH":
        score += 50
        reasons.append("Squall or storm front detected")

    # Geospatial protected area / boundary risk
    if geospatial.get("inside_protected_area") or geospatial.get("restricted_zone"):
        score += 50
        reasons.append("Vessel is inside a restricted or marine sanctuary zone")
    elif geospatial.get("near_boundary"):
        score += 25
        reasons.append("Vessel is operating close to restricted boundary")

    # Final Risk Tier
    if score >= 80:
        risk_level = "CRITICAL"
    elif score >= 60:
        risk_level = "HIGH"
    elif score >= 35:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "risk_score": min(score, 100),
        "risk_level": risk_level,
        "reasons": reasons,
    }


async def orchestrate(
    user_message: str,
    location: Optional[Union[Location, dict]] = None,
) -> dict:
    """
    Full end-to-end multi-agent orchestrator:
    1. Runs conversational_agent to extract user intent.
    2. Runs weather_agent, marine_agent, and geospatial_agent concurrently.
    3. Calculates deterministic risk assessment.
    4. Runs recommendation_agent for safety action, actionable tips, and LLM advice.
    5. Returns fully unified multi-agent telemetry and recommendation response.
    """
    conversation = conversational_agent(user_message)
    intent = conversation.get("intent") or "GENERAL_QUERY"

    # Default to standard vessel coordinate if not provided (Goa/Karwar waters)
    if location is None:
        loc_obj = Location(latitude=15.41, longitude=73.80)
    elif isinstance(location, dict):
        loc_obj = Location(**location)
    else:
        loc_obj = location

    # Run domain agents concurrently
    marine_task = marine_agent(loc_obj)
    weather_task = weather_agent(loc_obj)
    geo_task = geospatial_agent(loc_obj)

    results = await asyncio.gather(
        marine_task,
        weather_task,
        geo_task,
        return_exceptions=True,
    )

    marine_data = results[0] if not isinstance(results[0], Exception) else {
        "wave_height": 1.2,
        "sea_surface_temperature": 28.2,
        "ocean_current_velocity": 1.1,
    }
    weather_res = results[1] if not isinstance(results[1], Exception) else None
    geo_data = results[2] if not isinstance(results[2], Exception) else {
        "inside_protected_area": False,
        "restricted_zone": False,
        "near_boundary": False,
        "restrictions": [],
    }

    if hasattr(weather_res, "model_dump"):
        weather_data = weather_res.model_dump()
    elif isinstance(weather_res, dict):
        weather_data = weather_res
    else:
        weather_data = {
            "wind_speed": 12.0,
            "wave_height": float(marine_data.get("wave_height") or 1.2),
            "lightning_risk": "LOW",
            "storm_risk": "LOW",
        }

    # Cross-fill wave height from marine if weather had 0.0
    if not weather_data.get("wave_height") and marine_data.get("wave_height"):
        weather_data["wave_height"] = marine_data["wave_height"]

    # Calculate Risk
    risk_assessment = calculate_risk(marine_data, weather_data, geo_data)

    # Recommendation Agent Integration
    recommendation = await recommendation_agent(
        risk_data=risk_assessment,
        weather_data=weather_data,
        marine_data=marine_data,
        geo_data=geo_data,
    )

    # Attach UI helper fields
    recommendation["alerts"] = risk_assessment.get("reasons", [])
    if risk_assessment["risk_level"] in ("HIGH", "CRITICAL"):
        recommendation["map_layers"] = ["Weather Warnings", "Protected Areas"]
    elif risk_assessment["risk_level"] == "MEDIUM":
        recommendation["map_layers"] = ["Wind", "Waves", "Marine Conditions"]
    else:
        recommendation["map_layers"] = ["Sea Surface Temperature", "Chlorophyll", "PFZ"]

    logger.info(
        "Orchestrator completed: intent=%s, risk_level=%s, action=%s",
        intent,
        risk_assessment["risk_level"],
        recommendation.get("action"),
    )

    return {
        "user_message": user_message,
        "intent": intent,
        "conversation": conversation,
        "location": {"latitude": loc_obj.latitude, "longitude": loc_obj.longitude},
        "marine_data": marine_data,
        "weather_data": weather_data,
        "geospatial_data": geo_data,
        "risk_assessment": risk_assessment,
        "recommendation": recommendation,
    }


def orchestrator(user_message: str, location: Optional[Union[Location, dict]] = None) -> dict:
    """Synchronous entry point that runs the async orchestrate coroutine."""
    try:
        return asyncio.run(orchestrate(user_message, location))
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(orchestrate(user_message, location))
