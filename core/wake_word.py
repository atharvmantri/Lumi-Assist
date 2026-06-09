"""Wake word detection for Lumi — openWakeWord, CPU only.

Design:
  - Runs continuously on a dedicated background thread, never touching the GPU.
  - Reads 80-ms blocks of 16 kHz mono audio from the default mic.
  - On each block, openWakeWord returns scores in [0, 1] for the loaded models.
  - When `hey_lumi` crosses the configured sensitivity threshold, fire callback
    (or set a threading.Event) — caller is responsible for any cooldown / locking
    out re-triggers during the response cycle.

Two usage modes:

    # Event-based (clean for main.py orchestration):
    det = WakeWordDetector()
    det.start()
    det.wait()           # blocks until next trigger; clears event
    det.pause()          # stop detecting until det.resume()

    # Callback-based:
    det = WakeWordDetector(on_trigger=lambda score: print(f'WAKE! {score:.3f}'))
    det.start()
    ...
    det.stop()

Smoke test:
  python -m core.wake_word --smoke-test          # listen on mic, print each trigger
  python -m core.wake_word --file PATH.wav       # score a WAV (does not require mic)
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

try:
    from openwakeword.model import Model as OWWModel
except ImportError as e:  # pragma: no cover
    raise SystemExit(
        "openwakeword not installed. Run: pip install -r requirements.txt"
    ) from e

from core.config import load_config

# openWakeWord works on 16 kHz, 16-bit, mono — same as Whisper, so we share the rate.
SAMPLE_RATE = 16000
BLOCK_MS = 80                                  # openWakeWord's native block size
BLOCK_SAMPLES = SAMPLE_RATE * BLOCK_MS // 1000   # = 1280 samples

# Maps our config wake_word string to the openWakeWord pretrained model key.
# openWakeWord ships: hey_jarvis, alexa, hey_mycroft, hey_rhasspy.
# Custom wake words need their own .onnx — for branded wake words we map
# to the closest available model and accept the tradeoff.
_WAKE_WORD_TO_MODEL = {
    "hey lumi": "hey_jarvis",       # closest match — user says "hey lumi", model detects "hey jarvis" pattern
    "hey_lumi": "hey_jarvis",
    "hey jarvis": "hey_jarvis",
    "hey_jarvis": "hey_jarvis",
    "alexa": "alexa",
    "hey mycroft": "hey_mycroft",
    "hey rhasspy": "hey_rhasspy",
}


class WakeWordDetector:
    """Background mic listener that fires when the wake word is heard."""

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        *,
        on_trigger: Callable[[float], None] | None = None,
        verbose: bool = True,
    ) -> None:
        cfg = config or load_config()
        ww_cfg = cfg["lumi"]
        self.phrase: str = ww_cfg["wake_word"].strip().lower()
        self.sensitivity: float = float(ww_cfg["wake_word_sensitivity"])
        model_key = _WAKE_WORD_TO_MODEL.get(self.phrase)
        if model_key is None:
            raise ValueError(
                f"wake_word={self.phrase!r} not in supported set: "
                f"{sorted(_WAKE_WORD_TO_MODEL)}. Custom models would need their own .onnx."
            )
        self.model_key = model_key

        if verbose:
            print(f"[ww] loading openWakeWord model for {model_key!r} (threshold={self.sensitivity})...")
        t0 = time.perf_counter()
        self.model = OWWModel(
            wakeword_models=[model_key],
            inference_framework="onnx",  # tflite is also available but onnx is consistent with our stack
        )
        if verbose:
            print(f"[ww] model loaded in {time.perf_counter() - t0:.2f}s")

        self._on_trigger = on_trigger or (lambda score: None)
        self._trigger_event = threading.Event()
        self._last_score = 0.0
        self._listener_thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._paused = threading.Event()

        # Re-trigger guard: ignore further triggers for this many seconds after one fires.
        self.cooldown_s: float = 1.0

    # ---- event API -------------------------------------------------------

    @property
    def last_score(self) -> float:
        return self._last_score

    def is_triggered(self) -> bool:
        return self._trigger_event.is_set()

    def clear(self) -> None:
        self._trigger_event.clear()

    def wait(self, timeout: float | None = None) -> bool:
        """Block until the next trigger. Returns True if fired, False on timeout."""
        fired = self._trigger_event.wait(timeout=timeout)
        if fired:
            self._trigger_event.clear()
        return fired

    def pause(self) -> None:
        """Temporarily stop emitting triggers (mic still reads, just suppressed).
        Use during Lumi's own response cycle so its TTS doesn't self-trigger.
        """
        self._paused.set()

    def resume(self) -> None:
        # Drop any buffered state so the post-pause window starts clean
        self.model.reset()
        self._paused.clear()

    # ---- listener thread -------------------------------------------------

    def start(self) -> None:
        if self._listener_thread is not None and self._listener_thread.is_alive():
            return
        self._stop.clear()
        self._listener_thread = threading.Thread(
            target=self._run, name="wake-word-listener", daemon=True
        )
        self._listener_thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._listener_thread is not None:
            self._listener_thread.join(timeout=2.0)

    def _run(self) -> None:
        try:
            import sounddevice as sd
        except ImportError:
            print("[ww] sounddevice missing; listener thread exiting", file=sys.stderr)
            return

        last_trigger_at = 0.0
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=BLOCK_SAMPLES,
        ) as stream:
            while not self._stop.is_set():
                block, _overflow = stream.read(BLOCK_SAMPLES)
                if self._paused.is_set():
                    continue
                audio_i16 = block[:, 0] if block.ndim > 1 else block

                scores = self.model.predict(audio_i16)
                score = float(scores.get(self.model_key, 0.0))
                self._last_score = score

                if score >= self.sensitivity:
                    now = time.monotonic()
                    if now - last_trigger_at < self.cooldown_s:
                        continue
                    last_trigger_at = now
                    self._trigger_event.set()
                    try:
                        self._on_trigger(score)
                    except Exception as e:  # noqa: BLE001
                        print(f"[ww] on_trigger callback raised: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Scoring a WAV file (no mic required)
# ---------------------------------------------------------------------------

def score_wav(wav_path: str | Path, *, verbose: bool = True) -> tuple[float, list[float]]:
    """Run a WAV through the wake word model and return (peak_score, all_scores).

    Useful for testing without a mic, or for batch-evaluating accuracy on known
    positive/negative clips. WAV must be 16 kHz mono 16-bit PCM.
    """
    import wave as _wave
    cfg = load_config()
    phrase = cfg["lumi"]["wake_word"].strip().lower()
    model_key = _WAKE_WORD_TO_MODEL[phrase]

    with _wave.open(str(wav_path), "rb") as wf:
        if wf.getnchannels() != 1 or wf.getframerate() != SAMPLE_RATE or wf.getsampwidth() != 2:
            raise ValueError(
                f"WAV must be 16kHz mono 16-bit PCM (got "
                f"{wf.getframerate()}Hz/{wf.getnchannels()}ch/{wf.getsampwidth()*8}-bit)"
            )
        raw = wf.readframes(wf.getnframes())
    samples = np.frombuffer(raw, dtype=np.int16)

    if verbose:
        print(f"[ww] scoring {wav_path} ({samples.size / SAMPLE_RATE:.2f}s of audio)")
    model = OWWModel(wakeword_models=[model_key], inference_framework="onnx")
    all_scores: list[float] = []
    for start in range(0, samples.size - BLOCK_SAMPLES + 1, BLOCK_SAMPLES):
        block = samples[start:start + BLOCK_SAMPLES]
        s = float(model.predict(block).get(model_key, 0.0))
        all_scores.append(s)
    peak = max(all_scores) if all_scores else 0.0
    if verbose:
        print(f"[ww] peak score: {peak:.3f}  (avg {sum(all_scores)/max(1,len(all_scores)):.3f})")
    return peak, all_scores


# ---------------------------------------------------------------------------
# CLI / smoke test
# ---------------------------------------------------------------------------

def _live_listen(seconds: float) -> int:
    """Run the listener for `seconds` and print each trigger + a heartbeat."""
    triggers: list[tuple[float, float]] = []   # (elapsed_s, score)

    def on_trigger(score: float) -> None:
        elapsed = time.monotonic() - t0
        triggers.append((elapsed, score))
        print(f"  [{elapsed:5.1f}s] *** WAKE *** score={score:.3f}")

    det = WakeWordDetector(on_trigger=on_trigger)
    det.start()
    t0 = time.monotonic()
    print(f"[smoke] listening for {seconds:.0f}s — say 'hey lumi' a few times")
    print(f"[smoke] sensitivity threshold = {det.sensitivity}")
    print(f"[smoke] (heartbeat every 2s shows last block's score)")
    next_beat = t0 + 2.0
    try:
        while time.monotonic() - t0 < seconds:
            now = time.monotonic()
            if now >= next_beat:
                next_beat = now + 2.0
                print(f"  [{now - t0:5.1f}s] heartbeat   score={det.last_score:.3f}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        det.stop()
    print()
    print(f"[smoke] total triggers: {len(triggers)}")
    if not triggers:
        print("[smoke] NO TRIGGERS — try lowering wake_word_sensitivity in config.yaml")
        return 1
    print("[smoke] OK")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Lumi wake word (openWakeWord)")
    parser.add_argument("--smoke-test", action="store_true", help="Listen on mic for 30s and print triggers")
    parser.add_argument("--seconds", type=float, default=30.0, help="Listen duration for --smoke-test (default 30)")
    parser.add_argument("--file", metavar="WAV", help="Score a 16kHz mono WAV instead of listening on mic")
    args = parser.parse_args()

    if args.file:
        peak, scores = score_wav(args.file)
        # Exit 0 if peak crossed the configured threshold, else 1.
        cfg = load_config()
        thresh = float(cfg["lumi"]["wake_word_sensitivity"])
        triggered = peak >= thresh
        print(f"[result] threshold={thresh}  peak={peak:.3f}  triggered={triggered}")
        raise SystemExit(0 if triggered else 1)

    if args.smoke_test:
        raise SystemExit(_live_listen(args.seconds))

    parser.print_help()


if __name__ == "__main__":
    main()
