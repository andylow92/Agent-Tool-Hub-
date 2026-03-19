"""
Agent Adapter — Makes any HTTP tool compatible with the talk_to_agent protocol.

This adapter wraps an existing HTTP tool so it can receive messages from
talk_to_agent. It translates the inter-agent message format into tool-native
HTTP calls and wraps the response with the required request_id echo.

Usage:
  # Wrap the weather API (port 8001) and expose it on port 9001
  python adapter.py --tool-url http://localhost:8001 --port 9001 --agent-id weather-agent

  # Wrap the file converter (port 8003) and expose it on port 9003
  python adapter.py --tool-url http://localhost:8003 --port 9003 --agent-id file-converter

  # Auto-register with the talk_to_agent registry
  python adapter.py --tool-url http://localhost:8001 --port 9001 \
      --agent-id weather-agent --register http://localhost:8004

The adapter receives:
  POST / (the talk_to_agent protocol message)
  {
    "request_id": "uuid",
    "from": "caller-id",
    "message": "the user's question or request",
    "hop_count": 1
  }

And returns:
  {
    "request_id": "same-uuid-echoed-back",
    "from": "this-agent-id",
    "response": "the tool's response as a JSON string"
  }

The adapter parses the 'message' field to figure out how to call the
underlying tool. It supports two modes:

  1. Structured mode: If the message is valid JSON with a "path" key,
     the adapter calls that path on the tool with the given method/params.

  2. Natural language mode: The message is forwarded as-is to the tool's
     default endpoint (configurable with --default-path).
"""

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def call_tool(tool_url: str, message: str, default_path: str = "/") -> str:
    """
    Call the underlying tool based on the message content.

    If the message is valid JSON with routing info, use it.
    Otherwise, send the raw message to the default path.
    """
    # Try to parse as structured request
    try:
        parsed = json.loads(message)
        if isinstance(parsed, dict) and "path" in parsed:
            return _structured_call(tool_url, parsed)
    except (json.JSONDecodeError, TypeError):
        pass

    # Fall back to forwarding the raw message to default path
    return _raw_call(tool_url, default_path, message)


def _structured_call(tool_url: str, req: dict) -> str:
    """
    Make a structured call to the tool.

    Expected format:
    {
      "path": "/convert",
      "method": "POST",          // optional, default GET
      "params": {...},           // query params for GET, body for POST
      "body": {...}              // explicit body (overrides params for POST)
    }
    """
    path = req.get("path", "/")
    method = req.get("method", "GET").upper()
    params = req.get("params", {})
    body = req.get("body", None)

    url = f"{tool_url.rstrip('/')}{path}"

    if method == "GET" and params:
        url += "?" + urlencode(params)
        http_req = Request(url, method="GET")
    elif method == "POST":
        data = json.dumps(body if body is not None else params).encode()
        http_req = Request(
            url, data=data, method="POST", headers={"Content-Type": "application/json"}
        )
    else:
        http_req = Request(url, method=method)

    try:
        with urlopen(http_req, timeout=30) as resp:
            return resp.read().decode()
    except HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        return json.dumps({"error": f"Tool returned HTTP {e.code}", "detail": error_body})
    except (URLError, OSError) as e:
        return json.dumps({"error": f"Could not reach tool: {e}"})


def _raw_call(tool_url: str, default_path: str, message: str) -> str:
    """Forward the raw message to the tool's default path as a POST body."""
    url = f"{tool_url.rstrip('/')}{default_path}"
    data = json.dumps({"message": message}).encode()
    req = Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})

    try:
        with urlopen(req, timeout=30) as resp:
            return resp.read().decode()
    except HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        return json.dumps({"error": f"Tool returned HTTP {e.code}", "detail": error_body})
    except (URLError, OSError) as e:
        return json.dumps({"error": f"Could not reach tool: {e}"})


class AdapterHandler(BaseHTTPRequestHandler):
    """HTTP handler that bridges talk_to_agent protocol to a native tool."""

    tool_url = ""
    agent_id = ""
    default_path = "/"

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self._respond(400, {"error": "Empty request body"})
            return

        try:
            body = json.loads(self.rfile.read(content_length))
        except json.JSONDecodeError:
            self._respond(400, {"error": "Request body must be valid JSON"})
            return

        request_id = body.get("request_id")
        message = body.get("message", "")
        sender = body.get("from", "unknown")

        if not request_id:
            self._respond(400, {"error": "Missing required field: request_id"})
            return

        print(f"[adapter:{self.agent_id}] Message from '{sender}': {message[:100]}...")

        # Call the underlying tool
        tool_response = call_tool(self.tool_url, message, self.default_path)

        # Return with the echoed request_id
        response = {
            "request_id": request_id,
            "from": self.agent_id,
            "response": tool_response,
        }
        self._respond(200, response)

    def do_GET(self):
        if self.path == "/health":
            self._respond(
                200,
                {
                    "status": "ok",
                    "agent_id": self.agent_id,
                    "wraps": self.tool_url,
                },
            )
        else:
            self._respond(
                200,
                {
                    "agent_id": self.agent_id,
                    "wraps": self.tool_url,
                    "protocol": "talk_to_agent",
                    "description": "Send POST with {request_id, from, message} to communicate.",
                },
            )

    def _respond(self, status: int, body: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body, indent=2).encode())

    def log_message(self, fmt, *args):
        print(f"[adapter:{self.agent_id}] {args[0]}")


def auto_register(registry_url: str, agent_id: str, adapter_port: int):
    """Register this adapter with the talk_to_agent registry."""
    import socket

    hostname = socket.gethostname()

    payload = json.dumps(
        {
            "agent_id": agent_id,
            "endpoint": f"http://{hostname}:{adapter_port}",
            "name": f"{agent_id} (adapter)",
        }
    ).encode()

    req = Request(
        f"{registry_url.rstrip('/')}/registry",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
            print(f"[adapter] Registered with registry: {result}")
    except Exception as e:
        print(f"[adapter] Warning: could not register with registry: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Wrap an HTTP tool to speak the talk_to_agent protocol."
    )
    parser.add_argument(
        "--tool-url",
        required=True,
        help="Base URL of the tool to wrap (e.g. http://localhost:8001)",
    )
    parser.add_argument(
        "--port", type=int, default=9001, help="Port for this adapter to listen on (default: 9001)"
    )
    parser.add_argument(
        "--agent-id", required=True, help="Agent identifier for this adapter (e.g. weather-agent)"
    )
    parser.add_argument(
        "--default-path",
        default="/",
        help="Default path to call on the tool for raw messages (default: /)",
    )
    parser.add_argument(
        "--register",
        default=None,
        metavar="REGISTRY_URL",
        help="Auto-register with a talk_to_agent registry (e.g. http://localhost:8004)",
    )
    args = parser.parse_args()

    # Configure the handler class
    AdapterHandler.tool_url = args.tool_url
    AdapterHandler.agent_id = args.agent_id
    AdapterHandler.default_path = args.default_path

    # Auto-register if requested
    if args.register:
        auto_register(args.register, args.agent_id, args.port)

    server = HTTPServer(("0.0.0.0", args.port), AdapterHandler)
    print(f"Agent adapter '{args.agent_id}' running on http://localhost:{args.port}")
    print(f"  Wrapping tool at: {args.tool_url}")
    print(f"  Default path:     {args.default_path}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
