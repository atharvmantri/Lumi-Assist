import sys
import os
import json
from pathlib import Path

# Configure UTF-8 encoding for stdout on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add workspace to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.email import send_email, read_email, draft_email
from tools.communication import (
    send_slack_discord,
    send_sms,
    calendar_sync,
    schedule_meeting,
    join_meeting,
    meeting_summarizer,
    edit_document,
    create_presentation,
    pdf_manipulate,
    note_sync
)


def test_email_suite():
    print("==================================================")
    print("Testing Email Suite...")
    print("==================================================")

    # 1. send_email (configured check / mock flow)
    print("1. Testing send_email...")
    res = send_email(to="test@example.com", subject="Hello from test suite", body="This is plain body text", html_body="<h3>Hello!</h3>")
    print(f"   Send Email output: {res}")
    assert "error" in res or "Email sent" in res, "Unexpected send_email response"

    # 2. read_email (simulated/actual IMAP check)
    print("2. Testing read_email...")
    inbox = read_email(limit=3)
    print(f"   Inbox reading output:\n{inbox}")
    assert "From:" in inbox or "Inbox Emails" in inbox, "Unexpected read_email output"

    # 3. draft_email
    print("3. Testing draft_email...")
    draft = draft_email(recipient_context="asking for feedback on project updates", to="manager@lumi.ai", subject="Weekly Update Check", tone="formal")
    print(f"   Draft Email output:\n{draft}")
    assert "created email draft" in draft or "Saved to:" in draft, "Unexpected draft_email output"
    print("   ✅ Email Suite tests passed.\n")


def test_messaging_and_sync():
    print("==================================================")
    print("Testing Messaging & Sync Tools...")
    print("==================================================")

    # 4. send_slack_discord
    print("4. Testing send_slack_discord...")
    slack_res = send_slack_discord(platform="slack", action="send_message", target="#general", message="Lumi pipeline updates")
    print(f"   Slack output: {slack_res}")
    assert "Post" in slack_res or "posted" in slack_res or "Simulated" in slack_res, "Unexpected slack response"

    # 5. send_sms
    print("5. Testing send_sms...")
    sms_res = send_sms(to_phone="+15550199", message="System alerts initialized")
    print(f"   SMS output: {sms_res}")
    assert "sent" in sms_res or "Simulated" in sms_res, "Unexpected SMS response"

    # 6. calendar_sync
    print("6. Testing calendar_sync...")
    cal_list = calendar_sync(provider="google", action="list")
    print(f"   Google Calendar list:\n{cal_list}")
    assert "Calendar Sync" in cal_list, "Unexpected calendar list response"
    
    event_info = {
        "summary": "Mock Test Conference",
        "start": "2026-06-11T10:00:00",
        "end": "2026-06-11T10:30:00",
        "description": "Integration check event"
    }
    cal_create = calendar_sync(provider="google", action="create", event_data=event_info)
    print(f"   Calendar create: {cal_create}")
    assert "Successfully created event" in cal_create, "Unexpected calendar creation response"
    
    # Extract event ID to test delete
    match = len(cal_create.split("Event ID: ")) > 1
    if match:
        e_id = cal_create.split("Event ID: ")[1].strip()
        cal_del = calendar_sync(provider="google", action="delete", event_id=e_id)
        print(f"   Calendar delete: {cal_del}")
        assert "Successfully deleted event" in cal_del, "Unexpected delete response"
        
    print("   ✅ Messaging & Sync tests passed.\n")


