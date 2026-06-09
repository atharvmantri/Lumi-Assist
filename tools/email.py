"""Email compose and send via SMTP."""
from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from core.config import PROJECT_ROOT
from tools import tool


def _get_smtp_config() -> dict | None:
    """Read SMTP config from data/email_config.json if it exists."""
    config_path = PROJECT_ROOT / "data" / "email_config.json"
    if config_path.exists():
        import json
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    return None


@tool(
    name="send_email",
    description="Send an email via SMTP. Requires SMTP configuration to be set first via configure_email.",
    parameters={
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Recipient email address",
            },
            "subject": {
                "type": "string",
                "description": "Email subject line",
            },
            "body": {
                "type": "string",
                "description": "Email body text",
            },
        },
        "required": ["to", "subject", "body"],
    },
)
def send_email(to: str, subject: str, body: str) -> str:
    config = _get_smtp_config()
    if not config:
        return "error: email not configured. Use configure_email first with your SMTP details."

    try:
        msg = MIMEMultipart()
        msg["From"] = config["email"]
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(config["server"], int(config.get("port", 587))) as server:
            server.starttls()
            server.login(config["email"], config["password"])
            server.send_message(msg)

        return f"Email sent to {to}: {subject}"
    except Exception as e:
        return f"error sending email: {e}"


@tool(
    name="configure_email",
    description="Configure SMTP email settings. Requires server, port, email, and password/app-password.",
    parameters={
        "type": "object",
        "properties": {
            "server": {
                "type": "string",
                "description": "SMTP server (e.g. 'smtp.gmail.com')",
            },
            "port": {
                "type": "integer",
                "description": "SMTP port (default 587)",
            },
            "email": {
                "type": "string",
                "description": "Your email address",
            },
            "password": {
                "type": "string",
                "description": "SMTP password or app password",
            },
        },
        "required": ["server", "email", "password"],
    },
)
def configure_email(server: str, email: str, password: str, port: int = 587) -> str:
    import json
    config_path = PROJECT_ROOT / "data" / "email_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config = {
        "server": server,
        "port": port,
        "email": email,
        "password": password,
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f)

    # Mask password in response
    masked = email.split("@")[0] + "***@***"
    return f"Email configured for {masked} via {server}:{port}"
