# Backend/Services/prediction_service.py
"""
24-hour marine forecast service with an honest, verifiable evaluation.

Forecast
    The next 24 h come from physics-based numerical models (Open-Meteo best
    match; for waves and wind also ECMWF and NOAA as independent members).
    The uncertainty band is the SPREAD BETWEEN MODELS - a real disagreement
    measure - not a synthetic interval. If only one model is available the
    band collapses and `uncertainty_available` is False.

Evaluation (last 24 h)
    For every hour of the past day we compare three forecasting methods
    against the latest model hindcast ("truth" - note: a model analysis, not
    an in-situ buoy observation):
      * nwp_24h_ahead  - what the model predicted 24 h earlier (previous run)
      * persistence    - "same as 24 h ago"
      * linear_trend   - OLS line fitted on the preceding 24 h, extrapolated
    MAE / RMSE / R2 and a safety-band confusion matrix are reported, plus
    skill vs persistence. Nothing is ever filled with invented values: if a
    series is unavailable the endpoint says so.
"""

import asyncio
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from Services.http_cache import UpstreamError, cached_get_json

logger = logging.getLogger(__name__)

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
PREVIOUS_RUNS_URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
KMH_TO_KNOTS = 0.539957

VARIABLE_THRESHOLDS = {
    "wave_height": {"unit": "m", "label": "Significant Wave Height", "safe_max": 1.5, "caution_max": 2.5, "danger_min": 2.5},
    "wind_speed": {"unit": "kt", "label": "Wind Speed", "safe_max": 15.0, "caution_max": 25.0, "danger_min": 25.0},
    "swell_wave_height": {"unit": "m", "label": "Swell Wave Height", "safe_max": 1.2, "caution_max": 2.0, "danger_min": 2.0},
    "ocean_current_velocity": {"unit": "kt", "label": "Ocean Current", "safe_max": 1.5, "caution_max": 3.0, "danger_min": 3.0},
    "risk_score": {"unit": "idx", "label": "Marine Risk Index", "safe_max": 30.0, "caution_max": 55.0, "danger_min": 55.0},
}


class PredictionUnavailable(Exception):
    """No real series exists for this variable / location."""


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------
def fit_linear_regression(x_values: List[float], y_values: List[float]) -> Dict[str, Any]:
    """Ordinary least squares y = m*x + c with R2, Pearson r and residual SE."""
    n = len(x_values)
    if n < 2 or len(y_values) != n:
        c = y_values[0] if y_values else 0.0
        return {"slope": 0.0, "intercept": c, "r_squared": 0.0, "correlation": 0.0,
                "standard_error": 0.0, "equation": f"y = 0.00x + {c:.2f}"}
    sx, sy = sum(x_values), sum(y_values)
    sxy = sum(x * y for x, y in zip(x_values, y_values))
    sx2, sy2 = sum(x * x for x in x_values), sum(y * y for y in y_values)
    den = n * sx2 - sx ** 2
    slope = 0.0 if abs(den) < 1e-9 else (n * sxy - sx * sy) / den
    intercept = (sy - slope * sx) / n
    mean_y = sy / n
    ss_tot = sum((y - mean_y) ** 2 for y in y_values)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(x_values, y_values))
    r2 = max(0.0, min(1.0, 1 - ss_res / ss_tot)) if ss_tot > 1e-9 else (1.0 if ss_res < 1e-9 else 0.0)
    den_r = math.sqrt(max(1e-9, (n * sx2 - sx ** 2) * (n * sy2 - sy ** 2)))
    corr = max(-1.0, min(1.0, (n * sxy - sx * sy) / den_r)) if den_r > 1e-9 else 0.0
    se = math.sqrt(max(0.0, ss_res / max(1, n - 2)))
    sign = "+" if intercept >= 0 else "-"
    return {"slope": round(slope, 5), "intercept": round(intercept, 4), "r_squared": round(r2, 4),
            "correlation": round(corr, 4), "standard_error": round(se, 4),
            "equation": f"y = {slope:.4f}x {sign} {abs(intercept):.3f}"}


def _safety_class(value: float, config: Dict[str, Any]) -> str:
    if value >= config["danger_min"]:
        return "danger"
    if value >= config["safe_max"]:
        return "caution"
    return "safe"


