# Backend/Agents/marine_agent.py
"""
Marine Agent - turns the Open-Meteo marine payload into structured sea-state
facts: current conditions, a 12 h look-ahead, independent-model wave values
for cross-checking, and model-estimated tide timing.

No risk scoring here; the risk and consensus agents consume this output.
Missing values stay None - they are never replaced with zeros or defaults.
"""
import logging
from typing import Optional

from Models.schemas import Location
from Tools.marine_tools import MarineDataUnavailable, get_marine_data

logger = logging.getLogger(__name__)


class MarineAgentError(Exception):
    """Raised when marine data cannot be retrieved or parsed."""


_MARINE_FIELDS = [
    "wave_height",
    "wave_direction",
    "wave_period",
    "swell_wave_height",
    "swell_wave_period",
    "swell_wave_direction",
    "ocean_current_velocity",   # knots (converted in the tool)
    "ocean_current_direction",
    "sea_surface_temperature",
]


def _numbers(series) -> list:
    return [v for v in (series or []) if isinstance(v, (int, float))]


def _peak(times: list, series: list) -> tuple[Optional[float], Optional[str]]:
    best_val, best_time = None, None
    for t, v in zip(times, series or []):
        if isinstance(v, (int, float)) and (best_val is None or v > best_val):
            best_val, best_time = v, t
    return best_val, (f"{best_time}Z" if best_time else None)


def _tide_events(times: list, levels: list) -> dict:
    """Next high / low water from modelled sea level (local extrema, ~1 h resolution)."""
    pts = [(t, v) for t, v in zip(times, levels or []) if isinstance(v, (int, float))]
    next_high = next_low = None
    for i in range(1, len(pts) - 1):
        prev_v, (t, v), next_v = pts[i - 1][1], pts[i], pts[i + 1][1]
        if next_high is None and v >= prev_v and v > next_v:
            next_high = {"time": f"{t}Z", "level_m": v}
        if next_low is None and v <= prev_v and v < next_v:
            next_low = {"time": f"{t}Z", "level_m": v}
    return {
        "next_high": next_high,
        "next_low": next_low,
        "source": "Open-Meteo modelled sea level (tide + surge), not a tide gauge",
    }


async def marine_agent(location: Location) -> dict:
    """
    Fetch marine conditions for a position.

    Returns the flat current fields (backward compatible) plus:
        forecast_12h, models, tide, source, observed_at, stale, data_available
    Raises MarineAgentError when nothing usable can be retrieved.
    """
    try:
        raw = await get_marine_data(latitude=location.latitude, longitude=location.longitude)
    except MarineDataUnavailable as exc:
        logger.info("No marine coverage at (%s, %s)", location.latitude, location.longitude)
        raise MarineAgentError(str(exc)) from exc
    except Exception as exc:
        logger.error("Marine data fetch failed for (%s, %s): %s", location.latitude, location.longitude, exc)
        raise MarineAgentError("Unable to retrieve marine data") from exc

    current = raw.get("current") or {}
    conditions = {
        field: (current.get(field) if isinstance(current.get(field), (int, float)) else None)
        for field in _MARINE_FIELDS
    }

    times = raw.get("hourly_time") or []
    wave_fc = raw.get("forecast", {}).get("wave_height") or []
    swell_fc = raw.get("forecast", {}).get("swell_wave_height") or []
    wave_max, wave_max_time = _peak(times, wave_fc)
    swell_max, _ = _peak(times, swell_fc)

    models = {}
    for label, series in (raw.get("models") or {}).items():
        values = _numbers(series)
        if values:
            models[label] = {"wave_height_now": values[0], "wave_height_max_12h": max(values)}

    conditions.update({
        "forecast_12h": {
            "wave_height_max": wave_max,
            "wave_height_max_time": wave_max_time,
            "swell_wave_height_max": swell_max,
            "hours": len(times),
        },
        "models": models,
        "tide": _tide_events(times, raw.get("sea_level") or []),
        "source": "Open-Meteo Marine (best match + ECMWF WAM + NOAA GFS-Wave)",
        "observed_at": raw.get("observed_at"),
        "stale": bool(raw.get("stale")),
        "age_seconds": raw.get("age_seconds"),
        "data_available": True,
    })
    return conditions
