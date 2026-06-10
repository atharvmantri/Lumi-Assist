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
    description="Send an email via SMTP (supports HTML and file attachments). Requires SMTP configuration first.",
    parameters={
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email address"},
            "subject": {"type": "string", "description": "Email subject line"},
            "body": {"type": "string", "description": "Email plain text body"},
            "html_body": {"type": "string", "description": "Email HTML formatting body (optional)"},
            "attachments": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of local file paths to attach (optional)",
            },
        },
        "required": ["to", "subject", "body"],
    },
)
def send_email(
    to: str,
    subject: str,
    body: str,
    html_body: str | None = None,
    attachments: list[str] | None = None,
) -> str:
    config = _get_smtp_config()
    if not config:
        return "error: email not configured. Use configure_email first with your SMTP details."

    try:
        import mimetypes
        from email.mime.base import MIMEBase
        from email import encoders

        msg = MIMEMultipart()
        msg["From"] = config["email"]
        msg["To"] = to
        msg["Subject"] = subject

        # Attach text and/or HTML bodies
        msg.attach(MIMEText(body, "plain"))
        if html_body:
            msg.attach(MIMEText(html_body, "html"))

        # Process attachments
        if attachments:
            for filepath in attachments:
                p = Path(filepath)
                if not p.is_file():
                    continue
                # Guess mimetype
                ctype, encoding = mimetypes.guess_type(filepath)
                if ctype is None or encoding is not None:
                    ctype = "application/octet-stream"
                maintype, subtype = ctype.split("/", 1)

                with open(p, "rb") as fp:
                    attachment_part = MIMEBase(maintype, subtype)
                    attachment_part.set_payload(fp.read())
                encoders.encode_base64(attachment_part)
                attachment_part.add_header("Content-Disposition", "attachment", filename=p.name)
                msg.attach(attachment_part)

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


@tool(
    name="read_email",
    description="Fetch and parse emails from an IMAP inbox folder.",
    parameters={
        "type": "object",
        "properties": {
            "folder": {"type": "string", "description": "Inbox folder name (default 'INBOX')", "default": "INBOX"},
            "limit": {"type": "integer", "description": "Maximum number of recent emails to retrieve (default 10)", "default": 10},
            "search_query": {"type": "string", "description": "Optional search criteria, e.g. 'UNSEEN' (default 'ALL')", "default": "ALL"},
        },
    },
)
def read_email(
    folder: str = "INBOX",
    limit: int = 10,
    search_query: str = "ALL",
) -> str:
    config = _get_smtp_config()
    
    # Try actual IMAP fetch if config has server details, otherwise return simulation
    # We construct default IMAP server address from SMTP config
    imap_server = None
    if config:
        imap_server = config.get("imap_server") or "imap." + config["server"].replace("smtp.", "")
        
    # We do a basic check if IMAP module can connect
    if not config or not imap_server:
        # Fallback simulation
        sim_emails = [
            f"[Simulated IMAP Inbox - Folder: {folder} | Query: {search_query}]",
            "-" * 60,
            "1. From: support@github.com | Subject: [GitHub] Security Alert - New SSH Key Added",
            "   Date: 2026-06-10 12:45 | Body: A new SSH public key was added to your account...",
            "-" * 60,
            "2. From: team@lumi.ai | Subject: Meeting rescheduled: Sync-up",
            "   Date: 2026-06-10 10:15 | Body: Hi, we have moved the weekly project sync to 3 PM today...",
            "-" * 60,
            "3. From: newsletters@hackclub.com | Subject: Hack Club Newsletter June 2026",
            "   Date: 2026-06-09 18:30 | Body: Welcome to the summer edition of Hack Club news!...",
            "-" * 60,
        ]
        return "\n".join(sim_emails[:limit * 3])

    try:
        import imaplib
        import email
        from email.header import decode_header
        
        # Connect to IMAP
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(config["email"], config["password"])
        mail.select(folder)
        
        status, response = mail.search(None, search_query)
        if status != "OK":
            return f"error: failed to query mailbox with query: {search_query}"
            
        mail_ids = response[0].split()
        if not mail_ids:
            return f"Inbox folder '{folder}' is empty or has no matches."
            
        lines = [f"Inbox Emails ({folder} - showing last {min(len(mail_ids), limit)}):"]
        # Fetch from latest to oldest
        for m_id in reversed(mail_ids[-limit:]):
            status, data = mail.fetch(m_id, "(RFC822)")
            if status != "OK":
                continue
            
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Parse Subject
            subject, encoding = decode_header(msg["Subject"] or "")[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or "utf-8", errors="ignore")
                
            # Parse From
            sender, encoding = decode_header(msg["From"] or "")[0]
            if isinstance(sender, bytes):
                sender = sender.decode(encoding or "utf-8", errors="ignore")
                
            # Extract plain text body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disp = str(part.get("Content-Disposition"))
                    if content_type == "text/plain" and "attachment" not in content_disp:
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                
            body_summary = body.strip().replace("\n", " ")[:100] + ("..." if len(body) > 100 else "")
            lines.append("-" * 60)
            lines.append(f"From: {sender} | Subject: {subject}")
            lines.append(f"Content: {body_summary}")
            
        mail.logout()
        return "\n".join(lines)
    except Exception as e:
        return f"error reading IMAP inbox: {e}"


