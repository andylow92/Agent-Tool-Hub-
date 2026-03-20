"""
Web Scraper Tool — Fetch any URL and return clean, readable text.

Strips HTML tags, scripts, and styles to return just the content
that agents can read and reason about. No external dependencies.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, HTTPServer

DEFAULT_PORT = 8006
DEFAULT_TIMEOUT = 10
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
USER_AGENT = (
    "Mozilla/5.0 (compatible; AgentToolHub-Scraper/1.0; "
    "+https://github.com/andylow92/Agent-Tool-Hub-)"
)


class _TextExtractor(HTMLParser):
    """Strips HTML to plain text, ignoring script/style tags."""

    def __init__(self):
        super().__init__()
        self._pieces: list[str] = []
        self._skip = False
        self._skip_tags = {"script", "style", "noscript"}

    def handle_starttag(self, tag, attrs):
        if tag in self._skip_tags:
            self._skip = True
        if tag in ("br", "p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"):
            self._pieces.append("\n")

    def handle_endtag(self, tag):
        if tag in self._skip_tags:
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self._pieces.append(data)

    def get_text(self) -> str:
        raw = "".join(self._pieces)
        lines = [line.strip() for line in raw.splitlines()]
        return "\n".join(line for line in lines if line)


class _MetaExtractor(HTMLParser):
    """Extracts title and meta description from HTML."""

    def __init__(self):
        super().__init__()
        self.title = ""
        self.description = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            attr_dict = dict(attrs)
            name = attr_dict.get("name", "").lower()
            if name == "description":
                self.description = attr_dict.get("content", "")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def scrape(url: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Fetch a URL and return its text content.

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        dict with text content, title, description, and metadata.
    """
    if not url:
        return {"error": "URL is required"}

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return {"error": f"Unsupported scheme: {parsed.scheme}. Use http or https."}

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get("Content-Type", "")
            status = resp.status

            if "text/html" not in content_type and "text/plain" not in content_type:
                return {
                    "error": f"Unsupported content type: {content_type}",
                    "status": status,
                    "url": url,
                }

            raw = resp.read(MAX_CONTENT_LENGTH)
            charset = "utf-8"
            if "charset=" in content_type:
                charset = content_type.split("charset=")[-1].split(";")[0].strip()
            html = raw.decode(charset, errors="replace")

    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}", "url": url}
    except urllib.error.URLError as e:
        return {"error": f"Connection failed: {e.reason}", "url": url}
    except TimeoutError:
        return {"error": f"Request timed out after {timeout}s", "url": url}

    if "text/plain" in content_type:
        return {
            "url": url,
            "title": "",
            "description": "",
            "text": html,
            "characters": len(html),
        }

    text_extractor = _TextExtractor()
    text_extractor.feed(html)
    text = text_extractor.get_text()

    meta_extractor = _MetaExtractor()
    meta_extractor.feed(html)

    return {
        "url": url,
        "title": meta_extractor.title.strip(),
        "description": meta_extractor.description.strip(),
        "text": text,
        "characters": len(text),
    }


class ScrapeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/health":
            self._respond(200, {"status": "ok", "tool": "web-scraper"})
            return

        if parsed.path != "/scrape":
            self._respond(404, {"error": f"Not found: {parsed.path}"})
            return

        url = params.get("url", [None])[0]
        if not url:
            self._respond(400, {"error": "Missing required parameter: url"})
            return

        timeout = int(params.get("timeout", [DEFAULT_TIMEOUT])[0])
        result = scrape(url, timeout=timeout)
        status = 502 if "error" in result else 200
        self._respond(status, result)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path != "/scrape":
            self._respond(404, {"error": f"Not found: {parsed.path}"})
            return

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self._respond(400, {"error": "Empty request body"})
            return

        try:
            body = json.loads(self.rfile.read(content_length))
        except json.JSONDecodeError:
            self._respond(400, {"error": "Request body must be valid JSON"})
            return

        url = body.get("url")
        if not url:
            self._respond(400, {"error": "Missing required field: url"})
            return

        timeout = int(body.get("timeout", DEFAULT_TIMEOUT))
        result = scrape(url, timeout=timeout)
        status = 502 if "error" in result else 200
        self._respond(status, result)

    def _respond(self, status: int, body: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body, indent=2, default=str).encode())

    def log_message(self, fmt, *args):
        print(f"[web-scraper] {args[0]}")


def main():
    port = int(os.environ.get("PORT", DEFAULT_PORT))

    HTTPServer.allow_reuse_address = True
    max_retries = 5
    for attempt in range(max_retries):
        try:
            server = HTTPServer(("0.0.0.0", port), ScrapeHandler)
            break
        except OSError:
            if attempt < max_retries - 1:
                print(f"Port {port} in use, trying {port + 1}...")
                port += 1
            else:
                raise SystemExit(
                    f"Error: Could not bind to any port in range "
                    f"{port - max_retries + 1}-{port}. Free a port or set PORT env var."
                )
    print(f"Web Scraper running on http://localhost:{port}/scrape")
    print(f"Example: http://localhost:{port}/scrape?url=https://example.com")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
