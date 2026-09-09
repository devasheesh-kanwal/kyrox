# Backend/Services/prediction_service.py
"""
24-Hour Marine Linear Regression Prediction Service.
Performs Ordinary Least Squares (OLS) regression on marine time-series telemetry
(wave height, wind speed, ocean currents, swell, risk score) to model trendlines,
compute statistical fit metrics (slope, intercept, R², standard error), and project
hourly forward predictions for the next 24 hours with 95% confidence intervals.
"""

import math
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Standard maritime safety threshold limits for operational craft (<20m)
VARIABLE_THRESHOLDS = {
    "wave_height": {
        "unit": "m",
        "label": "Significant Wave Height",
        "safe_max": 1.5,
        "caution_max": 2.5,
        "danger_min": 2.5,
        "min_physical": 0.2,
        "max_physical": 9.0,
    },
    "wind_speed": {
        "unit": "kts",
        "label": "Wind Speed",
        "safe_max": 15.0,
        "caution_max": 25.0,
        "danger_min": 25.0,
        "min_physical": 0.0,
        "max_physical": 75.0,
    },
    "swell_wave_height": {
        "unit": "m",
        "label": "Swell Wave Height",
        "safe_max": 1.2,
        "caution_max": 2.0,
        "danger_min": 2.0,
        "min_physical": 0.1,
        "max_physical": 8.0,
    },
    "ocean_current_velocity": {
        "unit": "m/s",
        "label": "Ocean Current Velocity",
        "safe_max": 0.8,
        "caution_max": 1.5,
        "danger_min": 1.5,
        "min_physical": 0.05,
        "max_physical": 4.0,
    },
    "risk_score": {
        "unit": "idx",
        "label": "Marine Risk Index",
        "safe_max": 35.0,
        "caution_max": 70.0,
        "danger_min": 70.0,
        "min_physical": 0.0,
        "max_physical": 100.0,
    },
}


def fit_linear_regression(x_values: List[float], y_values: List[float]) -> Dict[str, Any]:
    """
    Fits an Ordinary Least Squares (OLS) line: y = m*x + c
    Computes:
      - slope (m)
      - intercept (c)
      - R² (coefficient of determination)
      - Pearson correlation (r)
      - Residual standard error (SE)
    """
    n = len(x_values)
    if n < 2 or len(y_values) != n:
        return {
            "slope": 0.0,
            "intercept": y_values[0] if y_values else 0.0,
            "r_squared": 0.0,
            "correlation": 0.0,
            "standard_error": 0.0,
            "equation": f"y = 0.00x + {(y_values[0] if y_values else 0.0):.2f}"
        }

    sum_x = sum(x_values)
    sum_y = sum(y_values)
    sum_xy = sum(x * y for x, y in zip(x_values, y_values))
    sum_x2 = sum(x ** 2 for x in x_values)
    sum_y2 = sum(y ** 2 for y in y_values)

    denominator = (n * sum_x2) - (sum_x ** 2)
    if abs(denominator) < 1e-9:
        slope = 0.0
        intercept = sum_y / n
    else:
        slope = ((n * sum_xy) - (sum_x * sum_y)) / denominator
        intercept = (sum_y - (slope * sum_x)) / n

    # Calculate residuals and R²
    y_mean = sum_y / n
    ss_tot = sum((y - y_mean) ** 2 for y in y_values)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(x_values, y_values))

    if ss_tot > 1e-9:
        r_squared = max(0.0, min(1.0, 1.0 - (ss_res / ss_tot)))
    else:
        r_squared = 1.0 if ss_res < 1e-9 else 0.0

    # Pearson correlation r
    denom_r = math.sqrt(max(1e-9, ((n * sum_x2) - sum_x ** 2) * ((n * sum_y2) - sum_y ** 2)))
    correlation = ((n * sum_xy) - (sum_x * sum_y)) / denom_r if denom_r > 1e-9 else 0.0
    correlation = max(-1.0, min(1.0, correlation))

    # Residual standard error
    dof = max(1, n - 2)
    standard_error = math.sqrt(max(0.0, ss_res / dof))

    eq_sign = "+" if intercept >= 0 else "-"
    equation = f"y = {slope:.4f}x {eq_sign} {abs(intercept):.3f}"

    return {
        "slope": round(slope, 5),
        "intercept": round(intercept, 4),
        "r_squared": round(r_squared, 4),
        "correlation": round(correlation, 4),
        "standard_error": round(standard_error, 4),
        "equation": equation
    }


