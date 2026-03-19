"""Tests for the weather-api tool."""

import json
import sys
import os
from unittest.mock import patch, MagicMock
from http.server import HTTPServer
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools", "weather-api"))
import weather


class TestGetWeather:
    """Tests for the get_weather function."""

    def test_missing_api_key(self):
        with patch.object(weather, "API_KEY", ""):
            result = weather.get_weather("London")
        assert "error" in result
        assert "OPENWEATHER_API_KEY" in result["error"]

    def test_invalid_units(self):
        with patch.object(weather, "API_KEY", "test-key"):
            result = weather.get_weather("London", units="invalid")
        assert "error" in result
        assert "Invalid units" in result["error"]

    def test_successful_response(self):
        mock_data = {
            "name": "London",
            "sys": {"country": "GB"},
            "coord": {"lat": 51.51, "lon": -0.13},
            "main": {
                "temp": 15.0,
                "feels_like": 14.0,
                "temp_min": 13.0,
                "temp_max": 17.0,
                "humidity": 72,
                "pressure": 1013,
            },
            "wind": {"speed": 3.5, "deg": 220},
            "weather": [{"main": "Clouds", "description": "overcast clouds", "icon": "04d"}],
            "visibility": 10000,
            "clouds": {"all": 90},
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_data).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch.object(weather, "API_KEY", "test-key"), \
             patch("urllib.request.urlopen", return_value=mock_response):
            result = weather.get_weather("London", "metric")

        assert result["city"] == "London"
        assert result["country"] == "GB"
        assert result["temperature"]["current"] == 15.0
        assert result["temperature"]["unit"] == "°C"
        assert result["humidity"] == 72
        assert result["wind"]["speed"] == 3.5

    def test_network_error(self):
        import urllib.error
        with patch.object(weather, "API_KEY", "test-key"), \
             patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
            result = weather.get_weather("London")
        assert "error" in result
        assert "Network error" in result["error"]


class TestWeatherHandler:
    """Tests for the HTTP handler."""

    def _make_handler(self, path):
        handler = weather.WeatherHandler.__new__(weather.WeatherHandler)
        handler.path = path
        handler.headers = {}
        handler.wfile = BytesIO()
        handler.requestline = "GET / HTTP/1.1"
        handler.client_address = ("127.0.0.1", 0)
        handler.request_version = "HTTP/1.1"
        handler.responses = {}
        return handler

    def test_health_endpoint(self):
        handler = self._make_handler("/health")
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.do_GET()
        handler.send_response.assert_called_with(200)
        body = json.loads(handler.wfile.getvalue())
        assert body["status"] == "ok"

    def test_missing_city_param(self):
        handler = self._make_handler("/weather")
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.do_GET()
        handler.send_response.assert_called_with(400)

    def test_not_found(self):
        handler = self._make_handler("/unknown")
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.do_GET()
        handler.send_response.assert_called_with(404)
