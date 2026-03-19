# AGENTS.md — File Converter Tool

> **You are an AI agent.** This file tells you everything you need to use this tool. No other files required.

---

## What This Tool Does

Converts file content between formats. You send content + source format + target format, and get back structured data. Handles CSV, TSV, JSON, PDF, HTML, Markdown, XLSX, and XML.

**Use this when you need to:** parse a PDF, convert a spreadsheet to JSON, extract text from HTML, transform CSV data, or convert between any supported format pair.

---

## Files In This Directory

| File | Purpose |
|------|---------|
| `convert.py` | Main code — HTTP server + importable `convert()` function |
| `tool.json` | Function-calling schema — load this as your tool definition |
| `README.md` | Human-readable documentation |
| `AGENTS.md` | You are here |
| `Dockerfile` | Run in a container |
| `requirements.txt` | Dependencies (PyPDF2, openpyxl are optional) |

---

## How to Call This Tool

### Option 1: HTTP POST (server must be running)

```
POST http://localhost:8003/convert
Content-Type: application/json

{
  "content": "name,age\nAlice,30\nBob,25",
  "from": "csv",
  "to": "json"
}
```

### Option 2: Python import (no server needed)

```python
from convert import convert
result = convert("name,age\nAlice,30", "csv", "json")
```

### Discovery endpoint

```
GET http://localhost:8003/conversions
```

Returns all supported conversion paths — call this first if you're unsure what's available.

---

## All Supported Conversions

| From     | To            | Notes |
|----------|---------------|-------|
| `csv`    | `json`        | Returns array of objects with column headers as keys |
| `csv`    | `tsv`         | Delimiter swap |
| `tsv`    | `json`        | Same as csv→json but tab-delimited |
| `json`   | `csv`         | Input must be array of objects |
| `json`   | `xml`         | Converts JSON structure to XML elements |
| `html`   | `text`        | Strips tags, returns plain text |
| `html`   | `json`        | Extracts `<table>` elements into structured data |
| `markdown`| `text`       | Strips formatting, returns plain text |
| `markdown`| `html`       | Converts to HTML |
| `xml`    | `json`        | Converts XML tree to nested dict |
| `pdf`    | `text`        | Extracts text per page (requires PyPDF2) |
| `pdf`    | `json`        | Same as pdf→text but structured by page |
| `xlsx`   | `json`        | All sheets, headers + rows (requires openpyxl) |
| `xlsx`   | `csv`         | One CSV per sheet (requires openpyxl) |

**Format aliases:** `md` → `markdown`, `htm` → `html`, `xls` → `xlsx`

---

## Parameters

| Field     | Type   | Required | Description |
|-----------|--------|----------|-------------|
| `content` | string | **YES**  | The file content. **Text formats:** send raw text. **Binary formats (PDF, XLSX):** send base64-encoded string. |
| `from`    | string | **YES**  | Source format: `csv`, `tsv`, `json`, `pdf`, `html`, `markdown`, `xlsx`, `xml` |
| `to`      | string | **YES**  | Target format: `csv`, `tsv`, `json`, `text`, `html`, `xml` |

### Important: Binary vs Text Content

- **Text formats** (CSV, TSV, JSON, HTML, Markdown, XML): send the raw text string as `content`.
- **Binary formats** (PDF, XLSX): you MUST base64-encode the file bytes first.

```python
import base64
with open("file.pdf", "rb") as f:
    content = base64.b64encode(f.read()).decode()
```

---

## Response Formats

### CSV/TSV → JSON

```json
{
  "data": [{"column1": "value1", "column2": "value2"}],
  "rows": 1,
  "columns": ["column1", "column2"]
}
```

### PDF → Text

```json
{
  "data": "all text concatenated",
  "pages": [{"page": 1, "text": "page 1 text"}, {"page": 2, "text": "page 2 text"}],
  "page_count": 2,
  "characters": 5000
}
```

### XLSX → JSON

```json
{
  "sheets": [
    {
      "sheet": "Sheet1",
      "headers": ["col1", "col2"],
      "data": [{"col1": "a", "col2": "b"}],
      "rows": 1
    }
  ],
  "sheet_count": 1
}
```

### HTML → Text

```json
{
  "data": "plain text content",
  "characters": 500
}
```

### HTML → JSON (table extraction)

```json
{
  "tables": [
    {"headers": ["H1", "H2"], "rows": [{"H1": "a", "H2": "b"}], "row_count": 1}
  ],
  "table_count": 1
}
```

### JSON → CSV

```json
{
  "data": "col1,col2\nval1,val2\n",
  "rows": 1,
  "format": "text/csv"
}
```

### Error

```json
{
  "error": "description of what went wrong",
  "supported": [{"from": "csv", "to": "json"}, ...]
}
```

**Always check for the `error` key before using the response.**

---

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| `Unsupported conversion: X → Y` | Format pair not supported | Check `GET /conversions` for valid paths |
| `PDF content must be base64-encoded` | Raw bytes sent for PDF | Base64-encode the file content first |
| `XLSX content must be base64-encoded` | Raw bytes sent for XLSX | Base64-encode the file content first |
| `PyPDF2 is not installed` | PDF dep missing | `pip install PyPDF2` |
| `openpyxl is not installed` | XLSX dep missing | `pip install openpyxl` |
| `Invalid JSON input: ...` | Bad JSON in content field | Check the JSON is valid |
| `Invalid XML: ...` | Malformed XML | Check the XML is well-formed |
| `JSON must be an array of objects` | json→csv needs a list | Wrap data in an array of objects |

---

## Setup (Before First Use)

1. **Install optional dependencies** (only if you need PDF or XLSX):
   ```bash
   pip install PyPDF2 openpyxl
   ```

2. **Start the server:**
   ```bash
   python convert.py
   # Runs on http://localhost:8003
   ```

3. **Or use Docker** (includes all dependencies):
   ```bash
   docker build -t file-converter .
   docker run -p 8003:8003 file-converter
   ```

---

## Function-Calling Schema

Load `tool.json` in this directory to register this as a callable tool:

```json
{
  "name": "file_converter",
  "description": "Convert file content between formats. Supports CSV, TSV, JSON, PDF, HTML, Markdown, XLSX, and XML.",
  "parameters": {
    "type": "object",
    "properties": {
      "content": { "type": "string", "description": "File content (raw text or base64 for binary)" },
      "from": { "type": "string", "enum": ["csv", "tsv", "json", "pdf", "html", "markdown", "xlsx", "xml"] },
      "to": { "type": "string", "enum": ["csv", "tsv", "json", "text", "html", "xml"] }
    },
    "required": ["content", "from", "to"]
  }
}
```

---

## Limits and Constraints

- **No auth required** — runs locally, no external API calls
- **No rate limits** — limited only by your machine's resources
- **Port:** 8003 (override with `PORT` env var)
- **PDF/XLSX** require optional pip packages; all other conversions are stdlib-only
- **Markdown parser** is regex-based — covers common patterns, may miss edge cases
- **HTML table extraction** only finds `<table>` elements; nested tables may produce unexpected results
- **Python:** 3.7+ required
