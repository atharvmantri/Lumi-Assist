# JARVIS — AI Voice Assistant for Windows
### Product Requirements Document · v1.0

---

## 1. Overview

**JARVIS** is a fully local, always-on AI voice assistant for Windows that feels like having a personal AI operating co-pilot. It listens for a wake word, transcribes your speech on-device using a GPU-accelerated Whisper model, routes your request through a powerful cloud LLM (Nemotron Ultra), executes actions on your PC, and responds with natural-sounding speech synthesized entirely on your GPU. Zero typing. Zero friction. Just talk.

> *"It's not a chatbot you open. It's an assistant that's already there."*

---

## 2. Goals & Non-Goals

### Goals
- Wake-word activated, always-listening assistant with near-zero latency
- Full GPU acceleration for both STT and TTS on an RTX 3060 12GB
- Unrestricted PC control — apps, files, browser, system settings, code, anything
- Sleek, minimal floating UI that stays out of the way
- Single-process Python application; one command to start

### Non-Goals
- Cloud STT/TTS (Whisper and TTS run **locally only**)
- Mobile or cross-platform support (Windows 11/10 only)
- Multi-user or multi-machine setups
- Fine-tuning or retraining models

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        JARVIS RUNTIME                           │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────────┐  │
│  │  WAKE WORD   │    │     STT      │    │       LLM         │  │
│  │  Detection   │───▶│   Whisper    │───▶│  Nemotron Ultra   │  │
│  │  (pvporcupine│    │  (GPU, CUDA) │    │  via HackClub API │  │
│  │   / openwake)│    │              │    │                   │  │
│  └──────────────┘    └──────────────┘    └────────┬──────────┘  │
│                                                   │             │
│  ┌──────────────┐    ┌──────────────┐    ┌────────▼──────────┐  │
│  │   FLOATING   │    │     TTS      │    │  ACTION EXECUTOR  │  │
│  │     UI       │◀───│  (GPU, CUDA) │◀───│  (Tool Calling /  │  │
│  │  (PyQt6/    │    │  Piper/Coqui │    │   OS Automation)  │  │
│  │   ttkbootst.)│    │              │    │                   │  │
│  └──────────────┘    └──────────────┘    └───────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │ GPU: RTX 3060 12GB — All ML inference runs here
```

---

## 4. Component Specifications

### 4.1 Wake Word Detection

| Property | Value |
|---|---|
| Library | `openWakeWord` (free, no key needed) or `pvporcupine` (Picovoice, free tier) |
| Wake phrase | `"Hey Jarvis"` (default, configurable in `config.yaml`) |
| Runs on | CPU (lightweight — leaves GPU free) |
| Latency | < 200ms to trigger STT |
| Behavior | Plays a soft chime, lights up UI, begins recording |

The wake word listener runs in a dedicated background thread. When triggered, it signals the STT pipeline and locks out further detection until the response cycle completes.

---

### 4.2 Speech-to-Text (STT)

| Property | Value |
|---|---|
| Model | `openai/whisper-large-v3` or `whisper-large-v3-turbo` |
| Backend | `faster-whisper` (CTranslate2) with CUDA |
| GPU Memory | ~3–4 GB VRAM at large-v3 |
| Transcription speed | ~2–5x real-time on RTX 3060 |
| Compute type | `float16` (GPU) |
| Language | Auto-detect, default English |

The STT model is loaded once at startup and stays warm in VRAM. Audio is recorded until 1.5 seconds of silence is detected (configurable), then passed as a buffer to Whisper.

```python
# Core STT init pattern
from faster_whisper import WhisperModel
stt_model = WhisperModel("large-v3", device="cuda", compute_type="float16")
```

---

### 4.3 Language Model (LLM)

| Property | Value |
|---|---|
| Model | `nvidia/nemotron-3-ultra-550b-a55b:free` |
| Provider | HackClub AI API |
| Base URL | `https://ai.hackclub.com/proxy/v1` |
| API Style | OpenAI-compatible (`/v1/chat/completions`) |
| Context window | Large (550B parameter model) |
| Streaming | Yes — token-by-token for low perceived latency |

