# KyroX

KyroX is a marine safety dashboard with a FastAPI backend and a browser frontend.

## Windows quick start

1. Install Python 3.10 or newer from <https://www.python.org/downloads/>. During installation, enable **Add Python to PATH**.
2. Double-click `run_app.bat`.
3. The app opens at <http://localhost:5500/index.html>.

The first start creates `Backend\.venv` and installs the required Python packages. Keep both terminal windows open while using the app. On later starts, dependencies are checked automatically.

Do not open `Frontend\index.html` by double-clicking it. Serving the frontend through localhost is required for browser geolocation and avoids local-file security restrictions.

## Manual start

From the repository folder, run these commands in separate terminals:

```bat
Backend\run_server.bat
Frontend\run_frontend.bat
```

Then open <http://localhost:5500/index.html>.

## Optional configuration

The app uses Open-Meteo's keyless weather and marine APIs by default. Optional provider settings can be placed in `Backend\.env`:

```text
HF_TOKEN=your_huggingface_token
WEATHER_KEY=your_openweather_key
WEATHER_URL=https://api.openweathermap.org/data/2.5/weather
```

Without `HF_TOKEN`, the backend uses its built-in deterministic safety fallback for recommendations. Without OpenWeather credentials, it falls back to Open-Meteo.

If Windows Firewall asks whether Python may communicate on private networks, allow it so the browser can reach the local backend.
