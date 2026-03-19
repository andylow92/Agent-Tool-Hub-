# AGENTS.md — Perplexity Search Tool

> **You are an AI agent.** This file tells you everything you need to use this tool. No other files required.

---

## What This Tool Does

Searches the web using the Perplexity Sonar API and returns a **direct answer with source citations** — not a list of links. You ask a question, you get an answer and the URLs it was sourced from.

**Use this when you need:** factual information, current events, real-time data, documentation lookups, or anything that requires up-to-date web knowledge.

---

## Files In This Directory

| File | Purpose |
|------|---------|
| `search.py` | Main code — HTTP server + importable `search()` function |
| `tool.json` | Function-calling schema — load this as your tool definition |
| `README.md` | Human-readable documentation |
| `Dockerfile` | Run in a container |
| `requirements.txt` | No external deps (stdlib only) |

---

## How to Call This Tool

### Option 1: HTTP (server must be running)

```
GET http://localhost:8002/search?q={query}&model={model}&recency={recency}&max_tokens={max_tokens}
```

### Option 2: Python import (no server needed)

```python
from search import search
result = search("your question here")
```

---

## Parameters

| Name         | Type    | Required | Default | Allowed Values |
|-------------|---------|----------|---------|----------------|
| `q` / `query` | string | **YES** | — | Any question or search query |
| `model`     | string  | no       | `sonar` | `sonar` = fast, lightweight; `sonar-pro` = deeper answers, more citations |
| `recency`   | string  | no       | none    | `day`, `week`, `month`, `year` — filters sources by freshness |
| `max_tokens`| integer | no       | `1024`  | Maximum answer length in tokens |

> Use `q` for HTTP calls, `query` for Python function calls.

---

## Response Format

### Success (HTTP 200)

```json
{
  "answer": "The answer text. Citations appear as [1], [2] referencing the citations array.",
  "citations": [
    "https://source-one.com/article",
    "https://source-two.com/page"
  ],
  "model": "sonar",
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 150,
    "total_tokens": 175
  }
}
```

**How to read the response:**
- `answer` — the synthesized answer. Numbers in brackets like `[1]` reference the `citations` array (0-indexed: `[1]` = `citations[0]`).
- `citations` — ordered list of source URLs the answer was built from.
- `usage` — token counts for tracking costs.

### Error (HTTP 400/401/502)

```json
{
  "error": "description of what went wrong"
}
```

**Always check for the `error` key before using the response.**

---

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| `PERPLEXITY_API_KEY environment variable is not set` | Missing API key | Set `export PERPLEXITY_API_KEY=your_key` |
| `API error 401: ...` | Invalid or expired key | Get a new key from perplexity.ai |
| `Invalid model '...'` | Bad model name | Use `sonar` or `sonar-pro` only |
| `Invalid recency '...'` | Bad recency value | Use `day`, `week`, `month`, or `year` |
| `Network error: ...` | Can't reach Perplexity | Check internet connectivity |
| `Missing required parameter: q` | No query provided | Include `?q=your+question` in the URL |

---

## Setup (Before First Use)

1. **Set the API key:**
   ```bash
   export PERPLEXITY_API_KEY=your_key_here
   ```

2. **Start the server:**
   ```bash
   python search.py
   # Runs on http://localhost:8002
   ```

3. **Or use Docker:**
   ```bash
   docker build -t perplexity-search .
   docker run -p 8002:8002 -e PERPLEXITY_API_KEY=your_key_here perplexity-search
   ```

---

## Function-Calling Schema

Load `tool.json` in this directory to register this as a callable tool:

```json
{
  "name": "perplexity_search",
  "description": "Search the web using Perplexity Sonar AI. Returns a direct, synthesized answer with citations.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": { "type": "string", "description": "The question or search query" },
      "model": { "type": "string", "enum": ["sonar", "sonar-pro"], "default": "sonar" },
      "recency": { "type": "string", "enum": ["day", "week", "month", "year"] },
      "max_tokens": { "type": "integer", "default": 1024 }
    },
    "required": ["query"]
  }
}
```

---

## Limits and Constraints

- **Rate limit:** ~50 requests/minute (varies by API tier)
- **Timeout:** 30 seconds per request
- **Pricing:** $1 per million tokens (input and output)
- **Port:** 8002 (override with `PORT` env var)
- **Python:** 3.7+ required
- **Dependencies:** None — Python standard library only