@tool(
    name="draft_email",
    description="Draft a professional email using AI context and save it to drafts vault.",
    parameters={
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email address (optional)"},
            "subject": {"type": "string", "description": "Email subject line (optional)"},
            "recipient_context": {"type": "string", "description": "Detailed background context on what to write about"},
            "tone": {"type": "string", "description": "Tone formatting style: 'formal', 'casual'", "enum": ["formal", "casual"], "default": "formal"},
        },
        "required": ["recipient_context"],
    },
)
def draft_email(
    recipient_context: str,
    to: str | None = None,
    subject: str | None = None,
    tone: str = "formal",
) -> str:
    from datetime import datetime
    import json
    
    drafts_path = PROJECT_ROOT / "data" / "drafts.json"
    drafts_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing drafts
    drafts = []
    if drafts_path.is_file():
        try:
            with open(drafts_path, "r", encoding="utf-8") as f:
                drafts = json.load(f)
        except Exception:
            pass

    # Build prompt
    system_prompt = (
        "You are an expert email copywriter. Draft a concise and clear email. "
        "Do NOT include placeholders (like [Name]), generate realistic fillers instead."
    )
    user_prompt = (
        f"Recipient Context: {recipient_context}\n"
        f"Subject Idea: {subject or 'Follow up'}\n"
        f"Desired Tone: {tone}\n"
        f"Compose the body of the email now."
    )
    
    # Query LLMClient or fallback if not configured
    try:
        from core.llm import LLMClient
        client = LLMClient()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        resp = client.client.chat.completions.create(
            model=client.model,
            messages=messages,
            temperature=0.7,
            max_tokens=600
        )
        body = resp.choices[0].message.content.strip()
    except Exception:
        # Fallback local draft generation
        greeting = "Dear Colleague," if tone == "formal" else "Hey there!"
        signoff = "Best regards,\nLumi Voice Assistant" if tone == "formal" else "Talk soon,\nLumi"
        body = (
            f"{greeting}\n\n"
            f"Regarding the topic of: {recipient_context}.\n"
            "I wanted to reach out and make sure we coordinate our schedules and align on next steps. "
            "Let me know what times work best for you this week.\n\n"
            f"{signoff}"
        )

    draft_entry = {
        "id": len(drafts) + 1,
        "to": to or "draft_recipient@example.com",
        "subject": subject or "Draft Follow Up",
        "body": body,
        "created_at": datetime.now().isoformat()
    }
    drafts.append(draft_entry)
    
    with open(drafts_path, "w", encoding="utf-8") as f:
        json.dump(drafts, f, indent=2)
        
    res = [
        f"Successfully created email draft #{draft_entry['id']}:",
        f"To: {draft_entry['to']}",
        f"Subject: {draft_entry['subject']}",
        "-" * 60,
        body,
        "-" * 60,
        f"Saved to: data/drafts.json"
    ]
    return "\n".join(res)
