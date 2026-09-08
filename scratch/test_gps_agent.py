import sys
import os
import math
sys.path.insert(0, os.path.abspath('.'))

from Backend.Agents.gps_agent import gps_agent
from Backend.Models.schemas import Location

def test_gps_agent_variations():
    # 1. Standard float input
    res1 = gps_agent(15.2460123, 73.8030456)
    assert res1["id"] == "user_location"
    assert res1["latitude"] == 15.246012
    assert res1["longitude"] == 73.803046
    assert res1["type"] == "CURRENT_LOCATION"
    assert res1["marker_type"] == "USER"
    print("Test 1 (Standard floats) passed!")

    # 2. String numeric input
    res2 = gps_agent("29.3755", "79.5306")
    assert res2["latitude"] == 29.3755
    assert res2["longitude"] == 79.5306
    print("Test 2 (String floats) passed!")

    # 3. Location object input
    loc = Location(latitude=15.2, longitude=73.8)
    res3 = gps_agent(loc)
    assert res3["latitude"] == 15.2
    assert res3["longitude"] == 73.8
    print("Test 3 (Location model) passed!")

    # 4. Dictionary input
    res4 = gps_agent({"latitude": 18.5, "longitude": 72.8})
    assert res4["latitude"] == 18.5
    assert res4["longitude"] == 72.8
    print("Test 4 (Dictionary) passed!")

    # 5. Out of bounds latitude
    try:
        gps_agent(95.0, 73.0)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print("Test 5 (Out of bounds lat) passed:", e)

    # 6. Out of bounds longitude
    try:
        gps_agent(15.0, 185.0)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print("Test 6 (Out of bounds lon) passed:", e)

    # 7. Non-numeric
    try:
        gps_agent("invalid", 73.0)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print("Test 7 (Non-numeric) passed:", e)

    # 8. NaN / Inf
    try:
        gps_agent(float('nan'), 73.0)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print("Test 8 (NaN) passed:", e)

    try:
        gps_agent(float('inf'), 73.0)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print("Test 8b (Inf) passed:", e)

    # 9. None
    try:
        gps_agent(None, None)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print("Test 9 (None) passed:", e)

    print("\nALL GPS AGENT TESTS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    test_gps_agent_variations()
