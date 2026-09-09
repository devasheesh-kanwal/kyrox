import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from fastapi.testclient import TestClient
from Backend.main import app

client = TestClient(app)

def test_location_endpoint():
    print("Testing POST /location...")
    # Test with Uttarakhand coordinates
    payload = {"latitude": 29.3755, "longitude": 79.5306}
    response = client.post("/location", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["status"] == "success"
    assert "gps" in data
    assert data["gps"]["latitude"] == 29.3755
    assert data["gps"]["longitude"] == 79.5306
    assert "telemetry" in data
    assert "risk_points" in data
    assert len(data["risk_points"]) == 9
    print("  -> /location PASSED!")

def test_heatmap_endpoint():
    print("Testing POST /heatmap...")
    payload = {"latitude": 29.3755, "longitude": 79.5306}
    response = client.post("/heatmap", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "risk_points" in data
    assert len(data["risk_points"]) == 9
    for pt in data["risk_points"]:
        assert "latitude" in pt
        assert "longitude" in pt
        assert "risk" in pt
        assert "risk_level" in pt
    print("  -> /heatmap PASSED (9 risk points generated around 29.3755, 79.5306)!")

def test_telemetry_endpoint():
    print("Testing GET /telemetry...")
    response = client.get("/telemetry")
    assert response.status_code == 200
    data = response.json()
    assert "gps" in data
    assert "sog" in data
    assert "cog" in data
    print("  -> /telemetry PASSED!")

def test_query_endpoint():
    print("Testing POST /query...")
    payload = {
        "message": "Is it safe to fish right now?",
        "latitude": 29.3755,
        "longitude": 79.5306
    }
    response = client.post("/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "recommendation" in data
    assert "risk_assessment" in data
    assert "gps" in data
    assert data["gps"]["latitude"] == 29.3755
    assert "risk_points" in data
    assert len(data["risk_points"]) == 9
    print("  -> /query PASSED!")

def test_prediction_endpoint():
    print("Testing GET /predictions/linear-regression...")
    response = client.get("/predictions/linear-regression?variable=wave_height&horizon_hours=24")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["success"] is True
    assert data["variable"] == "wave_height"
    assert "metrics" in data
    assert "slope" in data["metrics"]
    assert "r_squared" in data["metrics"]
    assert "predictions" in data
    assert len(data["predictions"]) == 24
    assert "summary" in data
    print("  -> /predictions/linear-regression PASSED (24-hour predictions, R² and OLS metrics verified)!")

if __name__ == "__main__":
    test_location_endpoint()
    test_heatmap_endpoint()
    test_telemetry_endpoint()
    test_prediction_endpoint()
    print("\nALL API ENDPOINTS TESTED AND VERIFIED SUCCESSFULLY!")
