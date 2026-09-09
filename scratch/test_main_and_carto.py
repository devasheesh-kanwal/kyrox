import os
import sys
from unittest.mock import patch, AsyncMock

# Add Backend to path
backend_path = os.path.abspath('Backend')
sys.path.insert(0, backend_path)

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    res = client.get('/health')
    assert res.status_code == 200, f"Health check failed: {res.status_code}"
    data = res.json()
    assert data['status'] == 'online'
    print("[PASS] Backend health check OK")

def test_location_endpoint():
    mock_heatmap = {
        "user_location": {"latitude": 15.25, "longitude": 73.80},
        "risk_points": [
            {"latitude": 15.215, "longitude": 73.765, "risk": 42.5, "risk_level": "MEDIUM"},
            {"latitude": 15.215, "longitude": 73.800, "risk": 38.0, "risk_level": "MEDIUM"},
            {"latitude": 15.215, "longitude": 73.835, "risk": 31.2, "risk_level": "MEDIUM"},
            {"latitude": 15.250, "longitude": 73.765, "risk": 55.4, "risk_level": "HIGH"},
            {"latitude": 15.250, "longitude": 73.800, "risk": 25.0, "risk_level": "LOW"},
            {"latitude": 15.250, "longitude": 73.835, "risk": 48.1, "risk_level": "MEDIUM"},
            {"latitude": 15.285, "longitude": 73.765, "risk": 68.2, "risk_level": "HIGH"},
            {"latitude": 15.285, "longitude": 73.800, "risk": 72.0, "risk_level": "HIGH"},
            {"latitude": 15.285, "longitude": 73.835, "risk": 82.5, "risk_level": "CRITICAL"}
        ]
    }
    with patch('main.generate_risk_heatmap', new=AsyncMock(return_value=mock_heatmap)):
        res = client.post('/location', json={'latitude': 15.25, 'longitude': 73.80})
        assert res.status_code == 200, f"/location failed: {res.status_code}"
        data = res.json()
        assert data['status'] == 'success'
        assert 'gps' in data
        assert 'risk_points' in data
        assert len(data['risk_points']) == 9
        print(f"[PASS] /location returned {len(data['risk_points'])} risk points successfully")

def test_risk_analysis_endpoint():
    mock_heatmap = {
        "user_location": {"latitude": 15.25, "longitude": 73.80},
        "risk_points": [
            {"latitude": 15.25, "longitude": 73.80, "risk": 30.0, "risk_level": "MEDIUM"}
        ]
    }
    with patch('main.generate_risk_heatmap', new=AsyncMock(return_value=mock_heatmap)):
        res = client.post('/api/v1/risk-analysis', json={'latitude': 15.25, 'longitude': 73.80})
        assert res.status_code == 200, f"/api/v1/risk-analysis failed: {res.status_code}"
        data = res.json()
        assert 'risk_points' in data
        print("[PASS] /api/v1/risk-analysis endpoint OK")

        res_heatmap = client.post('/heatmap', json={'latitude': 15.25, 'longitude': 73.80})
        assert res_heatmap.status_code == 200, f"/heatmap failed: {res_heatmap.status_code}"
        print("[PASS] /heatmap endpoint OK")

def test_query_canonical():
    mock_rec = {
        "action": "SAFE",
        "message": "Conditions are calm and safe.",
        "recommendations": ["Safe fishing permitted."],
        "explanation": "Low wind and wave height."
    }
    with patch('main.run_recommendation_agent', new=AsyncMock(return_value=mock_rec)):
        res = client.post('/query', json={'message': 'Is it safe to fish?', 'latitude': 15.25, 'longitude': 73.80})
        assert res.status_code == 200, f"/query failed: {res.status_code}"
        data = res.json()
        assert data['status'] == 'success'
        # Canonical keys
        for k in ['location', 'chat', 'weather', 'marine', 'geospatial', 'risk', 'recommendation', 'heatmap', 'alerts']:
            assert k in data, f"Missing canonical key '{k}' in /query response"
        assert 'risk_score' in data['risk']
        assert 'risk_level' in data['risk']
        assert 'risk_points' in data['heatmap']
        print("[PASS] /query returns full canonical contract successfully")

def test_no_keys_in_source():
    forbidden_terms = ['CARTO_API_KEY=', 'key=']
    # Check that in source files, no real keys are hardcoded
    with open('map_config.js', 'r', encoding='utf-8') as f:
        js = f.read()
    assert 'CARTO_API_KEY || \'\'' in js
    assert not ('CARTO_API_KEY = "' in js and len(js.split('CARTO_API_KEY = "')[1].split('"')[0]) > 5)
    print("[PASS] No hardcoded CARTO API keys in JS source")

if __name__ == '__main__':
    test_health()
    test_location_endpoint()
    test_risk_analysis_endpoint()
    test_query_canonical()
    test_no_keys_in_source()
    print("\n--- ALL BACKEND INTEGRATION TESTS PASSED (100%) ---")
