# ORCA: marine safety agents for fishers

ORCA tells a fisher, in plain words and in their own language, whether it is safe to go to sea from their exact position, and why.

It combines weather and wave forecasts, official warnings, protected areas and threatened-species records. Specialist AI agents each read one source, a consensus agent cross-checks them, and the app gives one verdict: **Suitable to go out**, **Go out with caution**, **Return to shore** or **Do not go to sea**.

Built for **Smart India Hackathon, problem SIH26176 (ISRO)**.

> ORCA is a planning aid. Always follow official warnings and local authorities. In distress: **VHF channel 16**, **India Coast Guard 1554**.

---

## Features

| Area | What it does |
|---|---|
| **Overview** | Verdict with reasons, risk gauge (0 to 100), 12-hour wave and wind trends, live map with a risk grid |
| **Live map** | Search any port, coast or coordinates; risk layer; safe-route planner by boat size |
| **Warnings** | Official INCOIS high-wave / swell-surge alerts and GDACS cyclones / tsunamis, plus the agents' live assessment |
| **Protected species** | IUCN Red List species recorded within ~25 km (OBIS), with photos and bycatch advice |
| **Forecast** | 24-hour forecast for waves, wind, swell, current and sea-state risk, with model spread and verification against the last 24 h |
| **Ask ORCA** | Chat in 22 Indian languages, with voice input and read-aloud; shows which agents answered and how ORCA decided |
| **Accessibility** | Works on phones, tablets and desktop; dark and high-contrast "Sunlight" themes; keyboard shortcuts (1 to 6, `/`) |

Missing data is never treated as calm: if a source cannot be reached, ORCA says so instead of guessing.

---

## How ORCA decides

```
            ┌─ Weather agent ........ ECMWF + NOAA wind, gusts, pressure (Open-Meteo)
            ├─ Marine agent ......... waves, swell, currents, sea temperature (Open-Meteo Marine)
question ──>├─ Official alerts agent  INCOIS + GDACS warnings near you
            ├─ Geospatial agent ..... marine reserves and restricted areas (OpenStreetMap)
            ├─ Ecosystem agent ...... threatened species records (OBIS)
            └─ Conversational agent . understands the question, place and language
                        │
                        v
               Consensus agent ...... compares sources, flags disagreement,
                        │             keeps the more cautious value
                        v
               Risk score (0-100) ... deterministic and explainable
                        │
                        v
               Recommendation agent . plain-language advice (rule-based;
                                      LLM-written if HF_TOKEN is set)
```

The risk score is rule-based and covered by tests, so the safety decision never depends on an LLM.

---

## Quick start (Windows)

