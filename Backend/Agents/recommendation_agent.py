# Backend/Agents/recommendation_agent.py
"""
LLM-powered Recommendation Agent for the KyroX Marine Safety System.

Responsibility:
  - Receive VERIFIED risk, weather, marine, and geospatial data.
  - Determine the safety ACTION deterministically in Python.
  - Use the existing Hugging Face LLM to generate a human-friendly
    explanation and recommendations.
  - The LLM MUST NOT calculate, modify, or override the risk score
    or the deterministic action.
"""
import asyncio
import json
import logging
import re

from Tools.huggingface_api import HuggingFaceAPIError, generate_chat_response

logger = logging.getLogger(__name__)

# =========================================================
# DETERMINISTIC ACTION MAP
# =========================================================
# The LLM is never allowed to override these mappings.
_RISK_LEVEL_TO_ACTION: dict[str, str] = {
    "LOW": "SAFE",
    "MEDIUM": "PROCEED_WITH_CAUTION",
    "HIGH": "RETURN_TO_SHORE",
    "CRITICAL": "DO_NOT_PROCEED",
}

_VALID_ACTIONS = set(_RISK_LEVEL_TO_ACTION.values())

# =========================================================
# LLM SYSTEM PROMPT
# =========================================================
_SYSTEM_PROMPT = """\
You are KyroX, an AI-powered Marine Safety Assistant for fishermen.

Your job is to convert verified weather, marine, geospatial, and risk \
analysis data into simple, practical safety recommendations.

Never invent measurements or conditions.
Never change the provided risk score or risk level.
Never contradict the deterministic safety action.
Prioritize human safety.
Explain the main risks clearly.
Use simple and direct language suitable for fishermen.
When risk is HIGH or CRITICAL, provide urgent and clear safety advice.
Only use information supplied in the verified data.

Return ONLY valid JSON with this exact shape and no markdown fences:
{"message":"<brief safety summary>","recommendations":["<tip 1>","<tip 2>"],"explanation":"<why these conditions matter>"}
"""

# Cap on the user-message payload sent to the LLM (chars).
_MAX_DATA_PAYLOAD_CHARS = 3000


class RecommendationAgentError(Exception):
    """Raised when the recommendation agent encounters an unrecoverable error."""


# =========================================================
# PUBLIC INTERFACE
# =========================================================
async def recommendation_agent(
    risk_data: dict,
    weather_data: dict,
    marine_data: dict,
    geo_data: dict,
) -> dict:
    """
    Generate a safety recommendation for the vessel.

    1. Determines the safety **action** deterministically from risk_level.
    2. Calls the Hugging Face LLM (if configured) for plain-language advice.
    3. Otherwise returns rule-based advice built only from verified values.

    Returns dict with: action, message, recommendations, explanation,
    confidence, mode ("llm" | "rules").
    """
    risk_data = risk_data if isinstance(risk_data, dict) else {}
    weather_data = weather_data if isinstance(weather_data, dict) else {}
    marine_data = marine_data if isinstance(marine_data, dict) else {}
    geo_data = geo_data if isinstance(geo_data, dict) else {}

    action = _determine_action(risk_data)
    llm_output = await _query_llm(
        action=action,
        risk_data=risk_data,
        weather_data=weather_data,
        marine_data=marine_data,
        geo_data=geo_data,
    )
    return {
        "action": action,
        "message": llm_output.get("message", ""),
        "recommendations": llm_output.get("recommendations", []),
        "explanation": llm_output.get("explanation", ""),
        "confidence": risk_data.get("confidence", "medium"),
        "mode": llm_output.get("mode", "rules"),
    }


# =========================================================
# DETERMINISTIC LOGIC
# =========================================================
def _determine_action(risk_data: dict) -> str:
    """
    Map the verified risk_level to a deterministic safety action.
    Defaults to RETURN_TO_SHORE if risk_level is missing or unrecognized
    (fail-safe: assume conditions are dangerous).
    """
    risk_level = risk_data.get("risk_level")
    if isinstance(risk_level, str):
        risk_level = risk_level.strip().upper()

    action = _RISK_LEVEL_TO_ACTION.get(risk_level)
    if action is None:
        logger.warning(
            "Unrecognized risk_level %r - defaulting to RETURN_TO_SHORE",
            risk_level,
        )
        action = "RETURN_TO_SHORE"

    return action


