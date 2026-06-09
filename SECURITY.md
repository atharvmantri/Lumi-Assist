# Security Policy

## Architecture Risks

JARVIS can **execute arbitrary Python code and shell commands** on your machine via the `run_python` and `run_command` tools. This is intentional — it's what lets JARVIS control your PC — but it also means:

- **Don't run JARVIS on a shared or production machine.** Only use it on your personal PC.
- **Don't expose JARVIS to untrusted input.** The wake word and mic are local, but the LLM runs via an external API. Your prompts and conversation history are sent to the LLM provider.
- **Keep your API key secret.** The `HACKCLUB_API_KEY` in `.env` should never be committed or shared.

## What We Protect

- `.env` is git-ignored — never commit API keys
- `config.local.yaml` is git-ignored — local overrides stay private
- `data/` is git-ignored — conversation logs are private
- `logs/` audio files are git-ignored — your voice data stays local

## Reporting a Vulnerability

If you find a security issue, please open an issue or contact the maintainer directly. We'll respond within 48 hours.

## Safe Defaults

- Destructive operations (deleting files, shutting down) require user confirmation
- Tool errors are caught and reported to the LLM — they don't crash the loop
- The overlay is click-through — it can't intercept your mouse
- No data is sent to external services except LLM API calls

## Dependencies

Run `pip audit` periodically to check for known vulnerabilities in dependencies.