def generate_baseline_telemetry(
    variable: str,
    current_val: Optional[float] = None,
    past_hours: int = 24
) -> List[Dict[str, Any]]:
    """
    Constructs realistic observed historical telemetry for past_hours up to hour 0 (now).
    If current_val is provided, sets the anchor at t=0 to current_val.
    """
    config = VARIABLE_THRESHOLDS.get(variable, VARIABLE_THRESHOLDS["wave_height"])
    default_anchor = {
        "wave_height": 1.45,
        "wind_speed": 18.2,
        "swell_wave_height": 1.15,
        "ocean_current_velocity": 0.85,
        "risk_score": 42.0,
    }.get(variable, 1.5)

    anchor = current_val if current_val is not None else default_anchor
    anchor = max(config["min_physical"], min(config["max_physical"], anchor))

    now = datetime.now(timezone.utc)
    data_points = []

    # Slight upward maritime wave/surge slope simulation typical before squalls
    simulated_slope = {
        "wave_height": 0.038,
        "wind_speed": 0.35,
        "swell_wave_height": 0.025,
        "ocean_current_velocity": 0.018,
        "risk_score": 1.1,
    }.get(variable, 0.04)

    for h in range(-past_hours, 1):
        dt = now + timedelta(hours=h)
        # Add slight natural oceanic tidal and diurnal wave oscillation
        tidal_cycle = math.sin(h * (2 * math.pi / 12.4)) * (anchor * 0.12)
        wind_gust_jitter = math.cos(h * (2 * math.pi / 6.0)) * (anchor * 0.06)
        trend_component = simulated_slope * h
        value = anchor + trend_component + tidal_cycle + wind_gust_jitter
        value = max(config["min_physical"], min(config["max_physical"], value))

        data_points.append({
            "hour_offset": h,
            "timestamp": dt.isoformat(),
            "time_label": dt.strftime("%H:%M UTC"),
            "value": round(value, 2),
            "is_historical": True,
            "is_current": (h == 0)
        })

    # Ensure hour 0 strictly equals current_val if given
    if data_points:
        data_points[-1]["value"] = round(anchor, 2)

    return data_points


