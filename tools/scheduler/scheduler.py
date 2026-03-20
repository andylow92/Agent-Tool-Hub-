"""
Scheduler Tool — Cron-like task scheduler for AI agents.

Agents can schedule HTTP callbacks at specific times or intervals.
Jobs persist to a JSON file and survive restarts. No external dependencies.
"""

import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

DEFAULT_PORT = 8010
JOBS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs.json")

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def _save_jobs():
    """Persist jobs to disk."""
    with open(JOBS_FILE, "w") as f:
        json.dump(_jobs, f, indent=2, default=str)


def _load_jobs():
    """Load jobs from disk."""
    global _jobs
    if os.path.exists(JOBS_FILE):
        try:
            with open(JOBS_FILE) as f:
                _jobs = json.load(f)
        except (json.JSONDecodeError, OSError):
            _jobs = {}


def schedule_job(
    callback_url: str,
    run_at: str = "",
    interval_seconds: int = 0,
    method: str = "POST",
    payload: dict | None = None,
    name: str = "",
    max_runs: int = 0,
) -> dict:
    """Schedule a new job.

    Args:
        callback_url: URL to call when the job fires.
        run_at: ISO 8601 datetime for one-shot jobs (e.g. "2025-06-01T12:00:00Z").
        interval_seconds: Repeat interval in seconds (0 = one-shot).
        method: HTTP method for the callback (GET or POST).
        payload: JSON body to send with POST callbacks.
        name: Human-readable job name.
        max_runs: Max number of executions (0 = unlimited for intervals, 1 for one-shot).

    Returns:
        dict with job details or error.
    """
    if not callback_url:
        return {"error": "callback_url is required."}
    if method not in ("GET", "POST"):
        return {"error": f"Invalid method: {method}. Use GET or POST."}
    if not run_at and interval_seconds <= 0:
        return {"error": "Provide run_at (ISO datetime) or interval_seconds > 0."}

    job_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc)

    if run_at:
        try:
            next_run = datetime.fromisoformat(run_at.replace("Z", "+00:00"))
        except ValueError:
            return {"error": f"Invalid run_at format: {run_at}. Use ISO 8601."}
        if next_run <= now:
            return {"error": "run_at must be in the future."}
    else:
        next_run = now

    if max_runs == 0 and interval_seconds <= 0:
        max_runs = 1

    job = {
        "id": job_id,
        "name": name or f"job-{job_id}",
        "callback_url": callback_url,
        "method": method,
        "payload": payload,
        "interval_seconds": interval_seconds,
        "next_run": next_run.isoformat(),
        "max_runs": max_runs,
        "run_count": 0,
        "last_result": None,
        "status": "active",
        "created_at": now.isoformat(),
    }

    with _lock:
        _jobs[job_id] = job
        _save_jobs()

    return {"status": "scheduled", "job": job}


def cancel_job(job_id: str) -> dict:
    """Cancel a scheduled job."""
    with _lock:
        if job_id not in _jobs:
            return {"error": f"Job not found: {job_id}"}
        _jobs[job_id]["status"] = "cancelled"
        _save_jobs()
    return {"status": "cancelled", "job_id": job_id}


def list_jobs() -> dict:
    """List all jobs."""
    with _lock:
        return {"jobs": dict(_jobs), "count": len(_jobs)}


def get_job(job_id: str) -> dict:
    """Get details of a specific job."""
    with _lock:
        if job_id not in _jobs:
            return {"error": f"Job not found: {job_id}"}
        return {"job": _jobs[job_id]}


def _execute_callback(job: dict) -> str:
    """Fire the HTTP callback for a job."""
    try:
        data = None
        if job["method"] == "POST" and job.get("payload"):
            data = json.dumps(job["payload"]).encode()

        req = urllib.request.Request(
            job["callback_url"],
            data=data,
            method=job["method"],
            headers={"Content-Type": "application/json"} if data else {},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return f"OK {resp.status}"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}"
    except (urllib.error.URLError, TimeoutError) as e:
        return f"Error: {e}"


def _scheduler_loop():
    """Background thread that checks and fires due jobs."""
    while True:
        now = datetime.now(timezone.utc)
        with _lock:
            for job_id, job in list(_jobs.items()):
                if job["status"] != "active":
                    continue

                next_run = datetime.fromisoformat(job["next_run"])
                if next_run > now:
                    continue

                result = _execute_callback(job)
                job["run_count"] += 1
                job["last_result"] = result
                job["last_run"] = now.isoformat()

                if job["interval_seconds"] > 0:
                    from datetime import timedelta

                    job["next_run"] = (now + timedelta(seconds=job["interval_seconds"])).isoformat()
                else:
                    job["status"] = "completed"

                if job["max_runs"] > 0 and job["run_count"] >= job["max_runs"]:
                    job["status"] = "completed"

                _save_jobs()

        time.sleep(1)


class SchedulerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/health":
            active = sum(1 for j in _jobs.values() if j["status"] == "active")
            self._respond(200, {"status": "ok", "tool": "scheduler", "active_jobs": active})
            return

        if parsed.path == "/jobs":
            self._respond(200, list_jobs())
            return

        if parsed.path.startswith("/jobs/"):
            job_id = parsed.path.split("/jobs/", 1)[1]
            result = get_job(job_id)
            status = 200 if "job" in result else 404
            self._respond(status, result)
            return

        self._respond(404, {"error": f"Not found: {parsed.path}"})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path != "/jobs":
            self._respond(404, {"error": f"Not found: {parsed.path}"})
            return

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self._respond(400, {"error": "Empty request body"})
            return

        try:
            body = json.loads(self.rfile.read(content_length))
        except json.JSONDecodeError:
            self._respond(400, {"error": "Request body must be valid JSON"})
            return

        result = schedule_job(
            callback_url=body.get("callback_url", ""),
            run_at=body.get("run_at", ""),
            interval_seconds=int(body.get("interval_seconds", 0)),
            method=body.get("method", "POST"),
            payload=body.get("payload"),
            name=body.get("name", ""),
            max_runs=int(body.get("max_runs", 0)),
        )
        status = 201 if "job" in result else 400
        self._respond(status, result)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)

        if not parsed.path.startswith("/jobs/"):
            self._respond(404, {"error": f"Not found: {parsed.path}"})
            return

        job_id = parsed.path.split("/jobs/", 1)[1]
        result = cancel_job(job_id)
        status = 200 if result.get("status") == "cancelled" else 404
        self._respond(status, result)

    def _respond(self, status: int, body: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body, indent=2, default=str).encode())

    def log_message(self, fmt, *args):
        print(f"[scheduler] {args[0]}")


def main():
    _load_jobs()

    port = int(os.environ.get("PORT", DEFAULT_PORT))

    HTTPServer.allow_reuse_address = True
    max_retries = 5
    for attempt in range(max_retries):
        try:
            server = HTTPServer(("0.0.0.0", port), SchedulerHandler)
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

    # Start background scheduler thread
    thread = threading.Thread(target=_scheduler_loop, daemon=True)
    thread.start()

    active = sum(1 for j in _jobs.values() if j["status"] == "active")
    print(f"Scheduler running on http://localhost:{port}")
    print("  POST   /jobs      — schedule a new job")
    print("  GET    /jobs      — list all jobs")
    print("  GET    /jobs/{id} — get job details")
    print("  DELETE /jobs/{id} — cancel a job")
    print("  GET    /health    — health check")
    print(f"\nLoaded {len(_jobs)} job(s) ({active} active) from {JOBS_FILE}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
