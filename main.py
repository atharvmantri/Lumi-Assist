"""Lumi — main entry point.

Wires the core modules into an always-on voice loop:

    wake-word  →  STT  →  LLM (streaming)  →  TTS (sentence streaming)

Architecture:
  - System tray runs in the main thread (via PyQt6)
  - Voice loop runs in a background thread
  - Tray icon changes color based on state
  - Windows toast notifications for wake word / errors
  - Taskbar progress indicator for long operations

Usage:
    python main.py                   # full voice loop + tray
    python main.py --dry-run         # one synthesized turn, no mic
    python main.py --type            # text input loop (no mic / no wake word)
    python main.py --no-tray         # voice loop without tray (terminal only)
"""
from __future__ import annotations

import argparse
import io
import os
import signal
import sys
import threading
import time
from datetime import datetime
from typing import Any

import numpy as np

# Force UTF-8 stdout on Windows
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)

from core.config import PROJECT_ROOT, load_config
from core import executor
from core.llm import LLMClient, LLMError
from core.stt import STT, write_wav
from core.tts import TTS
from core.wake_word import WakeWordDetector
from core.conversation_log import log_turn as _log_turn

# Tray module
try:
    from ui.tray import TrayState, set_state as _set_tray_state, shutdown as _shutdown_tray, run_tray
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False


POST_TTS_SETTLE_MS = 350
DUMP_TURNS = True


# ============================================================================
# Tray helpers (thread-safe)
# ============================================================================

def _tray(state: TrayState | None = None, text: str = "", show_toast: bool = False) -> None:
    """Push a state change to the tray. Thread-safe, no-op if tray not running."""
    if TRAY_AVAILABLE:
        _set_tray_state(state, text, show_toast)


# ============================================================================
# Taskbar progress (Windows native)
# ============================================================================

_taskbar_progress = None

def _init_taskbar():
    """Initialize Windows taskbar progress indicator."""
    global _taskbar_progress
    try:
        import comtypes.client as cc
        from comtypes import GUID
        # ITaskbarList3 interface for progress bar
        _taskbar_progress = cc.CreateObject(
            "{56FDF344-FD6D-11d0-958A-006097C9A090}",
            interface=GUID("{EA1AFB91-9E28-4B86-90E9-9E9F8A5EEFAF}")
        )
    except Exception:
        _taskbar_progress = None

def _set_taskbar_progress(value: float, state: str = "normal") -> None:
    """Set taskbar progress (0.0 to 1.0). State: 'normal', 'paused', 'error', 'indeterminate'."""
    if _taskbar_progress is None:
        return
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd:
            _taskbar_progress.SetProgressState(hwnd, {"normal": 0, "paused": 1, "error": 2, "indeterminate": 3}.get(state, 0))
            if state != "indeterminate":
                _taskbar_progress.SetProgressValue(hwnd, int(value * 100), 100)
    except Exception:
        pass


# ============================================================================
# Tool event logging
# ============================================================================

def _on_tool_event(event_type: str, payload: dict[str, Any]) -> None:
    if event_type == "call":
        args_str = ", ".join(f"{k}={v!r}" for k, v in (payload.get("args") or {}).items())
        if len(args_str) > 120:
            args_str = args_str[:120] + "..."
        print(f"\n  [tool→] {payload['name']}({args_str})")
    elif event_type == "result":
        result = str(payload.get("result", ""))
        short = result if len(result) < 200 else result[:200] + f"... ({len(result)-200} more)"
        short = short.replace("\n", "  ")
        print(f"  [←tool] {payload['name']}: {short}")


def build_pc_context() -> str:
    return f"Current time: {datetime.now().strftime('%A, %B %d %Y, %H:%M:%S')}"


def chime() -> None:
    try:
        import sounddevice as sd
        sr = 22050
        t = np.linspace(0, 0.10, int(sr * 0.10), endpoint=False)
        tone = (
            0.20 * np.sin(2 * np.pi * 760 * t)
            + 0.10 * np.sin(2 * np.pi * 1140 * t)
        ).astype(np.float32)
        n_fade = int(sr * 0.01)
        tone[:n_fade] *= np.linspace(0, 1, n_fade)
        tone[-n_fade:] *= np.linspace(1, 0, n_fade)
        sd.play(tone, sr)
        sd.wait()
    except Exception:
        pass


# ============================================================================
# Single turn
# ============================================================================

