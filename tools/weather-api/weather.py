"""
Weather API Tool — A simple weather lookup tool for AI agents.

Wraps the OpenWeatherMap API and returns structured weather data
that agents can easily parse and reason about.
"""

import os
import sys
import json
import urllib.request
import urllib.error
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
DEFAULT_PORT = 8001


def get_weather(city: str, units: str = "metric") -> dict:
    """Fetch current weather for a city.

    Args:
        city: City name (e.g., "London" or "London,GB").
        units: "metric" (Celsius), "imperial" (Fahrenheit), or "standard" (Kelvin).

    Returns:
        dict with structured weather data, or an error dict.
    """
    if not API_KEY:
        return {"error": "OPENWEATHER_API_KEY environment variable is not set"}

    if units not in ("metric", "imperial", "standard"):
        return {"error": f"Invalid units '{units}'. Use 'metric', 'imperial', or 'standard'."}

    params = urllib.parse.urlencode({
        "q": city,
        "appid": API_KEY,
        "units": units,
    })
    url = f"{BASE_URL}?{params}"

    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            detail = json.loads(body).get("message", body)
        except json.JSONDecodeError:
            detail = body
        return {"error": f"API error {e.code}: {detail}"}
    except urllib.error.URLError as e:
        return {"error": f"Network error: {e.reason}"}

    unit_labels = {"metric": "°C", "imperial": "°F", "standard": "K"}
    speed_labels = {"metric": "m/s", "imperial": "mph", "standard": "m/s"}

    return {
        "city": data.get("name"),
        "country": data.get("sys", {}).get("country"),
        "coordinates": {
            "lat": data.get("coord", {}).get("lat"),
            "lon": data.get("coord", {}).get("lon"),
        },
        "temperature": {
            "current": data.get("main", {}).get("temp"),
            "feels_like": data.get("main", {}).get("feels_like"),
            "min": data.get("main", {}).get("temp_min"),
            "max": data.get("main", {}).get("temp_max"),
            "unit": unit_labels[units],
        },
        "humidity": data.get("main", {}).get("humidity"),
        "pressure_hpa": data.get("main", {}).get("pressure"),
        "wind": {
            "speed": data.get("wind", {}).get("speed"),
            "unit": speed_labels[units],
            "direction_degrees": data.get("wind", {}).get("deg"),
        },
        "condition": {
            "summary": data.get("weather", [{}])[0].get("main"),
            "description": data.get("weather", [{}])[0].get("description"),
            "icon": data.get("weather", [{}])[0].get("icon"),
        },
        "visibility_meters": data.get("visibility"),
        "clouds_percent": data.get("clouds", {}).get("all"),
    }


class WeatherHandler(BaseHTTPRequestHandler):
    """HTTP handler that serves weather data as JSON."""

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/health":
            self._respond(200, {"status": "ok", "tool": "weather-api"})
            return
        if parsed.path != "/weather":
            self._respond(404, {"error": "Not found. Use GET /weather?city=London"})
            return

        params = urllib.parse.parse_qs(parsed.query)
        city = params.get("city", [None])[0]
        if not city:
            self._respond(400, {"error": "Missing required parameter: city"})
            return

        units = params.get("units", ["metric"])[0]
        result = get_weather(city, units)

        status = 502 if "error" in result else 200
        self._respond(status, result)

    def _respond(self, status: int, body: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body, indent=2).encode())

    def log_message(self, fmt, *args):
        print(f"[weather-api] {args[0]}")


def main():
    port = int(os.environ.get("PORT", DEFAULT_PORT))

    if not API_KEY:
        print("WARNING: OPENWEATHER_API_KEY is not set. Requests will return errors.")
        print("Get a free key at https://openweathermap.org/api")

    server = HTTPServer(("0.0.0.0", port), WeatherHandler)
    print(f"Weather API running on http://localhost:{port}/weather")
    print(f"Example: http://localhost:{port}/weather?city=London&units=metric")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