The LLM is the brain of JARVIS. It receives the transcribed text plus a powerful system prompt that defines its role, available tools, and PC context. It returns either a plain response or a structured tool call to execute.

**System Prompt Design:**
```
You are JARVIS, an all-powerful AI assistant running on a Windows PC.
Your job is to do ANYTHING the user asks — open apps, write code, manage
files, search the web, control system settings, automate tasks, answer
questions. You always find a way. You respond concisely (1-3 sentences max
for spoken replies). You think step by step before acting.

Available tools: [open_app, run_command, write_file, read_file,
web_search, type_text, click_element, take_screenshot, ...]
```

**HackClub API call pattern:**
```python
import openai

client = openai.OpenAI(
    api_key="YOUR_HACKCLUB_KEY",
    base_url="https://ai.hackclub.com/proxy/v1"
)

stream = client.chat.completions.create(
    model="nvidia/nemotron-3-ultra-550b-a55b:free",
    messages=conversation_history,
    stream=True,
    tools=TOOL_DEFINITIONS
)
```

---

### 4.4 Action Executor (PC Control)

This is what makes JARVIS genuinely powerful. The LLM can call any of these tools, and JARVIS executes them on your machine:

| Tool | Description | Library |
|---|---|---|
| `open_app` | Launch any application by name | `subprocess`, `pywinauto` |
| `run_command` | Execute PowerShell or CMD commands | `subprocess` |
| `write_file` | Create or edit any file | `pathlib` |
| `read_file` | Read file contents and report back | `pathlib` |
| `web_search` | Search the web and return results | `duckduckgo-search` |
| `open_url` | Open URL in default browser | `webbrowser` |
| `type_text` | Type text into focused window | `pyautogui` |
| `click_element` | Click UI elements | `pyautogui`, `pywinauto` |
| `take_screenshot` | Capture screen for visual context | `Pillow` |
| `get_screen_text` | OCR the current screen | `pytesseract` |
| `control_media` | Play/pause/skip media | `keyboard` |
| `set_volume` | Adjust system volume | `pycaw` |
| `clipboard_read` | Read clipboard contents | `pyperclip` |
| `clipboard_write` | Write to clipboard | `pyperclip` |
| `get_window_list` | List all open windows | `pywinauto` |
| `focus_window` | Bring a window to foreground | `pywinauto` |
| `run_python` | Execute arbitrary Python code | `exec()` in sandbox |
| `send_notification` | Windows toast notification | `win10toast` |

The executor supports **multi-step chaining**: if completing a task requires 5 tool calls in sequence, JARVIS figures that out autonomously and does them all before responding.

---

### 4.5 Text-to-Speech (TTS)

| Property | Value |
|---|---|
| Engine | `Piper TTS` (primary) or `Coqui TTS` (alternative) |
| Voice | `en_US-libritts_r-medium` or similar high-quality neural voice |
| GPU acceleration | CUDA via `torch` backend |
| GPU Memory | ~1–2 GB VRAM |
| Latency | < 300ms for first audio chunk |
| Streaming | Yes — audio plays as tokens arrive |

Piper is preferred for its speed and quality. The voice should sound confident and calm — not robotic. Users can swap voice models in `config.yaml`.

```python
# TTS output pipes directly to audio device
import piper
voice = piper.PiperVoice.load("en_US-libritts_r-medium.onnx", use_cuda=True)
```

---

## 5. UI Design

### Philosophy
The UI is **ambient** — it's there when you need it, invisible when you don't. Inspired by HUD elements from Iron Man: minimal, glassy, sharp.

### Floating HUD Window

```
╔══════════════════════════════════════╗
║  ◉  JARVIS                    — ✕   ║
║──────────────────────────────────────║
║                                      ║
║   [Animated waveform / orb here]     ║
║                                      ║
║  "Opening Spotify and playing your   ║
║   liked songs..."                    ║
║                                      ║
║  ─────────────────────────────────   ║
║  [Transcript of last exchange here]  ║
╚══════════════════════════════════════╝
```

**Visual States:**

