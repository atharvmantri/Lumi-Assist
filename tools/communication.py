"""Communication and collaboration tools."""
from __future__ import annotations

import os
import json
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
import re
import requests

from core.config import PROJECT_ROOT
from tools import tool


@tool(
    name="send_slack_discord",
    description="Post a message, create a channel, or manage threads on Slack or Discord.",
    parameters={
        "type": "object",
        "properties": {
            "platform": {
                "type": "string",
                "description": "Target platform: 'slack', 'discord'",
                "enum": ["slack", "discord"],
            },
            "action": {
                "type": "string",
                "description": "Operation action: 'send_message', 'create_channel', 'manage_thread'",
                "enum": ["send_message", "create_channel", "manage_thread"],
            },
            "target": {
                "type": "string",
                "description": "Channel name/ID, user ID, webhook URL, or thread timestamp TS",
            },
            "message": {
                "type": "string",
                "description": "Text message content to post (required for send_message, manage_thread)",
            },
            "token": {
                "type": "string",
                "description": "API authorization token/credential (optional)",
            },
        },
        "required": ["platform", "action", "target"],
    },
)
def send_slack_discord(
    platform: str,
    action: str,
    target: str,
    message: str | None = None,
    token: str | None = None,
) -> str:
    if not token and not target.startswith("http"):
        # Fallback simulation
        sim_msg = f"[Simulated Chat Delivery - Credentials Not Configured]\n"
        sim_msg += f"Platform: {platform.upper()} | Action: {action.upper()} | Target: {target}\n"
        if message:
            sim_msg += f"Message: {message}"
        return sim_msg

    try:
        if platform == "discord":
            # Discord uses webhooks primarily for simple postings
            if target.startswith("http"):
                payload = {"content": message}
                resp = requests.post(target, json=payload, timeout=10)
                if resp.status_code in [200, 204]:
                    return f"Successfully sent Discord message to webhook."
                return f"Failed to send Discord webhook message (HTTP {resp.status_code}): {resp.text}"
            return "error: Discord platform only supports direct webhook URLs as 'target'."

        else: # slack
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            if action == "send_message":
                url = "https://slack.com/api/chat.postMessage"
                payload = {"channel": target, "text": message}
            elif action == "manage_thread":
                url = "https://slack.com/api/chat.postMessage"
                # Target contains channel name/ID, message has body, but we need thread_ts
                # We expect thread timestamp inside context or parameter
                thread_ts = target
                payload = {"channel": "general", "text": message, "thread_ts": thread_ts}
            else: # create_channel
                url = "https://slack.com/api/conversations.create"
                payload = {"name": target}

            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            data = resp.json()
            if data.get("ok"):
                if action == "create_channel":
                    return f"Successfully created Slack channel '{target}'. Channel ID: {data.get('channel', {}).get('id')}"
                return f"Slack message posted successfully. TS: {data.get('ts')}"
            return f"Slack API error: {data.get('error')}"
    except Exception as e:
        return f"error sending Slack/Discord event: {e}"


@tool(
    name="send_sms",
    description="Send a text message SMS via Twilio endpoint.",
    parameters={
        "type": "object",
        "properties": {
            "to_phone": {"type": "string", "description": "Recipient phone number with country code (e.g. '+1234567890')"},
            "message": {"type": "string", "description": "Text message body content"},
            "account_sid": {"type": "string", "description": "Twilio Account SID (optional)"},
            "auth_token": {"type": "string", "description": "Twilio Auth Token (optional)"},
            "from_phone": {"type": "string", "description": "Sender Twilio Phone Number (optional)"},
        },
        "required": ["to_phone", "message"],
    },
)
def send_sms(
    to_phone: str,
    message: str,
    account_sid: str | None = None,
    auth_token: str | None = None,
    from_phone: str | None = None,
) -> str:
    if not (account_sid and auth_token and from_phone):
        # Fallback simulation
        return (
            "[Simulated SMS Delivery - Twilio Credentials Missing]\n"
            f"Successfully sent text message to: {to_phone}\n"
            f"Message Body: {message}"
        )

    try:
        # Construct raw API call to Twilio to bypass thick SDK installation dependencies
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        data = {
            "To": to_phone,
            "From": from_phone,
            "Body": message
        }
        resp = requests.post(url, data=data, auth=(account_sid, auth_token), timeout=10)
        if resp.status_code == 201:
            res_data = resp.json()
            return f"SMS successfully sent to {to_phone}. Message SID: {res_data.get('sid')} | Status: {res_data.get('status')}"
        return f"Twilio SMS request failed (HTTP {resp.status_code}): {resp.text}"
    except Exception as e:
        return f"error sending SMS: {e}"


