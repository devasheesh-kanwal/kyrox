"""Offline tests for the safety-critical agent logic (no network required).

Run with:  Backend\\.venv\\Scripts\\python.exe -m pytest tests -q
"""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Backend"))

from Agents import orchestrator  # noqa: E402
from Agents.consensus_agent import build_consensus  # noqa: E402
from Agents.orchestrator import calculate_risk, extract_location_and_zone_from_text  # noqa: E402
from Agents.recommendation_agent import _get_fallback  # noqa: E402
from Services import route_planner  # noqa: E402
from Tools import marine_tools  # noqa: E402
from Services.http_cache import CachedResponse  # noqa: E402


def calm_marine(**over):
    base = {"wave_height": 0.6, "swell_wave_height": 0.4, "sea_surface_temperature": 29.0,
            "forecast_12h": {"wave_height_max": 0.7},
            "models": {"ECMWF WAM": {"wave_height_now": 0.6, "wave_height_max_12h": 0.7},
                       "NOAA GFS-Wave": {"wave_height_now": 0.5, "wave_height_max_12h": 0.6}}}
    base.update(over)
    return base


def calm_weather(**over):
    base = {"wind_speed": 8.0, "wind_gusts": 11.0, "lightning_risk": "LOW", "storm_risk": "LOW",
            "pressure_tendency_3h": 0.2,
            "forecast_12h": {"wind_speed_max": 10.0, "wind_gusts_max": 13.0, "storm_expected": False},
            "models": {"ECMWF IFS": {"wind_speed_now": 8.0}, "NOAA GFS": {"wind_speed_now": 9.0}}}
    base.update(over)
    return base


# --------------------------------------------------------------------------- risk
def test_calm_conditions_are_low_risk_with_high_confidence():
    risk = calculate_risk(calm_marine(), calm_weather(), {})
    assert risk["risk_level"] == "LOW"
    assert risk["confidence"] == "high"


def test_missing_wind_and_waves_is_never_low():
    risk = calculate_risk({}, {}, {})
    assert risk["risk_level"] != "LOW"
    assert set(risk["data_gaps"]) == {"wave height", "wind speed"}
    assert risk["confidence"] == "low"


def test_zero_is_not_treated_as_missing_but_none_is():
    # 0 m waves is a real (calm) value; None is unknown.
    risk = calculate_risk(calm_marine(wave_height=0.0), calm_weather(), {})
    assert "wave height" not in risk["data_gaps"]
    risk = calculate_risk(calm_marine(wave_height=None, models={}), calm_weather(), {})
    assert "wave height" in risk["data_gaps"]


def test_model_disagreement_uses_conservative_value():
    marine = calm_marine(wave_height=0.8, models={
        "ECMWF WAM": {"wave_height_now": 0.8}, "NOAA GFS-Wave": {"wave_height_now": 2.9}})
    c = build_consensus(marine, calm_weather())
    assert c["effective"]["wave_height"] == pytest.approx(2.9)
    assert any(f["type"] == "conflict" for f in c["findings"])
    assert c["confidence"] != "high"
    assert calculate_risk(marine, calm_weather(), {}, consensus=c)["risk_level"] in ("MEDIUM", "HIGH")


def test_strong_wind_over_flat_sea_is_flagged():
    c = build_consensus(calm_marine(wave_height=0.3), calm_weather(wind_speed=26.0, models={}))
    assert any(f["type"] == "conflict" and "Strong wind" in f["message"] for f in c["findings"])


def test_worsening_forecast_raises_risk():
    now = calculate_risk(calm_marine(), calm_weather(), {})
    later = calculate_risk(calm_marine(forecast_12h={"wave_height_max": 3.6}),
                           calm_weather(forecast_12h={"wind_speed_max": 30.0, "storm_expected": True}), {})
    assert later["risk_score"] > now["risk_score"]
    assert any(r.startswith("Forecast:") for r in later["reasons"])


def test_falling_pressure_is_reported():
    risk = calculate_risk(calm_marine(), calm_weather(pressure_tendency_3h=-5.5), {})
    assert any("pressure" in r.lower() for r in risk["reasons"])


