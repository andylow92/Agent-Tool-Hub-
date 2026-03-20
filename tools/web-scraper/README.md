# Web Scraper

## What It Does

A lightweight HTTP server that fetches any URL and returns clean, readable text. Strips HTML tags, scripts, and styles — giving agents just the content they need to read and reason about.

## Why It Exists

Agents frequently need to read web pages but raw HTML is noisy and wastes tokens. This tool extracts the meaningful text content, page title, and meta description so agents can quickly understand a page without parsing HTML themselves.

## Inputs

| Parameter | Type      | Required | Default | Description                      |
|-----------|-----------|----------|---------|----------------------------------|
| `url`     | `string`  | Yes      | —       | URL to fetch and extract text from |
| `timeout` | `integer` | No       | `10`    | Request timeout in seconds       |

Supports both GET (query params) and POST (JSON body).

## Outputs

Returns a JSON object:

```json
{
  "url": "https://example.com",
  "title": "Example Domain",
  "description": "This domain is for use in illustrative examples.",
  "text": "Example Domain\nThis domain is for use in illustrative examples...",
  "characters": 234
}
```

On error:

```json
{
  "error": "HTTP 404: Not Found",
  "url": "https://example.com/missing"
}
```

## Setup

```bash
python scraper.py
```

The server starts on `http://localhost:8006` by default. Override with `PORT` env var.

### Or use Docker

```bash
docker build -t web-scraper .
docker run -p 8006:8006 web-scraper
```

## Example

```bash
# Scrape a page via GET
curl "http://localhost:8006/scrape?url=https://example.com"

# Scrape via POST with timeout
curl -X POST http://localhost:8006/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "timeout": 15}'
```

### Using as a Python function (no server needed)

```python
from scraper import scrape

result = scrape("https://example.com")
print(result["title"])  # "Example Domain"
print(result["text"])   # Clean text content
```

### Tool schema for agents

A ready-to-use tool definition is provided in [`tool.json`](tool.json).

## Notes

- **No external dependencies:** Uses only Python standard library.
- **5 MB content limit** to prevent memory issues on very large pages.
- **Respects robots.txt** via a descriptive User-Agent string.
- **Supports HTML and plain text** content types.
- **Python 3.7+** required.
