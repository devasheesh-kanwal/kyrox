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

# =========================================================
# SAFE FALLBACK (used when LLM fails or returns garbage)
# =========================================================
_FALLBACK_MESSAGES: dict[str, dict] = {
    "SAFE": {
        "message": "Current conditions appear safe for marine activity.",
        "recommendations": [
            "Continue monitoring weather and marine forecasts.",
            "Keep communication equipment operational.",
            "Follow standard maritime safety procedures.",
        ],
        "explanation": "The verified risk analysis shows low overall risk.",
    },
    "PROCEED_WITH_CAUTION": {
        "message": "Conditions are moderate — proceed with caution.",
        "recommendations": [
            "Stay alert to changing weather and sea conditions.",
            "Keep close to known safe harbors.",
            "Monitor official weather alerts.",
        ],
        "explanation": (
            "The verified risk analysis detected moderate concerns. "
            "Exercise caution and be prepared to return to shore."
        ),
    },
    "RETURN_TO_SHORE": {
        "message": "Safety risk is high based on the current analysis.",
        "recommendations": [
            "Move toward the nearest safe location.",
            "Avoid dangerous marine conditions.",
            "Monitor official weather alerts.",
        ],
        "explanation": (
            "The verified risk analysis detected significant safety concerns."
        ),
    },
    "DO_NOT_PROCEED": {
        "message": "Conditions are critical — do not proceed to sea.",
        "recommendations": [
            "Stay on shore or seek immediate shelter.",
            "Do not launch vessels until conditions improve.",
            "Follow all emergency advisories from local authorities.",
        ],
        "explanation": (
            "The verified risk analysis detected critical safety threats. "
            "Going to sea would endanger lives."
        ),
    },
}

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
    2. Calls the Hugging Face LLM to produce a human-friendly explanation.
    3. If the LLM fails, returns a safe deterministic fallback.

    Args:
        risk_data:    Dict with keys like risk_score, risk_level, reasons.
        weather_data: Dict with keys like wind_speed, lightning_risk, storm_risk.
        marine_data:  Dict with keys like wave_height, wave_direction, etc.
        geo_data:     Dict with keys like near_boundary, restricted_zone, etc.

    Returns:
        dict with keys: action, message, recommendations, explanation.
    """
    # ---- Safely coerce inputs to dicts ----
    risk_data = risk_data if isinstance(risk_data, dict) else {}
    weather_data = weather_data if isinstance(weather_data, dict) else {}
    marine_data = marine_data if isinstance(marine_data, dict) else {}
    geo_data = geo_data if isinstance(geo_data, dict) else {}

    # ---- Step 1: Deterministic action ----
    action = _determine_action(risk_data)

    # ---- Step 2: Ask the LLM for human-friendly advice ----
    llm_output = await _query_llm(
        action=action,
        risk_data=risk_data,
        weather_data=weather_data,
        marine_data=marine_data,
        geo_data=geo_data,
    )

    # ---- Step 3: Merge deterministic action with LLM-generated fields ----
    return {
        "action": action,
        "message": llm_output.get("message", ""),
        "recommendations": llm_output.get("recommendations", []),
        "explanation": llm_output.get("explanation", ""),
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
            "Unrecognized risk_level %r — defaulting to RETURN_TO_SHORE",
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
    return _validate_llm_output(parsed, fallback)


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
        },
        "weather_conditions": {
            "wind_speed": weather_data.get("wind_speed"),
            "lightning_risk": weather_data.get("lightning_risk"),
            "storm_risk": weather_data.get("storm_risk"),
        },
        "marine_conditions": {
            "wave_height": marine_data.get("wave_height"),
            "wave_direction": marine_data.get("wave_direction"),
            "wave_period": marine_data.get("wave_period"),
            "swell_wave_height": marine_data.get("swell_wave_height"),
            "ocean_current_velocity": marine_data.get("ocean_current_velocity"),
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
    """Return an intelligent, dynamic fallback customized with verified real-time conditions."""
    r_dict = risk_data or {}
    w_dict = weather_data or {}
    m_dict = marine_data or {}
    g_dict = geo_data or {}

    reasons = r_dict.get("reasons", [])
    risk_score = r_dict.get("risk_score", 0)

    def _f(src, key):
        v = src.get(key)
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    wave_h = _f(m_dict, "wave_height") or _f(w_dict, "wave_height")
    wind_spd = _f(w_dict, "wind_speed")
    swell_h = _f(m_dict, "swell_wave_height")
    curr_vel = _f(m_dict, "ocean_current_velocity")
    curr_dir = _f(m_dict, "ocean_current_direction")
    sst = _f(m_dict, "sea_surface_temperature")
    baro = _f(w_dict, "surface_pressure")

    wave_txt = f"{wave_h:.1f}m" if wave_h is not None else "unavailable"
    wind_txt = f"{wind_spd:.1f} kt" if wind_spd is not None else "unavailable"
    swell_txt = f"{swell_h:.1f}m" if swell_h is not None else "unavailable"
    curr_txt = f"{curr_vel:.1f} kts" if curr_vel is not None else "unavailable"
    sst_txt = f"{sst:.1f}°C" if sst is not None else "unavailable"
    baro_txt = f"{baro:.1f} hPa" if baro is not None else "unavailable"
    dir_txt = f"{int(curr_dir)}°" if curr_dir is not None else "unknown"

    primary_hazard = reasons[0] if reasons else None
    reasons_text = "; ".join(reasons) if reasons else ""

    shore_m = g_dict.get("distance_to_shore_meters")
    shore_txt = f"{float(shore_m)/1000:.1f} km" if isinstance(shore_m, (int, float)) else "unknown"

    if action in ("CRITICAL", "DO_NOT_PROCEED"):
        hazard_label = primary_hazard or f"Extreme sea state (waves {wave_txt}, wind {wind_txt})"
        msg = f"CRITICAL DANGER: {hazard_label}. Immediate return to harbor or shore shelter mandatory."
        explanation = (
            f"Dangerous maritime conditions detected (Risk Score {risk_score}/100). "
            + (f"Hazards: {reasons_text}. " if reasons_text else "")
            + f"Live sensors: wind {wind_txt}, waves {wave_txt}."
        )
        recommendations = [
            "Maintain continuous active guard on VHF Channel 16.",
            "Contact Indian Coast Guard Maritime Rescue (National Emergency: 1554 / VHF Ch 16) if in distress.",
            "Don all SOLAS-approved lifejackets immediately and secure deck gear.",
            f"Head towards closest port; prevailing sea state {wave_txt}.",
        ]
    elif action in ("HIGH", "RETURN_TO_SHORE"):
        hazard_label = primary_hazard or f"High sea swell ({wave_txt}) and wind ({wind_txt})"
        msg = f"HIGH RISK ADVISORY: {hazard_label}. Abort fishing operations and navigate towards shore."
        explanation = (
            f"Elevated marine hazards present (Risk Score {risk_score}/100). "
            + (f"Active alerts: {reasons_text}. " if reasons_text else "")
            + f"Live sensors: waves {wave_txt}, wind {wind_txt}."
        )
        recommendations = [
            "Proceed at safe navigational speed towards the nearest designated harbor.",
            f"Secure all trawl gear, nets, and loose equipment (sea state {wave_txt}).",
            f"Ocean current {curr_txt} towards {dir_txt} — account for set and drift.",
            "Monitor official INCOIS and Coast Guard safety bulletins continuously on VHF CH 16.",
        ]
    elif action == "PROCEED_WITH_CAUTION":
        hazard_label = primary_hazard or f"Moderate swell ({wave_txt}) with wind {wind_txt}"
        msg = f"CAUTION ADVISORY: {hazard_label}. Proceed with heightened vigilance."
        explanation = (
            f"Moderate sea conditions observed (Risk Score {risk_score}/100). "
            + (f"Notes: {reasons_text}. " if reasons_text else "")
            + f"Waves {wave_txt}, swell {swell_txt}, barometer {baro_txt}."
        )
        recommendations = [
            f"Remain within a known operational sector (distance to shore: {shore_txt}).",
            f"SST {sst_txt}; watch for wind changes (now {wind_txt}).",
            f"Current {curr_txt} — adjust anchor scope and drift lines accordingly.",
            "Ensure navigation lights, bilge pumps, and VHF radio are fully functional.",
        ]
    else:  # SAFE
        msg = f"CLEAR & SAFE: Live conditions — waves {wave_txt}, wind {wind_txt}."
        explanation = (
            f"Low maritime risk detected (Risk Score {risk_score}/100). "
            f"Barometer {baro_txt}, sea state {wave_txt}, SST {sst_txt}."
        )
        recommendations = [
            f"SST {sst_txt} from live marine telemetry.",
            f"Current {curr_txt}; swell {swell_txt}.",
            "Maintain standard VHF Channel 16 guard and log GPS waypoint hourly.",
            "Re-check conditions if wind or swell increases.",
        ]

    if g_dict.get("inside_protected_area"):
        recommendations.insert(0, "ALERT: Operating inside protected sanctuary boundary — bottom trawling prohibited.")
    elif g_dict.get("near_boundary"):
        recommendations.insert(0, "CAUTION: Operating within 2 km of marine sanctuary boundary.")

    return {
        "message": msg,
        "recommendations": recommendations,
        "explanation": explanation,
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
