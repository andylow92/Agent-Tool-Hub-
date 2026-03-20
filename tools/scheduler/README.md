# Scheduler

## What It Does

A lightweight HTTP server that lets agents schedule HTTP callbacks at specific times or recurring intervals. Jobs persist to a JSON file and survive restarts.

## Why It Exists

Agents often need to perform actions in the future — send a reminder, poll an API on a schedule, or trigger a workflow at a specific time. This tool provides a simple HTTP interface for scheduling, listing, and cancelling jobs without requiring cron, Celery, or any external task queue.

## Inputs

### Schedule a job (POST /jobs)

| Parameter          | Type      | Required | Default  | Description                                          |
|--------------------|-----------|----------|----------|------------------------------------------------------|
| `callback_url`     | `string`  | Yes      | —        | URL to call when the job fires                       |
| `run_at`           | `string`  | No*      | —        | ISO 8601 datetime for one-shot jobs                  |
| `interval_seconds` | `integer` | No*      | `0`      | Repeat interval in seconds                           |
| `method`           | `string`  | No       | `POST`   | HTTP method for the callback (`GET` or `POST`)       |
| `payload`          | `object`  | No       | —        | JSON body to send with POST callbacks                |
| `name`             | `string`  | No       | —        | Human-readable job name                              |
| `max_runs`         | `integer` | No       | `0`      | Max executions (0 = unlimited for intervals)         |

*Either `run_at` or `interval_seconds` must be provided.

## Outputs

### Schedule response

```json
{
  "status": "scheduled",
  "job": {
    "id": "a1b2c3d4",
    "name": "hourly-check",
    "callback_url": "http://localhost:8001/weather?city=London",
    "method": "GET",
    "interval_seconds": 3600,
    "next_run": "2025-06-01T12:00:00+00:00",
    "max_runs": 0,
    "run_count": 0,
    "status": "active"
  }
}
```

## Setup

```bash
python scheduler.py
```

The server starts on `http://localhost:8010` by default. Override with `PORT` env var.

### Or use Docker

```bash
docker build -t scheduler .
docker run -p 8010:8010 scheduler
```

## Example

```bash
# Schedule a recurring job every 60 seconds
curl -X POST http://localhost:8010/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "health-check",
    "callback_url": "http://localhost:8001/health",
    "method": "GET",
    "interval_seconds": 60
  }'

# Schedule a one-shot job
curl -X POST http://localhost:8010/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "send-reminder",
    "callback_url": "http://localhost:8008/send",
    "method": "POST",
    "run_at": "2025-06-01T09:00:00Z",
    "payload": {
      "to": "user@example.com",
      "subject": "Reminder",
      "body": "Your meeting starts in 10 minutes."
    }
  }'

# List all jobs
curl http://localhost:8010/jobs

# Get a specific job
curl http://localhost:8010/jobs/a1b2c3d4

# Cancel a job
curl -X DELETE http://localhost:8010/jobs/a1b2c3d4

# Health check
curl http://localhost:8010/health
```

### Using as a Python function (no server needed)

```python
from scheduler import schedule_job, list_jobs, cancel_job

result = schedule_job(
    callback_url="http://localhost:8001/health",
    interval_seconds=300,
    method="GET",
    name="5min-health-check"
)
print(result["job"]["id"])  # "a1b2c3d4"
```

### Tool schema for agents

A ready-to-use tool definition is provided in [`tool.json`](tool.json).

## Notes

- **No external dependencies:** Uses only Python standard library.
- **Jobs persist** to `jobs.json` and reload on restart.
- **Background thread** checks for due jobs every second.
- **Callbacks timeout** after 30 seconds.
- **Python 3.7+** required.
