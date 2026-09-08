import httpx


async def weather_agent(location: Location):
    """Fetches real-time weather and marine data using the OpenWeather API."""
    # Ensure you have your API key stored safely in environment variables
    import os

    api_key = os.getenv("OPENWEATHER_API_KEY", "your_api_key_here")

    # Assuming 'location' object has latitude and longitude attributes
    lat = location.latitude
    lon = location.longitude

    # Using One Call API 3.0 (Requires a subscription, handles daily/hourly)
    # Alternatively, use standard weather endpoint: f"https://openweathermap.org{lat}&lon={lon}&appid={api_key}"
    url = f"https://openweathermap.org{lat}&lon={lon}&exclude=minutely,hourly,daily,alerts&appid={api_key}&units=metric"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            current = data.get("current", {})
            wind_speed = current.get("wind_speed", 0.0)

            # Note: Standard OpenWeather endpoints do not provide marine data like wave height.
            # Lightning/Storm risk can be inferred roughly from the weather condition IDs.
            weather_id = current.get("weather", [{}])[0].get("id", 800)

            # OpenWeather IDs in the 2xx range denote Thunderstorms
            lightning_risk = "HIGH" if 200 <= weather_id <= 299 else "LOW"

            # OpenWeather IDs indicating severe storm conditions
            storm_risk = (
                "HIGH"
                if (200 <= weather_id <= 299)
                or weather_id in [502, 503, 504, 781]
                else "LOW"
            )

            return {
                "wind_speed": float(wind_speed),
                "wave_height": 0.0,  # OpenWeather doesn't support wave heights natively
                "lightning_risk": lightning_risk,
                "storm_risk": storm_risk,
            }

        except httpx.HTTPStatusError as e:
            # Fallback or error handling logic
            return {
                "error": f"API request failed with status {e.response.status_code}",
                "wind_speed": 0.0,
                "wave_height": 0.0,
                "lightning_risk": "UNKNOWN",
                "storm_risk": "UNKNOWN",
            }