| State | Animation | Color |
|---|---|---|
| Idle / Listening for wake word | Slow pulse | Dim blue `#1E2A3A` |
| Wake word detected | Flash + expand | Cyan `#00D4FF` |
| Listening (recording) | Live waveform | White `#FFFFFF` |
| Processing | Spinning arc | Purple `#7C3AED` |
| Speaking | Waveform sync to audio | Cyan-green `#00FFB3` |
| Error | Shake + red pulse | Red `#FF4444` |

**UI Stack:**
- Framework: `PyQt6` with `QGraphicsDropShadowEffect` for glassmorphism
- Always-on-top, frameless window
- Draggable anywhere on screen
- Remembers last position in `config.yaml`
- Semi-transparent background (`rgba(10, 14, 23, 0.85)`)
- System tray icon with right-click menu (Show/Hide, Settings, Quit)

---

## 6. Conversation & Memory

### Short-term Memory
Full conversation history is maintained in-session (rolling last 20 turns) and passed to the LLM on every call. This lets JARVIS remember context: *"Wait, which file did I ask you to edit earlier?"*

### Long-term Memory (v1.1)
A local `ChromaDB` or SQLite-based memory store. JARVIS will remember facts you tell it, preferences, and frequently used commands across sessions.

### PC Context Injection
On each LLM call, JARVIS injects live PC context:
```python
context = f"""
Current time: {datetime.now()}
Active window: {get_active_window()}
Open applications: {get_open_apps()}
Clipboard: {get_clipboard_preview()}
"""
```

---

## 7. Configuration (`config.yaml`)

```yaml
jarvis:
  wake_word: "hey jarvis"
  wake_word_sensitivity: 0.7

stt:
  model: "large-v3"           # Options: tiny, base, small, medium, large-v3
  device: "cuda"
  compute_type: "float16"
  silence_threshold_ms: 1500

llm:
  provider: "hackclub"
  api_key: "${HACKCLUB_API_KEY}"  # Loaded from .env
  model: "nvidia/nemotron-3-ultra-550b-a55b:free"
  base_url: "https://ai.hackclub.com/proxy/v1"
  max_tokens: 2048
  temperature: 0.7
  system_prompt_path: "prompts/system.md"

tts:
  engine: "piper"             # Options: piper, coqui
  voice: "en_US-libritts_r-medium"
  device: "cuda"
  speed: 1.0

ui:
  theme: "dark"
  opacity: 0.88
  always_on_top: true
  show_transcript: true
  window_position: [80, 80]   # x, y from top-left

audio:
  input_device: "default"
  output_device: "default"
  sample_rate: 16000
```

---

## 8. File & Folder Structure

```
jarvis/
├── main.py                  # Entry point — starts all threads
├── config.yaml              # User configuration
├── .env                     # API keys (gitignored)
├── requirements.txt
├── README.md
│
├── core/
│   ├── wake_word.py         # Wake word detection loop
│   ├── stt.py               # Whisper STT pipeline
│   ├── llm.py               # HackClub API + streaming
│   ├── tts.py               # Piper/Coqui TTS pipeline
│   └── executor.py          # Tool call dispatcher
│
├── tools/                   # One file per tool category
│   ├── apps.py              # open_app, focus_window
│   ├── shell.py             # run_command
│   ├── files.py             # write_file, read_file
│   ├── browser.py           # open_url, web_search
│   ├── input.py             # type_text, click_element
│   ├── screen.py            # take_screenshot, get_screen_text
│   ├── media.py             # control_media, set_volume
│   └── system.py            # clipboard, notifications
│
├── ui/
│   ├── hud.py               # Main floating window (PyQt6)
│   ├── tray.py              # System tray icon + menu
│   ├── animations.py        # Waveform, orb, state transitions
│   └── assets/
│       ├── icon.png
│       └── fonts/
│
├── prompts/
│   └── system.md            # Full system prompt for Nemotron
│
└── models/                  # Downloaded model weights (gitignored)
    ├── whisper/
    └── piper/
```

---

## 9. Setup & Installation Script

Claude Code should generate a `setup.bat` and `install.py` that:

1. Check Python 3.10+ and CUDA 12.x are installed
2. Create a virtual environment (`venv`)
3. Install all `requirements.txt` dependencies
4. Download Whisper large-v3 model weights
5. Download Piper voice model
6. Prompt user for HackClub API key and write to `.env`
7. Run a test inference on both STT and TTS to confirm GPU is working
8. Launch JARVIS