**You need:** Python 3.10 or newer ([python.org](https://www.python.org/downloads/)). During installation, tick **Add Python to PATH**.

1. Clone the repository:
   ```bash
   git clone https://github.com/devasheesh-kanwal/kyrox.git
   ```
2. Double-click **`run_app.bat`** in the project folder.
3. Your browser opens **http://localhost:5500/**.

The first start creates `Backend\.venv` and installs the Python packages (needs internet). Keep both terminal windows open while you use the app. If Windows Firewall asks, allow Python on private networks.

### Manual start

In two separate terminals, from the project folder:

```bash
Backend\run_server.bat
```
```bash
Frontend\run_frontend.bat
```

Then open http://localhost:5500/. The backend runs on port **8000** and the frontend on port **5500**.

> Do not open `Frontend\index.html` by double-clicking it. It must be served from `localhost` (browser location access and API calls need it).

### Open it on a phone

1. Start the app with `run_app.bat` on your PC.
2. Connect the phone to the **same Wi-Fi**.
3. Find your PC's IP address (run `ipconfig`, look for **IPv4 Address**).
4. On the phone, open `http://<your-PC-IP>:5500`.

"My location" (GPS) only works on `localhost` or HTTPS, so on a phone pick a port or search for a place instead.

---

## Configuration (optional)

ORCA works **without any API keys**: it uses Open-Meteo, INCOIS, GDACS, OBIS and OpenStreetMap, which are free and keyless.

To change settings, create `Backend/.env` (it is git-ignored, never commit it):

```env
# LLM-written advice (rule-based advice is used without it)
HF_TOKEN=
# HF_CHAT_MODEL=mistralai/Mistral-7B-Instruct-v0.3

# Extra independent wind cross-check
WEATHER_KEY=
WEATHER_URL=https://api.openweathermap.org/data/2.5/weather

# Deployment
ALLOWED_ORIGINS=*            # comma-separated frontend origins
RATE_LIMIT_PER_MINUTE=120    # per client IP, 0 disables
```

The frontend reads an optional `Frontend/env.js` (copy `Frontend/env.example.js`), for example to point at a deployed backend:

```js
window.__ENV__ = { KYROX_API_BASE: "https://your-backend.example.com" };
```

---

## Tests

Offline tests for the safety-critical logic (risk scoring, consensus, official alerts, wave-height parsing, route planning). No network needed.

```bash
Backend\.venv\Scripts\python.exe -m pip install -r Backend\requirements-dev.txt
```
```bash
Backend\.venv\Scripts\python.exe -m pytest tests -q
```

---

## Docker (backend)

```bash
docker build -t orca-backend Backend
```
```bash
docker run -p 8000:8000 --env-file Backend/.env orca-backend
```

Serve the `Frontend` folder with any static web server and set `KYROX_API_BASE` in `Frontend/env.js` to the backend URL.

---

## Main API endpoints

Backend: `http://localhost:8000`. Interactive docs: **http://localhost:8000/docs**.

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/query` | Ask a question; returns the verdict, advice, reasons and agent trace |
| `GET` | `/telemetry?lat=&lon=` | Live conditions and risk for a position |
| `GET` | `/bulletins?lat=&lon=` | Official warnings and the live assessment |
| `GET` | `/alerts/official?lat=&lon=` | INCOIS and GDACS alerts near a position |
| `GET` | `/ecosystem?lat=&lon=` | Threatened species recorded nearby (OBIS) |
| `GET` | `/predictions/forecast?variable=&lat=&lon=` | 24 h forecast with model spread and verification |
| `GET`/`POST` | `/heatmap` | Risk grid around a position |
| `POST` | `/route` | Safest route for a vessel size |
| `GET` | `/geocode?q=` | Place name to coordinates |
| `GET`/`POST` | `/translate` | Translate text into an Indian language |
| `GET` | `/health` | Service status |

---

## Project structure

```
kyrox/
├── run_app.bat              starts backend + frontend and opens the browser
├── Backend/
│   ├── main.py              FastAPI app and endpoints
│   ├── Agents/              weather, marine, geospatial, ecosystem, conversational,
│   │                        consensus, recommendation agents + orchestrator (risk score)
│   ├── Tools/               data-source clients (Open-Meteo, INCOIS/GDACS, OSM, ...)
│   ├── Services/            forecast, route planner, translation, HTTP cache
│   ├── Models/              request / response schemas
│   ├── requirements.txt
│   └── Dockerfile
├── Frontend/
│   ├── index.html           landing page + app (single page)
│   ├── css/                 orca-theme.css, landing.css, app.css
│   ├── js/                  orca-dashboard.js, landing.js, app-ui.js
│   ├── assets/              photographs (see credits)
│   └── serve.py             local no-cache static server
└── tests/                   pytest suite
```

---

## Data sources

| Source | Used for |
|---|---|
| [Open-Meteo](https://open-meteo.com/) (ECMWF IFS, NOAA GFS) | Wind, gusts, pressure, forecasts, place search |
| [Open-Meteo Marine](https://open-meteo.com/en/docs/marine-weather-api) (ECMWF WAM, NOAA GFS-Wave) | Waves, swell, currents, sea temperature |
| [INCOIS](https://incois.gov.in/) | Official high-wave and swell-surge alerts for Indian coasts |
| [GDACS](https://www.gdacs.org/) | Tropical cyclones and tsunamis |
| [OBIS](https://obis.org/) | Occurrence records of IUCN Red List marine species |
| [OpenStreetMap](https://www.openstreetmap.org/) (Overpass) | Marine reserves and restricted areas; map tiles |
| [Wikipedia](https://www.wikipedia.org/) | Species photos, common names and summaries (loaded in the browser) |

Species records are historical occurrences, not live tracking. Absence of records is not proof of absence.

### Photo credits

- Boat at Devaneri, Mahabalipuram: [Timothy A. Gonsalves](https://commons.wikimedia.org/wiki/File:Fishing_Boat_Waves_Devaneri_Mahabalipuram_Sep22_A7C_02637.jpg), CC BY-SA 4.0
- Fishermen repairing nets: [Ishtihaar](https://commons.wikimedia.org/wiki/File:Fishermen_repairing_their_fishing_net.jpg), CC BY-SA 4.0
