# backend/tools/marine_tools.py
import os
import httpx  
from dotenv import load_dotenv


load_dotenv()

NASA_API_KEY = os.getenv("NASA_API_KEY")

async def fetch_nasa_marine_data(latitude: float, longitude: float):
    """
    Async tool to fetch data from NASA. 
    Uses .env for the API key, and httpx for non-blocking requests.
    """
    # Example URL - replace with your actual marine/weather endpoint later
    url = "https://api.nasa.gov/planetary/apod"
    
    params = {
        "api_key": NASA_API_KEY,
        # Add lat/lon if the API supports it
        # "lat": latitude,
        # "lon": longitude
    }

    # Use async with to prevent blocking the event loop
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        
        # Using 'response.raise_for_status()' or checking 'is_success' is best
        if response.is_success:  # Equivalent to response.ok in requests
            data = response.json()
            print(data)  # Replace this with parsing logic later
            
            # TODO: Map the real data to your expected format
            return {
                "sst": 28.5,        # Replace with data.get("sst")
                "chlorophyll": 1.2,  # Replace with data.get("chlorophyll")
                "pfz_score": 0.82    # Replace with data.get("pfz")
            }
        else:
            # Raise an exception so your agent knows it failed
            raise Exception(f"NASA API Error: {response.status_code} - {response.text}")