# Contributing to Lumi

Thanks for your interest! Here's how to get started.

## Setup

```bat
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
:: edit .env and add your API key
```

## Running Tests

```bat
python tests/test_quick.py          # Smoke tests
python -m core.diagnostics           # Health check
python -m core.llm --smoke-test      # LLM connectivity
python -m core.stt --smoke-test      # STT round-trip
python -m core.tts --smoke-test      # TTS playback
python -m core.wake_word --smoke-test  # Wake word detection
```

## Adding a Tool

Tools live in `tools/`. Each tool is a function decorated with `@tool`:

```python
from tools import tool

@tool(
    name="my_tool",
    description="What this tool does. Shown to the LLM.",
    parameters={
        "type": "object",
        "properties": {
            "arg_name": {"type": "string", "description": "What this arg does"},
        },
        "required": ["arg_name"],
    },
)
def my_tool(arg_name: str) -> str:
    # Do something
    return f"Result: {arg_name}"
```

The tool is auto-registered — just add the file to `tools/` and it'll be picked up.

**Guidelines:**
- Return a `str` — this is what the LLM sees
- Handle errors gracefully — return error messages, don't raise
- Keep responses concise — the LLM has limited context
- One responsibility per tool — don't combine unrelated functionality

## Adding a Module

If you're adding a new core module under `core/`:
- Add a smoke test (`python -m core.your_module --smoke-test`)
- Document usage in the module docstring
- Update `CLAUDE.md` with the new module

## Pull Requests

1. Fork the repo
2. Create a branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run tests (`python tests/test_quick.py`)
5. Push and open a PR

## Code Style

- Match the existing code's style — it's consistent
- Docstrings on every public function
- Type hints on every function
- Error handling — never let exceptions bubble up to the voice loop
- No f-strings in tool args that get JSON-encoded (use `.format()` or `%`)

## Need Help?

Check the [README](README.md) for setup instructions and architecture overview.
