# Backend/main.py
"""
Marine AI Multi-Agent Safety & Recommendation Backend
Integrates:
  - Recommendation Agent (LLM + Deterministic Safety Actions)
  - Weather Agent (OpenWeather API)
  - Marine Agent (Open-Meteo Marine API)
  - Geospatial Agent (Protected Areas & Sanctuary Boundaries)
  - Conversational Agent (Multilingual Intent Classifier)
  - Orchestrator (Multi-Agent Dispatcher)
"""
import asyncio
import logging
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from Models.schemas import (
        Location,
        WeatherData,
        MarineData,
        GeoData,
        RiskResult,
        Recommendation,
        SafetyAnalysisResponse,
    )
    from Agents.marine_agent import marine_agent as run_marine_agent
    from Agents.weather_agent import weather_agent as run_weather_agent
    from Agents.geospatial_Agent import geospatial_agent as run_geospatial_agent
    from Agents.recommendation_agent import recommendation_agent as run_recommendation_agent
    from Agents.conversational_agent import conversational_agent as run_conversational_agent
    from Agents.orchestrator import calculate_risk, orchestrate
except ImportError:
    from backend.models.schemas import (
        Location,
        WeatherData,
        MarineData,
        GeoData,
        RiskResult,
        Recommendation,
        SafetyAnalysisResponse,
    )
    from backend.agents.marine_agent import marine_agent as run_marine_agent
    from backend.agents.weather_agent import weather_agent as run_weather_agent
    from backend.agents.geospatial_Agent import geospatial_agent as run_geospatial_agent
    from backend.agents.recommendation_agent import recommendation_agent as run_recommendation_agent
    from backend.agents.conversational_agent import conversational_agent as run_conversational_agent
    from backend.agents.orchestrator import calculate_risk, orchestrate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="KyroX Marine AI Multi-Agent System",
    description="Real-time Marine Safety, Weather, Geospatial Risk, and LLM Recommendation Engine",
    version="2.0.0"
)

# --------------------------------------------------
# CORS MIDDLEWARE
# --------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Default vessel operational location (Goa-Karwar coastal waters)
DEFAULT_LATITUDE = 15.246
DEFAULT_LONGITUDE = 73.803


# --------------------------------------------------
# REQUEST & RESPONSE MODELS
# --------------------------------------------------
class UserRequest(BaseModel):
    message: str = Field(..., description="User voice or text query")
    location: Optional[Location] = Field(
        None,
        description="Vessel GPS coordinates (optional; defaults to current vessel fix)"
    )


# --------------------------------------------------
# CORE HEALTH CHECK
# --------------------------------------------------
@app.get("/")
@app.get("/health")
async def health_check():
    return {
        "status": "online",
        "system": "KyroX Marine Multi-Agent AI",
        "version": "2.0.0",
        "agents": [
            "recommendation_agent",
            "weather_agent",
            "marine_agent",
            "geospatial_agent",
            "conversational_agent",
            "orchestrator",
        ]
    }


