# AGENTS.md — Talk to Agent Tool

> **You are an AI agent.** This file tells you everything you need to use this tool. No other files required.

---

## What This Tool Does

Sends verified messages to other agents and returns their responses. Guarantees that if the tool says an agent responded, it really did — no hallucinated answers possible. If anything fails, returns `response: null`.

**Use this when you need to:** ask another agent a question, request data from another service, relay a user's query to a specialist agent, or verify that an agent is reachable.

**CRITICAL RULE:** NEVER answer on behalf of another agent without using this tool. If this tool returns a failure, tell the user honestly — do NOT guess or fabricate an answer.

---

## Files In This Directory

| File | Purpose |
|------|---------|
| `agent_talk.py` | Main server — POST /talk, registry management, verification logic |
| `adapter.py` | Wraps existing HTTP tools to speak the talk_to_agent protocol |
| `registry.json` | Default agent registry (agent IDs → endpoints) |
| `tool.json` | Function-calling schema — load this as your tool definition |
| `audit.log` | Structured JSON audit trail (created at runtime) |
| `README.md` | Human-readable docs |
| `AGENTS.md` | You are here |
| `Dockerfile` | Container deployment |
| `requirements.txt` | Dependencies (none — stdlib only) |

---

## How to Call This Tool

### Option 1: HTTP POST (server running on port 8004)

```
POST http://localhost:8004/talk
Content-Type: application/json

{
  "target_agent": "weather-agent",
  "message": "{\"path\": \"/weather\", \"params\": {\"city\": \"London\"}}",
  "timeout_ms": 10000
}
```

### Option 2: Python import

```python
from agent_talk import talk_to_agent, _load_registry

_load_registry()
result = talk_to_agent("weather-agent", "What is the weather in London?")
```

### Discovery

```
GET http://localhost:8004/agents    — list all agents with status
GET http://localhost:8004/registry  — raw registry data
GET http://localhost:8004/health    — health check
```

---

## Parameters

| Field          | Type   | Required | Default | Description |
|----------------|--------|----------|---------|-------------|
| `target_agent` | string | **YES**  | —       | ID of the agent to contact. Must be in the registry. |
| `message`      | string | **YES**  | —       | What to send. Can be plain text or structured JSON (see below). |
| `timeout_ms`   | number | no       | 10000   | Max wait time in milliseconds. |
| `hop_count`    | number | no       | 0       | Current relay depth. Do NOT set this manually — it's managed internally. |

### Message formats

**Plain text** — forwarded as-is:
```
"What is the current balance for user 123?"
```

**Structured JSON** — routed to a specific tool endpoint:
```json
{
  "path": "/weather",
  "method": "GET",
  "params": {"city": "London", "units": "metric"}
}
```

```json
{
  "path": "/convert",
  "method": "POST",
  "body": {"content": "name,age\nAlice,30", "from": "csv", "to": "json"}
}
```

---

## Response Formats

### Success (status: "verified")

```json
{
  "status": "verified",
  "source": "weather-agent",
  "response": "{\"city\":\"London\",\"temperature\":{\"current\":12.5}}",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2025-01-15T10:30:00+00:00",
  "latency_ms": 234.5
}
```

**Always check `status == "verified"` before using `response`.**

### Failure (status: "failed")

```json
{
  "status": "failed",
  "error": "unreachable",
  "message": "Could not reach 'weather-agent' at http://localhost:9001.",
  "response": null,
  "request_id": "a1b2c3d4-...",
  "latency_ms": 10001.2
}
```

**`response` is ALWAYS `null` on failure. There is nothing to use.**

### Error codes

| Code | Meaning |
|------|---------|
| `unknown_agent` | Target agent ID not found in registry |
| `unreachable` | Could not connect to the target endpoint (offline, wrong URL, HTTP error) |
| `timeout` | Target did not respond within `timeout_ms` |
| `invalid_response` | Target responded but not with valid JSON |
| `request_id_mismatch` | Target returned a different `request_id` — response cannot be trusted |
| `response_too_large` | Response exceeded 100KB limit |
| `max_depth_exceeded` | Message relayed more than 5 times (circular call protection) |

---

## Registry Management

### List agents
```
GET http://localhost:8004/registry
```

### Register a new agent
```
POST http://localhost:8004/registry
{"agent_id": "my-agent", "endpoint": "http://localhost:9005", "name": "My Agent"}
```

### Remove an agent
```
DELETE http://localhost:8004/registry/my-agent
```

### Agents with status (richer than raw registry)
```
GET http://localhost:8004/agents
```
Returns last_status, last_contacted, last_latency_ms for each agent.

---

## Making Existing Tools Compatible

Our existing tools (weather-api, perplexity-search, file-converter) don't natively speak the talk_to_agent protocol. Use `adapter.py` to wrap them:

```bash
# Wrap weather-api (port 8001) → adapter on port 9001
python adapter.py --tool-url http://localhost:8001 --port 9001 --agent-id weather-agent

# Wrap file-converter (port 8003) → adapter on port 9003, auto-register
python adapter.py --tool-url http://localhost:8003 --port 9003 \
    --agent-id file-converter --register http://localhost:8004
```

Then talk_to_agent can reach them through the adapter.

### Structured message through adapter

To call the weather API through talk_to_agent:
```json
{
  "target_agent": "weather-agent",
  "message": "{\"path\": \"/weather\", \"method\": \"GET\", \"params\": {\"city\": \"Tokyo\"}}"
}
```

The adapter translates this into `GET http://localhost:8001/weather?city=Tokyo` and wraps the response.

---

## Target Agent Contract

Any agent that wants to be reachable must accept POST with:

```json
{
  "request_id": "uuid",
  "from": "caller-id",
  "message": "the question",
  "hop_count": 1
}
```

And respond with:

```json
{
  "request_id": "same-uuid-echoed-back",
  "from": "this-agent-id",
  "response": "the answer"
}
```

**The `request_id` MUST match.** If it doesn't, verification fails.

---

## Setup

1. **Start the server:**
   ```bash
   export AGENT_ID=orchestrator  # optional, defaults to "orchestrator"
   python agent_talk.py
   # Runs on http://localhost:8004
   ```

2. **Pre-configure agents** in `registry.json`, or register dynamically via `POST /registry`.

3. **Wrap existing tools** with `adapter.py` if they don't speak the protocol natively.

---

## Function-Calling Schema

Load `tool.json`:

```json
{
  "name": "talk_to_agent",
  "description": "Use this tool ANY time you need to ask another agent a question or request information from another agent. NEVER answer on behalf of another agent without using this tool. If this tool returns a failure, you MUST tell the user that the other agent could not be reached — do not guess or make up an answer.",
  "parameters": {
    "type": "object",
    "properties": {
      "target_agent": {"type": "string", "description": "Agent ID to contact"},
      "message": {"type": "string", "description": "Message to send"},
      "timeout_ms": {"type": "number", "default": 10000}
    },
    "required": ["target_agent", "message"]
  }
}
```

---

## Limits and Constraints

- **No external dependencies** — Python stdlib only
- **No auth** — runs locally, add network-level auth if needed
- **No retries** — failures are reported, not retried. Calling agent decides.
- **Port:** 8004 (override with `PORT` env var)
- **Timeout:** 10 seconds default, configurable per call
- **Response size:** 100KB max
- **Hop depth:** 5 max (prevents circular Agent A → B → A loops)
- **Audit log:** every call logged to `audit.log` as JSON lines
- **Registry:** persists to `registry.json` on every change
- **Python:** 3.7+ required