def test_official_tsunami_alert_dominates():
    official = {"alerts": [{"source": "GDACS", "kind": "Tsunami", "alert": "Tsunami", "level": "orange",
                            "severity": 2, "distance_km": 300.0, "message": "test"}]}
    c = build_consensus(calm_marine(), calm_weather(), official)
    risk = calculate_risk(calm_marine(), calm_weather(), {}, consensus=c)
    assert risk["risk_level"] in ("HIGH", "CRITICAL")
    assert any(r.startswith("OFFICIAL GDACS") for r in risk["reasons"])


# --------------------------------------------------------------------------- what the user describes
@pytest.mark.parametrize("text", [
    "Is it safe to fish near Goa today in a 9 m boat?",
    "I'm leaving Kochi harbour at 5am in a 12m boat. Is it safe to go 20 NM offshore?",
    "My trawler is 15 metres long",
    "We fish in 8 m deep water near the reef",
    "Wind is 10 m/s, should I go?",
    "Waves are fine, my 9 m boat is ready",
    "The harbour is 3 m away from the jetty",
])
def test_boat_lengths_depths_and_distances_are_not_waves(text):
    assert "wave_height" not in orchestrator.extract_user_conditions(text)


@pytest.mark.parametrize("text, expected", [
    ("What if there are 3 m waves?", 3.0),
    ("The waves are 4 meters today", 4.0),
    ("swell of 2.5 m reported outside the harbour", 2.5),
    ("3.5 metre high waves near the bar", 3.5),
    ("waves around 2 m and a 9 m boat", 2.0),
    ("3 मीटर लहरें", 3.0),
])
def test_described_wave_heights_are_read(text, expected):
    assert orchestrator.extract_user_conditions(text)["wave_height"] == pytest.approx(expected)


def test_boat_length_does_not_change_a_calm_verdict():
    risk = calculate_risk(calm_marine(), calm_weather(), {},
                          user_message="Is it safe to fish near Goa today in a 9 m boat?")
    assert risk["risk_level"] == "LOW"
    assert not any("waves" in r.lower() and "9.0" in r for r in risk["reasons"])


def test_described_rough_sea_is_scored_and_attributed():
    risk = calculate_risk(calm_marine(), calm_weather(), {}, user_message="What if there are 3 m waves?")
    assert risk["risk_level"] != "LOW"
    assert any("as you described" in r for r in risk["reasons"])


def test_described_calm_sea_never_lowers_measured_waves():
    rough = calm_marine(wave_height=3.0, models={})
    risk = calculate_risk(rough, calm_weather(), {}, user_message="waves are only 1 m")
    assert any("3.0 m" in r and "as you described" not in r for r in risk["reasons"])


def test_emergency_message_is_critical():
    assert calculate_risk(calm_marine(), calm_weather(), {}, user_message="MAYDAY boat sinking")["risk_level"] == "CRITICAL"


def test_land_position_gives_land_message_not_safe():
    c = build_consensus({"data_available": False, "no_coverage": True}, calm_weather())
    risk = calculate_risk({}, calm_weather(), {}, consensus=c)
    advice = _get_fallback("SAFE", risk, calm_weather(), {}, {})
    assert "land" in advice["message"].lower()
    assert "suitable" not in advice["message"].lower()


def test_missing_data_advice_says_cannot_confirm():
    risk = calculate_risk({}, {}, {})
    advice = _get_fallback("PROCEED_WITH_CAUTION", risk, {}, {}, {})
    assert advice["message"].startswith("CANNOT CONFIRM SAFETY")


# --------------------------------------------------------------------------- location parsing
@pytest.mark.parametrize("text,expected", [
    ("conditions at 15.24, 73.80", (15.24, 73.80)),
    ("position 33.9S 18.4E", (-33.9, 18.4)),
    ("is it safe near Goa", (15.42, 73.78)),
    ("hello there", None),
])
def test_coordinate_and_port_extraction(text, expected):
    loc, _ = extract_location_and_zone_from_text(text)
    if expected is None:
        assert loc is None
    else:
        assert (loc.latitude, loc.longitude) == pytest.approx(expected)