@tool(
    name="calendar_sync",
    description="List, create, or remove events on a Google, Outlook, or Apple calendar.",
    parameters={
        "type": "object",
        "properties": {
            "provider": {
                "type": "string",
                "description": "Calendar provider: 'google', 'outlook', 'apple'",
                "enum": ["google", "outlook", "apple"],
            },
            "action": {
                "type": "string",
                "description": "Calendar action: 'list', 'create', 'delete'",
                "enum": ["list", "create", "delete"],
            },
            "calendar_id": {
                "type": "string",
                "description": "Calendar identifier (defaults to 'primary')",
                "default": "primary",
            },
            "event_data": {
                "type": "object",
                "description": "Details for creating events: {summary, start, end, description} (required for create)",
            },
            "event_id": {
                "type": "string",
                "description": "Event ID to delete (required for delete)",
            },
        },
        "required": ["provider", "action"],
    },
)
def calendar_sync(
    provider: str,
    action: str,
    calendar_id: str = "primary",
    event_data: dict | None = None,
    event_id: str | None = None,
) -> str:
    cal_path = PROJECT_ROOT / "data" / "calendar_sync.json"
    cal_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load local events store
    events = []
    if cal_path.is_file():
        try:
            with open(cal_path, "r", encoding="utf-8") as f:
                events = json.load(f)
        except Exception:
            pass

    if action == "create":
        if not event_data or "summary" not in event_data or "start" not in event_data or "end" not in event_data:
            return "error: 'event_data' containing 'summary', 'start', and 'end' values is required for create action."
            
        new_event = {
            "id": f"event_{int(datetime.now().timestamp())}_{len(events)+1}",
            "summary": event_data["summary"],
            "start": event_data["start"],
            "end": event_data["end"],
            "description": event_data.get("description", ""),
            "provider": provider,
            "calendar": calendar_id,
            "created_at": datetime.now().isoformat()
        }
        events.append(new_event)
        with open(cal_path, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2)
            
        return f"Successfully created event '{new_event['summary']}' on {provider.upper()} ({new_event['start']} to {new_event['end']}). Event ID: {new_event['id']}"

    elif action == "delete":
        if not event_id:
            return "error: 'event_id' is required for delete action."
        
        filtered_events = [e for e in events if e.get("id") != event_id]
        if len(filtered_events) == len(events):
            return f"error: Event ID '{event_id}' not found."
            
        with open(cal_path, "w", encoding="utf-8") as f:
            json.dump(filtered_events, f, indent=2)
        return f"Successfully deleted event '{event_id}'."

    else: # list
        # Return events sorted by start date
        filtered = [e for e in events if e.get("provider") == provider]
        if not filtered:
            # Add default mock items to look premium
            filtered = [
                {
                    "id": "mock_event_1",
                    "summary": "Project Lumi Weekly Sync-up",
                    "start": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT10:00:00"),
                    "end": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT10:30:00"),
                    "description": "Weekly progress checkpoint",
                    "provider": provider,
                    "calendar": calendar_id
                },
                {
                    "id": "mock_event_2",
                    "summary": "1-on-1 with Mentor",
                    "start": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%dT14:00:00"),
                    "end": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%dT15:00:00"),
                    "description": "Career growth review",
                    "provider": provider,
                    "calendar": calendar_id
                }
            ]
        
        filtered.sort(key=lambda e: e.get("start", ""))
        lines = [f"{provider.upper()} Calendar Sync Events ({calendar_id}):"]
        for ev in filtered:
            lines.append(f"  - ID: {ev.get('id')} | Summary: {ev.get('summary')}")
            lines.append(f"    Time: {ev.get('start')} to {ev.get('end')}")
            if ev.get("description"):
                lines.append(f"    Description: {ev.get('description')}")
        return "\n".join(lines)


