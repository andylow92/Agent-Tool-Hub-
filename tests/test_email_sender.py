"""Tests for the email-sender tool."""

import json
import os
import sys
from io import BytesIO
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools", "email-sender"))
import email_sender


class TestSendEmail:
    """Tests for the send_email function."""

    def test_missing_smtp_host(self):
        with patch.object(email_sender, "SMTP_HOST", ""):
            result = email_sender.send_email("a@b.com", "Sub", "Body")
        assert "error" in result
        assert "SMTP_HOST" in result["error"]

    def test_missing_smtp_user(self):
        with (
            patch.object(email_sender, "SMTP_HOST", "smtp.test.com"),
            patch.object(email_sender, "SMTP_USER", ""),
        ):
            result = email_sender.send_email("a@b.com", "Sub", "Body")
        assert "error" in result
        assert "SMTP_USER" in result["error"]

    def test_missing_smtp_pass(self):
        with (
            patch.object(email_sender, "SMTP_HOST", "smtp.test.com"),
            patch.object(email_sender, "SMTP_USER", "user@test.com"),
            patch.object(email_sender, "SMTP_PASS", ""),
        ):
            result = email_sender.send_email("a@b.com", "Sub", "Body")
        assert "error" in result
        assert "SMTP_PASS" in result["error"]

    def test_missing_recipient(self):
        with (
            patch.object(email_sender, "SMTP_HOST", "smtp.test.com"),
            patch.object(email_sender, "SMTP_USER", "user@test.com"),
            patch.object(email_sender, "SMTP_PASS", "pass"),
        ):
            result = email_sender.send_email("", "Sub", "Body")
        assert "error" in result
        assert "Recipient" in result["error"]

    def test_missing_subject(self):
        with (
            patch.object(email_sender, "SMTP_HOST", "smtp.test.com"),
            patch.object(email_sender, "SMTP_USER", "user@test.com"),
            patch.object(email_sender, "SMTP_PASS", "pass"),
        ):
            result = email_sender.send_email("a@b.com", "", "Body")
        assert "error" in result
        assert "Subject" in result["error"]

    def test_invalid_body_type(self):
        with (
            patch.object(email_sender, "SMTP_HOST", "smtp.test.com"),
            patch.object(email_sender, "SMTP_USER", "user@test.com"),
            patch.object(email_sender, "SMTP_PASS", "pass"),
        ):
            result = email_sender.send_email("a@b.com", "Sub", "Body", body_type="xml")
        assert "error" in result
        assert "Invalid body_type" in result["error"]

    def test_successful_send(self):
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = lambda s: s
        mock_smtp.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(email_sender, "SMTP_HOST", "smtp.test.com"),
            patch.object(email_sender, "SMTP_PORT", 587),
            patch.object(email_sender, "SMTP_USER", "user@test.com"),
            patch.object(email_sender, "SMTP_PASS", "pass"),
            patch.object(email_sender, "FROM_EMAIL", "sender@test.com"),
            patch("smtplib.SMTP", return_value=mock_smtp),
        ):
            result = email_sender.send_email("a@b.com", "Test", "Hello")

        assert result["status"] == "sent"
        assert result["from"] == "sender@test.com"
        assert result["to"] == "a@b.com"
        mock_smtp.sendmail.assert_called_once()

    def test_auth_failure(self):
        import smtplib

        mock_smtp = MagicMock()
        mock_smtp.__enter__ = lambda s: s
        mock_smtp.__exit__ = MagicMock(return_value=False)
        mock_smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Bad creds")

        with (
            patch.object(email_sender, "SMTP_HOST", "smtp.test.com"),
            patch.object(email_sender, "SMTP_USER", "user@test.com"),
            patch.object(email_sender, "SMTP_PASS", "wrong"),
            patch("smtplib.SMTP", return_value=mock_smtp),
        ):
            result = email_sender.send_email("a@b.com", "Sub", "Body")

        assert "error" in result
        assert "authentication" in result["error"].lower()

    def test_send_with_cc_and_bcc(self):
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = lambda s: s
        mock_smtp.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(email_sender, "SMTP_HOST", "smtp.test.com"),
            patch.object(email_sender, "SMTP_USER", "user@test.com"),
            patch.object(email_sender, "SMTP_PASS", "pass"),
            patch("smtplib.SMTP", return_value=mock_smtp),
        ):
            result = email_sender.send_email(
                "a@b.com", "Sub", "Body", cc="cc@b.com", bcc="bcc@b.com"
            )

        assert result["status"] == "sent"
        # Check all recipients were included in sendmail
        call_args = mock_smtp.sendmail.call_args
        recipients = call_args[0][1]
        assert "a@b.com" in recipients
        assert "cc@b.com" in recipients
        assert "bcc@b.com" in recipients


class TestEmailHandler:
    """Tests for the HTTP handler."""

    def _make_handler(self, path):
        handler = email_sender.EmailHandler.__new__(email_sender.EmailHandler)
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
        assert body["tool"] == "email-sender"

    def test_not_found(self):
        handler = self._make_handler("/unknown")
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.do_GET()
        handler.send_response.assert_called_with(404)
