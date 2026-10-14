# Backend/Agents/consensus_agent.py
"""
Consensus Agent - where the specialist agents' outputs are checked against
each other before any advice is given.

Each check produces a *finding* attributed to the agents involved, so the
final advisory can explain not just WHAT the risk is but WHY the system
believes it and HOW SURE it is:

  1. Model agreement  - do independent wave models (ECMWF WAM vs NOAA
                        GFS-Wave) and wind models (ECMWF IFS vs NOAA GFS)
                        agree? On disagreement the conservative (worse)
                        value is used and confidence is lowered.
  2. Physical sanity  - is the wind consistent with the sea state the marine
                        agent reports (e.g. gale-force wind over flat water)?
  3. Trend            - falling barometric pressure; conditions forecast to
                        worsen within the next 12 h.
  4. Official alerts  - INCOIS / GDACS warnings near the position override
                        model optimism.
  5. Data gaps        - missing or stale inputs lower confidence and are
                        never treated as "calm".

The output `effective` values are what the risk calculation uses.
"""
from typing import Optional

WAVE_SPREAD_ABS_M = 0.5
WAVE_SPREAD_REL = 0.35
WIND_SPREAD_ABS_KT = 6.0
WIND_SPREAD_REL = 0.40
PRESSURE_DROP_WARN = -3.0      # hPa / 3 h
PRESSURE_DROP_SEVERE = -5.0


def _num(v) -> Optional[float]:
    return float(v) if isinstance(v, (int, float)) else None


def _spread(values: list[float]) -> tuple[float, float]:
    lo, hi = min(values), max(values)
    mean = sum(values) / len(values)
    return hi - lo, mean


def _finding(agents: list[str], kind: str, message: str, impact: str = "info") -> dict:
    return {"agents": agents, "type": kind, "message": message, "impact": impact}