def _regression_metrics(actual: List[float], predicted: List[float]) -> Dict[str, float]:
    if not actual or len(actual) != len(predicted):
        return {"mae": None, "rmse": None, "r_squared": None}
    mean_a = sum(actual) / len(actual)
    errs = [a - p for a, p in zip(actual, predicted)]
    ss_res = sum(e * e for e in errs)
    ss_tot = sum((a - mean_a) ** 2 for a in actual)
    return {
        "mae": round(sum(abs(e) for e in errs) / len(errs), 4),
        "rmse": round(math.sqrt(ss_res / len(errs)), 4),
        "r_squared": round(1 - ss_res / ss_tot, 4) if ss_tot > 1e-9 else None,
    }


def _confusion_matrix(actual: List[float], predicted: List[float], config: Dict[str, Any]) -> Dict[str, Any]:
    labels = ["safe", "caution", "danger"]
    matrix = {a: {p: 0 for p in labels} for a in labels}
    for a, p in zip(actual, predicted):
        matrix[_safety_class(a, config)][_safety_class(p, config)] += 1
    return {"labels": labels, "matrix": matrix, "total": len(actual)}


def _risk_index(wave: Optional[float], wind: Optional[float]) -> Optional[float]:
    """Same tiering as the live risk engine (waves + wind only)."""
    if wave is None or wind is None:
        return None
    score = 50 if wave >= 3.5 else 35 if wave >= 2.5 else 20 if wave >= 1.8 else 0
    score += 45 if wind >= 35 else 30 if wind >= 25 else 15 if wind >= 18 else 0
    return float(min(score, 100))


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------
def _num(v) -> Optional[float]:
    return float(v) if isinstance(v, (int, float)) else None


async def _marine_series(field: str, lat: float, lon: float) -> Dict[str, Any]:
    base = {"latitude": round(lat, 3), "longitude": round(lon, 3), "past_days": 2,
            "forecast_days": 2, "timezone": "GMT", "cell_selection": "sea"}
    main = await cached_get_json(MARINE_URL, {**base, "hourly": f"{field},{field}_previous_day1"}, ttl=1800)
    hourly = (main.data or {}).get("hourly") or {}
    scale = KMH_TO_KNOTS if field == "ocean_current_velocity" else 1.0
    conv = lambda s: [(_num(v) * scale if _num(v) is not None else None) for v in (s or [])]
    out = {"time": hourly.get("time") or [], "latest": conv(hourly.get(field)),
           "previous": conv(hourly.get(f"{field}_previous_day1")), "members": {}}
    if field == "wave_height":
        try:
            ens = await cached_get_json(MARINE_URL, {**base, "hourly": "wave_height",
                                                     "models": "ecmwf_wam025,ncep_gfswave025"}, ttl=1800)
            eh = (ens.data or {}).get("hourly") or {}
            times = eh.get("time") or []
            for key, label in (("ecmwf_wam025", "ECMWF WAM"), ("ncep_gfswave025", "NOAA GFS-Wave")):
                series = dict(zip(times, eh.get(f"wave_height_{key}") or []))
                out["members"][label] = [_num(series.get(t)) for t in out["time"]]
        except UpstreamError:
            pass
    return out


async def _wind_series(lat: float, lon: float) -> Dict[str, Any]:
    base = {"latitude": round(lat, 3), "longitude": round(lon, 3), "past_days": 2,
            "forecast_days": 2, "timezone": "GMT", "wind_speed_unit": "kn"}
    prev, ens = await asyncio.gather(
        cached_get_json(PREVIOUS_RUNS_URL, {**base, "hourly": "wind_speed_10m,wind_speed_10m_previous_day1"}, ttl=1800),
        cached_get_json(WEATHER_URL, {**base, "hourly": "wind_speed_10m", "models": "ecmwf_ifs025,gfs_seamless"}, ttl=1800),
    )
    ph = (prev.data or {}).get("hourly") or {}
    eh = (ens.data or {}).get("hourly") or {}
    times = ph.get("time") or []
    members = {}
    for key, label in (("ecmwf_ifs025", "ECMWF IFS"), ("gfs_seamless", "NOAA GFS")):
        series = dict(zip(eh.get("time") or [], eh.get(f"wind_speed_10m_{key}") or []))
        members[label] = [_num(series.get(t)) for t in times]
    return {"time": times, "latest": [_num(v) for v in ph.get("wind_speed_10m") or []],
            "previous": [_num(v) for v in ph.get("wind_speed_10m_previous_day1") or []], "members": members}


