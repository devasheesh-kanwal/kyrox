import os
import requests

NASA_API_KEY = os.getenv("NASA_API_KEY")

url = "https://api.nasa.gov/planetary/apod"

params = {
    "api_key": "8ECQNb6q6f9b7rD7h84pl1n8fZmpufeoccSDJss5"
}

response = requests.get(url, params=params)

if response.status_code == 200:
    data = response.json()
    print(data)
else:
    print("Error:", response.status_code)