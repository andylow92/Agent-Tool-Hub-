"""
Perplexity Search Tool — AI-powered web search for AI agents.

Wraps the Perplexity Sonar API to return direct answers with citations
instead of raw search links. Any agent can call this over HTTP or import it.
"""

import os
import json
import urllib.request
import urllib.error
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
API_URL = "https://api.perplexity.ai/chat/completions"
DEFAULT_PORT = 8002
DEFAULT_MODEL = "sonar"


def search(
    query: str,
    model: str = DEFAULT_MODEL,
    recency: str = None,
    max_tokens: int = 1024,
) -> dict:
    """Search the web using Perplexity Sonar and get a direct answer.

    Args:
        query: The question or search query.
        model: "sonar" (fast) or "sonar-pro" (deeper, more citations).
        recency: Filter sources by time — "day", "week", "month", "year", or None.
        max_tokens: Maximum length of the answer.

    Returns:
        dict with answer, citations, and usage, or an error dict.
    """
    if not API_KEY:
        return {"error": "PERPLEXITY_API_KEY environment variable is not set"}

    if model not in ("sonar", "sonar-pro"):
        return {"error": f"Invalid model '{model}'. Use 'sonar' or 'sonar-pro'."}

    if recency and recency not in ("day", "week", "month", "year"):
        return {
            "error": f"Invalid recency '{recency}'. Use 'day', 'week', 'month', or 'year'."
        }

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Be precise and concise."},
            {"role": "user", "content": query},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "return_citations": True,
    }

    if recency:
        body["search_recency_filter"] = recency

    data = json.dumps(body).encode()
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            detail = json.loads(raw).get("error", {}).get("message", raw)
        except (json.JSONDecodeError, AttributeError):
            detail = raw
        return {"error": f"API error {e.code}: {detail}"}
    except urllib.error.URLError as e:
        return {"error": f"Network error: {e.reason}"}

    choice = result.get("choices", [{}])[0]
    message = choice.get("message", {})
    usage = result.get("usage", {})

    return {
        "answer": message.get("content", ""),
        "citations": choice.get("citations", []),
        "model": result.get("model", model),
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
        },
    }


class SearchHandler(BaseHTTPRequestHandler):
    """HTTP handler that serves Perplexity search results as JSON."""

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/health":
            self._respond(200, {"status": "ok", "tool": "perplexity-search"})
            return
        if parsed.path != "/search":
            self._respond(404, {"error": "Not found. Use GET /search?q=your+question"})
            return

        params = urllib.parse.parse_qs(parsed.query)
        query = params.get("q", [None])[0]
        if not query:
            self._respond(400, {"error": "Missing required parameter: q"})
            return

        model = params.get("model", [DEFAULT_MODEL])[0]
        recency = params.get("recency", [None])[0]
        max_tokens = int(params.get("max_tokens", [1024])[0])

        result = search(query, model=model, recency=recency, max_tokens=max_tokens)

        status = 502 if "error" in result else 200
        self._respond(status, result)

    def _respond(self, status: int, body: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body, indent=2).encode())

    def log_message(self, fmt, *args):
        print(f"[perplexity-search] {args[0]}")


def main():
    port = int(os.environ.get("PORT", DEFAULT_PORT))

    if not API_KEY:
        print("WARNING: PERPLEXITY_API_KEY is not set. Requests will return errors.")
        print("Get a key at https://docs.perplexity.ai/")

    server = HTTPServer(("0.0.0.0", port), SearchHandler)
    print(f"Perplexity Search running on http://localhost:{port}/search")
    print(f"Example: http://localhost:{port}/search?q=What+is+quantum+computing")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