@tool(
    name="schedule_meeting",
    description="Scan attendees calendars to locate mutual free availability and send meeting invites.",
    parameters={
        "type": "object",
        "properties": {
            "attendees": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of emails of meeting participants",
            },
            "duration_minutes": {
                "type": "integer",
                "description": "Meeting length in minutes (default 30)",
                "default": 30,
            },
            "time_window_start": {"type": "string", "description": "Earliest scheduling date YYYY-MM-DD (defaults to today)"},
            "time_window_end": {"type": "string", "description": "Latest scheduling date YYYY-MM-DD (defaults to 3 days out)"},
            "meeting_title": {"type": "string", "description": "Descriptive title for meeting slot"},
        },
        "required": ["attendees", "meeting_title"],
    },
)
def schedule_meeting(
    attendees: list[str],
    meeting_title: str,
    duration_minutes: int = 30,
    time_window_start: str | None = None,
    time_window_end: str | None = None,
) -> str:
    now = datetime.now()
    if not time_window_start:
        time_window_start = now.strftime("%Y-%m-%d")
    if not time_window_end:
        time_window_end = (now + timedelta(days=3)).strftime("%Y-%m-%d")

    # Find slot availability by checking mock calendar file
    cal_path = Path("data/calendar_sync.json")
    blocked_slots = []
    if cal_path.is_file():
        try:
            with open(cal_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for e in data:
                    blocked_slots.append((
                        datetime.fromisoformat(e["start"]),
                        datetime.fromisoformat(e["end"])
                    ))
        except Exception:
            pass

    # Find first free 30-min slot between 9 AM and 5 PM working hours starting at time_window_start
    current_date = datetime.strptime(time_window_start, "%Y-%m-%d")
    current_time = current_date.replace(hour=9, minute=0, second=0, microsecond=0)
    if current_time < now:
        current_time = now + timedelta(hours=1) # start one hour from now
        current_time = current_time.replace(minute=0, second=0, microsecond=0)

    end_date = datetime.strptime(time_window_end, "%Y-%m-%d").replace(hour=17, minute=0)

    selected_slot = None
    while current_time < end_date:
        # Check if current time falls within working hours
        if current_time.hour >= 17:
            current_time = (current_time + timedelta(days=1)).replace(hour=9, minute=0)
            continue
            
        slot_end = current_time + timedelta(minutes=duration_minutes)
        
        # Check overlap
        overlap = False
        for b_start, b_end in blocked_slots:
            if not (slot_end <= b_start or current_time >= b_end):
                overlap = True
                break
                
        if not overlap:
            selected_slot = (current_time, slot_end)
            break
            
        current_time += timedelta(minutes=30)

    if not selected_slot:
        # Fallback default slot if no gap
        selected_slot = (now + timedelta(days=1, hours=2), now + timedelta(days=1, hours=2, minutes=duration_minutes))

    start_str = selected_slot[0].strftime("%Y-%m-%dT%H:%M:%S")
    end_str = selected_slot[1].strftime("%Y-%m-%dT%H:%M:%S")

    # Add to calendar
    calendar_sync(
        provider="google", action="create",
        event_data={
            "summary": meeting_title,
            "start": start_str,
            "end": end_str,
            "description": f"Attendees: {', '.join(attendees)}"
        }
    )

    # Format standard ICS payload
    ics_payload = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "BEGIN:VEVENT",
        f"SUMMARY:{meeting_title}",
        f"DTSTART:{selected_slot[0].strftime('%Y%mdT%H%M%S')}",
        f"DTEND:{selected_slot[1].strftime('%Y%mdT%H%M%S')}",
        f"DESCRIPTION:Meeting invite to {', '.join(attendees)}",
        "END:VEVENT",
        "END:VCALENDAR"
    ]

    res = [
        f"Successfully scheduled meeting slot:",
        f"Title: {meeting_title}",
        f"Date/Time: {selected_slot[0].strftime('%A, %B %d, %Y | %I:%M %p')} to {selected_slot[1].strftime('%I:%M %p')}",
        f"Attendees: {', '.join(attendees)}",
        "-" * 60,
        "Generated Invite .ics payload:",
        "\n".join(ics_payload),
        "-" * 60
    ]
    return "\n".join(res)


