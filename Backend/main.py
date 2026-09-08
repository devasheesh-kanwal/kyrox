from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import asyncio
import logging

from Models.schemas import Location

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Marine AI Multi-Agent System",
    description="Marine, Weather and Geospatial Risk Analysis",
    version="1.0.0"
)

# --------------------------------------------------
# CORS MIDDLEWARE
# --------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # TODO: restrict to specific origins in production
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# --------------------------------------------------
# REQUEST MODEL
# --------------------------------------------------

# Location is imported from Models.schemas (includes lat/lon range validation)


class UserRequest(BaseModel):
    message: str
    location: Optional[Location] = None


# --------------------------------------------------
# RESPONSE MODELS
# --------------------------------------------------

class MarineResult(BaseModel):
    sst: float
    chlorophyll: float
    pfz_score: float


class WeatherResult(BaseModel):
    wind_speed: float
    wave_height: float
    lightning_risk: str
    storm_risk: str


class GeospatialResult(BaseModel):
    inside_protected_area: bool
    restrictions: list[str]


# --------------------------------------------------
# MARINE AGENT
# --------------------------------------------------

async def marine_agent(location: Location):

    # TODO:
    # Replace these values with real Marine API data

    return {
        "sst": 28.5,
        "chlorophyll": 1.2,
        "pfz_score": 0.82
    }


# --------------------------------------------------
# WEATHER AGENT
# --------------------------------------------------

async def weather_agent(location: Location):

    # TODO:
    # Replace with real weather API


    return {
        "wind_speed": 18.0,
        "wave_height": 1.5,
        "lightning_risk": "LOW",
        "storm_risk": "LOW"
    }


# --------------------------------------------------


# --------------------------------------------------

async def geospatial_agent(location: Location):

    # TODO:
    # Replace with PostGIS / GIS API

    return {
        "inside_protected_area": False,
        "restrictions": []
    }


# --------------------------------------------------
# RISK AGENT
# --------------------------------------------------

def calculate_risk(marine, weather, geospatial):

    score = 0
    reasons = []

    # WEATHER RISK

    if weather["wave_height"] > 3:
        score += 40
        reasons.append("High wave height")

    if weather["wind_speed"] > 30:
        score += 30
        reasons.append("Strong wind")

    if weather["lightning_risk"] == "HIGH":
        score += 40
        reasons.append("High lightning risk")

    if weather["storm_risk"] == "HIGH":
        score += 50
        reasons.append("Storm risk detected")

    # GEOSPATIAL RISK

    if geospatial["inside_protected_area"]:
        score += 50
        reasons.append("Location is inside a protected area")

    # RISK LEVEL

    if score >= 70:
        risk_level = "HIGH"

    elif score >= 40:
        risk_level = "MEDIUM"

    else:
        risk_level = "LOW"

    return {
        "risk_score": min(score, 100),
        "risk_level": risk_level,
        "reasons": reasons
    }


# --------------------------------------------------
# RECOMMENDATION AGENT
# --------------------------------------------------

def generate_recommendation(risk, marine):

    if risk["risk_level"] == "HIGH":

        return {
            "message": (
                "High marine risk detected. "
                "Marine activity is not recommended."
            ),
            "map_layers": [
                "Weather Warnings",
                "Protected Areas"
            ],
            "alerts": risk["reasons"]
        }

    elif risk["risk_level"] == "MEDIUM":

        return {
            "message": (
                "Moderate marine risk detected. "
                "Proceed with caution and monitor weather conditions."
            ),
            "map_layers": [
                "Wind",
                "Waves",
                "Marine Conditions"
            ],
            "alerts": risk["reasons"]
        }

    else:

        message = "Conditions appear relatively safe."

        if marine["pfz_score"] > 0.8:
            message += " A potential fishing zone has also been detected."

        return {
            "message": message,
            "map_layers": [
                "Sea Surface Temperature",
                "Chlorophyll",
                "PFZ"
            ],
            "alerts": []
        }


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/")
async def root():

    return {
        "message": "Marine AI Multi-Agent System is running"
    }


# --------------------------------------------------
# MAIN API ENDPOINT
# --------------------------------------------------

@app.post("/query")
async def process_query(request: UserRequest):

    # Check location

    if request.location is None:

        return {
            "error": "Location is required for marine analysis"
        }

    # ------------------------------------------------
    # ORCHESTRATOR
    #
    # Run Marine, Weather and Geospatial Agents
    # in parallel
    # ------------------------------------------------

    marine, weather, geospatial = await asyncio.gather(

        marine_agent(request.location),

        weather_agent(request.location),

        geospatial_agent(request.location)
    )

    # ------------------------------------------------
    # RISK AGENT
    # ------------------------------------------------

    risk = calculate_risk(
        marine,
        weather,
        geospatial
    )

    # ------------------------------------------------
    # RECOMMENDATION AGENT
    # ------------------------------------------------

    recommendation = generate_recommendation(
        risk,
        marine
    )

    # ------------------------------------------------
    # FINAL RESPONSE
    # ------------------------------------------------

    return {

        "user_query": request.message,

        "location": request.location,

        "marine_data": marine,

        "weather_data": weather,

        "geospatial_data": geospatial,

        "risk_assessment": risk,

        "recommendation": recommendation
    }


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
