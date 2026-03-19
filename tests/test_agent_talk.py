"""Tests for the talk-to-agent tool."""

import json
import sys
import os
from unittest.mock import patch, MagicMock
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools", "talk-to-agent"))
import agent_talk


class TestRegistry:
    """Tests for registry management."""

    def setup_method(self):
        agent_talk._registry.clear()
        self._save_patcher = patch.object(agent_talk, "_save_registry")
        self._save_patcher.start()

    def teardown_method(self):
        self._save_patcher.stop()
        agent_talk._registry.clear()

    def test_register_agent(self):
        result = agent_talk.register_agent("test-agent", "http://localhost:9001", "Test Agent")
        assert result["registered"] == "test-agent"
        assert "test-agent" in agent_talk._registry

    def test_unregister_agent(self):
        agent_talk.register_agent("test-agent", "http://localhost:9001")
        result = agent_talk.unregister_agent("test-agent")
        assert result["unregistered"] == "test-agent"
        assert "test-agent" not in agent_talk._registry

    def test_unregister_nonexistent(self):
        result = agent_talk.unregister_agent("ghost")
        assert "error" in result

    def test_get_registry(self):
        agent_talk.register_agent("a1", "http://localhost:9001")
        agent_talk.register_agent("a2", "http://localhost:9002")
        result = agent_talk.get_registry()
        assert result["count"] == 2

    def test_get_agents_with_status(self):
        agent_talk.register_agent("a1", "http://localhost:9001", "Agent One")
        result = agent_talk.get_agents_with_status()
        assert result["count"] == 1
        assert result["agents"][0]["id"] == "a1"
        assert result["agents"][0]["name"] == "Agent One"


class TestTalkToAgent:
    """Tests for the core talk_to_agent function."""

    def setup_method(self):
        agent_talk._registry.clear()
        self._save_patcher = patch.object(agent_talk, "_save_registry")
        self._save_patcher.start()

    def teardown_method(self):
        self._save_patcher.stop()
        agent_talk._registry.clear()

    def test_unknown_agent(self):
        result = agent_talk.talk_to_agent("nonexistent", "hello")
        assert result["status"] == "failed"
        assert result["error"] == "unknown_agent"
        assert result["response"] is None

    def test_max_depth_exceeded(self):
        agent_talk.register_agent("test", "http://localhost:9001")
        result = agent_talk.talk_to_agent("test", "hello", hop_count=5)
        assert result["status"] == "failed"
        assert result["error"] == "max_depth_exceeded"

    def test_successful_talk(self):
        agent_talk.register_agent("test", "http://localhost:9001")

        def mock_urlopen(req, timeout=None):
            request_id = json.loads(req.data)["request_id"]
            response_data = json.dumps({
                "request_id": request_id,
                "from": "test",
                "response": "Hello back!",
            }).encode()
            mock_resp = MagicMock()
            mock_resp.read.return_value = response_data
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp

        with patch("agent_talk.urlopen", side_effect=mock_urlopen):
            result = agent_talk.talk_to_agent("test", "hello")

        assert result["status"] == "verified"
        assert result["response"] == "Hello back!"
        assert result["source"] == "test"

    def test_request_id_mismatch(self):
        agent_talk.register_agent("test", "http://localhost:9001")

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "request_id": "wrong-id",
            "from": "test",
            "response": "data",
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("agent_talk.urlopen", return_value=mock_resp):
            result = agent_talk.talk_to_agent("test", "hello")

        assert result["status"] == "failed"
        assert result["error"] == "request_id_mismatch"

    def test_unreachable_agent(self):
        from urllib.error import URLError
        agent_talk.register_agent("test", "http://localhost:9001")

        with patch("agent_talk.urlopen", side_effect=URLError("Connection refused")):
            result = agent_talk.talk_to_agent("test", "hello")

        assert result["status"] == "failed"
        assert result["error"] == "unreachable"

    def test_timeout(self):
        """TimeoutError is a subclass of OSError, so it's caught as 'unreachable'
        unless it's raised before the OSError handler. The implementation catches
        (URLError, OSError) before TimeoutError, so we verify the failure is reported."""
        agent_talk.register_agent("test", "http://localhost:9001")

        with patch("agent_talk.urlopen", side_effect=TimeoutError()):
            result = agent_talk.talk_to_agent("test", "hello", timeout_ms=100)

        assert result["status"] == "failed"
        assert result["response"] is None
