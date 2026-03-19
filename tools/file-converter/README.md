# File Converter

## What It Does

Converts file content between common formats — CSV, TSV, JSON, PDF, HTML, Markdown, XLSX, and XML. Accepts content via HTTP POST and returns structured JSON that agents can parse and reason about.

## Why It Exists

AI agents frequently receive files they can't natively read (PDFs, spreadsheets, HTML pages) or need data in a different format for downstream processing. Instead of building a conversion pipeline into every agent, this tool handles it as a standalone service.

## Supported Conversions

| From       | To               | Dependencies        |
|------------|------------------|---------------------|
| CSV        | JSON, TSV        | None (stdlib)       |
| TSV        | JSON             | None (stdlib)       |
| JSON       | CSV, XML         | None (stdlib)       |
| HTML       | Text, JSON       | None (stdlib)       |
| Markdown   | Text, HTML       | None (stdlib)       |
| XML        | JSON             | None (stdlib)       |
| JSON       | XML              | None (stdlib)       |
| PDF        | Text, JSON       | PyPDF2              |
| XLSX       | JSON, CSV        | openpyxl            |

## Inputs

Send a POST request with a JSON body:

| Field     | Type     | Required | Description                                                           |
|-----------|----------|----------|-----------------------------------------------------------------------|
| `content` | `string` | Yes      | File content. Raw text for text formats, base64-encoded for binary (PDF, XLSX). |
| `from`    | `string` | Yes      | Source format: `csv`, `tsv`, `json`, `pdf`, `html`, `markdown`, `xlsx`, `xml` |
| `to`      | `string` | Yes      | Target format: `csv`, `tsv`, `json`, `text`, `html`, `xml`           |

Aliases accepted: `md` → `markdown`, `htm` → `html`, `xls` → `xlsx`.

## Outputs

### CSV / TSV → JSON

```json
{
  "data": [{"name": "Alice", "age": "30"}, {"name": "Bob", "age": "25"}],
  "rows": 2,
  "columns": ["name", "age"]
}
```

### PDF → Text

```json
{
  "data": "Full extracted text...",
  "pages": [
    {"page": 1, "text": "Page 1 text..."},
    {"page": 2, "text": "Page 2 text..."}
  ],
  "page_count": 2,
  "characters": 4521
}
```

### XLSX → JSON

```json
{
  "sheets": [
    {
      "sheet": "Sheet1",
      "headers": ["name", "age"],
      "data": [{"name": "Alice", "age": 30}],
      "rows": 1
    }
  ],
  "sheet_count": 1
}
```

### HTML → Text

```json
{
  "data": "Plain text extracted from HTML...",
  "characters": 1234
}
```

### HTML → JSON (table extraction)

```json
{
  "tables": [
    {"headers": ["Col1", "Col2"], "rows": [{"Col1": "a", "Col2": "b"}], "row_count": 1}
  ],
  "table_count": 1
}
```

### Error

```json
{
  "error": "Unsupported conversion: foo → bar",
  "supported": [{"from": "csv", "to": "json"}, ...]
}
```

## Setup

### 1. Install optional dependencies (only if you need PDF or XLSX)

```bash
pip install PyPDF2 openpyxl
```

These are optional — all other conversions work with zero dependencies.

### 2. Run the server

```bash
python convert.py
```

The server starts on `http://localhost:8003` by default. Override with `PORT` env var.

### 3. Or use Docker

```bash
docker build -t file-converter .
docker run -p 8003:8003 file-converter
```

## Example

```bash
# CSV to JSON
curl -X POST http://localhost:8003/convert \
  -H "Content-Type: application/json" \
  -d '{"content": "name,age\nAlice,30\nBob,25", "from": "csv", "to": "json"}'

# HTML to plain text
curl -X POST http://localhost:8003/convert \
  -H "Content-Type: application/json" \
  -d '{"content": "<h1>Hello</h1><p>World</p>", "from": "html", "to": "text"}'

# PDF to text (base64-encoded PDF)
curl -X POST http://localhost:8003/convert \
  -H "Content-Type: application/json" \
  -d "{\"content\": \"$(base64 -w0 document.pdf)\", \"from\": \"pdf\", \"to\": \"text\"}"

# List all supported conversions
curl http://localhost:8003/conversions
```

### Using as a Python function (no server needed)

```python
from convert import convert

# CSV to JSON
result = convert("name,age\nAlice,30\nBob,25", "csv", "json")
print(result["data"])  # [{"name": "Alice", "age": "30"}, ...]

# PDF to text (base64-encoded)
import base64
with open("document.pdf", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
result = convert(b64, "pdf", "text")
print(result["data"])
```

### Tool schema for agents

A ready-to-use tool definition is provided in [`tool.json`](tool.json).

## Notes

- **No auth required** — this tool runs locally and doesn't call external APIs.
- **Binary formats (PDF, XLSX) must be base64-encoded** in the `content` field.
- **PDF and XLSX require optional dependencies** (`PyPDF2`, `openpyxl`). All other conversions use Python stdlib only.
- **HTML table extraction** (`html` → `json`) pulls structured data from `<table>` elements. If no tables are found, it falls back to plain text.
- **Markdown conversion** is lightweight (regex-based, no external parser). Covers common patterns but may miss edge cases.
- **GET `/conversions`** returns a list of all supported conversion paths — useful for agents to discover what's available.
- **Python 3.7+** required.
