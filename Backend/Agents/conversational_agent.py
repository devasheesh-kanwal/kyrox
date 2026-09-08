# backend/agents/conversational_agent.py
import json
import logging
import re

from backend.tools.huggingface_api import HuggingFaceAPIError, generate_chat_response

logger = logging.getLogger(__name__)

VALID_INTENTS = {
    "CHECK_SAFETY",
    "WEATHER_QUERY",
    "MARINE_QUERY",
    "BOUNDARY_WARNING",
    "EMERGENCY",
    "GENERAL_QUERY",
}

KYROX_SYSTEM_PROMPT = """KyroX is an AI-powered Marine Safety Assistant designed to help fishermen understand weather conditions, marine conditions, fishing safety, emergencies, and maritime boundary risks.

You must classify the user's message into exactly one intent:
- CHECK_SAFETY: overall safety / should I go out / is it safe to fish or sail
- WEATHER_QUERY: wind, waves, storms, lightning, rain, forecast
- MARINE_QUERY: sea state, SST, chlorophyll, fishing zones, currents, visibility
- BOUNDARY_WARNING: borders, EEZ, protected areas, restricted zones, maritime boundaries
- EMERGENCY: distress, man overboard, sinking, medical emergency, mayday, immediate danger
- GENERAL_QUERY: greetings, explanations, anything else

Return ONLY valid JSON with this exact shape and no markdown:
{"intent":"<ONE_OF_THE_INTENTS>","response":"<helpful assistant reply to the user>"}

The response should be practical, calm, and safety-focused. Do not invent live sensor readings.
"""


class ConversationalAgentError(Exception):
    """Raised when the conversational agent cannot produce a result."""


def conversational_agent(user_message: str) -> dict:
    """
    Send a user message to the Hugging Face LLM and return intent + reply.
    Invalid or unparseable model output defaults to GENERAL_QUERY.
    """
    if not isinstance(user_message, str) or not user_message.strip():
        return {
            "user_message": user_message if isinstance(user_message, str) else "",
            "intent": "GENERAL_QUERY",
            "response": "Please share a marine safety question so KyroX can help.",
        }

    cleaned_message = user_message.strip()

    try:
        raw = generate_chat_response(
            system_prompt=KYROX_SYSTEM_PROMPT,
            user_message=cleaned_message,
        )
    except HuggingFaceAPIError as exc:
        logger.error("Conversational LLM call failed: %s", type(exc).__name__)
        raise ConversationalAgentError("Unable to process the message with KyroX") from exc

    parsed = _parse_llm_payload(raw)
    intent = parsed.get("intent", "GENERAL_QUERY")
    if intent not in VALID_INTENTS:
        intent = "GENERAL_QUERY"

    response = parsed.get("response")
    if not isinstance(response, str) or not response.strip():
        response = (
            "I can help with marine safety, weather, fishing conditions, "
            "boundaries, and emergencies. Please tell me what you need."
        )

    return {
        "user_message": cleaned_message,
        "intent": intent,
        "response": response.strip(),
    }


def _parse_llm_payload(raw: str) -> dict:
    """Extract a JSON object from the model output; fail closed to GENERAL_QUERY."""
    if not raw:
        return {"intent": "GENERAL_QUERY", "response": ""}

    candidates = [raw.strip()]
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL | re.IGNORECASE)
    if fenced:
        candidates.insert(0, fenced.group(1).strip())
    braced = re.search(r"\{.*\}", raw, re.DOTALL)
    if braced:
        candidates.insert(0, braced.group(0).strip())

    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            intent = data.get("intent")
            if isinstance(intent, str):
                data["intent"] = intent.strip().upper()
            return data

    logger.warning("Conversational agent received unstructured LLM output; defaulting intent")
    return {
        "intent": "GENERAL_QUERY",
        "response": raw.strip(),
    }