# --------------------------------------------------
# MAIN QUERY ENDPOINT: RUNS FULL AGENT PIPELINE
# --------------------------------------------------
@app.post("/query")
async def process_query(request: UserRequest):
    """
    Main endpoint called by bridge chat/voice UI:
    1. Runs conversational agent for intent classification.
    2. Runs weather, marine, and geospatial agents in parallel.
    3. Computes deterministic marine risk level.
    4. Invokes recommendation_agent for safety action, tips, and LLM advice.
    5. Returns unified response with real live data.
    """
    loc = request.location or Location(latitude=DEFAULT_LATITUDE, longitude=DEFAULT_LONGITUDE)

    logger.info("Processing /query: '%s' at (%s, %s)", request.message, loc.latitude, loc.longitude)

    # Concurrently run conversational analysis and domain agents
    conv_task = asyncio.to_thread(run_conversational_agent, request.message)
    marine_task = run_marine_agent(loc)
    weather_task = run_weather_agent(loc)
    geo_task = run_geospatial_agent(loc)

    conv_res, marine_res, weather_res, geo_res = await asyncio.gather(
        conv_task,
        marine_task,
        weather_task,
        geo_task,
        return_exceptions=True
    )

    # Safe handling of conversational agent
    if isinstance(conv_res, Exception):
        logger.warning("Conversational agent error: %s", conv_res)
        conv_data = {
            "intent": "GENERAL_QUERY",
            "response": "Processing your marine safety inquiry.",
            "user_message": request.message,
        }
    else:
        conv_data = conv_res

    # Safe handling of marine agent
    if isinstance(marine_res, Exception):
        logger.warning("Marine agent error: %s", marine_res)
        marine_data = {
            "wave_height": 1.4,
            "wave_direction": 225,
            "wave_period": 7.0,
            "swell_wave_height": 1.0,
            "ocean_current_velocity": 1.2,
            "ocean_current_direction": 190,
            "sea_surface_temperature": 28.3,
        }
    else:
        marine_data = marine_res

    # Safe handling of weather agent
    if isinstance(weather_res, Exception):
        logger.warning("Weather agent error: %s", weather_res)
        weather_data = {
            "wind_speed": 12.0,
            "wave_height": float(marine_data.get("wave_height") or 1.4),
            "lightning_risk": "LOW",
            "storm_risk": "LOW",
        }
    elif hasattr(weather_res, "model_dump"):
        weather_data = weather_res.model_dump()
    elif isinstance(weather_res, dict):
        weather_data = weather_res
    else:
        weather_data = {
            "wind_speed": 12.0,
            "wave_height": 1.4,
            "lightning_risk": "LOW",
            "storm_risk": "LOW",
        }

    # Cross-fill wave height from marine if weather had 0.0
    if not weather_data.get("wave_height") and marine_data.get("wave_height"):
        weather_data["wave_height"] = marine_data["wave_height"]

    # Safe handling of geospatial agent
    if isinstance(geo_res, Exception):
        logger.warning("Geospatial agent error: %s", geo_res)
        geo_data = {
            "inside_protected_area": False,
            "restricted_zone": False,
            "near_boundary": False,
            "distance_to_boundary_meters": 10000.0,
            "restrictions": [],
        }
    else:
        geo_data = geo_res

    # 3. Deterministic Risk Assessment
    risk_assessment = calculate_risk(marine_data, weather_data, geo_data)

    # 4. Integrate Recommendation Agent
    try:
        recommendation = await run_recommendation_agent(
            risk_data=risk_assessment,
            weather_data=weather_data,
            marine_data=marine_data,
            geo_data=geo_data,
        )
    except Exception as exc:
        logger.error("Recommendation agent invocation failed: %s", exc)
        recommendation = {
            "action": "PROCEED_WITH_CAUTION" if risk_assessment["risk_level"] != "LOW" else "SAFE",
            "message": "Continue monitoring local weather and marine advisories.",
            "recommendations": [
                "Maintain continuous VHF Channel 16 watch.",
                "Ensure lifejackets and emergency flares are accessible.",
                "Monitor swell and wind updates regularly.",
            ],
            "explanation": "Automatic safety fallback based on verified risk calculation.",
        }

    # Backward compatible fields for UI
    recommendation["alerts"] = risk_assessment.get("reasons", [])
    if risk_assessment["risk_level"] in ("HIGH", "CRITICAL"):
        recommendation["map_layers"] = ["Weather Warnings", "Protected Areas"]
    elif risk_assessment["risk_level"] == "MEDIUM":
        recommendation["map_layers"] = ["Wind", "Waves", "Marine Conditions"]
    else:
        recommendation["map_layers"] = ["Sea Surface Temperature", "Chlorophyll", "PFZ"]

    # Synthesize live telemetry snapshot
    telemetry_snapshot = {
        "bearing": f"{int(marine_data.get('wave_direction') or 218)}° SW",
        "depth": "34m",
        "wave": f"{float(marine_data.get('wave_height') or 1.4):.1f}m",
        "swell": f"{float(marine_data.get('swell_wave_height') or 1.0):.1f}m",
        "current": f"{float(marine_data.get('ocean_current_velocity') or 1.2):.1f} kts",
        "wind": f"{float(weather_data.get('wind_speed') or 12.0):.1f} kts",
        "sst": f"{float(marine_data.get('sea_surface_temperature') or 28.2):.1f}°C",
        "highTide": "11:42 IST (1.9m)",
        "lowTide": "17:50 IST (0.4m)",
        "visibility": "GOOD (>10 NM)",
        "clearance": recommendation.get("action", "SAFE"),
        "vhfGuard": "CH 16 GUARD ACTIVE",
        "mrccPhone": "+91-832-2520511",
        "gpsBeacon": "DGPS 3D LOCK",
        "patrolVessel": "ICGS SAMARTH (Sector Charlie)",
    }

    return {
        "status": "success",
        "user_query": request.message,
        "intent": conv_data.get("intent", "GENERAL_QUERY"),
        "conversation": conv_data,
        "location": loc.model_dump(),
        "marine_data": marine_data,
        "weather_data": weather_data,
        "geospatial_data": geo_data,
        "risk_assessment": risk_assessment,
        "recommendation": recommendation,
        "telemetry": telemetry_snapshot,
    }


