# backend/agents/orchestrator.py
import logging

from backend.agents.conversational_agent import conversational_agent

logger = logging.getLogger(__name__)

# Placeholder routing only. Do not import or run domain agents here yet.
INTENT_NEXT_ACTION = {
    "CHECK_SAFETY": "weather_marine_geospatial_risk",
    "WEATHER_QUERY": "weather_agent",
    "MARINE_QUERY": "marine_agent",
    "BOUNDARY_WARNING": "geospatial_agent",
    "EMERGENCY": "emergency_alert_service",
    "GENERAL_QUERY": "conversational_response",
}

INTENT_PLACEHOLDER_RESULT = {
    "CHECK_SAFETY": (
        "Future action: run weather_agent, marine_agent, geospatial_agent, "
        "and risk_agent, then recommendation_agent."
    ),
    "WEATHER_QUERY": "Future action: run weather_agent.",
    "MARINE_QUERY": "Future action: run marine_agent.",
    "BOUNDARY_WARNING": "Future action: run geospatial_agent.",
    "EMERGENCY": "Future action: run emergency handling / alert service.",
    "GENERAL_QUERY": "Future action: conversational response only.",
}


def orchestrator(user_message: str) -> dict:
    """
    Run the conversational agent first, then decide the next backend action
    from the classified intent. Domain agents are not executed yet.
    """
    conversation = conversational_agent(user_message)
    intent = conversation.get("intent") or "GENERAL_QUERY"
    if intent not in INTENT_NEXT_ACTION:
        intent = "GENERAL_QUERY"

    next_action = INTENT_NEXT_ACTION[intent]
    if intent == "GENERAL_QUERY":
        result = conversation.get("response") or INTENT_PLACEHOLDER_RESULT[intent]
    else:
        result = INTENT_PLACEHOLDER_RESULT[intent]

    logger.info("Orchestrator routed intent=%s next_action=%s", intent, next_action)

    return {
        "conversation": conversation,
        "intent": intent,
        "next_action": next_action,
        "result": result,
    }
