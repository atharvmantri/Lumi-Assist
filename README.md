# JARVIS

A local-first, always-on AI voice assistant for Windows 11. Controlled entirely by voice through a wake word, JARVIS runs on your machine and can open applications, manage files, browse the web, retrieve system information, set timers, take screenshots, and execute arbitrary code -- all hands-free.

JARVIS is built around a four-stage pipeline: wake word detection, speech-to-text, a streaming LLM with tool calling, and sentence-streaming text-to-speech. An animated overlay at the bottom center of the screen provides visual feedback across four states. A system tray icon shows the current state at a glance.

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Hardware Requirements](#hardware-requirements)
- [Configuration](#configuration)
- [Usage](#usage)
- [Overlay States](#overlay-states)
- [Tool System](#tool-system)
- [Conversation Logging](#conversation-logging)
- [Learning System](#learning-system)
- [Directory Structure](#directory-structure)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Security](#security)
- [License](#license)

## Quick Start

### Prerequisites

- Windows 10 or Windows 11
- Python 3.11
- A microphone and speakers
- An API key for the LLM provider (HackClub proxy or compatible OpenAI-compatible endpoint)

### Installation

Run the setup script:

```bat
setup.bat
```

This script performs the following steps:

1. Verifies Python 3.11 is installed
2. Creates a virtual environment
3. Installs all Python dependencies from `requirements.txt`
4. Downloads the Piper TTS voice model from Hugging Face
5. Creates required directories (`data/`, `logs/`, `models/`)
6. Generates a `.env` template for your API key
7. Runs diagnostics to confirm all components are functional

Alternatively, set up manually:

```bat
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

For GPU-accelerated speech-to-text (requires NVIDIA GPU with CUDA 12.x):

```bat
pip install torch==2.2.* --index-url https://download.pytorch.org/whl/cu121
```

### Configuration

Copy the example environment file and add your API key:

```bat
copy .env.example .env
```

Edit `.env` and set your API key:

```env
HACKCLUB_API_KEY=your_key_here
```

### Running

```bat
python main.py                    # Full voice loop with tray and overlay
python main.py --type             # Text input mode (no microphone required)
python main.py --dry-run          # Single test turn without wake word or microphone
python main.py --no-tray          # Voice loop without system tray (terminal only)
```

## Architecture

JARVIS runs two concurrent threads: a background voice loop and a main Qt thread for the system tray and desktop overlay.

```
main.py
  |
  +-- voice_loop (background thread)
  |     |
  |     +-- WakeWordDetector  (openWakeWord, continuous listening)
  |     +-- STT               (faster-whisper, GPU or CPU)
  |     +-- LLMClient         (OpenAI-compatible API, streaming + tool calls)
  |     +-- TTS               (Piper, sentence-streaming synthesis)
  |
  +-- TrayManager (main Qt thread)
  |     +-- QSystemTrayIcon   (color-coded state indicator)
  |     +-- DesktopOverlay    (bottom-center animated particles)
  |     +-- ToastNotifier     (Windows notifications)
  |
  +-- ConversationLogger      (auto-logs every turn to data/conversations/)
```

### Component Responsibilities

| Component | Module | Function |
|---|---|---|
| Wake word | `core/wake_word.py` | Continuous openWakeWord listening with cooldown and pause/resume |
| Speech-to-text | `core/stt.py` | faster-whisper transcription with VAD filter and mic capture |
| LLM | `core/llm.py` | Streaming chat with tool execution, history window, and lesson injection |
| Text-to-speech | `core/tts.py` | Piper TTS with sentence-level streaming and markdown cleanup |
| Tool executor | `core/executor.py` | Dispatch, timing, logging, and failure hint generation |
| Learning | `core/learning.py` | Persistent failure memory with lesson injection into system prompt |
| Overlay | `ui/overlay.py` | 600x220 frameless, click-through, always-on-top animated widget |
| Tray | `ui/tray.py` | Pure PyQt6 system tray with state-synchronized icon colors |

## Hardware Requirements

### Minimum (CPU-only)

| Component | Requirement |
|---|---|
| OS | Windows 10 or 11 |
| CPU | Any modern x86-64 processor |
| RAM | 8 GB |
| Storage | 5 GB free (for model downloads) |
| Python | 3.11 |
| Microphone | Any working input device |
| Speakers | Any working output device |

On CPU-only hardware, speech-to-text will be slower than real-time and TTS will run at reduced speed. The wake word detector and overlay have negligible CPU overhead.

### Recommended (GPU-accelerated)

| Component | Requirement |
|---|---|
| GPU | NVIDIA RTX 3060 12GB or equivalent |
| RAM | 16 GB or more |
| Storage | 10 GB free |
| CUDA | 12.x with cuBLAS and cuDNN |

With a capable GPU, speech-to-text runs faster than real-time and all three model stages (wake word, STT, TTS) can operate concurrently without contention.

### GPU Configuration

The `config.yaml` file configures each component's compute target independently:

```yaml
stt:
  device: "cuda"              # Set to "cpu" for CPU-only
  compute_type: "float16"     # Set to "int8" for lower VRAM usage

tts:
  device: "cpu"               # Piper is faster-than-realtime on CPU
```

The LLM runs entirely on a remote API and does not use local GPU resources.

## Configuration

### Main Configuration (`config.yaml`)

All user-tunable settings live in `config.yaml`. Key sections:

```yaml
jarvis:
  wake_word: "hey jarvis"
  wake_word_sensitivity: 0.7    # Lower = more sensitive (0.3-0.9)

stt:
  model: "large-v3"             # Whisper model variant
  device: "cuda"                # "cuda" or "cpu"
  compute_type: "float16"       # "float16", "int8", or "float32"
  silence_threshold_ms: 1500    # Milliseconds of silence to end recording
  language: null                # null = auto-detect, or set to "en", etc.

llm:
  provider: "hackclub"
  api_key_env: "HACKCLUB_API_KEY"
  model: "openrouter/free"
  base_url: "https://ai.hackclub.com/proxy/v1"
  max_tokens: 2048
  temperature: 0.7
  history_turns: 20             # Rolling conversation window

tts:
  engine: "piper"
  voice: "en_GB-southern_english_female-low"
  device: "cpu"
  speed: 1.0
```

### Local Overrides (`config.local.yaml`)

Create `config.local.yaml` for personal overrides. This file is git-ignored and takes precedence over `config.yaml` through deep merge:

```yaml
tts:
  voice: "en_US-amy-medium"
  speed: 1.1
stt:
  model: "large-v3-turbo"
```

### System Prompt (`prompts/system.md`)

The system prompt controls JARVIS's behavior, tone, tool selection priorities, and safety rules. Edit this file to customize how JARVIS responds and interacts with tools.

## Usage

### Voice Mode

1. Start JARVIS with `python main.py`
2. Wait for the tray icon to appear (grey = idle)
3. Say "hey jarvis" to wake the assistant
4. A chime confirms wake word detection
5. Speak your request; JARVIS will respond out loud

### Text Mode

```bat
python main.py --type
```

Type messages directly without a microphone. Useful for testing or environments where voice is impractical.

### Dry Run

```bat
python main.py --dry-run
```

Runs a single complete turn (STT synthesis, LLM call, TTS playback) without listening for wake word or requiring a microphone. Confirms the full pipeline is functional.

### Diagnostics

```bat
python -m core.diagnostics
```

Runs a health check across nine components: Python version, configuration, environment variables, pip packages, Piper voice model, Whisper model snapshot, audio devices, screen capture, and overlay initialization.

## Overlay States

The desktop overlay appears at the bottom center of the primary screen, above the taskbar. It is frameless, translucent, and click-through so it does not interfere with any work.

| State | Visual | Trigger |
|---|---|---|
| Idle | Invisible | Default state; overlay is hidden |
| Listening | Golden waveform bars with multi-harmonic sine modulation | Wake word detected |
| Thinking | Blue glowing hexagonal orb with concentric pulse rings and orbiting dots | Processing the request (STT or LLM active) |
| Responding | Golden particle swirl with flowing waveform outline and response text bubble | Speaking the reply through TTS |

State transitions include a 400ms fade animation. The overlay emits a particle burst on activation from the idle state. The tray icon changes color to match the current overlay state.

## Tool System

JARVIS has access to a registry of tools that the LLM can call during conversation. Tools are registered via a decorator in `tools/*.py` modules and are auto-discovered at startup.

### Available Tool Categories

- **Application control** -- launch apps, focus windows, list open windows
- **File operations** -- read, write, search, organize, compare, hash files
- **System information** -- CPU, RAM, battery, disk, GPU, processes, uptime
- **Media control** -- play/pause, next/previous track, volume, keyboard shortcuts
- **Web and network** -- search, fetch pages, ping, speed test, DNS lookup
- **Productivity** -- tasks/todos, notes, persistent memory, timers, calendar
- **Screen** -- screenshots, OCR, image comparison, ASCII art conversion
- **Code execution** -- arbitrary Python, shell commands, file diff
- **System management** -- services, scheduled tasks, startup programs, firewall

A complete tool reference is available in `docs/TOOLS.md`.

### Adding a Tool

Create a new Python file in the `tools/` directory:

```python
from tools import tool

@tool(
    name="my_tool",
    description="A brief description shown to the LLM.",
    parameters={
        "type": "object",
        "properties": {
            "arg_name": {
                "type": "string",
                "description": "Description of this argument.",
            },
        },
        "required": ["arg_name"],
    },
)
def my_tool(arg_name: str) -> str:
    # Implementation
    return f"Result: {arg_name}"
```

The tool is automatically registered on import. The return value is what the LLM sees as the tool result. Handle errors by returning error messages rather than raising exceptions -- the executor catches unhandled exceptions and reports them to the model.

### Safety Model

The system prompt instructs JARVIS to request confirmation before any destructive or irreversible action, including file deletion, drive formatting, system setting changes, or data transmission beyond simple GET requests. Read-only operations execute without confirmation.

## Conversation Logging

Every interaction is automatically logged to `data/conversations/YYYY-MM-DD.jsonl`. Each entry records the user's input, the assistant's full response, any tools called with their arguments and results, timing metrics, and the interaction mode (voice, text, or dry-run).

The conversation log is git-ignored and remains entirely on your machine. It can be loaded programmatically:

```python
from core.conversation_log import load_dataset

entries = load_dataset(days=7)
print(f"{len(entries)} turns in the last 7 days")
```

## Learning System

JARVIS maintains a persistent record of tool failures. When a tool call fails, the error is logged with a signature of the arguments and error type. If the same error pattern recurs, JARVIS receives a hint at runtime suggesting an alternative approach. On every turn, the system prompt includes a summary of recent failure patterns so the model can avoid repeating known mistakes.

View learned lessons:

```bat
python -m core.learning --show
python -m core.learning --tail 20
```

## Directory Structure

```
jarvis/
  main.py                     Entry point, voice loop, text mode
  config.yaml                 Main configuration
  requirements.txt            Python dependencies
  setup.bat                   One-command setup installer
  launch.bat                  Quick launcher
  .env.example                API key template
  .env                        API key (git-ignored, not in repo)
  .gitignore                  Git exclusions

  core/
    config.py                 Configuration loading with local override support
    llm.py                    LLM client with streaming, tool execution, history
    stt.py                    Whisper STT with VAD and microphone capture
    tts.py                    Piper TTS with sentence streaming
    wake_word.py              openWakeWord background listener
    executor.py               Tool dispatch, timing, and error handling
    learning.py               Failure memory and lesson injection
    conversation_log.py       Automatic conversation dataset builder
    diagnostics.py            Component health check

  ui/
    overlay.py                Bottom-center animated overlay widget
    tray.py                   System tray manager (pure PyQt6)

  tools/                      Tool modules (auto-discovered)
    apps.py                   Application launching and window focus
    screen.py                 Screenshots and OCR
    system.py                 Clipboard, notifications, volume
    python_exec.py            Arbitrary Python execution
    ...                       Additional tool modules

  prompts/
    system.md                 JARVIS system prompt

  tests/
    test_quick.py             Smoke tests
    test_tools_e2e.py         End-to-end tool invocation tests

  data/                       Auto-created at runtime (git-ignored)
    conversations/            Daily JSONL conversation logs

  logs/                       Auto-created at runtime (git-ignored)
    executor.log              Tool dispatch log
    learning/                 Failure memory records
    screenshots/              Captured screenshots
```

## Testing

Run the smoke test suite:

```bat
python tests/test_quick.py
```

This verifies configuration loading, learning store initialization, conversation logging, TTS text cleaning, tool registration, and overlay module initialization.

Individual component smoke tests:

```bat
python -m core.llm --smoke-test         # LLM connectivity and streaming
python -m core.stt --smoke-test          # STT round-trip (synthesizes via SAPI)
python -m core.tts --smoke-test          # TTS synthesis and playback
python -m core.wake_word --smoke-test    # Wake word detection (30s mic listen)
python -m core.executor --list           # List all registered tools
python -m core.diagnostics               # Full component health check
```

## Troubleshooting

### Wake word not detecting

Lower the `wake_word_sensitivity` value in `config.yaml`. The default is `0.7`; try `0.5` if it is not responding reliably. Test with `python -m core.wake_word --smoke-test`.

### Overlay not visible

Right-click the tray icon and select "Test Overlay" to cycle through all four states. If the overlay does not appear, run `python -m core.diagnostics` to verify Qt initialization.

### TTS not working

Verify the Piper voice model exists in `models/piper/`. The default voice is `en_GB-southern_english_female-low`. If the model file is missing, re-run `setup.bat` or download it manually from Hugging Face.

### STT running slowly

Confirm the Whisper model is loaded on GPU. In `config.yaml`, set `stt.device` to `"cuda"` and `stt.compute_type` to `"float16"`. Run `python -m core.stt --smoke-test` to verify transcription speed.

### LLM errors

Check that `HACKCLUB_API_KEY` is set in `.env`. Test connectivity with `python -m core.llm --smoke-test`. If the API key is invalid or the service is unavailable, the LLM client will raise an error that surfaces as a tray notification and spoken message.

### "No audio devices found"

Ensure a default microphone is configured in Windows Sound settings. Run `python -m core.diagnostics` to list available input and output devices.

## Contributing

See `CONTRIBUTING.md` for development setup, coding guidelines, and pull request process. Briefly:

1. Fork the repository
2. Create a feature branch
3. Add or modify tools in `tools/`
4. Run `python tests/test_quick.py` to verify
5. Submit a pull request

### Adding Tools

Tools are self-registering Python functions decorated with `@tool`. Place the file in `tools/` and it is automatically available on next startup. See the tool system section above for the decorator format.

## Security

### Execution Model

JARVIS can execute arbitrary Python code and shell commands through the `run_python` and `run_command` tools. This is the mechanism that enables PC control, but it also means JARVIS should only be run on personal machines in trusted environments.

### Protected Data

The following are excluded from the repository and remain on your machine:

- `.env` -- contains your API key
- `config.local.yaml` -- personal configuration overrides
- `data/` -- conversation logs and user data
- `logs/` -- audio recordings, executor logs, learning data
- `models/` -- downloaded model weights
- `.claude/` -- Claude Code session state

### Tool Safety

Destructive operations require explicit user confirmation before execution. The system prompt instructs JARVIS to state what it is about to do and wait for approval. Tool errors are caught and reported rather than causing the voice loop to crash.

See `SECURITY.md` for the complete security policy.

## License

MIT License. See `LICENSE` for details.