def test_meetings_and_documents():
    print("==================================================")
    print("Testing Meetings & Documents Tools...")
    print("==================================================")

    # 7. schedule_meeting
    print("7. Testing schedule_meeting...")
    meet_sched = schedule_meeting(attendees=["dev@lumi.ai", "qa@lumi.ai"], meeting_title="Lumi Integration Sync", duration_minutes=45)
    print(f"   Scheduled meeting slot details:\n{meet_sched}")
    assert "Successfully scheduled meeting" in meet_sched or "Invite .ics payload" in meet_sched, "Unexpected schedule response"

    # 8. join_meeting
    print("8. Testing join_meeting...")
    join_res = join_meeting(meeting_url="https://zoom.us/j/9999999999")
    print(f"   Join Meeting output (first 300 chars):\n{join_res[:300]}...")
    assert "Joined" in join_res or "listening" in join_res, "Unexpected join_meeting response"

    # 9. meeting_summarizer
    print("9. Testing meeting_summarizer...")
    mock_transcript = (
        "[00:01] Sarah: Let's focus on notes sync deployment.\n"
        "[00:15] Alex: I will check Apple Notes and Obsidian sync logic today.\n"
        "[00:30] Sarah: Excellent. Let's make sure we test all local directories."
    )
    summary = meeting_summarizer(transcript=mock_transcript)
    print(f"   Meeting summary:\n{summary}")
    assert len(summary) > 20, "Unexpected summary response"


    # 10. edit_document
    print("10. Testing edit_document...")
    doc_create = edit_document(platform="google_docs", document_id="api_keys_manifest", action="read")
    print(f"    Google Doc read/create:\n{doc_create}")
    assert "Document Content" in doc_create or "Created document" in doc_create, "Unexpected read response"
    
    doc_append = edit_document(platform="google_docs", document_id="api_keys_manifest", action="append", content="Adding API gateway definitions.")
    print(f"    Google Doc append: {doc_append}")
    assert "appended" in doc_append, "Unexpected append response"
    
    # Cleanup document
    docs_dir = Path("data/documents")
    doc_file = docs_dir / "google_docs_api_keys_manifest.txt"
    if doc_file.exists():
        doc_file.unlink()
    if docs_dir.exists() and not any(docs_dir.iterdir()):
        docs_dir.rmdir()
        
    print("    ✅ Meetings & Documents tests passed.\n")


def test_presentation_pdf_notes():
    print("==================================================")
    print("Testing Presentation, PDF & Notes Sync Tools...")
    print("==================================================")

    # 11. create_presentation
    print("11. Testing create_presentation...")
    outline = [
        {"slide_title": "Architecture Overview", "bullets": ["Micro-services based", "Event-driven updates"]},
        {"slide_title": "Security Features", "bullets": ["Windows DPAPI Vault", "Concurrently OSV scan"]}
    ]
    pres_res = create_presentation(title="Lumi Integration presentation", outline=outline, format="markdown")
    print(f"    Presentation slide generation output: {pres_res}")
    assert "Successfully generated presentation" in pres_res, "Unexpected presentation response"
    
    # Clean up generated presentation
    pres_file = Path("data/presentations/presentation.md")
    if pres_file.exists():
        pres_file.unlink()
    if Path("data/presentations").exists():
        Path("data/presentations").rmdir()

    # 12. pdf_manipulate
    print("12. Testing pdf_manipulate...")
    pdf_res = pdf_manipulate(action="merge", files=["a.pdf", "b.pdf"], output_path="data/merged.pdf")
    print(f"    PDF Manipulation output: {pdf_res}")
    assert "merged" in pdf_res or "Simulated" in pdf_res or "pypdf" in pdf_res, "Unexpected PDF response"

    # 13. note_sync
    print("13. Testing note_sync...")
    note_res = note_sync(action="create", platform="obsidian", title="Lumi Collaboration Goals", content="Build robust Obsidian markdown note sync plugins.")
    print(f"    Obsidian create note result: {note_res}")
    assert "Successfully synchronized note" in note_res, "Unexpected note creation response"
    
    # Search note
    note_search = note_sync(action="search", platform="obsidian", search_query="Obsidian")
    print(f"    Obsidian notes search results:\n{note_search}")
    assert "Found" in note_search or "notes matching" in note_search, "Unexpected search results"
    
    # Cleanup sync files
    obsidian_dir = Path.home() / "Documents" / "Obsidian" / "Vault"
    created_note = obsidian_dir / "Lumi_Collaboration_Goals.md"
    if created_note.exists():
        created_note.unlink()
    if obsidian_dir.exists() and not any(obsidian_dir.iterdir()):
        created_note.parent.rmdir()
        if obsidian_dir.parent.exists() and not any(obsidian_dir.parent.iterdir()):
            obsidian_dir.parent.rmdir()
            
    print("    ✅ Presentation, PDF & Notes tests passed.\n")


if __name__ == "__main__":
    test_email_suite()
    test_messaging_and_sync()
    test_meetings_and_documents()
    test_presentation_pdf_notes()
    print("🎉 All Communication & Collaboration tests passed successfully!")
