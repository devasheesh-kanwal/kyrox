from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# =========================================================
# LOCATION
# =========================================================
class Location(BaseModel):
    latitude: float = Field(
        ...,
        ge=-90,
        le=90,
        description="Latitude of the vessel"
    )
    longitude: float = Field(
        ...,
        ge=-180,
        le=180,
        description="Longitude of the vessel"
    )

# =========================================================
# WEATHER DATA
# =========================================================
class WeatherData(BaseModel):
    wind_speed: float = Field(..., ge=0, description="Wind speed in knots or m/s")
    wave_height: float = Field(..., ge=0, description="Significant wave height in meters")
    lightning_risk: Literal["LOW", "MEDIUM", "HIGH"]
    storm_risk: Literal["LOW", "MEDIUM", "HIGH"]

# =========================================================
# MARINE DATA
# =========================================================
class MarineData(BaseModel):
    sea_state: Literal["CALM", "MODERATE", "ROUGH", "VERY_ROUGH"]
    current_speed: float = Field(..., ge=0, description="Current speed in knots")
    visibility: Literal["EXCELLENT", "GOOD", "POOR", "ZERO"]
    water_temperature: Optional[float] = Field(None, description="Temperature in Celsius")

# =========================================================
# GEOSPATIAL DATA
# =========================================================
class GeoData(BaseModel):
    near_boundary: bool
    distance_to_boundary_meters: float = Field(..., ge=0)
    restricted_zone: bool
    distance_to_shore_meters: Optional[float] = Field(None, ge=0)

# =========================================================
# RISK ANALYSIS
# =========================================================
class RiskResult(BaseModel):
    risk_score: float = Field(..., ge=0, le=100)
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    reasons: List[str]

# =========================================================
# RECOMMENDATION
# =========================================================
class Recommendation(BaseModel):
    action: Literal["SAFE", "PROCEED_WITH_CAUTION", "RETURN_TO_SHORE", "DO_NOT_PROCEED"]
    message: str
    recommendations: List[str]
    explanation: Optional[str] = None

# =========================================================
# FINAL RESPONSE
# =========================================================
class SafetyAnalysisResponse(BaseModel):
    location: Location
    weather: WeatherData
    marine: MarineData
    geospatial: GeoData
    risk: RiskResult
    recommendation: Recommendation

# =========================================================
# USER REQUEST
# =========================================================
class UserRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User query or dispatch message")
    location: Optional[Location] = Field(None, description="Vessel GPS coordinates")
    zone_id: Optional[str] = Field(None, max_length=100, description="Active or queried navigational zone ID")
    context: Optional[dict] = Field(None, description="Optional telemetry or query context")
