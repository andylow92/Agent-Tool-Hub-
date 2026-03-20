"""
Email Sender Tool — Send emails via SMTP for AI agents.

Supports any SMTP provider (Gmail, SendGrid, AWS SES, etc.).
No external dependencies — uses Python's built-in smtplib and email modules.
"""

import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from http.server import BaseHTTPRequestHandler, HTTPServer

DEFAULT_PORT = 8008
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "")


def send_email(
    to: str,
    subject: str,
    body: str,
    body_type: str = "plain",
    cc: str = "",
    bcc: str = "",
) -> dict:
    """Send an email via SMTP.

    Args:
        to: Recipient email address (comma-separated for multiple).
        subject: Email subject line.
        body: Email body content.
        body_type: "plain" for text or "html" for HTML content.
        cc: CC recipients (comma-separated).
        bcc: BCC recipients (comma-separated).

    Returns:
        dict with send status or error.
    """
    if not SMTP_HOST:
        return {"error": "SMTP_HOST is not configured. Set the SMTP_HOST env var."}
    if not SMTP_USER:
        return {"error": "SMTP_USER is not configured. Set the SMTP_USER env var."}
    if not SMTP_PASS:
        return {"error": "SMTP_PASS is not configured. Set the SMTP_PASS env var."}
    if not to:
        return {"error": "Recipient (to) is required."}
    if not subject:
        return {"error": "Subject is required."}
    if not body:
        return {"error": "Body is required."}
    if body_type not in ("plain", "html"):
        return {"error": f"Invalid body_type: {body_type}. Use 'plain' or 'html'."}

    sender = FROM_EMAIL or SMTP_USER

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    msg.attach(MIMEText(body, body_type))

    all_recipients = [addr.strip() for addr in to.split(",")]
    if cc:
        all_recipients += [addr.strip() for addr in cc.split(",")]
    if bcc:
        all_recipients += [addr.strip() for addr in bcc.split(",")]

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            if SMTP_PORT != 25:
                server.starttls()
                server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(sender, all_recipients, msg.as_string())
    except smtplib.SMTPAuthenticationError:
        return {"error": "SMTP authentication failed. Check SMTP_USER and SMTP_PASS."}
    except smtplib.SMTPRecipientsRefused:
        return {"error": f"Recipient refused: {to}"}
    except smtplib.SMTPException as e:
        return {"error": f"SMTP error: {e}"}
    except (TimeoutError, OSError) as e:
        return {"error": f"Connection failed: {e}"}

    return {
        "status": "sent",
        "from": sender,
        "to": to,
        "subject": subject,
        "cc": cc or None,
        "bcc": bcc or None,
        "body_type": body_type,
    }


class EmailHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = __import__("urllib.parse", fromlist=["parse"]).urlparse(self.path)

        if parsed.path == "/health":
            configured = all([SMTP_HOST, SMTP_USER, SMTP_PASS])
            self._respond(
                200,
                {
                    "status": "ok",
                    "tool": "email-sender",
                    "smtp_configured": configured,
                },
            )
            return

        self._respond(404, {"error": f"Not found: {parsed.path}"})

    def do_POST(self):
        parsed = __import__("urllib.parse", fromlist=["parse"]).urlparse(self.path)

        if parsed.path != "/send":
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

        result = send_email(
            to=body.get("to", ""),
            subject=body.get("subject", ""),
            body=body.get("body", ""),
            body_type=body.get("body_type", "plain"),
            cc=body.get("cc", ""),
            bcc=body.get("bcc", ""),
        )
        status = 200 if result.get("status") == "sent" else 400
        self._respond(status, result)

    def _respond(self, status: int, body: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body, indent=2, default=str).encode())

    def log_message(self, fmt, *args):
        print(f"[email-sender] {args[0]}")


def main():
    port = int(os.environ.get("PORT", DEFAULT_PORT))

    if not SMTP_HOST:
        print("WARNING: SMTP_HOST is not set. Emails will fail.")
        print("Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS env vars.")

    HTTPServer.allow_reuse_address = True
    max_retries = 5
    for attempt in range(max_retries):
        try:
            server = HTTPServer(("0.0.0.0", port), EmailHandler)
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
    print(f"Email Sender running on http://localhost:{port}")
    print("  POST /send   — send an email")
    print("  GET  /health — health check")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
