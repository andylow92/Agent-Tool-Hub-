# Talk to Agent

## What It Does

Provides verified inter-agent communication. An AI agent calls this tool whenever it needs to ask another agent a question. The tool handles connection, message delivery, and response verification in one atomic call. If the target agent is unreachable or the response can't be verified, the tool returns an explicit failure with `response: null` — making it impossible for the calling LLM to hallucinate a response.

## Why It Exists

In multi-agent systems, when Agent A relays a question to Agent B and the connection silently fails, Agent A (an LLM) often fabricates a plausible-sounding answer and presents it as if Agent B said it. The user has no way to tell the difference. This tool eliminates that failure mode entirely by:

1. Generating a unique `request_id` per call
2. Requiring the target agent to echo it back
3. Returning `response: null` on any failure — giving the LLM nothing to fabricate from

## How It Works

1. Agent calls `POST /talk` with a target agent ID and message
2. Tool looks up the target in its registry
3. Tool generates a UUID `request_id` and POSTs to the target's endpoint
4. Target agent must echo back the same `request_id` in its response
5. If `request_id` matches → **verified** response returned
6. If anything fails → **failed** with `response: null`

## Inputs

### POST /talk

| Field          | Type   | Required | Default | Description |
|----------------|--------|----------|---------|-------------|
| `target_agent` | string | Yes      | —       | ID of the agent to contact (must be in registry) |
| `message`      | string | Yes      | —       | Message or question to send |
| `timeout_ms`   | number | No       | 10000   | Max wait time in milliseconds |
| `hop_count`    | number | No       | 0       | Current relay depth (for circular call protection) |

### POST /registry

| Field      | Type   | Required | Description |
|------------|--------|----------|-------------|
| `agent_id` | string | Yes      | Unique identifier for the agent |
| `endpoint` | string | Yes      | URL where the agent accepts messages |
| `name`     | string | No       | Human-readable name |

## Outputs

### Success

```json
{
  "status": "verified",
  "source": "billing-agent",
  "response": "Your balance is $2,340.00",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2025-01-15T10:30:00+00:00",
  "latency_ms": 234.5
}
```

### Failure

```json
{
  "status": "failed",
  "error": "unreachable",
  "message": "Could not reach 'billing-agent' at http://localhost:9001. The agent may be offline.",
  "response": null,
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "latency_ms": 10001.2
}
```

Error codes: `unknown_agent`, `unreachable`, `timeout`, `invalid_response`, `request_id_mismatch`, `response_too_large`, `max_depth_exceeded`.

### GET /agents

```json
{
  "agents": [
    {
      "id": "weather-agent",
      "name": "Weather Agent",
      "endpoint": "http://localhost:9001",
      "registered_at": "2025-01-15T10:00:00+00:00",
      "last_status": "ok",
      "last_contacted": "2025-01-15T10:30:00+00:00",
      "last_latency_ms": 234.5
    }
  ],
  "count": 1
}
```

## Setup

### 1. Start the talk_to_agent server

```bash
# Optional: set your agent identity
export AGENT_ID=orchestrator

python agent_talk.py
# Runs on http://localhost:8004
```

### 2. Register agents (or use registry.json)

Agents can be pre-configured in `registry.json`:

```json
{
  "weather-agent": {
    "endpoint": "http://localhost:9001",
    "name": "Weather Agent"
  }
}
```

Or registered dynamically:

```bash
curl -X POST http://localhost:8004/registry \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "weather-agent", "endpoint": "http://localhost:9001", "name": "Weather Agent"}'
```

### 3. Make existing tools talk_to_agent-compatible

Use the included **adapter** to wrap any HTTP tool:

```bash
# Wrap the weather API (port 8001) as a talk_to_agent-compatible agent on port 9001
python adapter.py --tool-url http://localhost:8001 --port 9001 --agent-id weather-agent

# Wrap the file converter (port 8003) on port 9003, auto-register with the hub
python adapter.py --tool-url http://localhost:8003 --port 9003 \
    --agent-id file-converter --register http://localhost:8004
```

### 4. Or use Docker

```bash
docker build -t talk-to-agent .
docker run -p 8004:8004 -e AGENT_ID=orchestrator talk-to-agent
```

## Example