def run_turn(
    user_audio: np.ndarray,
    *,
    stt: STT,
    llm: LLMClient,
    tts: TTS,
    turn_id: int | None = None,
) -> dict[str, Any]:
    t_turn_start = time.perf_counter()

    if DUMP_TURNS and turn_id is not None:
        try:
            user_wav = PROJECT_ROOT / "logs" / f"turn_{turn_id:02d}_user.wav"
            write_wav(user_wav, user_audio)
        except Exception as e:
            print(f"  [warn] couldn't write user WAV: {e}")

    _tray(TrayState.LISTENING)
    _set_taskbar_progress(0.3, "indeterminate")
    t0 = time.perf_counter()
    user_text, info = stt.transcribe(user_audio)
    stt_elapsed = time.perf_counter() - t0
    _tray(TrayState.THINKING)
    print(f"  [stt {stt_elapsed:.2f}s, lang={info['language']}] you: {user_text!r}")

    if not user_text.strip():
        print("  [skip] empty transcription — ignoring turn")
        _tray(TrayState.IDLE)
        _set_taskbar_progress(0, "normal")
        return {"empty": True, "total_s": time.perf_counter() - t_turn_start}
    if len(user_text.split()) <= 1 and len(user_text) < 4:
        print(f"  [skip] transcript too short ({user_text!r}) — ignoring turn")
        _tray(TrayState.IDLE)
        _set_taskbar_progress(0, "normal")
        return {"empty": True, "total_s": time.perf_counter() - t_turn_start}

    _tray(TrayState.THINKING, "Thinking...")
    print("  [llm→tts streaming] lumi: ", end="", flush=True)

    full_reply_parts: list[str] = []
    tool_calls_log: list[dict[str, Any]] = []
    tool_schemas = executor.get_schemas()

    def _capture_tool_event(event_type: str, payload: dict[str, Any]) -> None:
        _on_tool_event(event_type, payload)
        if event_type == "call":
            tool_calls_log.append({"name": payload["name"], "args": payload.get("args", {})})
        elif event_type == "result":
            # Attach result to last tool call
            if tool_calls_log:
                tool_calls_log[-1]["result"] = str(payload.get("result", ""))[:500]

    def teed_stream():
        for tok in llm.stream(
            user_text,
            pc_context=build_pc_context(),
            tools=tool_schemas,
            on_tool_event=_capture_tool_event,
        ):
            sys.stdout.write(tok)
            sys.stdout.flush()
            full_reply_parts.append(tok)
            yield tok

    # Set RESPONDING BEFORE TTS starts so the overlay shows during speech
    _tray(TrayState.RESPONDING, "")
    try:
        timing = tts.speak_token_stream(teed_stream())
    except LLMError as e:
        print(f"\n  [llm FAILED] {e}")
        tts.speak("Sorry, I lost contact with my brain.")
        _tray(TrayState.ERROR, str(e)[:100], show_toast=True)
        _set_taskbar_progress(1, "error")
        return {"error": str(e), "total_s": time.perf_counter() - t_turn_start}

    print()
    # Update response text now that we have the full reply
    _tray(TrayState.RESPONDING, full_reply_parts[-1] if full_reply_parts else "")
    _set_taskbar_progress(0.8, "normal")

    # Build metrics
    metrics = {
        "stt_s": stt_elapsed,
        "llm_first_token_s": timing["first_token_s"],
        "tts_first_audio_s": timing["first_audio_s"],
        "tts_total_s": timing["total_s"],
        "audio_duration_s": timing["audio_duration_s"],
        "reply_chars": len(full_reply_parts),
        "total_s": time.perf_counter() - t_turn_start,
    }

    # Log conversation to dataset
    full_reply = "".join(full_reply_parts)
    try:
        _log_turn(
            user_text=user_text,
            response=full_reply,
            tools_called=tool_calls_log,
            metrics=metrics,
            mode="voice",
        )
    except Exception:
        pass  # logging is best-effort

    print(
        f"  [turn done] stt={metrics['stt_s']:.2f}s  "
        f"llm-first={metrics['llm_first_token_s']:.2f}s  "
        f"tts-first={metrics['tts_first_audio_s']:.2f}s  "
        f"total={metrics['total_s']:.2f}s"
    )
    _tray(TrayState.IDLE)
    _set_taskbar_progress(0, "normal")
    return metrics


# ============================================================================
# Voice loop (runs in background thread)
# ============================================================================

def voice_loop(stt: STT, llm: LLMClient, tts: TTS, stop_event: threading.Event) -> None:
    """Background-thread voice loop. Runs until stop_event is set."""
    det = WakeWordDetector(verbose=False)
    det.start()

    print()
    print("Lumi is listening. Say 'hey lumi' to wake. Ctrl+C to exit.")
    print()

    turn = 0
    while not stop_event.is_set():
        fired = det.wait(timeout=0.5)
        if not fired or stop_event.is_set():
            continue

        turn += 1
        print(f"\n--- turn {turn} ---")
        print(f"  [wake] score={det.last_score:.3f}")
        _tray(TrayState.LISTENING, "Wake word detected!", show_toast=True)

        det.pause()
        try:
            chime()
            audio = stt.record_until_silence(show_meter=True)
            if audio.size == 0:
                print("  [skip] no audio captured")
                continue
            run_turn(audio, stt=stt, llm=llm, tts=tts, turn_id=turn)
            time.sleep(POST_TTS_SETTLE_MS / 1000)
        finally:
            det.resume()

    det.stop()
    print("[voice-loop] stopped.")


# ============================================================================
# Text mode loop
# ============================================================================

