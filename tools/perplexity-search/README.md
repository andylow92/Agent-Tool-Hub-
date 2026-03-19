# Perplexity Search

## What It Does

An AI-powered web search tool that returns **direct answers with citations** instead of raw search links. Wraps the [Perplexity Sonar API](https://docs.perplexity.ai/) as a standalone HTTP server any agent can call.

## Why It Exists

Traditional search APIs return a list of links. The agent then has to fetch each page, extract text, and synthesize an answer — that's slow, error-prone, and expensive. Perplexity does all of that in one call: it searches the web, reads the sources, and returns a clean answer with references.

This makes it the ideal "search tool" for agents that need factual, up-to-date information without a scraping pipeline.

## Inputs

| Parameter    | Type      | Required | Default  | Description                                                       |
|-------------|-----------|----------|----------|-------------------------------------------------------------------|
| `q`         | `string`  | Yes      | —        | The question or search query                                      |
| `model`     | `string`  | No       | `sonar`  | `sonar` (fast) or `sonar-pro` (deeper, more citations)           |
| `recency`   | `string`  | No       | —        | Filter sources: `day`, `week`, `month`, or `year`                |
| `max_tokens`| `integer` | No       | `1024`   | Maximum answer length in tokens                                   |

## Outputs

Returns a JSON object:

```json
{
  "answer": "Quantum computing uses quantum bits (qubits) that can exist in superposition, allowing them to process multiple states simultaneously. Unlike classical bits which are either 0 or 1, qubits can be both at once [1]. This enables quantum computers to solve certain problems exponentially faster than classical computers [2].",
  "citations": [
    "https://en.wikipedia.org/wiki/Quantum_computing",
    "https://www.ibm.com/topics/quantum-computing"
  ],
  "model": "sonar",
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 150,
    "total_tokens": 175
  }
}
```

On error, returns:

```json
{
  "error": "API error 401: Invalid API key"
}
```

## Setup

### 1. Get an API key

Sign up at [perplexity.ai](https://docs.perplexity.ai/) and generate an API key in the API settings.

### 2. Run the server

```bash
export PERPLEXITY_API_KEY=your_key_here
python search.py
```

The server starts on `http://localhost:8002` by default. Override with `PORT` env var.

### 3. Or use Docker

```bash
docker build -t perplexity-search .
docker run -p 8002:8002 -e PERPLEXITY_API_KEY=your_key_here perplexity-search
```

## Example

```bash
# Basic search
curl "http://localhost:8002/search?q=What+is+quantum+computing"

# Use the deeper model
curl "http://localhost:8002/search?q=latest+AI+breakthroughs&model=sonar-pro"

# Only recent sources (last week)
curl "http://localhost:8002/search?q=tech+news+today&recency=week"

# Combine options
curl "http://localhost:8002/search?q=Python+3.13+new+features&model=sonar-pro&recency=month&max_tokens=2048"
```

### Using as a Python function (no server needed)

```python
from search import search

result = search("What is the population of Tokyo?")
if "error" in result:
    print(f"Failed: {result['error']}")
else:
    print(result["answer"])
    print(f"Sources: {result['citations']}")
```

### Tool schema for agents

A ready-to-use tool definition is provided in [`tool.json`](tool.json) — compatible with OpenAI function calling format, LangChain, and similar frameworks.

## Notes

- **No free tier** — Perplexity API requires a payment method, but pricing is low ($1/M tokens for both input and output).
- **No external dependencies** — uses only Python standard library (`http.server`, `urllib`).
- **Two models available:**
  - `sonar` — fast, lightweight, good for simple factual queries.
  - `sonar-pro` — deeper analysis, more citations, better for complex questions.
- **Recency filter** is optional — omit it to search all time periods.
- **Citations are numbered** in the answer text (e.g., `[1]`, `[2]`) and correspond to the `citations` array by index.
- **Rate limits** — ~50 requests/minute depending on your tier.
- **30-second timeout** per request.
- **Python 3.7+** required.
- The `tool.json` file can be fed directly to an LLM as a function/tool definition.
