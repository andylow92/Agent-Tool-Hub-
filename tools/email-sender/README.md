# Email Sender

## What It Does

A lightweight HTTP server that sends emails via SMTP. Supports plain text and HTML bodies, CC, and BCC. Works with any SMTP provider — Gmail, SendGrid, AWS SES, Outlook, etc.

## Why It Exists

Agents often need to send notifications, reports, or alerts via email. This tool provides a simple HTTP interface so any agent can send emails without embedding SMTP logic or credentials in its own code.

## Inputs

| Parameter   | Type     | Required | Default  | Description                                       |
|-------------|----------|----------|----------|---------------------------------------------------|
| `to`        | `string` | Yes      | —        | Recipient email (comma-separated for multiple)    |
| `subject`   | `string` | Yes      | —        | Email subject line                                |
| `body`      | `string` | Yes      | —        | Email body content                                |
| `body_type` | `string` | No       | `plain`  | `plain` for text or `html` for HTML content       |
| `cc`        | `string` | No       | —        | CC recipients (comma-separated)                   |
| `bcc`       | `string` | No       | —        | BCC recipients (comma-separated)                  |

## Outputs

Returns a JSON object:

```json
{
  "status": "sent",
  "from": "you@gmail.com",
  "to": "recipient@example.com",
  "subject": "Hello from Agent",
  "cc": null,
  "bcc": null,
  "body_type": "plain"
}
```

On error:

```json
{
  "error": "SMTP authentication failed. Check SMTP_USER and SMTP_PASS."
}
```

## Setup

### 1. Configure SMTP credentials

```bash
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=you@gmail.com
export SMTP_PASS=your-app-password
export FROM_EMAIL=you@gmail.com  # optional, defaults to SMTP_USER
```

For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833) (not your regular password).

### 2. Run the server

```bash
python email_sender.py
```

The server starts on `http://localhost:8008` by default. Override with `PORT` env var.

### 3. Or use Docker

```bash
docker build -t email-sender .
docker run -p 8008:8008 \
  -e SMTP_HOST=smtp.gmail.com \
  -e SMTP_PORT=587 \
  -e SMTP_USER=you@gmail.com \
  -e SMTP_PASS=your-app-password \
  email-sender
```

## Example

```bash
# Send a plain text email
curl -X POST http://localhost:8008/send \
  -H "Content-Type: application/json" \
  -d '{
    "to": "recipient@example.com",
    "subject": "Weekly Report",
    "body": "Here is your weekly report summary..."
  }'

# Send an HTML email with CC
curl -X POST http://localhost:8008/send \
  -H "Content-Type: application/json" \
  -d '{
    "to": "recipient@example.com",
    "cc": "manager@example.com",
    "subject": "Status Update",
    "body": "<h1>Status</h1><p>All systems operational.</p>",
    "body_type": "html"
  }'
```

### Using as a Python function (no server needed)

```python
from email_sender import send_email

result = send_email(
    to="recipient@example.com",
    subject="Hello",
    body="Sent from an AI agent!"
)
print(result["status"])  # "sent"
```

### Tool schema for agents

A ready-to-use tool definition is provided in [`tool.json`](tool.json).

## Notes

- **No external dependencies:** Uses only Python standard library (`smtplib`, `email`).
- **STARTTLS** is used by default on non-port-25 connections.
- **Never log credentials** — SMTP password is only used at send time.
- **Python 3.7+** required.
