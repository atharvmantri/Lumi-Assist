# Lumi Quick Start Guide

## First Time Setup
1. Double-click `setup.bat` — it will check Python, install dependencies, download the voice model, and run diagnostics
2. Edit `.env` and add your `HACKCLUB_API_KEY`
3. Double-click `launch.bat` to start Lumi

## Once Lumi is Running
1. Say **"hey lumi"** to wake it up
2. Wait for the chime, then speak your request
3. Lumi will respond out loud

## What Lumi Can Do
- **Open apps:** "Open Notepad", "Open Chrome"
- **Control media:** "Pause music", "Volume up", "Next track"
- **System info:** "What's my battery?", "How much RAM am I using?"
- **Weather:** "What's the weather?"
- **Screen:** "Take a screenshot", "What's on my screen?"
- **Files:** "Find my report.pdf", "What's in my downloads?"
- **Web:** "Search for...", "Open youtube.com"
- **Clipboard:** "What's in my clipboard?", "Copy this text"
- **Tasks:** "Add a task to buy groceries", "List my tasks"
- **Notes:** "Take a note: meeting at 3pm", "What notes do I have?"
- **Memory:** "Remember my favorite color is blue", "What do you know about me?"
- **Timers:** "Set a timer for 10 minutes", "List my timers"
- **Conversation history:** "What did I ask you yesterday?", "Show me conversation stats"
- **Network:** "Check my internet speed", "Ping google.com"
- **Math:** "Calculate sqrt(144) * 3", "Convert 100 fahrenheit to celsius"
- **Morning briefing:** "Good morning" or "Daily briefing"
- **Self test:** "Run a self test" or "Are you working?"
- **And 60+ more things — just ask!**

## Command Line Modes
```bat
python main.py                    # Full voice loop + tray + overlay
python main.py --type             # Text input mode (no mic)
python main.py --dry-run          # Test one turn without mic/wake word
python main.py --no-tray          # Terminal only (no tray icon)
python -m core.diagnostics        # Health check
python tests/test_quick.py        # Smoke tests
```

## Tray Menu
Right-click the Lumi tray icon to:
- See current status
- Test the overlay animation
- Quit Lumi

## Configuration
- `config.yaml` — main settings (don't edit if you want to keep git clean)
- `config.local.yaml` — your personal overrides (git-ignored)
- `.env` — API keys (git-ignored)

### Example config.local.yaml
```yaml
tts:
  voice: "en_US-amy-medium"    # Switch to American voice
  speed: 1.1                   # Slightly faster
stt:
  model: "large-v3-turbo"      # Faster whisper model
```

## Troubleshooting
- **No overlay showing?** → Right-click tray icon → "Test Overlay"
- **Wake word not detecting?** → Lower `wake_word_sensitivity` in config.yaml (try 0.5)
- **TTS not working?** → Check that voice model exists in `models/piper/`
- **Tools not working?** → Run `python -m core.diagnostics`
