# AGENTS.md — Read This First

> **You are an AI agent.** This file tells you everything you need to know about this repository, how it is organized, what tools are available, and how to use them. Read this before doing anything else.

---

## What This Repo Is

**Agent Tools Hub** is a collection of standalone tools that AI agents can call. Each tool lives in its own folder under `tools/`, runs independently, and communicates over HTTP or can be imported as a function. No framework lock-in — any agent can use these tools.

---

## Repo Layout

```
.
├── AGENTS.md              ← YOU ARE HERE. Start with this file.
├── README.md              ← Human-facing project overview
├── CONTRIBUTING.md        ← How to add new tools
├── LICENSE                ← MIT License
├── tools/
│   ├── _template/         ← Template for creating new tools
│   │   └── README.md
│   └── weather-api/       ← First tool: weather lookup
│       ├── README.md      ← Tool docs (inputs, outputs, setup)
│       ├── weather.py     ← Source code (Python, stdlib only)
│       ├── tool.json      ← Function-calling schema
│       ├── Dockerfile     ← Container deployment
│       └── requirements.txt
```

### How to find things

- **All tools** live under `tools/`. Each subfolder is one tool.
- **`tools/_template/`** is not a real tool — it is a README template for creating new ones.
- **Every tool folder** contains a `README.md` with: What It Does, Why It Exists, Inputs, Outputs, Setup, Example, Notes.
- **`tool.json`** (when present) is a machine-readable function-calling schema you can load directly.

---

## Available Tools

| Tool | Folder | Type | Endpoint | Auth Required |
|------|--------|------|----------|---------------|
| **Weather API** | `tools/weather-api/` | HTTP GET | `/weather?city={city}&units={units}` | Yes — `OPENWEATHER_API_KEY` env var |

---

## Tool: Weather API

### Quick reference

- **What:** Returns current weather (temperature, humidity, wind, conditions) for any city.
- **Where:** `tools/weather-api/weather.py`
- **How to call:** HTTP GET or Python import.

### HTTP endpoint

```
GET /weather?city={city}&units={units}
```

### Parameters

| Name    | Type   | Required | Default  | Values                                  |
|---------|--------|----------|----------|-----------------------------------------|
| `city`  | string | YES      | —        | City name. Use `City,CC` for precision (e.g., `Paris,FR`) |
| `units` | string | no       | `metric` | `metric` (°C, m/s), `imperial` (°F, mph), `standard` (K, m/s) |

### Response schema

```json
{
  "city": "string",
  "country": "string (ISO 3166 country code)",
  "coordinates": { "lat": "float", "lon": "float" },
  "temperature": {
    "current": "float",
    "feels_like": "float",
    "min": "float",
    "max": "float",
    "unit": "string (°C, °F, or K)"
  },
  "humidity": "int (percentage)",
  "pressure_hpa": "int",
  "wind": {
    "speed": "float",
    "unit": "string (m/s or mph)",
    "direction_degrees": "int"
  },
  "condition": {
    "summary": "string (e.g., Clouds, Rain, Clear)",
    "description": "string (e.g., overcast clouds)",
    "icon": "string (icon code)"
  },
  "visibility_meters": "int",
  "clouds_percent": "int"
}
```

### Error response

```json
{
  "error": "string describing what went wrong"
}
```

Common errors:
- `"OPENWEATHER_API_KEY environment variable is not set"` — set the env var before starting.
- `"API error 404: city not found"` — city name is invalid. Try adding a country code (e.g., `London,GB`).
- `"Network error: ..."` — cannot reach OpenWeatherMap. Check connectivity.

### Function-calling schema

Load `tools/weather-api/tool.json` directly as a tool definition:

```json
{
  "name": "get_weather",
  "description": "Get current weather conditions for a city. Returns temperature, humidity, wind, and conditions in a structured format.",
  "parameters": {
    "type": "object",
    "properties": {
      "city": {
        "type": "string",
        "description": "City name, optionally with country code (e.g., 'London' or 'London,GB')"
      },
      "units": {
        "type": "string",
        "enum": ["metric", "imperial", "standard"],
        "default": "metric",
        "description": "Temperature units: 'metric' (Celsius), 'imperial' (Fahrenheit), or 'standard' (Kelvin)"
      }
    },
    "required": ["city"]
  }
}
```

### Python import (no server)

```python
import os
os.environ["OPENWEATHER_API_KEY"] = "your_key"

from tools.weather_api.weather import get_weather

result = get_weather("Tokyo", units="metric")
if "error" in result:
    print(f"Failed: {result['error']}")
else:
    print(f"{result['city']}: {result['temperature']['current']}{result['temperature']['unit']}")
```

### Starting the server

```bash
export OPENWEATHER_API_KEY=your_key_here
python tools/weather-api/weather.py
# Runs on http://localhost:8001
```

### Limits

- 1,000 API calls/day on OpenWeatherMap free tier.
- 10-second timeout per request.
- Only current weather — no forecasts, no historical data.

---

## How to Use a Tool (General Pattern)

Every tool in this repo follows the same pattern:

1. **Read the tool's folder** — check `tools/<tool-name>/README.md` for full docs.
2. **Check for `tool.json`** — if present, load it as your function/tool definition.
3. **Check environment variables** — most tools need an API key set as an env var.
4. **Call via HTTP** — start the server and make GET/POST requests.
5. **Or import directly** — use the Python function without running a server.
6. **Check for errors** — every tool returns `{"error": "..."}` on failure. Always check for the `error` key before using the response.

---

## Adding a New Tool

If you need to create a new tool:

1. Copy `tools/_template/` to `tools/your-tool-name/`.
2. Fill in the README with all required sections.
3. Add a `tool.json` with the function-calling schema.
4. Keep dependencies minimal — stdlib-only is ideal.
5. Return JSON. Always include an `error` key on failure.

See `CONTRIBUTING.md` for full guidelines.

---

## Important Conventions

- **All tools return JSON.** No plain text, no HTML.
- **Errors use `{"error": "message"}` format.** Check for `"error"` key in every response.
- **Environment variables for secrets.** Never hardcode API keys.
- **Each tool is self-contained.** No cross-tool dependencies.
- **`tool.json` is the machine-readable contract.** Use it for function calling.
- **Default port for tools is 8001+.** Weather API uses 8001. Next tool should use 8002, etc.