def build_consensus(marine: dict, weather: dict, official: Optional[dict] = None,
                    geo: Optional[dict] = None) -> dict:
    marine = marine or {}
    weather = weather or {}
    official = official or {}
    findings: list[dict] = []
    confidence_penalty = 0

    wave_now = _num(marine.get("wave_height"))
    wind_now = _num(weather.get("wind_speed"))
    gust_now = _num(weather.get("wind_gusts"))

    # ---- 1. Model agreement -------------------------------------------------
    wave_models = {k: v["wave_height_now"] for k, v in (marine.get("models") or {}).items()
                   if isinstance(v.get("wave_height_now"), (int, float))}
    effective_wave = wave_now
    if len(wave_models) >= 2:
        spread, mean = _spread(list(wave_models.values()))
        detail = ", ".join(f"{k} {v:.1f} m" for k, v in wave_models.items())
        if spread > max(WAVE_SPREAD_ABS_M, WAVE_SPREAD_REL * mean):
            effective_wave = max([wave_now or 0.0] + list(wave_models.values()))
            confidence_penalty += 1
            findings.append(_finding(["marine_agent"], "conflict",
                f"Wave models disagree ({detail}); using the higher value {effective_wave:.1f} m to stay on the safe side.",
                "raises_risk"))
        else:
            findings.append(_finding(["marine_agent"], "agreement",
                f"Independent wave models agree ({detail})."))

    wind_models = {k: v["wind_speed_now"] for k, v in (weather.get("models") or {}).items()
                   if isinstance(v.get("wind_speed_now"), (int, float))}
    effective_wind = wind_now
    if len(wind_models) >= 2:
        spread, mean = _spread(list(wind_models.values()))
        detail = ", ".join(f"{k} {v:.0f} kt" for k, v in wind_models.items())
        if spread > max(WIND_SPREAD_ABS_KT, WIND_SPREAD_REL * mean):
            effective_wind = max([wind_now or 0.0] + list(wind_models.values()))
            confidence_penalty += 1
            findings.append(_finding(["weather_agent"], "conflict",
                f"Wind sources disagree ({detail}); using the higher value {effective_wind:.0f} kt.",
                "raises_risk"))
        else:
            findings.append(_finding(["weather_agent"], "agreement",
                f"Independent wind models agree ({detail})."))

    # ---- 2. Physical consistency between agents ------------------------------
    if effective_wind is not None and effective_wave is not None:
        if effective_wind >= 22 and effective_wave < 0.6:
            confidence_penalty += 1
            findings.append(_finding(["weather_agent", "marine_agent"], "conflict",
                f"Strong wind ({effective_wind:.0f} kt) but low waves ({effective_wave:.1f} m): "
                "the sea is likely to build quickly, or one feed is lagging. Expect rougher water than reported.",
                "raises_risk"))
        elif effective_wave >= 2.5 and effective_wind < 10:
            findings.append(_finding(["weather_agent", "marine_agent"], "insight",
                f"High waves ({effective_wave:.1f} m) with light wind ({effective_wind:.0f} kt) indicate long-period "
                "swell from a distant system - dangerous near shore, bars and harbour mouths."))

    # ---- 3. Trends -----------------------------------------------------------
    tendency = _num(weather.get("pressure_tendency_3h"))
    pressure_flag = None
    if tendency is not None:
        if tendency <= PRESSURE_DROP_SEVERE:
            pressure_flag = "severe"
            findings.append(_finding(["weather_agent"], "trend",
                f"Pressure falling fast ({tendency:+.1f} hPa in 3 h) - a strong weather system may be approaching.",
                "raises_risk"))
        elif tendency <= PRESSURE_DROP_WARN:
            pressure_flag = "falling"
            findings.append(_finding(["weather_agent"], "trend",
                f"Pressure falling ({tendency:+.1f} hPa in 3 h) - weather likely to deteriorate.",
                "raises_risk"))

    wfc = weather.get("forecast_12h") or {}
    mfc = marine.get("forecast_12h") or {}
    wind_ahead = _num(wfc.get("wind_speed_max"))
    gust_ahead = _num(wfc.get("wind_gusts_max"))
    wave_ahead = _num(mfc.get("wave_height_max"))
    # Independent models' 12 h maxima count too (conservative).
    for v in (marine.get("models") or {}).values():
        if isinstance(v.get("wave_height_max_12h"), (int, float)):
            wave_ahead = max(wave_ahead or 0.0, v["wave_height_max_12h"])
    if wind_ahead is not None and effective_wind is not None and wind_ahead >= effective_wind + 8 and wind_ahead >= 18:
        findings.append(_finding(["weather_agent"], "trend",
            f"Wind forecast to rise to {wind_ahead:.0f} kt around {wfc.get('worst_time') or 'later today'}.",
            "raises_risk"))
    if wave_ahead is not None and effective_wave is not None and wave_ahead >= effective_wave + 0.6 and wave_ahead >= 1.5:
        findings.append(_finding(["marine_agent"], "trend",
            f"Waves forecast to build to {wave_ahead:.1f} m around {mfc.get('wave_height_max_time') or 'later today'}.",
            "raises_risk"))
    if wfc.get("storm_expected"):
        findings.append(_finding(["weather_agent"], "trend",
            "Thunderstorms are forecast within the next 12 hours.", "raises_risk"))

    # ---- 4. Official alerts --------------------------------------------------
    official_alerts = official.get("alerts") or []
    for alert in official_alerts[:5]:
        findings.append(_finding(["official_alerts_agent"], "official",
            f"{alert['source']} {alert.get('alert') or alert['kind']} ({alert['level']}), "
            f"{alert['distance_km']:.0f} km away: {alert.get('message') or ''}".strip(),
            "raises_risk" if alert.get("severity", 0) >= 1 else "info"))

    # ---- 5. Data gaps --------------------------------------------------------
    gaps = []
    if wave_now is None:
        gaps.append("wave height")
    if wind_now is None:
        gaps.append("wind speed")
    no_sea = bool(marine.get("no_coverage"))
    if no_sea:
        findings.append(_finding(["marine_agent"], "gap",
            "This position is on land or outside sea-state model coverage - pick a point at sea or a harbour.", "info"))
    elif gaps:
        confidence_penalty += 2 if len(gaps) == 2 else 1
        findings.append(_finding(["consensus_agent"], "gap",
            f"Live {' and '.join(gaps)} unavailable - safety cannot be confirmed from data.", "raises_risk"))
    if geo is not None and geo.get("data_available") is False:
        findings.append(_finding(["geospatial_agent"], "gap",
            "Protected-area check incomplete (OpenStreetMap unreachable); only known sanctuaries were checked.", "info"))
    stale = [name for name, src in (("marine", marine), ("weather", weather)) if src.get("stale")]
    if stale:
        confidence_penalty += 1
        findings.append(_finding(["consensus_agent"], "gap",
            f"Upstream {', '.join(stale)} feed is down; using last good data.", "info"))
    for feed, meta in ((official.get("feeds") or {}).items()):
        if meta and meta.get("available") is False:
            findings.append(_finding(["official_alerts_agent"], "gap",
                f"{feed} alert feed unavailable - check official channels directly.", "info"))

    confidence = "high" if confidence_penalty == 0 else ("medium" if confidence_penalty <= 1 else "low")

    return {
        "confidence": confidence,
        "findings": findings,
        "data_gaps": gaps,
        "no_sea_coverage": no_sea,
        "effective": {
            "wave_height": effective_wave,
            "wind_speed": effective_wind,
            "wind_gusts": gust_now,
            "wave_height_max_12h": wave_ahead,
            "wind_speed_max_12h": wind_ahead,
            "wind_gusts_max_12h": gust_ahead,
            "pressure_trend": pressure_flag,
            "storm_expected_12h": bool(wfc.get("storm_expected")),
        },
        "official_alerts": official_alerts,
    }
