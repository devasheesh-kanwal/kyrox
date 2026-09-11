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
# GPS DATA
# =========================================================
class GPSData(BaseModel):
    id: str = Field("user_location", description="Identifier for user GPS pin")
    name: str = Field("Your Current Location", description="Display name for location")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude of the vessel")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude of the vessel")
    type: str = Field("CURRENT_LOCATION", description="Type classification")
    marker_type: str = Field("USER", description="Cartographic marker symbol type")

# =========================================================
# WEATHER DATA
# =========================================================
class WeatherData(BaseModel):
    wind_speed: float = Field(..., ge=0, description="Wind speed in knots")
    wave_height: float = Field(..., ge=0, description="Significant wave height in meters")
    lightning_risk: Literal["LOW", "MEDIUM", "HIGH"]
    storm_risk: Literal["LOW", "MEDIUM", "HIGH"]
    temperature: Optional[float] = Field(None, description="Air temperature in Celsius")
    surface_pressure: Optional[float] = Field(None, description="Barometric pressure in hPa")
    wind_direction: Optional[float] = Field(None, description="Wind direction in degrees")

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
# RISK HEATMAP
# =========================================================
class RiskPoint(BaseModel):
    latitude: float = Field(..., ge=-90, le=90, description="Latitude of grid point")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude of grid point")
    risk: float = Field(..., ge=0, le=100, description="Calculated risk score (0-100)")
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(..., description="Categorized risk tier")

class HeatmapResponse(BaseModel):
    user_location: Location
    risk_points: List[RiskPoint]

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
    gps: Optional[GPSData] = None
    weather: WeatherData
    marine: MarineData
    geospatial: GeoData
    risk: RiskResult
    recommendation: Recommendation

# =========================================================
# USER REQUEST
# =========================================================
class UserRequest(BaseModel):
    message: str = Field("General maritime safety check", min_length=0, max_length=2000, description="User query or dispatch message")
    location: Optional[Location] = Field(None, description="Vessel GPS coordinates")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Direct latitude parameter")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Direct longitude parameter")
    zone_id: Optional[str] = Field(None, max_length=100, description="Active or queried navigational zone ID")
    context: Optional[dict] = Field(None, description="Optional telemetry or query context")