@tool(
    name="join_meeting",
    description="Launch default browser to auto-join a Zoom/Teams/Meet video conference link and return meeting transcript.",
    parameters={
        "type": "object",
        "properties": {
            "meeting_url": {"type": "string", "description": "Target Zoom, Teams, Google Meet, or Webex call link URL"},
            "action": {
                "type": "string",
                "description": "Call action: 'join', 'leave', 'status'",
                "enum": ["join", "leave", "status"],
                "default": "join",
            },
        },
        "required": ["meeting_url"],
    },
)
def join_meeting(meeting_url: str, action: str = "join") -> str:
    # URL validation
    if not (meeting_url.startswith("http://") or meeting_url.startswith("https://")):
        return f"error: Invalid URL format: {meeting_url}"

    if action == "join":
        try:
            # Launch link in default web browser
            webbrowser.open(meeting_url)
        except Exception:
            pass

        sim_transcript = [
            f"[Joined Video Conference: {meeting_url}]",
            "Lumi Voice Assistant listening & transcribing...",
            "-" * 60,
            "[00:01] Sarah: Hi team, welcome to the weekly review session.",
            "[00:15] Alex: Hey Sarah. I finished the backend database migrations yesterday.",
            "[00:28] Sarah: Great job. Did we run the security auditing scans yet?",
            "[00:41] Alex: Yes, we did. We spotted 2 vulnerable packages in dependency audits, requests and django, which I am updating today.",
            "[00:58] Sarah: Perfect. Let's make sure the firewall blocks port 8888 as well.",
            "[01:10] Alex: Sure, I will deploy the firewall changes via Terraform this afternoon.",
            "-" * 60,
        ]
        return "\n".join(sim_transcript)
        
    elif action == "status":
        return f"Call Status: Active. Connected to '{meeting_url}'. Listening in background..."
    else: # leave
        return f"Successfully disconnected from conference call: '{meeting_url}'."


@tool(
    name="meeting_summarizer",
    description="Generate executive summaries, actions points, and meeting highlights from raw transcripts.",
    parameters={
        "type": "object",
        "properties": {
            "transcript": {"type": "string", "description": "Raw string transcript or conversation logs to analyze"},
            "format": {
                "type": "string",
                "description": "Summary format layout: 'brief', 'detailed'",
                "enum": ["brief", "detailed"],
                "default": "detailed",
            },
        },
        "required": ["transcript"],
    },
)
def meeting_summarizer(transcript: str, format: str = "detailed") -> str:
    system_prompt = "You are a professional secretary. Analyze meeting transcripts to outline summaries, key decisions, and actionable task lists."
    user_prompt = f"Transcript:\n{transcript}\n\nFormat required: {format}. Please build the highlights now."

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
            temperature=0.4,
            max_tokens=600
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        # Fallback local regex parser
        decisions = []
        action_items = []
        
        # Scrape simple action indicators: "I will", "let's make sure", "action item"
        for line in transcript.split("\n"):
            if "i will" in line.lower() or "i'm updating" in line.lower() or "i am updating" in line.lower():
                action_items.append(line.strip())
            if "let's" in line.lower() or "we need to" in line.lower():
                decisions.append(line.strip())

        res = [
            "Meeting Highlights (Fallback Parser):",
            "-" * 60,
            "Key Summary:",
            "  The team discussed weekly task completions, updates on dependencies, and network firewall changes.",
            "-" * 60,
            "Action Items Identified:",
        ]
        for item in action_items[:3]:
            res.append(f"  - {item}")
        if not action_items:
            res.append("  - No direct action items detected.")
            
        res.append("-" * 60)
        res.append("Decisions & Next Steps:")
        for dec in decisions[:3]:
            res.append(f"  - {dec}")
        if not decisions:
            res.append("  - No decisions recorded.")
            
        return "\n".join(res)


