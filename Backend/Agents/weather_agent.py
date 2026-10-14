# Backend/Agents/weather_agent.py
"""
Weather Agent - atmospheric conditions for a position.

Primary source: Open-Meteo (global, keyless) with two independent NWP models,
ECMWF IFS and NOAA GFS. If an OpenWeather key is configured, its observation
is added as a third, independent cross-check.

Output keeps the legacy fields (wind_speed in knots, lightning_risk,
storm_risk, ...) and adds gusts, pressure tendency, a 12 h look-ahead and
per-model values. Missing values stay None; they are never replaced by 0,
because 0 kt wind would read as "safe".
"""
import logging
from typing import Optional

from Models.schemas import Location
from Tools.openmeteo_weather import MODEL_LABELS, WEATHER_MODELS, get_openmeteo_weather
from Tools.openweather import get_weather as get_openweather

logger = logging.getLogger(__name__)


class WeatherAgentError(Exception):
    """Raised when weather data cannot be retrieved or parsed."""


THUNDER_CODES = {95, 96, 99}
SHOWER_SQUALL_CODES = {81, 82}
HEAVY_RAIN_CODES = {63, 65, 80}


def _num(value) -> Optional[float]:
    return float(value) if isinstance(value, (int, float)) else None


def _now_index(times: list, current_time: Optional[str]) -> int:
    """Index of the hourly slot containing `current_time` (both GMT ISO strings)."""
    if not times:
        return 0
    if current_time:
        hour = current_time[:13] + ":00"
        if hour in times:
            return times.index(hour)
    return 0


def _storm_flags(wind: Optional[float], gust: Optional[float], code: Optional[int]) -> tuple[str, str]:
    lightning = "HIGH" if code in THUNDER_CODES else "LOW"
    if code in THUNDER_CODES or code in SHOWER_SQUALL_CODES or (wind or 0) >= 30 or (gust or 0) >= 40:
        storm = "HIGH"
    elif (wind or 0) >= 20 or (gust or 0) >= 28 or code in HEAVY_RAIN_CODES:
        storm = "MEDIUM"
    else:
        storm = "LOW"
    return lightning, storm


async def weather_agent(location: Location) -> dict:
    try:
        data = await get_openmeteo_weather(location.latitude, location.longitude)
    except Exception as exc:
        logger.error("Weather fetch failed for (%.4f, %.4f): %s", location.latitude, location.longitude, exc)
        raise WeatherAgentError("Unable to retrieve live weather data") from exc

    current = data.get("current") or {}
    hourly = data.get("hourly") or {}
    times = list(hourly.get("time") or [])
    now_i = _now_index(times, current.get("time"))

    wind = _num(current.get("wind_speed_10m"))
    gust = _num(current.get("wind_gusts_10m"))
    code = current.get("weather_code") if isinstance(current.get("weather_code"), int) else None
    lightning, storm = _storm_flags(wind, gust, code)

    # Per-model look-ahead and pressure tendency (primary model = ECMWF).
    models = {}
    forecast = {"wind_speed_max": None, "wind_gusts_max": None, "worst_time": None, "storm_expected": False}
    pressure_tendency = None
    for model in WEATHER_MODELS:
        label = MODEL_LABELS[model]
        winds = hourly.get(f"wind_speed_10m_{model}") or []
        gusts = hourly.get(f"wind_gusts_10m_{model}") or []
        codes = hourly.get(f"weather_code_{model}") or []
        pressures = hourly.get(f"pressure_msl_{model}") or []
        future = range(now_i, len(times))
        fw = [(times[i], winds[i]) for i in future if i < len(winds) and isinstance(winds[i], (int, float))]
        fg = [gusts[i] for i in future if i < len(gusts) and isinstance(gusts[i], (int, float))]
        if not fw:
            continue
        worst_time, worst_wind = max(fw, key=lambda tv: tv[1])
        models[label] = {
            "wind_speed_now": fw[0][1],
            "wind_speed_max_12h": worst_wind,
            "wind_gusts_max_12h": max(fg) if fg else None,
        }
        storm_ahead = any(isinstance(codes[i], int) and codes[i] in THUNDER_CODES for i in future if i < len(codes))
        if forecast["wind_speed_max"] is None or worst_wind > forecast["wind_speed_max"]:
            forecast["wind_speed_max"] = worst_wind
            forecast["worst_time"] = f"{worst_time}Z"
        if fg and (forecast["wind_gusts_max"] is None or max(fg) > forecast["wind_gusts_max"]):
            forecast["wind_gusts_max"] = max(fg)
        forecast["storm_expected"] = forecast["storm_expected"] or storm_ahead
        if pressure_tendency is None and now_i >= 3 and now_i < len(pressures):
            p_now, p_then = pressures[now_i], pressures[now_i - 3]
            if isinstance(p_now, (int, float)) and isinstance(p_then, (int, float)):
                pressure_tendency = round(p_now - p_then, 1)

    sources = ["Open-Meteo (ECMWF IFS + NOAA GFS)"]
    try:
        ow = await get_openweather(latitude=location.latitude, longitude=location.longitude)
        ow_wind = (ow.get("wind") or {}).get("speed")
        if isinstance(ow_wind, (int, float)):
            # OpenWeather metric units are m/s.
            models["OpenWeather (observed)"] = {"wind_speed_now": round(ow_wind * 1.94384, 1)}
            sources.append("OpenWeather")
    except Exception:
        pass  # Optional source; not configured or unavailable.

    visibility = _num(current.get("visibility"))
    return {
        "wind_speed": round(wind, 1) if wind is not None else None,
        "wind_gusts": round(gust, 1) if gust is not None else None,
        "wind_direction": _num(current.get("wind_direction_10m")),
        "wave_height": None,  # waves come from the marine agent only
        "lightning_risk": lightning,
        "storm_risk": storm,
        "weather_code": code,
        "temperature": _num(current.get("temperature_2m")),
        "surface_pressure": _num(current.get("surface_pressure")),
        "pressure_msl": _num(current.get("pressure_msl")),
        "pressure_tendency_3h": pressure_tendency,
        "visibility_m": visibility,
        "precipitation_mm": _num(current.get("precipitation")),
        "forecast_12h": forecast,
        "models": models,
        "source": " + ".join(sources),
        "observed_at": f"{current['time']}Z" if current.get("time") else None,
        "stale": bool(data.get("stale")),
        "age_seconds": data.get("age_seconds"),
        "data_available": wind is not None,
    }