def test_place_pattern_prefers_last_place(monkeypatch):
    seen = []

    async def fake_geocode(name):
        seen.append(name)
        return {"latitude": -29.86, "longitude": 31.03, "name": name}

    monkeypatch.setattr(orchestrator, "geocode_place", fake_geocode)
    loc, name = asyncio.run(orchestrator.resolve_location_from_text("Is it safe to fish near Durban today?"))
    assert name == "Durban" and loc.latitude == pytest.approx(-29.86)
    assert seen == ["Durban"]


# --------------------------------------------------------------------------- marine tool
def test_marine_currents_converted_to_knots_and_land_rejected(monkeypatch):
    payload = {"latitude": 15.2, "longitude": 73.5,
               "current": {"time": "2026-10-10T08:45", "wave_height": 0.6, "ocean_current_velocity": 1.852,
                           "sea_surface_temperature": 30.0},
               "hourly": {"time": ["2026-10-10T08:00"], "wave_height_marine_best_match": [0.6]}}

    async def fake_get(url, params=None, **kw):
        return CachedResponse(payload, 0.0)

    monkeypatch.setattr(marine_tools, "cached_get_json", fake_get)
    data = asyncio.run(marine_tools.get_marine_data(15.2, 73.5))
    assert data["current"]["ocean_current_velocity"] == pytest.approx(1.0, abs=0.01)  # 1.852 km/h = 1 kn

    payload = {"current": {"wave_height": None, "sea_surface_temperature": None}}
    with pytest.raises(marine_tools.MarineDataUnavailable):
        asyncio.run(marine_tools.get_marine_data(28.6, 77.2))


# --------------------------------------------------------------------------- route planner
def _install_fake_grid(monkeypatch, cell_fn):
    async def fake_marine(points, hours=12):
        out = []
        for lat, lon in points:
            kind = cell_fn(lat, lon)
            out.append(None if kind == "land" else {
                "wave_height": 3.0 if kind == "storm" else 0.5,
                "wave_height_max_12h": 3.0 if kind == "storm" else 0.6})
        return out

    async def fake_weather(points, hours=12):
        return [None if cell_fn(lat, lon) == "land" else {"wind_speed": 8.0, "wind_speed_max_12h": 10.0}
                for lat, lon in points]

    monkeypatch.setattr(route_planner, "get_marine_grid", fake_marine)
    monkeypatch.setattr(route_planner, "get_weather_grid", fake_weather)


def test_route_direct_when_open_calm_sea(monkeypatch):
    _install_fake_grid(monkeypatch, lambda lat, lon: "sea")
    r = asyncio.run(route_planner.plan_route(10.0, 70.0, 10.0, 71.0, "small"))
    assert r["verdict"] == "DIRECT_OK"
    assert r["route_conditions"]["hazard_cells_crossed"] == 0


def test_route_detours_around_storm(monkeypatch):
    # A storm band across the direct line, open water to the north.
    _install_fake_grid(monkeypatch, lambda lat, lon: "storm" if 70.4 <= lon <= 70.6 and lat < 10.25 else "sea")
    r = asyncio.run(route_planner.plan_route(10.0, 70.0, 10.0, 71.0, "small"))
    assert r["verdict"] == "DETOUR"
    assert r["route_conditions"]["hazard_cells_crossed"] == 0
    assert r["direct_conditions"]["hazard_cells_crossed"] > 0
    assert max(w["latitude"] for w in r["waypoints"]) > 10.2


def test_route_reports_no_safe_route(monkeypatch):
    _install_fake_grid(monkeypatch, lambda lat, lon: "storm" if 70.4 <= lon <= 70.6 else "sea")
    r = asyncio.run(route_planner.plan_route(10.0, 70.0, 10.0, 71.0, "small"))
    assert r["verdict"] == "NO_SAFE_ROUTE"
    # A large vessel tolerates 3 m waves (< 3.5 m limit).
    r = asyncio.run(route_planner.plan_route(10.0, 70.0, 10.0, 71.0, "large"))
    assert r["verdict"] == "DIRECT_OK"


def test_route_rejects_absurd_distances():
    with pytest.raises(route_planner.RouteError):
        asyncio.run(route_planner.plan_route(10.0, 70.0, 40.0, 150.0, "small"))