def compute_24h_prediction(
    variable: str = "wave_height",
    current_val: Optional[float] = None,
    past_hours: int = 24,
    horizon_hours: int = 24
) -> Dict[str, Any]:
    """
    Core function for 24-hour Linear Regression prediction modelling.
    Returns:
      - variable config and thresholds
      - historical observed telemetry (-past_hours to 0)
      - regression metrics (slope, intercept, R², SE, equation)
      - 24-hour predictions (1 to horizon_hours) with 95% confidence bands
      - maritime safety advisory and status classification
    """
    if variable not in VARIABLE_THRESHOLDS:
        variable = "wave_height"

    cfg = VARIABLE_THRESHOLDS[variable]
    history = generate_baseline_telemetry(variable, current_val, past_hours)

    x_hist = [pt["hour_offset"] for pt in history]
    y_hist = [pt["value"] for pt in history]

    metrics = fit_linear_regression(x_hist, y_hist)
    slope = metrics["slope"]
    intercept = metrics["intercept"]
    se = metrics["standard_error"]

    now = datetime.now(timezone.utc)
    predictions = []
    max_val = -1e9
    max_val_hour = 0

    x_mean = sum(x_hist) / len(x_hist)
    sum_x_diff_sq = max(1e-6, sum((x - x_mean) ** 2 for x in x_hist))
    n = len(x_hist)

    for h in range(1, horizon_hours + 1):
        dt = now + timedelta(hours=h)
        # Linear regression modeled value
        pred_val = (slope * h) + intercept
        # Clamp to physical real-world boundaries
        pred_val = max(cfg["min_physical"], min(cfg["max_physical"], pred_val))

        # 95% prediction interval band
        leverage = math.sqrt(1.0 + (1.0 / n) + (((h - x_mean) ** 2) / sum_x_diff_sq))
        margin = 1.96 * se * leverage
        ci_lower = max(cfg["min_physical"], pred_val - margin)
        ci_upper = min(cfg["max_physical"], pred_val + margin)

        if pred_val >= cfg["danger_min"]:
            safety_status = "danger"
        elif pred_val >= cfg["caution_max"] or (pred_val >= cfg["safe_max"] and slope > 0):
            safety_status = "caution"
        else:
            safety_status = "safe"

        if pred_val > max_val:
            max_val = pred_val
            max_val_hour = h

        predictions.append({
            "hour_offset": h,
            "timestamp": dt.isoformat(),
            "time_label": f"+{h}h ({dt.strftime('%H:%M')})",
            "predicted_value": round(pred_val, 2),
            "ci_lower": round(ci_lower, 2),
            "ci_upper": round(ci_upper, 2),
            "safety_status": safety_status,
            "delta_from_now": round(pred_val - y_hist[-1], 2)
        })

    # Overall 24h trend classification
    val_now = y_hist[-1]
    val_24h = predictions[-1]["predicted_value"] if predictions else val_now
    delta_24h = round(val_24h - val_now, 2)

    if slope > 0.03:
        trend = "SHARP_INCREASE"
        trend_label = "तीव्र वृद्धि (Surging)"
    elif slope > 0.005:
        trend = "MODERATE_RISE"
        trend_label = "मध्यम वृद्धि (Rising)"
    elif slope < -0.03:
        trend = "SHARP_DECREASE"
        trend_label = "तीव्र कमी (Easing)"
    elif slope < -0.005:
        trend = "MODERATE_FALL"
        trend_label = "मध्यम कमी (Falling)"
    else:
        trend = "STABLE"
        trend_label = "स्थिर (Stable)"

    # Advisory messages in Hindi, English, and Tamil
    if max_val >= cfg["danger_min"]:
        overall_status = "danger"
        advisory_hi = f"चेतावनी: अगले 24 घंटों में {cfg['label']} {max_val:.1f}{cfg['unit']} (घंटा +{max_val_hour}) तक पहुंचने का अनुमान है। छोटी नौकाएं तट के निकट रहें।"
        advisory_en = f"Warning: 24h linear regression models {cfg['label']} reaching hazardous peak of {max_val:.1f}{cfg['unit']} at +{max_val_hour}h. Craft <20m should remain inshore."
        advisory_ta = f"எச்சரிக்கை: அடுத்த 24 மணி நேரத்தில் {cfg['label']} {max_val:.1f}{cfg['unit']} வரை உயரும் என கணிக்கப்பட்டுள்ளது. சிறிய படகுகள் கரைக்குத் திரும்பவும்."
    elif max_val >= cfg["safe_max"]:
        overall_status = "caution"
        advisory_hi = f"सतर्कता: {cfg['label']} में अगले 24 घंटों में {delta_24h:+.1f}{cfg['unit']} की वृद्धि का रुझान है। मौसम पर सतत निगरानी रखें।"
        advisory_en = f"Advisory: Linear trend indicates a {delta_24h:+.1f}{cfg['unit']} increase over 24h. Keep crew on standby and monitor barometric telemetry."
        advisory_ta = f"கவனம்: அடுத்த 24 மணி நேரத்தில் {cfg['label']} {delta_24h:+.1f}{cfg['unit']} அதிகரிக்கும் போக்கு உள்ளது. விழிப்புடன் இருக்கவும்."
    else:
        overall_status = "safe"
        advisory_hi = f"सुरक्षित: अगले 24 घंटे की सांख्यिकीय मॉडलिंग अनुकूल स्थिति दर्शाती है ({val_24h:.1f}{cfg['unit']})। सामान्य मत्स्य संचालन अनुशंसित है।"
        advisory_en = f"Clear: 24h linear regression projects favorable operational conditions ({val_24h:.1f}{cfg['unit']}). Normal fishing permitted."
        advisory_ta = f"பாதுகாப்பானது: அடுத்த 24 மணி நேர கணிப்பு சாதகமான கடல் சூழலைக் குறிக்கிறது ({val_24h:.1f}{cfg['unit']})."

    return {
        "success": True,
        "variable": variable,
        "unit": cfg["unit"],
        "label": cfg["label"],
        "thresholds": {
            "safe_max": cfg["safe_max"],
            "caution_max": cfg["caution_max"],
            "danger_min": cfg["danger_min"]
        },
        "current_value": round(val_now, 2),
        "horizon_hours": horizon_hours,
        "past_hours": past_hours,
        "metrics": metrics,
        "summary": {
            "trend": trend,
            "trend_label": trend_label,
            "overall_status": overall_status,
            "val_now": round(val_now, 2),
            "val_24h": round(val_24h, 2),
            "delta_24h": delta_24h,
            "peak_val": round(max_val, 2),
            "peak_hour": max_val_hour,
            "advisory_hi": advisory_hi,
            "advisory_en": advisory_en,
            "advisory_ta": advisory_ta
        },
        "history": history,
        "predictions": predictions
    }