---

## 10. Requirements

### Python Dependencies (`requirements.txt`)

```
# Core
faster-whisper>=1.0.0
openai>=1.0.0
torch>=2.2.0+cu121
pyaudio>=0.2.14

# TTS
piper-tts>=1.2.0

# Wake word
openwakeword>=0.6.0

# UI
PyQt6>=6.6.0

# PC Automation
pyautogui>=0.9.54
pywinauto>=0.6.8
keyboard>=0.13.5
pycaw>=20240910
pyperclip>=1.8.2
Pillow>=10.0.0
pytesseract>=0.3.10
win10toast>=0.9

# Web
duckduckgo-search>=6.0.0
requests>=2.31.0

# Utilities
python-dotenv>=1.0.0
PyYAML>=6.0.1
numpy>=1.26.0
sounddevice>=0.4.6
```

### Hardware Requirements

| Component | Minimum | Recommended |
|---|---|---|
| GPU | RTX 3060 12GB | RTX 3060 12GB ✓ |
| VRAM | 8 GB | 12 GB ✓ |
| RAM | 16 GB | 32 GB |
| OS | Windows 10 | Windows 11 |
| Python | 3.10 | 3.11 |
| CUDA | 12.0 | 12.1+ |

---

## 11. VRAM Budget (RTX 3060 12GB)

| Component | VRAM Usage |
|---|---|
| Whisper large-v3 (float16) | ~3.5 GB |
| Piper TTS | ~1.0 GB |
| OS + driver overhead | ~0.5 GB |
| **Total** | **~5 GB** |
| **Available headroom** | **~7 GB** |

The 12GB VRAM is more than enough. Both models stay loaded permanently — no loading/unloading between requests.

---

## 12. Latency Budget (Target: < 2s end-to-end)

| Stage | Target Latency |
|---|---|
| Wake word → STT start | < 200ms |
| Audio recording (user speaking ~5s) | 3–7s (user-dependent) |
| Whisper transcription | < 500ms |
| LLM first token (streaming) | < 800ms |
| TTS first audio chunk | < 300ms |
| **Total perceived latency** | **< 2s after user stops talking** |

---

## 13. Security & Privacy

- All STT and TTS processing is **100% local** — audio never leaves the machine
- Only the transcribed text is sent to HackClub (no raw audio)
- API key stored in `.env`, never hardcoded
- `run_python` tool executes in a scoped namespace (no `__builtins__` escape)
- `run_command` logs all shell executions to `logs/commands.log`
- Optional: confirmation prompt before destructive actions (deletions, system changes)

---

## 14. Future Roadmap

### v1.1
- Long-term memory via ChromaDB
- Custom wake word training
- Multi-language STT support
- Voice profile switching

### v1.2
- Vision — take screenshots and ask JARVIS what's on screen
- Browser automation via Playwright
- Calendar & email integration (local clients)

### v2.0
- Proactive mode — JARVIS notices things and tells you ("Your RAM is at 95%", "You have a meeting in 10 mins")
- Plugin system for community-built tools
- Local Nemotron model support (when hardware allows)

---

## 15. Claude Code Instructions

When building this project, follow this order:

1. **Start with `core/stt.py`** — get Whisper running on CUDA, test with a sample WAV
2. **Build `core/tts.py`** — get Piper generating audio on CUDA
3. **Wire up `core/llm.py`** — connect to HackClub, test basic completion
4. **Implement `core/wake_word.py`** — integrate openWakeWord, test detection
5. **Build tools layer** — start with `shell.py`, `apps.py`, `files.py`
6. **Create `core/executor.py`** — tool call parsing and dispatch
7. **Build the UI** — floating HUD with PyQt6, system tray
8. **Integration in `main.py`** — wire all threads together with asyncio
9. **Setup scripts** — `setup.bat`, first-run wizard
10. **Testing** — end-to-end smoke test with 10 sample commands

For each module, write tests in `tests/` before moving to the next.

---

*Document version: 1.0 | Target build time: ~2–3 days of focused Claude Code sessions*