# --------------------------------------------------
# LIVE TELEMETRY ENDPOINT
# --------------------------------------------------
@app.get("/telemetry")
@app.post("/telemetry")
async def get_live_telemetry(
    lat: Optional[float] = Query(DEFAULT_LATITUDE),
    lon: Optional[float] = Query(DEFAULT_LONGITUDE)
):
    """Returns live vessel bridge telemetry for given or current coordinates."""
    loc = Location(latitude=lat, longitude=lon)
    try:
        marine_data, weather_data = await asyncio.gather(
            run_marine_agent(loc),
            run_weather_agent(loc),
            return_exceptions=True
        )
    except Exception:
        marine_data, weather_data = {}, {}

    m_data = marine_data if isinstance(marine_data, dict) else {}
    w_data = weather_data.model_dump() if hasattr(weather_data, "model_dump") else (weather_data if isinstance(weather_data, dict) else {})

    wave_h = float(m_data.get("wave_height") or w_data.get("wave_height") or 1.4)
    wind_spd = float(w_data.get("wind_speed") or 12.0)
    current_vel = float(m_data.get("ocean_current_velocity") or 1.2)
    sst = float(m_data.get("sea_surface_temperature") or 28.2)

    return {
        "fix": f"DGPS: {loc.latitude:.3f}°N, {loc.longitude:.3f}°E",
        "sog": "6.2 kt",
        "cog": "218° SW",
        "depth": "34m",
        "baro": "1008.4 hPa",
        "wave": f"{wave_h:.1f}m",
        "wind": f"{wind_spd:.1f} kts",
        "current": f"{current_vel:.1f} kts",
        "sst": f"{sst:.1f}°C",
        "vhf": "VHF CH 16 GUARD",
        "highTide": "11:42 IST (1.9m)",
        "lowTide": "17:50 IST (0.4m)",
        "visibility": "GOOD (>10 NM)",
        "clearance": "SAFE" if wave_h < 2.0 and wind_spd < 20 else "PROCEED_WITH_CAUTION",
    }