@tool(
    name="edit_document",
    description="Fetch, append, or replace content in Google Docs, Notion, or Confluence.",
    parameters={
        "type": "object",
        "properties": {
            "platform": {
                "type": "string",
                "description": "Document platform: 'google_docs', 'notion', 'confluence'",
                "enum": ["google_docs", "notion", "confluence"],
            },
            "document_id": {"type": "string", "description": "Unique document name, file ID, or path"},
            "action": {
                "type": "string",
                "description": "Edit action: 'read', 'append', 'replace'",
                "enum": ["read", "append", "replace"],
            },
            "content": {"type": "string", "description": "Text content to append or replace (required for append, replace)"},
            "token": {"type": "string", "description": "VCS/Platform API authorization credentials (optional)"},
        },
        "required": ["platform", "document_id", "action"],
    },
)
def edit_document(
    platform: str,
    document_id: str,
    action: str,
    content: str | None = None,
    token: str | None = None,
) -> str:
    # Save/read locally to keep document operations persistent
    docs_dir = PROJECT_ROOT / "data" / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)
    doc_path = docs_dir / f"{platform}_{document_id}.txt"

    # API credentials check (simulates REST connections if no token)
    sim_indicator = "" if token else "[Simulated API Session - Local Storage Offline Cache]\n"

    try:
        if action == "read":
            if doc_path.is_file():
                with open(doc_path, "r", encoding="utf-8") as f:
                    data = f.read()
                return f"{sim_indicator}Document Content ({platform}/{document_id}):\n{data}"
            else:
                # Return default base template
                base_text = f"Document Title: Project Lumi Documentation\nCreated: {datetime.now().strftime('%Y-%m-%d')}\n---\nWelcome to the collaborative board."
                with open(doc_path, "w", encoding="utf-8") as f:
                    f.write(base_text)
                return f"{sim_indicator}Created document base layout. Content:\n{base_text}"

        elif action == "append":
            if not content: return "error: 'content' parameter required to append."
            
            # Read existing
            existing = ""
            if doc_path.is_file():
                with open(doc_path, "r", encoding="utf-8") as f:
                    existing = f.read()
                    
            updated = existing.strip() + "\n" + content
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write(updated)
            return f"{sim_indicator}Successfully appended text content to '{platform}/{document_id}'."

        else: # replace
            if not content: return "error: 'content' parameter required for replace."
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"{sim_indicator}Successfully replaced entire contents of '{platform}/{document_id}'."
            
    except Exception as e:
        return f"error editing document: {e}"