# =========================================================
# LLM INTERACTION
# =========================================================
async def _query_llm(
    action: str,
    risk_data: dict,
    weather_data: dict,
    marine_data: dict,
    geo_data: dict,
) -> dict:
    """
    Build a data payload and call the existing Hugging Face LLM.
    Returns a dict with message, recommendations, explanation.
    On ANY failure, returns the deterministic fallback.
    """
    fallback = _get_fallback(
        action=action,
        risk_data=risk_data,
        weather_data=weather_data,
        marine_data=marine_data,
        geo_data=geo_data,
    )

    # Build the user message with all verified data
    user_message = _build_user_message(
        action=action,
        risk_data=risk_data,
        weather_data=weather_data,
        marine_data=marine_data,
        geo_data=geo_data,
    )

    try:
        raw = await asyncio.wait_for(
            asyncio.to_thread(
                generate_chat_response,
                _SYSTEM_PROMPT,
                user_message,
            ),
            # Keep the interactive safety response responsive. The deterministic
            # fallback is already grounded in the verified live measurements.
            timeout=6.0,
        )
    except asyncio.TimeoutError:
        logger.warning("Recommendation LLM timed out; using live-data fallback")
        return fallback
    except (HuggingFaceAPIError, RuntimeError) as exc:
        logger.error("Recommendation LLM call failed: %s", exc)
        return fallback
    except Exception as exc:
        logger.error("Recommendation agent LLM call failed unexpectedly: %s", exc)
        return fallback

    # Parse the LLM's JSON response
    parsed = _parse_llm_json(raw)
    if parsed is None:
        logger.warning("LLM returned unparseable output; using fallback")
        return fallback

    # Validate and sanitize the parsed output
    validated = _validate_llm_output(parsed, fallback)
    validated["mode"] = "llm"
    return validated


def _build_user_message(
    action: str,
    risk_data: dict,
    weather_data: dict,
    marine_data: dict,
    geo_data: dict,
) -> str:
    """
    Build a structured user message containing all verified data
    for the LLM to base its recommendations on.
    """
    payload = {
        "deterministic_action": action,
        "risk_analysis": {
            "risk_score": risk_data.get("risk_score"),
            "risk_level": risk_data.get("risk_level"),
            "reasons": risk_data.get("reasons", []),
            "confidence": risk_data.get("confidence"),
            "data_gaps": risk_data.get("data_gaps", []),
            "outlook_next_12h": risk_data.get("outlook", {}),
            "agent_findings": [f.get("message") for f in risk_data.get("findings", [])][:8],
        },
        "weather_conditions": {
            "wind_speed_kt": weather_data.get("wind_speed"),
            "wind_gusts_kt": weather_data.get("wind_gusts"),
            "pressure_tendency_3h_hpa": weather_data.get("pressure_tendency_3h"),
            "lightning_risk": weather_data.get("lightning_risk"),
            "storm_risk": weather_data.get("storm_risk"),
        },
        "marine_conditions": {
            "wave_height": marine_data.get("wave_height"),
            "wave_direction": marine_data.get("wave_direction"),
            "wave_period": marine_data.get("wave_period"),
            "swell_wave_height": marine_data.get("swell_wave_height"),
            "ocean_current_knots": marine_data.get("ocean_current_velocity"),
            "sea_surface_temperature": marine_data.get("sea_surface_temperature"),
        },
        "geospatial_conditions": {
            "near_boundary": geo_data.get("near_boundary"),
            "restricted_zone": geo_data.get("restricted_zone"),
            "distance_to_boundary_meters": geo_data.get("distance_to_boundary_meters"),
        },
    }

    data_str = json.dumps(payload, default=str)[:_MAX_DATA_PAYLOAD_CHARS]

    return (
        "Below is verified safety data for a vessel. "
        "Generate a JSON response with message, recommendations, and explanation. "
        "Do NOT change the deterministic_action or risk values.\n\n"
        f"{data_str}"
    )