async def _load_series(variable: str, lat: float, lon: float) -> Dict[str, Any]:
    if variable == "wind_speed":
        return await _wind_series(lat, lon)
    if variable == "risk_score":
        wave, wind = await asyncio.gather(_marine_series("wave_height", lat, lon), _wind_series(lat, lon))
        wind_by_t = {t: (l, p) for t, l, p in zip(wind["time"], wind["latest"], wind["previous"])}
        latest, previous = [], []
        for t, wl, wp in zip(wave["time"], wave["latest"], wave["previous"]):
            nl, np_ = wind_by_t.get(t, (None, None))
            latest.append(_risk_index(wl, nl))
            previous.append(_risk_index(wp, np_))
        return {"time": wave["time"], "latest": latest, "previous": previous, "members": {}}
    return await _marine_series(variable, lat, lon)


def _now_index(times: List[str]) -> Optional[int]:
    if not times:
        return None
    hour = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00")
    if hour in times:
        return times.index(hour)
    # Fall back to the closest earlier timestamp.
    earlier = [i for i, t in enumerate(times) if t <= hour]
    return earlier[-1] if earlier else None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
async def compute_forecast(variable: str, lat: float, lon: float, horizon_hours: int = 24,
                           past_hours: int = 24) -> Dict[str, Any]:
    variable = variable if variable in VARIABLE_THRESHOLDS else "wave_height"
    cfg = VARIABLE_THRESHOLDS[variable]
    horizon_hours = max(1, min(int(horizon_hours or 24), 24))
    past_hours = max(6, min(int(past_hours or 24), 24))

    series = await _load_series(variable, lat, lon)
    times, latest, previous = series["time"], series["latest"], series["previous"]
    now_i = _now_index(times)
    if now_i is None or now_i >= len(latest) or latest[now_i] is None:
        raise PredictionUnavailable(f"No {cfg['label'].lower()} data for this position (land or no model coverage)")

    def label(t: str, offset: int) -> str:
        return f"{t[11:16]} UTC" if offset <= 0 else f"+{offset}h ({t[11:16]} UTC)"

    # History (model hindcast) -------------------------------------------------
    history = []
    for off in range(-past_hours, 1):
        i = now_i + off
        if 0 <= i < len(latest) and latest[i] is not None:
            history.append({"hour_offset": off, "timestamp": f"{times[i]}Z", "time_label": label(times[i], off),
                            "value": round(latest[i], 2), "is_historical": True, "is_current": off == 0})

    # Forecast with inter-model spread ---------------------------------------
    val_now = latest[now_i]
    predictions = []
    band_available = False
    for h in range(1, horizon_hours + 1):
        i = now_i + h
        if i >= len(latest) or latest[i] is None:
            continue
        value = latest[i]
        members = [m[i] for m in series["members"].values() if i < len(m) and m[i] is not None]
        lo, hi = min(members + [value]), max(members + [value])
        band_available = band_available or len(members) >= 2
        predictions.append({
            "hour_offset": h, "timestamp": f"{times[i]}Z", "time_label": label(times[i], h),
            "predicted_value": round(value, 2), "ci_lower": round(lo, 2), "ci_upper": round(hi, 2),
            "safety_status": _safety_class(hi, cfg),  # judge on the worse member
            "delta_from_now": round(value - val_now, 2),
        })
    if not predictions:
        raise PredictionUnavailable("Forecast series unavailable for this position")

    # Verification over the past 24 h ----------------------------------------
    truth, nwp, persist, trend = [], [], [], []
    for off in range(-24, 0):
        t = now_i + off
        if t - 48 < 0 or latest[t] is None or t >= len(previous) or previous[t] is None or latest[t - 24] is None:
            continue
        window = [(x, latest[t - 48 + x]) for x in range(24) if latest[t - 48 + x] is not None]
        if len(window) < 12:
            continue
        fit = fit_linear_regression([w[0] for w in window], [w[1] for w in window])
        truth.append(latest[t])
        nwp.append(previous[t])
        persist.append(latest[t - 24])
        # Window x=0..23 covers t-48..t-25, so the target hour t is x=48.
        trend.append(fit["slope"] * 48 + fit["intercept"])
    evaluation_models = {}
    verification_note = None
    identical = sum(1 for a, b in zip(truth, nwp) if abs(a - b) < 1e-6)
    if truth and identical >= 0.8 * len(truth):
        # The upstream returned the latest run as the "previous" run, so a
        # forecast-vs-truth comparison would be meaningless (MAE = 0).
        verification_note = "Previous-run archive not available for this variable; NWP skill not verified."
        truth = []
    elif not truth:
        verification_note = "Not enough history to verify the forecast."
    if truth:
        for name, pred in (("nwp_24h_ahead", nwp), ("persistence", persist), ("linear_trend", trend)):
            evaluation_models[name] = {**_regression_metrics(truth, pred), "validation_size": len(truth),
                                       "confusion_matrix": _confusion_matrix(truth, pred, cfg)}
    best = min(evaluation_models, key=lambda k: evaluation_models[k]["mae"]) if evaluation_models else "nwp_forecast"
    skill = None
    if evaluation_models and evaluation_models["persistence"]["mae"]:
        skill = round(1 - evaluation_models["nwp_24h_ahead"]["mae"] / evaluation_models["persistence"]["mae"], 3)

    # Summary ---------------------------------------------------------------
    peak = max(predictions, key=lambda p: p["ci_upper"])
    val_24h = predictions[-1]["predicted_value"]
    trend_fit = fit_linear_regression([p["hour_offset"] for p in predictions], [p["predicted_value"] for p in predictions])
    slope = trend_fit["slope"]
    rel = slope * 24 / max(abs(val_now), cfg["safe_max"] * 0.25)
    trend_code = ("SHARP_INCREASE" if rel > 0.5 else "MODERATE_RISE" if rel > 0.15 else
                  "SHARP_DECREASE" if rel < -0.5 else "MODERATE_FALL" if rel < -0.15 else "STABLE")
    unit = cfg["unit"]
    status = _safety_class(peak["ci_upper"], cfg)
    when = peak["time_label"]
    if status == "danger":
        advisory = f"Warning: {cfg['label']} forecast to reach {peak['ci_upper']:.1f} {unit} around {when}. Small craft should stay in harbour."
    elif status == "caution":
        advisory = f"Caution: {cfg['label']} up to {peak['ci_upper']:.1f} {unit} around {when}. Plan an early return."
    else:
        advisory = f"{cfg['label']} stays below {cfg['safe_max']:g} {unit} for the next {horizon_hours} h (max {peak['ci_upper']:.1f} {unit})."
    if skill is not None:
        advisory += f" Model forecast error over the last day: {evaluation_models['nwp_24h_ahead']['mae']:.2f} {unit} (persistence: {evaluation_models['persistence']['mae']:.2f})."

    nwp_eval = evaluation_models.get("nwp_24h_ahead", {})
    return {
        "success": True,
        "variable": variable,
        "unit": unit,
        "label": cfg["label"],
        "thresholds": {"safe_max": cfg["safe_max"], "caution_max": cfg["caution_max"], "danger_min": cfg["danger_min"]},
        "current_value": round(val_now, 2),
        "horizon_hours": horizon_hours,
        "past_hours": past_hours,
        "forecast_source": "Open-Meteo numerical models" + (" (spread: ECMWF vs NOAA)" if band_available else ""),
        "uncertainty_available": band_available,
        "metrics": {
            "equation": f"NWP forecast - last-24h MAE {nwp_eval.get('mae')} {unit}" if nwp_eval else "NWP forecast",
            "r_squared": nwp_eval.get("r_squared"),
            "mae": nwp_eval.get("mae"),
            "rmse": nwp_eval.get("rmse"),
            "skill_vs_persistence": skill,
            "forecast_trend_slope_per_h": slope,
        },
        "model_evaluation": {
            "best_model": best,
            "selection_metric": "lowest_mae_last_24h",
            "truth_source": "latest model hindcast (not in-situ observations)",
            "note": verification_note,
            "models": evaluation_models,
            "confusion_matrix": evaluation_models.get("nwp_24h_ahead", {}).get("confusion_matrix"),
        },
        "summary": {
            "trend": trend_code,
            "trend_label": trend_code.replace("_", " ").title(),
            "overall_status": status,
            "val_now": round(val_now, 2),
            "val_24h": round(val_24h, 2),
            "delta_24h": round(val_24h - val_now, 2),
            "peak_val": round(peak["ci_upper"], 2),
            "peak_hour": peak["hour_offset"],
            "advisory_en": advisory,
        },
        "history": history,
        "predictions": predictions,
    }