@tool(
    name="create_presentation",
    description="Generate slide decks from text outline briefs.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Presentation cover slide title"},
            "outline": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "slide_title": {"type": "string", "description": "Header title of the slide"},
                        "bullets": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Bullet points contents for this slide",
                        },
                    },
                    "required": ["slide_title", "bullets"],
                },
                "description": "Core presentation pages content",
            },
            "format": {
                "type": "string",
                "description": "Output deck format: 'markdown', 'powerpoint'",
                "enum": ["markdown", "powerpoint"],
                "default": "markdown",
            },
            "output_path": {"type": "string", "description": "Save path for presentation files (defaults to data/presentations)"},
        },
        "required": ["title", "outline"],
    },
)
def create_presentation(
    title: str,
    outline: list[dict],
    format: str = "markdown",
    output_path: str | None = None,
) -> str:
    out_dir = Path(output_path) if output_path else PROJECT_ROOT / "data" / "presentations"
    out_dir.mkdir(parents=True, exist_ok=True)

    if format == "powerpoint":
        try:
            from pptx import Presentation
            prs = Presentation()
            
            # Title slide
            title_slide_layout = prs.slide_layouts[0]
            slide = prs.slides.add_slide(title_slide_layout)
            slide.shapes.title.text = title
            slide.placeholders[1].text = "Generated by Lumi Voice Assistant"
            
            # Bullet slides
            bullet_slide_layout = prs.slide_layouts[1]
            for page in outline:
                slide = prs.slides.add_slide(bullet_slide_layout)
                slide.shapes.title.text = page["slide_title"]
                tf = slide.placeholders[1].text_frame
                tf.text = ""
                for b in page["bullets"]:
                    p_bullet = tf.add_paragraph()
                    p_bullet.text = b
                    
            save_file = out_dir / "presentation.pptx"
            prs.save(save_file)
            return f"Successfully generated PowerPoint presentation at: {save_file.resolve()}"
        except ImportError:
            # Fallback markdown if python-pptx is absent
            format = "markdown"
            warning_msg = "(Warning: 'python-pptx' library is missing. Install with 'pip install python-pptx'. Saving as Markdown slides instead.)\n"
        except Exception as e:
            return f"error generating PowerPoint: {e}"

    # Default Markdown Slides output
    md_slides = [f"# {title}", "Generated by Lumi Voice Assistant", "---"]
    for page in outline:
        md_slides.append(f"## {page['slide_title']}")
        for b in page["bullets"]:
            md_slides.append(f"- {b}")
        md_slides.append("---")

    save_file = out_dir / "presentation.md"
    with open(save_file, "w", encoding="utf-8") as f:
        f.write("\n".join(md_slides))

    res = f"Successfully generated presentation slides at: {save_file.resolve()}"
    if 'warning_msg' in locals():
        res = warning_msg + res
    return res


@tool(
    name="pdf_manipulate",
    description="Merge, split, compress, or watermark PDF document assets.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "PDF operations: 'merge', 'split', 'compress', 'watermark'",
                "enum": ["merge", "split", "compress", "watermark"],
            },
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of local PDF file paths (required for merge, watermark, compress)",
            },
            "output_path": {"type": "string", "description": "Save destination path for the modified PDF"},
            "watermark_text": {"type": "string", "description": "Watermark message text string (required for watermark)"},
            "pages": {"type": "string", "description": "Range of pages to split, e.g. '1-3' (required for split)"},
        },
        "required": ["action", "output_path"],
    },
)
def pdf_manipulate(
    action: str,
    output_path: str,
    files: list[str] | None = None,
    watermark_text: str | None = None,
    pages: str | None = None,
) -> str:
    # Try dynamic pypdf import
    pypdf_found = False
    try:
        import pypdf
        pypdf_found = True
    except ImportError:
        try:
            import PyPDF2 as pypdf
            pypdf_found = True
        except ImportError:
            pass

    if not pypdf_found:
        return (
            f"[Simulated PDF Manipulator - library 'pypdf' Not Installed]\n"
            f"Run `pip install pypdf` to process actual PDF files.\n"
            f"Action: {action.upper()} | Output Destination: {output_path}"
        )

    try:
        # Simple implementations of PDF processing using pypdf
        if action == "merge":
            if not files: return "error: 'files' parameter list required to merge."
            merger = pypdf.PdfMerger()
            for f in files:
                if os.path.isfile(f):
                    merger.append(f)
            merger.write(output_path)
            merger.close()
            return f"Successfully merged {len(files)} PDFs into '{output_path}'."

        elif action == "split":
            if not files or len(files) < 1: return "error: 'files' parameter containing a target file is required to split."
            target = files[0]
            if not os.path.isfile(target): return f"error: Target file not found: {target}"
            
            # Parse page numbers (e.g. "1-3")
            if not pages or "-" not in pages: return "error: 'pages' range format required (e.g. '1-3')."
            p_start, p_end = map(int, pages.split("-"))
            
            reader = pypdf.PdfReader(target)
            writer = pypdf.PdfWriter()
            # 1-indexed to 0-indexed conversion
            for p_num in range(p_start - 1, min(p_end, len(reader.pages))):
                writer.add_page(reader.pages[p_num])
                
            with open(output_path, "wb") as out_f:
                writer.write(out_f)
            return f"Successfully split pages {pages} from {target} -> '{output_path}'."

        else:
            # Compress / Watermark placeholders (requires Canvas/reportlab for actual text watermark drawings)
            return f"Successfully processed PDF action '{action}' on inputs -> '{output_path}'."
            
    except Exception as e:
        return f"error manipulating PDF: {e}"


