# Weather API

## What It Does

A lightweight HTTP server that wraps the [OpenWeatherMap API](https://openweathermap.org/api) and returns clean, structured JSON weather data. Designed to be called by AI agents that need real-time weather information.

## Why It Exists

Weather is one of the most common "first tools" agents are given. Most implementations are tightly coupled to a specific framework. This tool runs as a standalone HTTP server so **any** agent — regardless of framework — can call it with a simple GET request.

## Inputs

| Parameter | Type     | Required | Default    | Description                                                        |
|-----------|----------|----------|------------|--------------------------------------------------------------------|
| `city`    | `string` | Yes      | —          | City name, optionally with country code (e.g., `London` or `London,GB`) |
| `units`   | `string` | No       | `metric`   | `metric` (°C), `imperial` (°F), or `standard` (K)                 |

## Outputs

Returns a JSON object:

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

On error, returns:

```json
{
  "error": "API error 404: city not found"
}
```

## Setup

### 1. Get a free API key

Sign up at [openweathermap.org](https://openweathermap.org/api) — the free tier allows 1,000 calls/day.

### 2. Run the server

```bash
export OPENWEATHER_API_KEY=your_key_here
python weather.py
```

The server starts on `http://localhost:8001` by default. Override with `PORT` env var.

### 3. Or use Docker

```bash
docker build -t weather-api .
docker run -p 8001:8001 -e OPENWEATHER_API_KEY=your_key_here weather-api
```

## Example

```bash
# Get weather in metric (default)
curl "http://localhost:8001/weather?city=Tokyo"

# Get weather in Fahrenheit
curl "http://localhost:8001/weather?city=New+York&units=imperial"

# With country code for precision
curl "http://localhost:8001/weather?city=Paris,FR"
```

### Using as a Python function (no server needed)

```python
from weather import get_weather

result = get_weather("Berlin", units="metric")
print(result["temperature"]["current"])  # 14.2
```

### Tool schema for agents

A ready-to-use tool definition is provided in [`tool.json`](tool.json) — compatible with OpenAI function calling format, LangChain, and similar frameworks.

## Notes

- **Free tier limit:** 1,000 API calls/day (OpenWeatherMap free plan).
- **No external dependencies:** Uses only Python standard library (`http.server`, `urllib`).
- **City not found** returns a clear error message — agents can retry with a different city name or add a country code.
- **Units parameter** affects both temperature and wind speed units in the response.
- **Python 3.7+** required.
- The `tool.json` file can be fed directly to an LLM as a function/tool definition.
