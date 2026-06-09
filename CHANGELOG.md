# Changelog

All notable changes to Lumi.

## [0.3.0] — 2026-06-08 (Improvement Session)

### New Tools (33 added)
- **System info:** `get_system_info`, `get_battery`, `get_cpu_usage`, `get_processes`
- **Media control:** `media_play_pause`, `media_next`, `media_previous`, `volume_up`, `volume_down`, `mute`, `keyboard_type`, `keyboard_press`
- **Mouse:** `mouse_click`, `mouse_move`, `get_mouse_position`, `scroll`
- **Tasks/todos:** `add_task`, `complete_task`, `list_tasks`, `delete_task`
- **Notes:** `add_note`, `list_notes`, `read_note`, `delete_note`
- **Memory:** `remember`, `recall`, `forget`, `list_memories`
- **Timers:** `set_timer`, `cancel_timer`, `list_timers`
- **Calculator:** `calculate` (safe math evaluator), `convert_units`
- **Briefing:** `daily_briefing`
- **Capabilities:** `list_capabilities`
- **Conversations:** `search_conversations`, `conversation_stats`, `conversation_summary`, `cleanup_conversations`, `export_conversations_html`
- **Network:** `get_network_info`, `ping`, `internet_speed_test`
- **File search:** `search_files` (recursive)
- **Voice:** `speak` (proactive output)
- **Diagnostics:** `self_test`
- **Weather:** `get_weather`, `get_time`

### Overlay Improvements
- Size increased to 600x220 (was 400x200)
- 3-layer particle glow (outer glow → mid → bright core)
- Gaussian envelope on waveform bars
- Multi-harmonic sine for organic motion
- Concentric pulse rings in thinking state
- Orbiting dots around thinking orb
- Activation burst effect (40 particles on wake)
- Golden flash on activation
- Transition alpha for smooth state morphing
- Tray icons upgraded to 48x48 with circular mic design
- Tray menu: status label + "Test Overlay" cycle

### Module Improvements
- **core/tts.py:** Markdown stripping before TTS synthesis
- **core/config.py:** config.local.yaml deep-merge overrides
- **core/conversation_log.py:** New — every conversation logged to JSONL
- **core/diagnostics.py:** New — 9-component health check
- **ui/tray.py:** Status label in menu, test overlay cycle
- **main.py:** Conversation logging, tool call tracking, metrics ordering fix
- **prompts/system.md:** Updated with all 75 tools, memory/notes/tasks section

### Infrastructure
- `setup.bat` — 8-step setup with diagnostics
- `launch.bat` — one-click launch
- `tests/test_quick.py` — 6 smoke tests
- `VERSION.py`, `.env.example`, `.gitignore`, `.gitattributes`
- `CLAUDE.md`, `MEMORY.md` — session context
- `README.md` — fully updated

### Bug Fixes
- `main.py`: metrics dict referenced before definition — fixed ordering
- `setup.bat`: `/dev/null` → `nul` (Windows fix)
- `tools/file_search.py`: syntax error in list comprehension — fixed
- Tool name collision: removed duplicate read_file/write_file/list_dir from file_search.py

### Stats
- 50 Python files, all compile cleanly
- 75 tools across 27 modules
- 16 new files created
- 6/6 tests pass

## [0.2.0] — 2026-06-08 (Session Start)

- System tray + bottom-center animated overlay (pure PyQt6)
- 4 overlay states: invisible, listening waveform, thinking orb, responding particles
- Conversation logging (dataset builder)
- Config local overrides (config.local.yaml)
- setup.bat for one-command fresh install
- Diagnostics module

## [0.1.0] — 2026-06-07

- Initial project scaffold
- LLM client (HackClub / Nemotron)
- STT (faster-whisper)
- TTS (Piper)
- Wake word (openWakeWord)
- Tool layer + executor
- Learning from failures