# =========================================================
# LLM OUTPUT PARSING & VALIDATION
# =========================================================
def _parse_llm_json(raw: str) -> dict | None:
    """
    Extract a JSON object from the raw LLM output.
    Returns the parsed dict or None if extraction fails.
    """
    if not isinstance(raw, str) or not raw.strip():
        return None

    sample = raw.strip()[:8000]
    candidates: list[str] = []

    # Try fenced code block first
    fenced = re.search(
        r"```(?:json)?\s*(\{.{0,4000}\})\s*```",
        sample,
        re.DOTALL | re.IGNORECASE,
    )
    if fenced:
        candidates.append(fenced.group(1).strip())

    # Try raw braced JSON
    braced = re.search(r"\{.{0,4000}\}", sample, re.DOTALL)
    if braced:
        candidates.append(braced.group(0).strip())

    # Try the full sample
    candidates.append(sample)

    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data

    return None


def _validate_llm_output(parsed: dict, fallback: dict) -> dict:
    """
    Validate and sanitize the parsed LLM output.
    Falls back to defaults for any field that is missing or malformed.
    """
    # --- message ---
    message = parsed.get("message")
    if not isinstance(message, str) or not message.strip():
        message = fallback["message"]
    else:
        message = _sanitize_text(message)

    # --- recommendations ---
    recommendations = parsed.get("recommendations")
    if not isinstance(recommendations, list) or not recommendations:
        recommendations = fallback["recommendations"]
    else:
        recommendations = [
            _sanitize_text(r)
            for r in recommendations
            if isinstance(r, str) and r.strip()
        ]
        if not recommendations:
            recommendations = fallback["recommendations"]

    # --- explanation ---
    explanation = parsed.get("explanation")
    if not isinstance(explanation, str) or not explanation.strip():
        explanation = fallback["explanation"]
    else:
        explanation = _sanitize_text(explanation)

    return {
        "message": message,
        "recommendations": recommendations,
        "explanation": explanation,
    }


def _sanitize_text(text: str) -> str:
    """Strip control characters and HTML tags from LLM output."""
    cleaned = text.replace("\x00", "")
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", cleaned)
    cleaned = re.sub(r"(?is)<script.*?>.*?</script>", "", cleaned)
    cleaned = re.sub(r"(?is)<style.*?>.*?</style>", "", cleaned)
    cleaned = re.sub(r"(?i)<[^>]+>", "", cleaned)
    return cleaned.strip()[:1500]


