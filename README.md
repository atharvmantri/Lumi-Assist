# JARVIS
> Local-first, always-on AI voice assistant for Windows 11

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%7C11-lightgrey)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tools](https://img.shields.io/badge/tools-263-orange)](#what-jarvis-can-do)

**Wake word** → **STT** → **LLM** → **TTS** → **263 tools** — all running locally on your PC.

Say *"hey jarvis"* and control your entire machine with voice. Open apps, check weather, manage files, browse the web, take screenshots, set timers, search the web, and hundreds more things — all hands-free.

![JARVIS in action](docs/jarviz-overlay.png)
> *Bottom-center overlay: golden waveform (listening), blue orb (thinking), particle swirl (responding)*

---

## ✨ Features

- **Always-on wake word** — "hey jarvis" detection via openWakeWord, no cloud needed
- **GPU-accelerated STT** — Whisper large-v3 via faster-whisper on CUDA
- **Streaming LLM** — HackClub-proxied Nemotron with tool calling, auto-retry, and learning from past failures
- **Sentence-streaming TTS** — Piper voice that starts speaking after the first sentence, not the whole reply
- **Animated desktop overlay** — bottom-center particles that morph between 4 states (invisible → waveform → orb → swirl)
- **System tray integration** — color-changing icon, status menu, overlay test
- **263 built-in tools** — PC control, web, files, media, timers, weather, notes, tasks, memory, and more
- **Conversation dataset** — every prompt/response auto-logged to `data/conversations/`
- **Learning system** — JARVIS remembers its tool failures and avoids repeating them
- **Self-test** — `self_test` tool checks all components on demand

## 🚀 Quick Start

### One-command setup
```bat
setup.bat
```
Then edit `.env` and add your API key.

### Manual setup
```bat
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
:: Optional: GPU torch for faster STT
pip install torch==2.2.* --index-url https://download.pytorch.org/whl/cu121
```

Edit `.env` (copy from `.env.example`):
```env
HACKCLUB_API_KEY=your_key_here
```

### Run
```bat
python main.py                    # Full voice loop + tray + overlay
python main.py --type             # Text input mode (no mic)
python main.py --dry-run          # Test one turn without mic/wake word
python main.py --no-tray          # Terminal only
python -m core.diagnostics        # Health check
python tests/test_quick.py        # Smoke tests
```

## 🎤 How It Works

```
┌─────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐
│  Wake Word  │───▶│    STT     │───▶│    LLM     │───▶│    TTS     │
│ openWakeWord│    │  Whisper   │    │  Nemotron  │    │   Piper    │
│   (CPU)     │    │ (GPU/CUDA) │    │  (API)     │    │  (CPU)     │
└─────────────┘    └────────────┘    └────────────┘    └────────────┘
       │                                                       │
       ▼                                                       ▼
┌─────────────┐                                        ┌────────────┐
│   Tray +    │                                        │  Speakers  │
│  Overlay    │                                        │  (audio)   │
│  (PyQt6)    │                                        └────────────┘
└─────────────┘
```

1. **Wake word** — openWakeWord listens continuously on a background thread
2. **STT** — faster-whisper transcribes your speech to text
3. **LLM** — Nemotron (via HackClub proxy) processes the request, calls tools, and streams a reply
4. **TTS** — Piper synthesizes sentence-by-sentence for low-latency speech
5. **Overlay** — animated particles show JARVIS's current state at the bottom center of your screen

## 🛠️ What JARVIS Can Do

### System & PC Control
| Tool | Description |
|---|---|
| `open_app` | Launch apps by name |
| `focus_window` | Bring a window to front |
| `get_system_info` | Full PC specs |
| `get_battery` | Battery % and status |
| `get_cpu_usage` | CPU % per core |
| `get_processes` | Top processes |
| `set_volume` / `volume_up/down` | Control volume |
| `mute` | Toggle mute |

### Files & Search
| Tool | Description |
|---|---|
| `search_files` | Recursive file finder |
| `read_file` / `write_file` | Read/write text files |
| `list_dir` | List folder contents |
| `organize_folder` | Auto-sort files by type |
| `find_duplicates` | Find duplicate files |
| `file_hash` | Compute MD5/SHA256 |
| `diff_files` | Compare two files |

### Web & Network
| Tool | Description |
|---|---|
| `web_search` | DuckDuckGo search |
| `get_weather` | Weather (no API key) |
| `ping` | Ping a host |
| `internet_speed_test` | Speed test |
| `fetch_page` | Fetch and read web pages |
| `shorten_url` | Shorten URLs |

### Productivity
| Tool | Description |
|---|---|
| `add_task` / `list_tasks` | Todo list with priorities |
| `add_note` / `list_notes` | Persistent notes |
| `remember` / `recall` | Store & search facts |
| `set_timer` / `list_timers` | Timers with toast notifications |
| `daily_briefing` | Morning summary |
| `calculate` | Math expressions |
| `convert_units` | Unit conversion |

### Media & Screen
| Tool | Description |
|---|---|
| `take_screenshot` | Full or region screenshot |
| `get_screen_text` | OCR screen text |
| `media_play_pause` / `next` / `previous` | Media control |
| `keyboard_type` / `keyboard_press` | Simulate typing & shortcuts |
| `record_screen` | Screen recording (ffmpeg) |

### And 200+ more...
Run `list_capabilities` to see the full tool catalog, or check [docs/TOOLS.md](docs/TOOLS.md).

## 🏗️ Architecture

```
g:\assistant/
├── main.py                    # Entry point — voice loop + tray
├── config.yaml                # Main configuration
├── requirements.txt           # Python dependencies
├── setup.bat                  # One-command setup
├── launch.bat                 # Quick launch
│
├── core/
│   ├── config.py              # Config loading + local overrides
│   ├── llm.py                 # LLM client with tool calling + learning
│   ├── stt.py                 # Whisper STT + mic capture
│   ├── tts.py                 # Piper TTS with sentence streaming
│   ├── wake_word.py           # openWakeWord detector
│   ├── executor.py            # Tool dispatch + failure learning
│   ├── learning.py            # Persistent failure memory
│   ├── conversation_log.py    # Auto-logging every turn
│   └── diagnostics.py         # Health check module
│
├── ui/
│   ├── overlay.py             # Bottom-center animated particles
│   └── tray.py                # System tray (pure PyQt6)
│
├── tools/                     # 263 tools across 90 modules
│   ├── apps.py                # App launching + window focus
│   ├── browser.py             # Web search + URL opening
│   ├── screen.py              # Screenshots + OCR
│   ├── system.py              # Clipboard + notifications
│   ├── python_exec.py         # Arbitrary Python execution
│   └── ...                    # 85 more tool modules
│
├── prompts/
│   └── system.md              # JARVIS system prompt
│
├── tests/
│   └── test_quick.py          # Smoke tests
│
└── data/                      # Auto-created at runtime
    ├── conversations/          # JSONL conversation dataset
    └── ...                     # Notes, tasks, memories, etc.
```

## ⚙️ Configuration

### `config.yaml` — Main settings
```yaml
jarvis:
  wake_word: "hey jarvis"
  wake_word_sensitivity: 0.7

stt:
  model: "large-v3"
  device: "cuda"

llm:
  provider: "hackclub"
  model: "openrouter/free"

tts:
  engine: "piper"
  voice: "en_GB-southern_english_female-low"
```

### `config.local.yaml` — Your overrides (git-ignored)
```yaml
tts:
  voice: "en_US-amy-medium"
  speed: 1.1
stt:
  model: "large-v3-turbo"
```

### `.env` — API keys (git-ignored)
```env
HACKCLUB_API_KEY=your_key_here
```

## 📊 Conversation Dataset

Every interaction is automatically logged to `data/conversations/YYYY-MM-DD.jsonl`. Over time this builds a dataset you can use for:
- Analyzing JARVIS behavior patterns
- Evaluating tool usage
- Debugging edge cases
- Fine-tuning future models

```python
from core.conversation_log import load_dataset
entries = load_dataset(days=7)  # Last 7 days
print(f"{len(entries)} turns logged")
```

## 🧠 Learning System

JARVIS remembers its mistakes. Every tool failure is logged and injected into the system prompt on subsequent turns, so JARVIS learns not to repeat the same errors.

```python
python -m core.learning --show    # View learned lessons
python -m core.diagnostics         # Run health check
```

## 🖥️ Hardware Requirements

| Component | Minimum | Recommended |
|---|---|---|
| **GPU** | None (CPU mode) | NVIDIA RTX 3060 12GB+ |
| **RAM** | 8 GB | 16 GB+ |
| **Storage** | 5 GB | 10 GB+ (for models) |
| **OS** | Windows 10/11 | Windows 11 |
| **Python** | 3.11 | 3.11 |

> JARVIS works on CPU too — just slower. The STT model will download on first run.

## 📝 License

MIT. See [LICENSE](LICENSE) for details.

## 🤝 Contributing

Want to help? See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and guidelines.

## ⚠️ Disclaimer

JARVIS can execute arbitrary Python code and shell commands on your machine. Only use it in trusted environments. The tool execution system has safety guards for destructive operations, but you are responsible for what runs on your PC.

---

*Built by Atharv. Voice-powered, locally-first, and always listening.*
