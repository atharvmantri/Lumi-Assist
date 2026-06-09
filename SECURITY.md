# Security Policy

## Architecture Risks

Lumi can **execute arbitrary Python code and shell commands** on your machine via the `run_python` and `run_command` tools. This is what enables PC control, but it also means:

- **Only run Lumi on your personal PC.** Do not install it on shared, production, or multi-user machines.
- **The LLM runs via an external API.** Your prompts and conversation history are sent to the LLM provider (HackClub proxy). Do not paste sensitive information into voice commands.
- **Keep your API key secret.** The `HACKCLUB_API_KEY` in `.env` should never be committed, shared, or exposed in screenshots.

## What Stays Private

The following are git-ignored and never leave your machine:

| Path | What it contains |
|---|---|
| `.env` | Your API key |
| `config.local.yaml` | Personal configuration overrides |
| `data/` | Conversation logs and user data |
| `logs/` | Audio recordings, executor logs, failure memory |
| `.claude/` | Development session state |

## Reporting a Vulnerability

Open an issue or contact the maintainer. We will respond within 48 hours.

## Safe Defaults

- Destructive operations (file deletion, system shutdown, setting changes) require explicit user confirmation before executing
- Tool errors are caught and reported to the LLM rather than crashing the voice loop
- The overlay is click-through — it cannot intercept mouse events or keyboard input
- No data is sent to external services except LLM API calls
- The installer downloads models only from Hugging Face (trusted source)

## Supply Chain

All dependencies are installed from PyPI. The installer does not execute unsigned scripts or download executables. Model weights are downloaded from Hugging Face's official `rhassys/piper-voices` and `Systran/faster-whisper` repositories.

## Auditing

Run `pip audit` periodically to check for known vulnerabilities in installed dependencies.