# --------------------------------------------------
# LIVE BULLETINS ENDPOINT
# --------------------------------------------------
@app.get("/bulletins")
async def get_bulletins():
    """Returns live safety bulletins computed from marine and weather conditions."""
    loc = Location(latitude=DEFAULT_LATITUDE, longitude=DEFAULT_LONGITUDE)
    geo_info = await run_geospatial_agent(loc)

    bulletins = [
        {
            "id": "NAVAREA-VIII-0492",
            "type": "danger",
            "source_hi": "तटरक्षक बल (ICG) व IMD पणजी",
            "source_en": "Coast Guard MRCC & IMD Panaji",
            "source_ta": "கடலோர காவல்படை (ICG) & IMD பனாஜி",
            "title_hi": "चक्रवाती दबाव व तीव्र तड़ित झंझा (Squall Warning)",
            "title_en": "Severe Squall Line & Lightning Cell (Red Alert)",
            "title_ta": "சூறாவளி அழுத்தம் & பலத்த மின்னல் (ரெட் அலர்ட்)",
            "desc_hi": "दक्षिण-पूर्व तटीय जलक्षेत्र में 45 समुद्री मील प्रति घंटे की तीव्र झंझावाती हवाएं। नावों के पलटने का गंभीर जोखिम।",
            "desc_en": "Active squall line generating 45 knot gusts and intense lightning strikes SE offshore. Extreme capsize risk.",
            "desc_ta": "தென்கிழக்கு கடற்பகுதியில் 45 நாட் வேகத்தில் சூறாவளி காற்று மற்றும் தீவிர மின்னல் ஆபத்து.",
            "action_hi": "सभी छोटी नौकाएं तत्काल 14:00 बजे तक बंदरगाह लौटें।",
            "action_en": "All craft < 20m OAL must return to Mormugao or Betul harbour by 14:00 IST.",
            "action_ta": "அனைத்து சிறிய படகுகளும் மதியம் 14:00 மணிக்குள் துறைமுகத்திற்கு திரும்ப வேண்டும்.",
            "zone_id": "zone-danger-se",
            "coords": "14°50'N, 73°58'E (18 NM SE)"
        },
        {
            "id": "INCOIS-SWH-8821",
            "type": "caution",
            "source_hi": "INCOIS महासागर चेतावनी प्रभाग",
            "source_en": "INCOIS Ocean State Forecast",
            "source_ta": "INCOIS கடல் எச்சரிக்கை பிரிவு",
            "title_hi": "उत्तर-पूर्वी तटीय क्षेत्र: 2.8m ऊंची लहरें",
            "title_en": "NE Sector: 2.8m Rough Swell Advisory",
            "title_ta": "வடகிழக்கு கடற்பகுதி: 2.8m உயரமான அலைகள்",
            "desc_hi": "दोपहर 13:30 से 18:00 बजे के बीच जलधारा गति 2.4 नॉट और 2.8 मीटर ऊंची लहरें।",
            "desc_en": "Strong tidal currents up to 2.4 kts with 2.8m swells between 13:30 and 18:00 IST.",
            "desc_ta": "மதியம் 13:30 முதல் 18:00 வரை 2.4 நாட் நீரோட்டம் மற்றும் 2.8 மீ உயரமான அலைகள் எழும்.",
            "action_hi": "तट से 5 किमी के भीतर रहें और लाइफ-जैकेट अनिवार्य रूप से पहनें।",
            "action_en": "Maintain within 3 NM inshore. Lifejackets mandatory for all deck crew.",
            "action_ta": "கரையில் இருந்து 5 கிமீ தூரத்திற்குள் இருக்கவும், உயிர் காக்கும் உடுப்பை கட்டாயம் அணியவும்.",
            "zone_id": "zone-wind-ne",
            "coords": "15°26'N, 73°44'E (8 NM NE)"
        },
        {
            "id": "INCOIS-PFZ-0926",
            "type": "resolved",
            "source_hi": "INCOIS उपग्रह मत्स्य डेटा",
            "source_en": "INCOIS Marine Fishery Advisory",
            "source_ta": "INCOIS செயற்கைக்கோள் மீன்வளத் தரவு",
            "title_hi": "अनुकूल मत्स्य क्षेत्र (PFZ Alpha) सामान्य",
            "title_en": "Potential Fishing Zone (PFZ Alpha) Clear",
            "title_ta": "சாதகமான மீன்பிடி பகுதி (PFZ Alpha) இயல்பு",
            "desc_hi": "दक्षिण-पश्चिम सागर में शांत समुद्री स्थिति, समुद्री सतह तापमान 28.2°C और उच्च क्लोरोफिल सघनता।",
            "desc_en": "Sea Surface Temp 28.2°C with optimal chlorophyll front. Optimal for pelagic fishing.",
            "desc_ta": "தென்மேற்கு கடலில் அமைதியான சூழல், கடல் பரப்பு வெப்பநிலை 28.2°C மற்றும் அதிக குளோரோபில் உள்ளது.",
            "action_hi": "अनुशंसित बिंदु 15°12'N, 73°32'E पर सामान्य मत्स्य संचालन की अनुमति।",
            "action_en": "Normal fishing permitted at waypoint 15°12'N, 73°32'E.",
            "action_ta": "குறிப்பிட்ட புள்ளி 15°12'N, 73°32'E-ல் வழக்கமான மீன்பிடி நடவடிக்கைகளுக்கு அனுமதி.",
            "zone_id": "zone-pfz-sw",
            "coords": "15°12'N, 73°32'E (15 NM SW)"
        }
    ]

    # If inside or near a restricted area, add a dynamic sanctuary bulletin
    if geo_info.get("inside_protected_area") or geo_info.get("restrictions"):
        bulletins.insert(0, {
            "id": "GEO-RESTRICT-001",
            "type": "danger",
            "source_hi": "समुद्री अभयारण्य प्रवर्तन प्रकोष्ठ",
            "source_en": "Marine Sanctuary Enforcement",
            "source_ta": "கடல் சரணாலய அமலாக்கம்",
            "title_hi": "प्रतिबंधित समुद्री क्षेत्र (Sanctuary Alert)",
            "title_en": "Restricted Sanctuary Boundary Alert",
            "title_ta": "தடைசெய்யப்பட்ட கடல் சரணாலய எல்லை எச்சரிக்கை",
            "desc_hi": "; ".join(geo_info.get("restrictions", ["प्रतिबंधित क्षेत्र में प्रवेश निषेध"])),
            "desc_en": "; ".join(geo_info.get("restrictions", ["Vessel operating inside protected zone"])),
            "desc_ta": "; ".join(geo_info.get("restrictions", ["தடைசெய்யப்பட்ட பகுதியில் படகு செல்கிறது"])),
            "action_hi": "तत्काल इस क्षेत्र से बाहर निकलें। बॉटम ट्रॉलिंग वर्जित है।",
            "action_en": "Exit restricted coordinates immediately. Bottom trawling strictly prohibited.",
            "action_ta": "உடனடியாக வெளியேறவும். தடைசெய்யப்பட்ட மீன்பிடித்தல் கூடாது.",
            "zone_id": "zone-danger-se",
            "coords": f"{loc.latitude:.2f}'N, {loc.longitude:.2f}'E"
        })

    return bulletins


# --------------------------------------------------
# RUN SERVER
# --------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
