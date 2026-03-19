# AGENTS.md — Weather API Tool

> **You are an AI agent.** This file tells you everything you need to use this tool. No other files required.

---

## What This Tool Does

Returns **current weather data** (temperature, humidity, wind, conditions) for any city in the world. Wraps the OpenWeatherMap API and returns clean, structured JSON.

**Use this when you need:** current temperature, weather conditions, wind speed, humidity, or atmospheric pressure for a specific location.

---

## Files In This Directory

| File | Purpose |
|------|---------|
| `weather.py` | Main code — HTTP server + importable `get_weather()` function |
| `tool.json` | Function-calling schema — load this as your tool definition |
| `README.md` | Human-readable documentation |
| `Dockerfile` | Run in a container |
| `requirements.txt` | No external deps (stdlib only) |

---

## How to Call This Tool

### Option 1: HTTP (server must be running)

```
GET http://localhost:8001/weather?city={city}&units={units}
```

### Option 2: Python import (no server needed)

```python
from weather import get_weather
result = get_weather("Tokyo", units="metric")
```

---

## Parameters

| Name    | Type   | Required | Default  | Allowed Values |
|---------|--------|----------|----------|----------------|
| `city`  | string | **YES**  | —        | City name. Add country code for precision: `London,GB`, `Paris,FR` |
| `units` | string | no       | `metric` | `metric` (°C, m/s), `imperial` (°F, mph), `standard` (K, m/s) |

---

## Response Format

### Success (HTTP 200)

```json
{
  "city": "London",
  "country": "GB",
  "coordinates": { "lat": 51.5085, "lon": -0.1257 },
  "temperature": {
    "current": 14.2,
    "feels_like": 13.5,
    "min": 12.8,
    "max": 15.1,
    "unit": "°C"
  },
  "humidity": 72,
  "pressure_hpa": 1013,
  "wind": {
    "speed": 4.6,
    "unit": "m/s",
    "direction_degrees": 230
  },
  "condition": {
    "summary": "Clouds",
    "description": "overcast clouds",
    "icon": "04d"
  },
  "visibility_meters": 10000,
  "clouds_percent": 90
}
```

**How to read the response:**
- `temperature.current` — the main temperature reading in the unit specified by `temperature.unit`.
- `condition.summary` — one-word weather category (Clear, Clouds, Rain, Snow, etc.).
- `condition.description` — more detailed description (e.g., "light rain", "overcast clouds").
- `wind.direction_degrees` — wind direction in meteorological degrees (0=N, 90=E, 180=S, 270=W).

### Error (HTTP 400/502)

```json
{
  "error": "description of what went wrong"
}
```

**Always check for the `error` key before using the response.**

---

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| `OPENWEATHER_API_KEY environment variable is not set` | Missing API key | Set `export OPENWEATHER_API_KEY=your_key` |
| `API error 404: city not found` | Invalid city name | Try adding a country code (e.g., `London,GB`) |
| `Invalid units '...'` | Bad units value | Use `metric`, `imperial`, or `standard` |
| `Network error: ...` | Can't reach OpenWeatherMap | Check internet connectivity |
| `Missing required parameter: city` | No city provided | Include `?city=London` in the URL |

---

## Setup (Before First Use)

1. **Get a free API key** at [openweathermap.org](https://openweathermap.org/api) (1,000 calls/day free).

2. **Set the API key:**
   ```bash
   export OPENWEATHER_API_KEY=your_key_here
   ```

3. **Start the server:**
   ```bash
   python weather.py
   # Runs on http://localhost:8001
   ```

4. **Or use Docker:**
   ```bash
   docker build -t weather-api .
   docker run -p 8001:8001 -e OPENWEATHER_API_KEY=your_key_here weather-api
   ```

---

## Function-Calling Schema

Load `tool.json` in this directory to register this as a callable tool:

```json
{
  "name": "get_weather",
  "description": "Get current weather conditions for a city. Returns temperature, humidity, wind, and conditions in a structured format.",
  "parameters": {
    "type": "object",
    "properties": {
      "city": { "type": "string", "description": "City name, optionally with country code (e.g., 'London' or 'London,GB')" },
      "units": { "type": "string", "enum": ["metric", "imperial", "standard"], "default": "metric" }
    },
    "required": ["city"]
  }
}
```

---

## Limits and Constraints

- **Rate limit:** 1,000 calls/day on free tier
- **Timeout:** 10 seconds per request
- **Data:** Current weather only — no forecasts, no historical
- **Port:** 8001 (override with `PORT` env var)
- **Python:** 3.7+ required
- **Dependencies:** None — Python standard library only
