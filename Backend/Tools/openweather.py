import requests

# Apni OpenWeather API key yahan daalo
API_KEY = "WEATHER_KEY"

# Jis location ka weather chahiye
CITY = "Haldwani"

# OpenWeather API URL
url = "WEATHER_URL"

# API ko bhejne wale parameters
params = {
    "q": CITY,
    "appid": API_KEY,
    "units": "metric"
}

# API request
response = requests.get(url, params=params)

# Response check
if response.status_code == 200:
    data = response.json()

    temperature = data["main"]["temp"]
    humidity = data["main"]["humidity"]
    weather = data["weather"][0]["description"]
    wind_speed = data["wind"]["speed"]

    print("Location:", CITY)
    print("Temperature:", temperature, "°C")
    print("Humidity:", humidity, "%")
    print("Weather:", weather)
    print("Wind Speed:", wind_speed, "m/s")

else:
    print("API Error:", response.status_code)
    print(response.text)