### Success flow

```bash
# Send a message to the weather agent
curl -X POST http://localhost:8004/talk \
  -H "Content-Type: application/json" \
  -d '{
    "target_agent": "weather-agent",
    "message": "{\"path\": \"/weather\", \"params\": {\"city\": \"London\"}}"
  }'

# Response:
# {
#   "status": "verified",
#   "source": "weather-agent",
#   "response": "{\"city\":\"London\",\"temperature\":{\"current\":12.5,...}}",
#   "request_id": "a1b2c3d4-...",
#   "latency_ms": 342.1
# }
```

### Failure flow

```bash
# Try to reach an offline agent
curl -X POST http://localhost:8004/talk \
  -H "Content-Type: application/json" \
  -d '{"target_agent": "billing-agent", "message": "What is my balance?"}'

# Response:
# {
#   "status": "failed",
#   "error": "unreachable",
#   "message": "Could not reach 'billing-agent' at ...",
#   "response": null,
#   "request_id": "e5f6a7b8-...",
#   "latency_ms": 10001.3
# }
```

### Discover available agents

```bash
curl http://localhost:8004/agents
```

### Using as a Python function

```python
from agent_talk import talk_to_agent, register_agent, _load_registry

_load_registry()
# Or register manually:
register_agent("my-agent", "http://localhost:9001", "My Agent")

result = talk_to_agent("my-agent", "Hello, what can you do?")
if result["status"] == "verified":
    print(f"Response: {result['response']}")
else:
    print(f"Failed: {result['message']}")
```

## Target Agent Contract

For any agent to be reachable via talk_to_agent, it must accept POST requests with:

```json
{
  "request_id": "uuid-string",
  "from": "calling-agent-id",
  "message": "the question or request",
  "hop_count": 1
}
```

And respond with:

```json
{
  "request_id": "same-uuid-echoed-back",
  "from": "this-agent-id",
  "response": "the actual answer"
}
```

The `request_id` **must** match. If it doesn't, verification fails.

Use `adapter.py` to wrap existing HTTP tools that don't natively support this protocol.

## Architecture

```
┌─────────────┐     POST /talk      ┌──────────────┐     POST (protocol)    ┌──────────────┐
│  Calling LLM │ ──────────────────> │ talk_to_agent │ ───────────────────> │ Target Agent  │
│  (Agent A)   │ <────────────────── │  (port 8004)  │ <─────────────────── │  (adapter)    │
└─────────────┘   verified/failed    └──────────────┘   {request_id, ...}   └──────┬───────┘
                                           │                                       │
                                      ┌────┴────┐                            ┌─────┴──────┐
                                      │Registry │                            │ Actual Tool │
                                      │  .json  │                            │ (e.g. 8001) │
                                      └─────────┘                            └────────────┘
```

## Adapter

The `adapter.py` script wraps any HTTP tool to make it speak the talk_to_agent protocol. It supports two message modes:

**Structured mode** — message is JSON with routing info:
```json
{"path": "/weather", "method": "GET", "params": {"city": "London"}}
```

**Natural language mode** — message is plain text, forwarded to the tool's default endpoint:
```
"What is the weather in London?"
```

Adapter options:
- `--tool-url` — base URL of the tool to wrap (required)
- `--port` — port for the adapter (default: 9001)
- `--agent-id` — identifier for this adapted agent (required)
- `--default-path` — default path for raw messages (default: `/`)
- `--register` — auto-register with a talk_to_agent registry URL

## Notes

- **No external dependencies** — Python stdlib only.
- **No auth** — runs locally. Add auth at the network level if needed.
- **No retries** — if a call fails, the failure is reported. The calling agent or user decides whether to retry.
- **Audit log** — every call is logged to `audit.log` as structured JSON lines (timestamp, request_id, target, status, latency).
- **Hop count protection** — messages are rejected after 5 relays to prevent circular calls between agents.
- **Response size limit** — responses over 100KB are rejected with `response_too_large`.
- **Timeout** — default 10 seconds per call, configurable per request.
- **Registry** — loaded from `registry.json` on startup, updated dynamically via `POST /registry`. Changes persist to disk.
- **Port** — 8004 by default, override with `PORT` env var.
- **Python 3.7+** required.
