"""Tests for the web-scraper tool."""

import json
import os
import sys
from io import BytesIO
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools", "web-scraper"))
import scraper


class TestScrape:
    """Tests for the scrape function."""

    def test_missing_url(self):
        result = scraper.scrape("")
        assert "error" in result

    def test_invalid_scheme(self):
        result = scraper.scrape("ftp://example.com")
        assert "error" in result
        assert "Unsupported scheme" in result["error"]

    def test_successful_html_scrape(self):
        html = (
            "<html><head><title>Test Page</title>"
            '<meta name="description" content="A test page">'
            "</head><body><p>Hello World</p></body></html>"
        )
        mock_response = MagicMock()
        mock_response.read.return_value = html.encode()
        mock_response.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_response.status = 200
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = scraper.scrape("https://example.com")

        assert result["title"] == "Test Page"
        assert result["description"] == "A test page"
        assert "Hello World" in result["text"]
        assert result["characters"] > 0

    def test_strips_script_and_style(self):
        html = (
            "<html><body>"
            "<style>body { color: red; }</style>"
            "<script>alert('xss')</script>"
            "<p>Visible text</p>"
            "</body></html>"
        )
        mock_response = MagicMock()
        mock_response.read.return_value = html.encode()
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.status = 200
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = scraper.scrape("https://example.com")

        assert "Visible text" in result["text"]
        assert "alert" not in result["text"]
        assert "color: red" not in result["text"]

    def test_plain_text_content(self):
        mock_response = MagicMock()
        mock_response.read.return_value = b"Just plain text"
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_response.status = 200
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = scraper.scrape("https://example.com/file.txt")

        assert result["text"] == "Just plain text"

    def test_http_error(self):
        import urllib.error

        err = urllib.error.HTTPError("https://example.com", 404, "Not Found", {}, None)
        with patch("urllib.request.urlopen", side_effect=err):
            result = scraper.scrape("https://example.com/missing")

        assert "error" in result
        assert "404" in result["error"]

    def test_network_error(self):
        import urllib.error

        err = urllib.error.URLError("Connection refused")
        with patch("urllib.request.urlopen", side_effect=err):
            result = scraper.scrape("https://example.com")

        assert "error" in result
        assert "Connection failed" in result["error"]


class TestScrapeHandler:
    """Tests for the HTTP handler."""

    def _make_handler(self, path):
        handler = scraper.ScrapeHandler.__new__(scraper.ScrapeHandler)
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
        assert body["tool"] == "web-scraper"

    def test_missing_url_param(self):
        handler = self._make_handler("/scrape")
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
