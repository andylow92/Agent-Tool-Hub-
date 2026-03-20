"""
talk_to_agent — Verified inter-agent communication tool.

Provides a single atomic tool for AI agents to communicate with other agents.
Generates a request_id per call, sends it to the target, and verifies the
target echoes it back. If anything fails, returns an explicit failure with
response: null so the calling LLM cannot hallucinate an answer.

Endpoints:
  POST /talk              — Send a message to another agent (the main tool)
  GET  /registry          — List all registered agents
  POST /registry          — Register or update an agent
  DELETE /registry/<id>   — Remove an agent
  GET  /agents            — List agents with status info
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_PORT = 8004
DEFAULT_TIMEOUT_MS = 10000
MAX_RESPONSE_BYTES = 100 * 1024  # 100 KB
MAX_HOP_COUNT = 5
REGISTRY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "registry.json")
AUDIT_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit.log")
AGENT_ID = os.environ.get("AGENT_ID", "orchestrator")

# ---------------------------------------------------------------------------
# Audit logger — structured JSON lines
# ---------------------------------------------------------------------------

audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)
audit_logger.propagate = False

_audit_handler = logging.FileHandler(AUDIT_LOG_FILE)
_audit_handler.setFormatter(logging.Formatter("%(message)s"))
audit_logger.addHandler(_audit_handler)

# Also log to stdout for visibility
_stdout_handler = logging.StreamHandler()
_stdout_handler.setFormatter(logging.Formatter("[audit] %(message)s"))
audit_logger.addHandler(_stdout_handler)


def audit(entry: dict):
    """Write a structured JSON audit log entry."""
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    entry["caller"] = AGENT_ID
    audit_logger.info(json.dumps(entry, default=str))


# ---------------------------------------------------------------------------
# Registry — in-memory with file persistence
# ---------------------------------------------------------------------------

_registry: dict = {}


def _load_registry():
    """Load registry from disk if the file exists."""
    global _registry
    if os.path.exists(REGISTRY_FILE):
        try:
            with open(REGISTRY_FILE, "r") as f:
                _registry = json.load(f)
        except (json.JSONDecodeError, IOError):
            _registry = {}


def _save_registry():
    """Persist registry to disk."""
    try:
        with open(REGISTRY_FILE, "w") as f:
            json.dump(_registry, f, indent=2)
    except IOError:
        pass


def register_agent(agent_id: str, endpoint: str, name: str = None) -> dict:
    """Add or update an agent in the registry."""
    _registry[agent_id] = {
        "endpoint": endpoint.rstrip("/"),
        "name": name or agent_id,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_registry()
    return {"registered": agent_id, "endpoint": endpoint}


def unregister_agent(agent_id: str) -> dict:
    """Remove an agent from the registry."""
    if agent_id not in _registry:
        return {"error": f"Agent '{agent_id}' not found in registry"}
    del _registry[agent_id]
    _save_registry()
    return {"unregistered": agent_id}


def get_registry() -> dict:
    """Return the full registry."""
    return {"agents": _registry, "count": len(_registry)}


def get_agents_with_status() -> dict:
    """Return registry entries enriched with last-known status info."""
    agents = []
    for agent_id, info in _registry.items():
        agents.append(
            {
                "id": agent_id,
                "name": info.get("name", agent_id),
                "endpoint": info.get("endpoint"),
                "registered_at": info.get("registered_at"),
                "last_status": info.get("last_status"),
                "last_contacted": info.get("last_contacted"),
                "last_latency_ms": info.get("last_latency_ms"),
            }
        )
    return {"agents": agents, "count": len(agents)}


# ---------------------------------------------------------------------------
# Core: talk_to_agent
# ---------------------------------------------------------------------------


def talk_to_agent(
    target_agent: str, message: str, timeout_ms: int = DEFAULT_TIMEOUT_MS, hop_count: int = 0
) -> dict:
    """
    Send a verified message to another agent.

    Returns a structured result with status 'verified' or 'failed'.
    On failure, response is always null.
    """
    request_id = str(uuid.uuid4())
    start_time = time.monotonic()

    # --- Check hop count ---
    if hop_count >= MAX_HOP_COUNT:
        result = _failure(
            "max_depth_exceeded",
            f"Message has been relayed {hop_count} times, exceeding "
            f"the maximum depth of {MAX_HOP_COUNT}. Possible circular call.",
            request_id,
            start_time,
            target_agent,
        )
        return result

    # --- Look up target in registry ---
    agent_info = _registry.get(target_agent)
    if not agent_info:
        result = _failure(
            "unknown_agent",
            f"Agent '{target_agent}' is not registered. "
            f"Known agents: {', '.join(_registry.keys()) or 'none'}.",
            request_id,
            start_time,
            target_agent,
        )
        return result

    endpoint = agent_info["endpoint"]

    # --- Build the request ---
    payload = json.dumps(
        {
            "request_id": request_id,
            "from": AGENT_ID,
            "message": message,
            "hop_count": hop_count + 1,
        }
    ).encode()

    req = Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    timeout_sec = timeout_ms / 1000.0

    # --- Send and receive ---
    try:
        with urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read(MAX_RESPONSE_BYTES + 1)

            if len(raw) > MAX_RESPONSE_BYTES:
                result = _failure(
                    "response_too_large",
                    f"Response from '{target_agent}' exceeded {MAX_RESPONSE_BYTES} bytes limit.",
                    request_id,
                    start_time,
                    target_agent,
                )
                return result

            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                result = _failure(
                    "invalid_response",
                    f"Response from '{target_agent}' is not valid JSON.",
                    request_id,
                    start_time,
                    target_agent,
                )
                return result

    except HTTPError as e:
        result = _failure(
            "unreachable",
            f"HTTP {e.code} from '{target_agent}' at {endpoint}.",
            request_id,
            start_time,
            target_agent,
        )
        return result

    except (URLError, OSError) as e:
        result = _failure(
            "unreachable",
            f"Could not reach '{target_agent}' at {endpoint}. "
            f"The agent may be offline or the endpoint misconfigured. "
            f"Detail: {e}",
            request_id,
            start_time,
            target_agent,
        )
        return result

    except TimeoutError:
        result = _failure(
            "timeout",
            f"Request to '{target_agent}' timed out after {timeout_ms}ms.",
            request_id,
            start_time,
            target_agent,
        )
        return result

    # --- Verify request_id ---
    returned_id = body.get("request_id")
    if returned_id != request_id:
        result = _failure(
            "request_id_mismatch",
            f"Response from '{target_agent}' returned request_id "
            f"'{returned_id}' but expected '{request_id}'. "
            f"The response cannot be verified.",
            request_id,
            start_time,
            target_agent,
        )
        return result

    # --- Success ---
    latency_ms = round((time.monotonic() - start_time) * 1000, 1)
    response_content = body.get("response", "")
    source = body.get("from", target_agent)

    # Update registry with status
    if target_agent in _registry:
        _registry[target_agent]["last_status"] = "ok"
        _registry[target_agent]["last_contacted"] = datetime.now(timezone.utc).isoformat()
        _registry[target_agent]["last_latency_ms"] = latency_ms

    result = {
        "status": "verified",
        "source": source,
        "response": response_content,
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "latency_ms": latency_ms,
    }

    audit(
        {
            "action": "talk",
            "target": target_agent,
            "request_id": request_id,
            "status": "verified",
            "latency_ms": latency_ms,
        }
    )

    return result


def _failure(
    error_code: str, message: str, request_id: str, start_time: float, target_agent: str
) -> dict:
    """Build a failure response and audit log it."""
    latency_ms = round((time.monotonic() - start_time) * 1000, 1)

    # Update registry with failure status
    if target_agent in _registry:
        _registry[target_agent]["last_status"] = error_code
        _registry[target_agent]["last_contacted"] = datetime.now(timezone.utc).isoformat()
        _registry[target_agent]["last_latency_ms"] = latency_ms

    audit(
        {
            "action": "talk",
            "target": target_agent,
            "request_id": request_id,
            "status": "failed",
            "error": error_code,
            "latency_ms": latency_ms,
        }
    )

    return {
        "status": "failed",
        "error": error_code,
        "message": message,
        "response": None,
        "request_id": request_id,
        "latency_ms": latency_ms,
    }


# ---------------------------------------------------------------------------
# HTTP Server
# ---------------------------------------------------------------------------


class TalkHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        import urllib.parse

        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/registry":
            self._respond(200, get_registry())
        elif parsed.path == "/agents":
            self._respond(200, get_agents_with_status())
        elif parsed.path == "/health":
            self._respond(200, {"status": "ok", "agent_id": AGENT_ID})
        else:
            self._respond(
                404,
                {
                    "error": "Not found",
                    "endpoints": {
                        "POST /talk": "Send a verified message to another agent",
                        "GET /registry": "List registered agents",
                        "POST /registry": "Register or update an agent",
                        "DELETE /registry/<id>": "Remove an agent",
                        "GET /agents": "List agents with status info",
                        "GET /health": "Health check",
                    },
                },
            )

    def do_POST(self):
        import urllib.parse

        parsed = urllib.parse.urlparse(self.path)
        body = self._read_body()
        if body is None:
            return

        if parsed.path == "/talk":
            self._handle_talk(body)
        elif parsed.path == "/registry":
            self._handle_register(body)
        else:
            self._respond(404, {"error": "Not found. Use POST /talk or POST /registry."})

    def do_DELETE(self):
        import urllib.parse

        parsed = urllib.parse.urlparse(self.path)

        if parsed.path.startswith("/registry/"):
            agent_id = parsed.path[len("/registry/") :]
            if not agent_id:
                self._respond(400, {"error": "Missing agent ID in path"})
                return
            result = unregister_agent(agent_id)
            status = 404 if "error" in result else 200
            self._respond(status, result)
        else:
            self._respond(404, {"error": "Not found."})

    def _handle_talk(self, body: dict):
        target = body.get("target_agent")
        message = body.get("message")
        timeout_ms = body.get("timeout_ms", DEFAULT_TIMEOUT_MS)
        hop_count = body.get("hop_count", 0)

        if not target:
            self._respond(400, {"error": "Missing required field: target_agent"})
            return
        if not message:
            self._respond(400, {"error": "Missing required field: message"})
            return
        if not isinstance(timeout_ms, (int, float)) or timeout_ms <= 0:
            timeout_ms = DEFAULT_TIMEOUT_MS

        result = talk_to_agent(target, message, int(timeout_ms), int(hop_count))
        status_code = 200 if result["status"] == "verified" else 502
        self._respond(status_code, result)

    def _handle_register(self, body: dict):
        agent_id = body.get("agent_id") or body.get("id")
        endpoint = body.get("endpoint")
        name = body.get("name")

        if not agent_id:
            self._respond(400, {"error": "Missing required field: agent_id"})
            return
        if not endpoint:
            self._respond(400, {"error": "Missing required field: endpoint"})
            return

        result = register_agent(agent_id, endpoint, name)
        self._respond(200, result)

    def _read_body(self) -> dict | None:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self._respond(400, {"error": "Empty request body"})
            return None
        try:
            return json.loads(self.rfile.read(content_length))
        except json.JSONDecodeError:
            self._respond(400, {"error": "Request body must be valid JSON"})
            return None

    def _respond(self, status: int, body: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body, indent=2, default=str).encode())

    def log_message(self, fmt, *args):
        print(f"[talk-to-agent] {args[0]}")


def main():
    _load_registry()

    port = int(os.environ.get("PORT", DEFAULT_PORT))
    HTTPServer.allow_reuse_address = True
    max_retries = 5
    for attempt in range(max_retries):
        try:
            server = HTTPServer(("0.0.0.0", port), TalkHandler)
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

    print(f"talk_to_agent running on http://localhost:{port}")
    print(f"  Agent ID: {AGENT_ID}")
    print("  POST /talk        — send a verified message to another agent")
    print("  GET  /registry    — list registered agents")
    print("  POST /registry    — register/update an agent")
    print("  DELETE /registry/ — remove an agent")
    print("  GET  /agents      — list agents with status info")
    print("  GET  /health      — health check")
    print(f"\nRegistry: {len(_registry)} agent(s) loaded from {REGISTRY_FILE}")
    for aid, info in _registry.items():
        print(f"  {aid} → {info.get('endpoint')} ({info.get('name', aid)})")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
