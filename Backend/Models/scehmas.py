# backend/models/schemas.py
from pydantic import BaseModel
from typing import Optional, List

class Location(BaseModel):
    latitude: float
    longitude: float

class UserRequest(BaseModel):
    message: str
    location: Optional[Location] = None

# Optional response schemas (for better documentation)
class MarineData(BaseModel):
    sst: float
    chlorophyll: float
    pfz_score: float

class WeatherData(BaseModel):
    wind_speed: float
    wave_height: float
    lightning_risk: str
    storm_risk: str

class GeospatialData(BaseModel):
    inside_protected_area: bool
    restrictions: List[str]

class RiskAssessment(BaseModel):
    risk_score: int
    risk_level: str
    reasons: List[str]

class Recommendation(BaseModel):
    message: str
    map_layers: List[str]
    alerts: List[str]