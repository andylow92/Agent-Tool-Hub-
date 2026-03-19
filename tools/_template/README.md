# Tool Name

## What It Does

Brief description of the tool's purpose and functionality.

## Why It Exists

What problem does this solve for AI agents? Why would an agent need this tool?

## Inputs

| Parameter | Type     | Required | Description          |
|-----------|----------|----------|----------------------|
| `query`   | `string` | Yes      | The search query     |
| `limit`   | `int`    | No       | Max results to return|

## Outputs

| Field     | Type     | Description              |
|-----------|----------|--------------------------|
| `results` | `array`  | List of matching items   |
| `count`   | `int`    | Total number of results  |

Example response:

```json
{
  "results": ["item1", "item2"],
  "count": 2
}
```

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set required environment variables
export API_KEY=your_key_here

# Run the tool
python main.py
```

## Example

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"query": "example search", "limit": 5}'
```

## Notes

- Rate limited to 100 requests/minute
- Requires API key from [service provider]
- Returns empty results array if no matches found
- Maximum query length: 500 characters