def _get_fallback(
    action: str,
    risk_data: dict = None,
    weather_data: dict = None,
    marine_data: dict = None,
    geo_data: dict = None,
) -> dict:
    """Rule-based advice built strictly from verified values (no invented numbers)."""
    r_dict = risk_data or {}
    w_dict = weather_data or {}
    m_dict = marine_data or {}
    g_dict = geo_data or {}

    reasons = r_dict.get("reasons", [])
    risk_score = r_dict.get("risk_score", 0)
    confidence = r_dict.get("confidence", "medium")
    gaps = r_dict.get("data_gaps") or []
    outlook = r_dict.get("outlook") or {}

    def _f(src, key):
        v = src.get(key)
        return float(v) if isinstance(v, (int, float)) else None

    wave_h = _f(m_dict, "wave_height")
    wind_spd = _f(w_dict, "wind_speed")
    gust = _f(w_dict, "wind_gusts")
    swell_h = _f(m_dict, "swell_wave_height")
    curr_vel = _f(m_dict, "ocean_current_velocity")
    curr_dir = _f(m_dict, "ocean_current_direction")
    sst = _f(m_dict, "sea_surface_temperature")

    def fmt(v, unit, digits=1):
        return f"{v:.{digits}f} {unit}" if v is not None else "unavailable"

    wave_txt, wind_txt = fmt(wave_h, "m"), fmt(wind_spd, "kt", 0)
    conditions = f"Waves {wave_txt}, wind {wind_txt}" + (f" (gusts {gust:.0f} kt)" if gust is not None else "")
    ahead = []
    if isinstance(outlook.get("wind_speed_max_12h"), (int, float)):
        ahead.append(f"wind up to {outlook['wind_speed_max_12h']:.0f} kt")
    if isinstance(outlook.get("wave_height_max_12h"), (int, float)):
        ahead.append(f"waves up to {outlook['wave_height_max_12h']:.1f} m")
    outlook_txt = f" Next 12 h: {', '.join(ahead)}." if ahead else ""
    conf_txt = {
        "high": "Independent sources agree.",
        "medium": "Sources partly disagree - the more dangerous values were used.",
        "low": "Low confidence - data is incomplete or conflicting.",
    }.get(confidence, "")
    reasons_text = "; ".join(reasons[:4])

    if action == "DO_NOT_PROCEED":
        msg = f"DANGER - DO NOT GO TO SEA. {reasons[0] if reasons else conditions}."
        recommendations = [
            "Stay in harbour; if already at sea, head for the nearest safe shelter now.",
            "Keep VHF Channel 16 on; in distress send MAYDAY / DSC alert (India Coast Guard: 1554).",
            "Everyone on deck wears a lifejacket; secure all gear.",
        ]
    elif action == "RETURN_TO_SHORE":
        msg = f"HIGH RISK - RETURN TO SHORE. {reasons[0] if reasons else conditions}."
        recommendations = [
            "Stop fishing operations and move towards the nearest harbour.",
            "Secure nets and loose gear; keep the bow into the waves.",
            "Tell someone ashore your position and expected arrival time.",
        ]
    elif action == "PROCEED_WITH_CAUTION":
        msg = f"CAUTION. {reasons[0] if reasons else conditions}."
        recommendations = [
            "Stay close to the coast and plan an early return.",
            "Re-check conditions before going further out.",
            "Carry lifejackets, a charged radio/phone and enough fuel to return.",
        ]
    else:
        msg = f"Conditions look suitable now. {conditions}." + (f" Note: {reasons[0]}." if reasons else "")
        recommendations = [
            "Re-check the forecast before departure and again at sea.",
            "Keep VHF Channel 16 on and share your fishing area with someone ashore.",
        ]

    if any("not at sea" in g for g in gaps):
        msg = "No sea-state data here: this position looks like land. Choose a harbour or a point at sea."
        recommendations = ["Search a coastal port, tap the sea on the map, or enable GPS when at the coast."]
    elif gaps:
        msg = f"CANNOT CONFIRM SAFETY - live {' and '.join(gaps)} unavailable. " + msg
        recommendations.insert(0, "Check the official marine forecast (e.g. INCOIS or your national met service) before going out.")
    if curr_vel is not None:
        dir_txt = f" towards {int(curr_dir)}°" if curr_dir is not None else ""
        recommendations.append(f"Current {curr_vel:.1f} kt{dir_txt} - allow for drift.")
    if g_dict.get("inside_protected_area"):
        recommendations.insert(0, "You are inside a protected or restricted area - follow local fishing rules.")
    elif g_dict.get("near_boundary"):
        recommendations.insert(0, "You are close to a protected-area boundary.")

    explanation = (
        f"Risk {risk_score}/100. {conditions}; swell {fmt(swell_h, 'm')}, sea temperature {fmt(sst, '°C')}."
        f"{outlook_txt} {conf_txt}"
        + (f" Reasons: {reasons_text}." if reasons_text else "")
    ).strip()

    return {
        "message": msg,
        "recommendations": recommendations,
        "explanation": explanation,
        "mode": "rules",
    }


# ---------- Example Usage (Test this file directly) ----------
if __name__ == "__main__":
    import asyncio

    async def test():
        risk = {
            "risk_score": 75,
            "risk_level": "HIGH",
            "reasons": [
                "High wave height",
                "Strong winds",
                "Near maritime boundary",
            ],
        }
        weather = {
            "wind_speed": 18,
            "lightning_risk": "LOW",
            "storm_risk": "MEDIUM",
        }
        marine = {
            "wave_height": 3.2,
            "wave_direction": 220,
            "wave_period": 8,
            "swell_wave_height": 2.1,
            "ocean_current_velocity": 1.5,
            "sea_surface_temperature": 28,
        }
        geo = {
            "near_boundary": True,
            "restricted_zone": False,
            "distance_to_boundary_meters": 5000,
        }

        try:
            result = await recommendation_agent(risk, weather, marine, geo)
            print("Recommendation Result:")
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Error: {e}")

    asyncio.run(test())
