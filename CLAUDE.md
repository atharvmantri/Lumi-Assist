# Lumi Project — Claude Session Guide

## Quick Context
This is **Lumi**, a local-first voice assistant for Windows 11 built by **Atharv**.
- **Wake word:** "hey computer"
- **Architecture:** voice loop (background thread) + system tray + animated overlay (main Qt thread)
- **Tech stack:** Python 3.11, PyQt6, faster-whisper, Piper TTS, openWakeWord, HackClub API proxy

## Key Architecture
```
main.py → voice_loop (wake_word → stt → llm → tts)
        → tray + overlay (QSystemTrayIcon + DesktopOverlay)
        → conversation logging (data/conversations/)
```

## Overlay States (ui/overlay.py)
- IDLE → invisible
- LISTENING → golden waveform bars
- THINKING → blue glowing hexagonal orb
- RESPONDING → golden particle swirl + text bubble

## Important Files
- `main.py` — entry point, voice loop, text mode
- `ui/overlay.py` — 600x220 animated particle overlay
- `ui/tray.py` — system tray manager (pure PyQt6)
- `core/llm.py` — LLM client with tool execution
- `core/stt.py` — Whisper STT
- `core/tts.py` — Piper TTS with sentence streaming
- `core/wake_word.py` — openWakeWord detector
- `core/executor.py` — tool dispatch + learning
- `core/learning.py` — failure memory + lessons injection
- `core/conversation_log.py` — prompt/response dataset builder
- `core/diagnostics.py` — health check module
- `tools/` — all registered tools (open_app, focus_window, screenshot, etc.)

## Memory System
- `memory/user-atharv-profile.md` — permanent user profile (HARD memory)
- `memory/session-context-soft.md` — current session state (SOFT memory)
- `data/conversations/YYYY-MM-DD.jsonl` — conversation dataset

## Known Constraints
- Pure PyQt6 for tray (no pystray — WNDPROC conflict with Qt event loop)
- LLM tool calls use non-streaming API (HackClub/DeepInfra fragmentation bug)
- `run_python` code arg is JSON-encoded — NO f-strings (breaks JSON parser)

## Conversation Dataset
Every Lumi interaction is logged to `data/conversations/`. This is Atharv's intentional training dataset. Do not delete or modify these files.
