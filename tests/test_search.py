"""Tests for the perplexity-search tool."""

import json
import sys
import os
from unittest.mock import patch, MagicMock
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools", "perplexity-search"))
import search


class TestSearch:
    """Tests for the search function."""

    def test_missing_api_key(self):
        with patch.object(search, "API_KEY", ""):
            result = search.search("test query")
        assert "error" in result
        assert "PERPLEXITY_API_KEY" in result["error"]

    def test_invalid_model(self):
        with patch.object(search, "API_KEY", "test-key"):
            result = search.search("test", model="invalid")
        assert "error" in result
        assert "Invalid model" in result["error"]

    def test_invalid_recency(self):
        with patch.object(search, "API_KEY", "test-key"):
            result = search.search("test", recency="invalid")
        assert "error" in result
        assert "Invalid recency" in result["error"]

    def test_successful_search(self):
        mock_data = {
            "choices": [{
                "message": {"content": "Test answer"},
                "citations": ["https://example.com"],
            }],
            "model": "sonar",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_data).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch.object(search, "API_KEY", "test-key"), \
             patch("urllib.request.urlopen", return_value=mock_response):
            result = search.search("What is Python?")

        assert result["answer"] == "Test answer"
        assert result["citations"] == ["https://example.com"]
        assert result["usage"]["total_tokens"] == 30

    def test_network_error(self):
        import urllib.error
        with patch.object(search, "API_KEY", "test-key"), \
             patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
            result = search.search("test")
        assert "error" in result
        assert "Network error" in result["error"]


class TestSearchHandler:
    """Tests for the HTTP handler."""

    def _make_handler(self, path):
        handler = search.SearchHandler.__new__(search.SearchHandler)
        handler.path = path
        handler.headers = {}
        handler.wfile = BytesIO()
        handler.requestline = "GET / HTTP/1.1"
        handler.client_address = ("127.0.0.1", 0)
        handler.request_version = "HTTP/1.1"
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

    def test_missing_query_param(self):
        handler = self._make_handler("/search")
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.do_GET()
        handler.send_response.assert_called_with(400)