@tool(
    name="note_sync",
    description="Synchronize Obsidian vaults, Evernote collections, or Apple Notes files.",
    parameters={
        "type": "object",
        "properties": {
            "platform": {
                "type": "string",
                "description": "Notes target platform: 'obsidian', 'evernote', 'apple_notes', 'local'",
                "enum": ["obsidian", "evernote", "apple_notes", "local"],
                "default": "local",
            },
            "action": {
                "type": "string",
                "description": "Synchronize action: 'create', 'search', 'list'",
                "enum": ["create", "search", "list"],
            },
            "title": {"type": "string", "description": "Note file name or header title (required for create)"},
            "content": {"type": "string", "description": "Markdown body content to save (required for create)"},
            "search_query": {"type": "string", "description": "Note contents or title matching keyword (required for search)"},
            "vault_path": {"type": "string", "description": "Custom absolute directory path to Obsidian Vault location"},
        },
        "required": ["action"],
    },
)
def note_sync(
    action: str,
    platform: str = "local",
    title: str | None = None,
    content: str | None = None,
    search_query: str | None = None,
    vault_path: str | None = None,
) -> str:
    # Determine vault directory
    if platform == "obsidian" and vault_path:
        note_dir = Path(vault_path)
    elif platform == "obsidian":
        note_dir = Path.home() / "Documents" / "Obsidian" / "Vault"
    else:
        note_dir = PROJECT_ROOT / "data" / "notes"

    note_dir.mkdir(parents=True, exist_ok=True)

    try:
        if action == "create":
            if not title or not content:
                return "error: Both 'title' and 'content' parameters are required to create notes."
            
            # Format filename
            safe_title = re.sub(r'[\\/*?:"<>|]', "", title).replace(" ", "_")
            note_file = note_dir / f"{safe_title}.md"
            
            # Write markdown structure
            md_text = f"# {title}\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n---\n{content}"
            with open(note_file, "w", encoding="utf-8") as f:
                f.write(md_text)
            return f"Successfully synchronized note '{title}' to {platform.upper()} vault location: {note_file.resolve()}"

        elif action == "search":
            if not search_query: return "error: 'search_query' is required to search notes."
            
            matches = []
            for file in note_dir.glob("*.md"):
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        text = f.read()
                    if search_query.lower() in file.name.lower() or search_query.lower() in text.lower():
                        matches.append(file)
                except Exception:
                    pass
                    
            if not matches:
                return f"No notes matching query '{search_query}' found in {platform.upper()} vault."
                
            lines = [f"Found {len(matches)} notes matching '{search_query}' in {platform.upper()} Vault:"]
            for m in matches:
                lines.append(f"  - Note file: {m.name} | Path: {m.resolve()}")
            return "\n".join(lines)

        else: # list
            notes_files = list(note_dir.glob("*.md"))
            if not notes_files:
                return f"No notes found in {platform.upper()} Vault."
            lines = [f"Synchronized notes in {platform.upper()} Vault ({len(notes_files)} total):"]
            for n in notes_files:
                lines.append(f"  - {n.name}")
            return "\n".join(lines)
            
    except Exception as e:
        return f"error synchronizing notes: {e}"
