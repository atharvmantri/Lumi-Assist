# Lumi

A local-first, always-on AI voice assistant for Windows. Controlled entirely by voice through a wake word, Lumi runs on your machine and can open applications, manage files, browse the web, retrieve system information, set timers, take screenshots, and execute code — all hands-free.

> Say **"hey lumi"** and talk to your computer like it's a person.

---

## Quick Start

### One-line install

Paste this into **PowerShell** and press Enter. The installer handles everything:

```powershell
irm https://raw.githubusercontent.com/atharvmantri/Lumi-Assist/main/install.ps1 | iex
```

That's it. When the installer finishes, a **Lumi** icon sits on your desktop. Double-click it and start talking.

---

### Manual install

If you prefer to see every step:

```powershell
git clone https://github.com/atharvmantri/Lumi-Assist.git
cd Lumi-Assist
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# edit .env and paste your API key
python main.py
```

---

### API Key

Lumi uses the HackClub AI proxy (free, no credit card). Get a key at [hackclub.com](https://hackclub.com/) and put it in `.env`:

```env
HACKCLUB_API_KEY=sk-hc-v1-...
```

---

## Requirements

| | Minimum (CPU only) | Recommended (GPU) |
|---|---|---|
| **OS** | Windows 10 / 11 | Windows 11 |
| **CPU** | Any x86-64, 2+ cores | Quad-core or better |
| **GPU** | None | NVIDIA, **5 GB+ VRAM** (GTX 1060 6GB, RTX 2060, etc.) |
| **RAM** | 4 GB | 8 GB |
| **Disk** | 3 GB free | 5 GB free |
| **Python** | 3.11 | 3.11 |
| **Mic / Speakers** | Any | Any |

Everything runs locally — the only external dependency is the LLM API call. On CPU, speech-to-text is slower but fully functional. The TTS engine (Piper) runs faster than real-time on CPU and does not need a GPU.

---

## How It Works

```
Wake word (openWakeWord, CPU)
  │
  ▼
Speech-to-text (faster-whisper, GPU or CPU)
  │
  ▼
LLM (streaming, tool-calling, via HackClub API)
  │
  ▼
Text-to-speech (Piper, CPU, sentence-streaming)
  │
  ▼
Speakers
```

Two threads run concurrently:

| Thread | Runs | Manages |
|---|---|---|
| **Voice loop** | Background thread | Wake word → STT → LLM → TTS pipeline |
| **Tray + overlay** | Main Qt thread | System tray icon, bottom-center animated overlay, Windows toast notifications |

---

## Overlay

A frameless, click-through widget sits at the bottom center of your screen above the taskbar. It is invisible by default and appears with a fade animation when Lumi is active.

| State | Appearance | When |
|---|---|---|
| **Idle** | *(hidden)* | Default — Lumi is listening for the wake word |
| **Listening** | Golden waveform bars | Wake word detected, waiting for your speech |
| **Thinking** | Blue glowing orb with rotating hexagonal pattern | Processing — STT transcription or LLM reasoning |
| **Responding** | Golden particle swirl with response text | Speaking the reply through speakers |

The tray icon changes color to match: grey (idle), red (listening), purple (thinking), green (responding).

---

## Configuration

All settings live in `config.yaml`. For personal overrides that stay off git, create `config.local.yaml` — it deep-merges on top of the base config:

```yaml
# config.local.yaml
tts:
  voice: "en_US-amy-medium"      # switch voice
  speed: 1.1                     # slightly faster
stt:
  model: "large-v3-turbo"        # smaller, faster whisper model
lumi:
  wake_word_sensitivity: 0.5     # lower = more sensitive
```

The full configuration reference:

| Setting | Default | Notes |
|---|---|---|
| `lumi.wake_word` | `"hey lumi"` | Wake phrase |
| `lumi.wake_word_sensitivity` | `0.7` | Trigger threshold, 0.3–0.9 |
| `stt.model` | `"large-v3"` | Whisper model: `tiny`, `small`, `medium`, `large-v3`, `large-v3-turbo` |
| `stt.device` | `"cuda"` | `"cuda"` for GPU, `"cpu"` for CPU-only |
| `stt.compute_type` | `"float16"` | `"float16"` (GPU), `"int8"` (low VRAM), `"float32"` (CPU) |
| `tts.voice` | `en_GB-southern_english_female-low` | Piper voice name |
| `tts.device` | `"cpu"` | Piper is fast enough on CPU |
| `llm.model` | `"openrouter/free"` | Model on the HackClub proxy |
| `llm.history_turns` | `20` | Rolling conversation memory window |

---

## What Lumi Can Do

Lumi has **260+ built-in tools** the LLM can call during conversation. A selection:

| Category | Examples |
|---|---|
| **Apps** | Open Notepad, focus a window, list running apps |
| **Files** | Search, read, write, organize, hash, compare, find duplicates |
| **System** | CPU/RAM/battery stats, processes, uptime, disk usage |
| **Media** | Play/pause music, volume control, keyboard shortcuts, mouse control |
| **Web** | DuckDuckGo search, fetch pages, ping hosts, speed test, DNS lookup |
| **Productivity** | Todo lists, notes, persistent memory, timers, calendar, weather |
| **Screen** | Screenshots, OCR text from screen, image comparison |
| **Code** | Arbitrary Python execution, shell commands, file diff, regex |
| **System ops** | Windows services, scheduled tasks, startup programs, firewall rules |

Run `list_capabilities` in conversation to see the full catalog, or browse `docs/TOOLS.md`.

---

## Conversation Logging

Every interaction is automatically saved to `data/conversations/YYYY-MM-DD.jsonl`. Each entry records the user input, the full assistant response, any tools called with arguments and results, and timing metrics.

The logs stay entirely on your machine (git-ignored). Load them programmatically:

```python
from core.conversation_log import load_dataset
entries = load_dataset(days=7)
print(f"{len(entries)} turns in the last 7 days")
```

---

## Learning From Mistakes

When a tool call fails, Lumi records the error. If the same error pattern recurs, the model receives a hint suggesting an alternative approach. Recent failure summaries are also injected into the system prompt so Lumi avoids repeating known mistakes across sessions.

View what Lumi has learned:

```powershell
python -m core.learning --show
```

---

## Testing

```powershell
python tests/test_quick.py          # Smoke tests (config, tools, overlay, TTS cleaning)
python -m core.diagnostics           # Health check (9 components)
python -m core.llm --smoke-test      # LLM connectivity
python -m core.stt --smoke-test      # STT round-trip
python -m core.tts --smoke-test      # TTS synthesis
python -m core.wake_word --smoke-test  # Wake word (30s mic listen)
python -m core.executor --list       # List all registered tools
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Wake word not detecting | Lower `wake_word_sensitivity` to `0.5` in `config.yaml` |
| Overlay not visible | Right-click tray icon → **Test Overlay** to cycle through states |
| TTS silent | Verify voice model exists in `models/piper/` |
| STT too slow | Set `stt.device: "cuda"` in `config.yaml` (requires NVIDIA GPU) |
| LLM errors | Check `.env` has a valid `HACKCLUB_API_KEY` |
| No audio devices | Run `python -m core.diagnostics` to list available devices |

---

## Adding Tools

Create a file in `tools/` — it auto-registers on startup:

```python
from tools import tool

@tool(
    name="my_tool",
    description="What this tool does.",
    parameters={
        "type": "object",
        "properties": {
            "arg": {"type": "string", "description": "An argument."},
        },
        "required": ["arg"],
    },
)
def my_tool(arg: str) -> str:
    return f"Result: {arg}"
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

---

## Directory Structure

```
Lumi-Assist/
  main.py                     Entry point — voice loop + tray
  config.yaml                 Main configuration
  install.ps1                 One-line PowerShell installer
  requirements.txt            Python dependencies
  .env.example                API key template

  core/                       Pipeline components
    llm.py                    Streaming LLM client with tool execution
    stt.py                    Whisper STT + mic capture
    tts.py                    Piper TTS with sentence streaming
    wake_word.py              openWakeWord detector
    executor.py               Tool dispatch + failure learning
    learning.py               Persistent failure memory
    conversation_log.py       Auto-logging every turn
    diagnostics.py            Health check

  ui/                         Desktop interface
    overlay.py                Bottom-center animated particles
    tray.py                   System tray (pure PyQt6)

  tools/                      91 tool modules, 260+ tools
  prompts/system.md           System prompt
  tests/                      Smoke and E2E tests
  data/                       Auto-created — conversation dataset
```

---

## Security

Lumi can execute arbitrary Python and shell commands on your machine. Only run it on personal hardware in trusted environments. Your `.env`, conversation logs, and audio recordings never leave your machine.

Destructive operations (file deletion, shutdown, system setting changes) require your explicit voice confirmation before executing.

See [SECURITY.md](SECURITY.md) for the full policy.

---

## License

MIT. See [LICENSE](LICENSE).

---

*Built by [Atharv](https://github.com/atharvmantri).*