def text_loop(stt: STT, llm: LLMClient, tts: TTS) -> None:
    print()
    print("Lumi (text mode). Type a message, blank line to exit.")
    print()
    tool_schemas = executor.get_schemas()
    turn = 0
    while True:
        try:
            user_text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_text:
            break
        turn += 1
        print(f"\n--- turn {turn} ---")
        print("  lumi: ", end="", flush=True)
        full_reply = []
        tool_calls_log = []

        def _text_tool_event(event_type: str, payload: dict[str, Any]) -> None:
            _on_tool_event(event_type, payload)
            if event_type == "call":
                tool_calls_log.append({"name": payload["name"], "args": payload.get("args", {})})
            elif event_type == "result":
                if tool_calls_log:
                    tool_calls_log[-1]["result"] = str(payload.get("result", ""))[:500]

        def _captured_stream():
            for tok in llm.stream(
                user_text,
                pc_context=build_pc_context(),
                tools=tool_schemas,
                on_tool_event=_text_tool_event,
            ):
                sys.stdout.write(tok)
                sys.stdout.flush()
                full_reply.append(tok)
                yield tok

        try:
            timing = tts.speak_token_stream(_captured_stream())
            print()
            print(
                f"  [turn done] llm-first={timing['first_token_s']:.2f}s  "
                f"tts-first={timing['first_audio_s']:.2f}s  total={timing['total_s']:.2f}s"
            )
            # Log conversation to dataset
            try:
                _log_turn(
                    user_text=user_text,
                    response="".join(full_reply),
                    tools_called=tool_calls_log,
                    metrics=timing,
                    mode="text",
                )
            except Exception:
                pass
        except LLMError as e:
            print(f"\n  [error] {e}")
    print("[main] stopped.")


# ============================================================================
# Dry run
# ============================================================================

def dry_run(stt: STT, llm: LLMClient, tts: TTS) -> int:
    fake_phrase = "Hello Lumi, what time is it?"
    print(f"[dry] synthesizing fake user utterance: {fake_phrase!r}")

    audio_22k = tts.synthesize_all(fake_phrase)
    try:
        from scipy.signal import resample_poly
        audio_16k = resample_poly(audio_22k, up=16000, down=tts.sample_rate).astype(np.float32)
    except ImportError:
        ratio = tts.sample_rate / 16000
        idx = (np.arange(int(audio_22k.size / ratio)) * ratio).astype(int)
        audio_16k = audio_22k[idx]

    # Dry run doesn't use tray/overlay — skip state changes
    original_tray_available = TRAY_AVAILABLE
    import main
    main.TRAY_AVAILABLE = False

    try:
        metrics = run_turn(audio_16k, stt=stt, llm=llm, tts=tts)
        if metrics.get("empty") or metrics.get("error"):
            print("[dry] FAILED")
            return 1
        print("[dry] OK")
        return 0
    finally:
        main.TRAY_AVAILABLE = original_tray_available


# ============================================================================
# Helpers
# ============================================================================

def _print_passthrough(token_iter):
    for tok in token_iter:
        sys.stdout.write(tok)
        sys.stdout.flush()
        yield tok


def init_all(verbose: bool = True) -> tuple[STT, LLMClient, TTS]:
    cfg = load_config()
    t0 = time.perf_counter()
    if verbose:
        print("[main] loading models...")
    stt = STT(cfg)
    llm = LLMClient(cfg)
    tts = TTS(cfg)
    if verbose:
        print(f"[main] all modules ready in {time.perf_counter() - t0:.1f}s")
    return stt, llm, tts


# ============================================================================
# Main
# ============================================================================

def _run_with_tray(cfg: dict[str, Any], stt: STT, llm: LLMClient, tts: TTS) -> None:
    """Run tray in main thread, voice loop in background thread."""
    stop_event = threading.Event()

    # Initialize taskbar progress
    _init_taskbar()

    # Start voice loop in background
    voice_thread = threading.Thread(
        target=voice_loop,
        args=(stt, llm, tts, stop_event),
        name="lumi-voice-loop",
        daemon=True,
    )
    voice_thread.start()

    # Tray runs in main thread
    try:
        run_tray()
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        voice_thread.join(timeout=3.0)
        _shutdown_tray()
        print("[main] quit.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Lumi — local voice assistant")
    parser.add_argument("--dry-run", action="store_true", help="One synthetic turn, no mic, no wake word")
    parser.add_argument("--type", action="store_true", help="Text input loop (no mic / no wake word)")
    parser.add_argument("--no-tray", action="store_true", help="Disable system tray (terminal only)")
    args = parser.parse_args()

    show_tray = TRAY_AVAILABLE and not args.no_tray
    cfg = load_config()
    stt, llm, tts = init_all()

    if args.dry_run:
        raise SystemExit(dry_run(stt, llm, tts))

    if args.type:
        text_loop(stt, llm, tts)
        return

    # Full voice loop: tray in main thread, voice in background thread
    if show_tray:
        _run_with_tray(cfg, stt, llm, tts)
    else:
        # No tray: run voice loop directly in main thread
        voice_loop(stt, llm, tts, stop_event=threading.Event())


if __name__ == "__main__":
    main()

