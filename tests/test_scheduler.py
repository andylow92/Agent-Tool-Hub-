"""Tests for the scheduler tool."""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from io import BytesIO
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools", "scheduler"))
import scheduler


def _clear_jobs():
    """Reset job state between tests."""
    scheduler._jobs.clear()


class TestScheduleJob:
    """Tests for the schedule_job function."""

    def setup_method(self):
        _clear_jobs()

    def test_missing_callback_url(self):
        result = scheduler.schedule_job("")
        assert "error" in result
        assert "callback_url" in result["error"]

    def test_invalid_method(self):
        result = scheduler.schedule_job(
            "http://localhost:8001/health",
            interval_seconds=60,
            method="DELETE",
        )
        assert "error" in result
        assert "Invalid method" in result["error"]

    def test_missing_time_spec(self):
        result = scheduler.schedule_job("http://localhost:8001/health")
        assert "error" in result
        assert "run_at" in result["error"]

    def test_invalid_run_at(self):
        result = scheduler.schedule_job("http://localhost:8001/health", run_at="not-a-date")
        assert "error" in result
        assert "Invalid run_at" in result["error"]

    def test_past_run_at(self):
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        result = scheduler.schedule_job("http://localhost:8001/health", run_at=past)
        assert "error" in result
        assert "future" in result["error"]

    def test_successful_interval_job(self):
        result = scheduler.schedule_job(
            "http://localhost:8001/health",
            interval_seconds=60,
            method="GET",
            name="test-job",
        )
        assert result["status"] == "scheduled"
        assert result["job"]["name"] == "test-job"
        assert result["job"]["interval_seconds"] == 60
        assert result["job"]["status"] == "active"

    def test_successful_one_shot_job(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        result = scheduler.schedule_job(
            "http://localhost:8001/health",
            run_at=future,
            method="GET",
        )
        assert result["status"] == "scheduled"
        assert result["job"]["max_runs"] == 1


class TestCancelJob:
    """Tests for the cancel_job function."""

    def setup_method(self):
        _clear_jobs()

    def test_cancel_nonexistent(self):
        result = scheduler.cancel_job("fake-id")
        assert "error" in result

    def test_cancel_existing(self):
        created = scheduler.schedule_job("http://localhost:8001/health", interval_seconds=60)
        job_id = created["job"]["id"]
        result = scheduler.cancel_job(job_id)
        assert result["status"] == "cancelled"


class TestListJobs:
    """Tests for the list_jobs function."""

    def setup_method(self):
        _clear_jobs()

    def test_empty_list(self):
        result = scheduler.list_jobs()
        assert result["count"] == 0

    def test_list_after_schedule(self):
        scheduler.schedule_job("http://localhost:8001/health", interval_seconds=60)
        result = scheduler.list_jobs()
        assert result["count"] == 1


class TestGetJob:
    """Tests for the get_job function."""

    def setup_method(self):
        _clear_jobs()

    def test_get_nonexistent(self):
        result = scheduler.get_job("fake-id")
        assert "error" in result

    def test_get_existing(self):
        created = scheduler.schedule_job("http://localhost:8001/health", interval_seconds=60)
        job_id = created["job"]["id"]
        result = scheduler.get_job(job_id)
        assert result["job"]["id"] == job_id


class TestSchedulerHandler:
    """Tests for the HTTP handler."""

    def _make_handler(self, path):
        handler = scheduler.SchedulerHandler.__new__(scheduler.SchedulerHandler)
        handler.path = path
        handler.headers = {}
        handler.wfile = BytesIO()
        handler.requestline = "GET / HTTP/1.1"
        handler.client_address = ("127.0.0.1", 0)
        handler.request_version = "HTTP/1.1"
        handler.responses = {}
        return handler

    def test_health_endpoint(self):
        handler = self._make_handler("/health")
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.do_GET()
        handler.send_response.assert_called_with(200)
        body = json.loads(handler.wfile.getvalue())
        assert body["status"] == "ok"
        assert body["tool"] == "scheduler"

    def test_list_jobs_endpoint(self):
        _clear_jobs()
        handler = self._make_handler("/jobs")
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.do_GET()
        handler.send_response.assert_called_with(200)
        body = json.loads(handler.wfile.getvalue())
        assert "jobs" in body

    def test_not_found(self):
        handler = self._make_handler("/unknown")
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.do_GET()
        handler.send_response.assert_called_with(404)
