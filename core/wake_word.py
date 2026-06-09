"""Wake word detection for Lumi using livekit-wakeword.

Uses livekit-wakeword library (based on openWakeWord but with better Conv-Attention classifier)
for reliable detection of: "hey lumi", "ok lumi", "yo lumi", "lumi"

Fallback to energy-based detection + quick transcription if livekit-wakeword is not installed.
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

# Check if livekit-wakeword is available
try:
    from livekit.wakeword import WakeWordModel
    HAS_LIVEKIT_WAKEWORD = True
except ImportError:
    HAS_LIVEKIT_WAKEWORD = False

# Default model path (will be updated when custom model is trained)
MODEL_DIR = Path(__file__).resolve().parent.parent / "data" / "wakeword_models"
DEFAULT_MODEL = MODEL_DIR / "hey_lumi.onnx"

# Fallback: energy-based detection parameters
SAMPLE_RATE = 16000
ENERGY_RATIO_THRESHOLD = 2.5


class WakeWordDetector:
    """Background mic listener for wake word detection.

    Uses livekit-wakeword if available (best accuracy),
    otherwise falls back to energy detection + quick transcription.
    """

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        *,
        on_trigger: Callable[[float], None] | None = None,
        verbose: bool = True,
    ) -> None:
        cfg = config or {}
        lumi_cfg = cfg.get("lumi", cfg.get("jarvis", {}))
        self.sensitivity: float = float(lumi_cfg.get("wake_word_sensitivity", 0.5))
        # Map sensitivity to threshold: low sensitivity = high threshold
        self.threshold = 1.0 - (self.sensitivity * 0.8)  # 0.2 to 1.0

        self._on_trigger = on_trigger or (lambda score: None)
        self._trigger_event = threading.Event()
        self._last_score = 0.0
        self._listener_thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._paused = threading.Event()
        self.cooldown_s: float = 1.0

        # Initialize wake word model
        self._model = None
        self._use_fallback = False

        if HAS_LIVEKIT_WAKEWORD:
            model_path = DEFAULT_MODEL if DEFAULT_MODEL.exists() else None
            if model_path:
                try:
                    if verbose:
                        print(f"[ww] Loading custom wake word model: {model_path}")
                    self._model = WakeWordModel(models=[str(model_path)])
                    if verbose:
                        print(f"[ww] Custom model loaded successfully")
                except Exception as e:
                    if verbose:
                        print(f"[ww] Failed to load custom model: {e}")
                        print(f"[ww] Falling back to energy-based detection")
                    self._use_fallback = True
            else:
                if verbose:
                    print(f"[ww] No custom model found at {DEFAULT_MODEL}")
                    print(f"[ww] Falling back to energy-based detection")
                    print(f"[ww] To train a custom model:")
                    print(f"[ww]   1. Run: python record_wake_samples.py")
                    print(f"[ww]   2. Run: pip install livekit-wakeword[train,eval,export]")
                    print(f"[ww]   3. Run: livekit-wakeword run configs/lumi.yaml")
                self._use_fallback = True
        else:
            if verbose:
                print(f"[ww] livekit-wakeword not installed")
                print(f"[ww] Using energy-based detection")
                print(f"[ww] For better accuracy, install livekit-wakeword:")
                print(f"[ww]   pip install livekit-wakeword[listener]")
            self._use_fallback = True

        if verbose:
            print(f"[ww] Sensitivity: {self.sensitivity} (threshold: {self.threshold:.2f})")

    @property
    def last_score(self) -> float:
        return self._last_score

    def is_triggered(self) -> bool:
        return self._trigger_event.is_set()

    def clear(self) -> None:
        self._trigger_event.clear()

    def wait(self, timeout: float | None = None) -> bool:
        fired = self._trigger_event.wait(timeout=timeout)
        if fired:
            self._trigger_event.clear()
        return fired

    def pause(self) -> None:
        self._paused.set()

    def resume(self) -> None:
        self._paused.clear()

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
            print("[ww] sounddevice missing; listener thread exiting")
            return

        if self._use_fallback:
            self._run_fallback(sd)
        else:
            self._run_livekit(sd)

    def _run_livekit(self, sd) -> None:
        """Run using livekit-wakeword model."""
        last_trigger_at = 0.0
        block_ms = 80
        block_samples = int(SAMPLE_RATE * block_ms / 1000)

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=block_samples,
        ) as stream:
            while not self._stop.is_set():
                if self._paused.is_set():
                    time.sleep(0.1)
                    continue

                block, _overflow = stream.read(block_samples)
                audio = block[:, 0] if block.ndim > 1 else block

                scores = self._model.predict(audio)

                # Check all wake word variants
                max_score = 0.0
                for key, score in scores.items():
                    if score > max_score:
                        max_score = score

                self._last_score = max_score

                if max_score > self.threshold:
                    now = time.monotonic()
                    if now - last_trigger_at >= self.cooldown_s:
                        last_trigger_at = now
                        self._trigger_event.set()
                        try:
                            self._on_trigger(max_score)
                        except Exception:
                            pass

    def _run_fallback(self, sd) -> None:
        """Fallback: energy-based detection + quick transcription."""
        last_trigger_at = 0.0
        energy_buffer = []
        buffer_size = 100
        speech_frames = []
        is_speaking = False
        speech_start_time = 0

        block_ms = 50
        block_samples = int(SAMPLE_RATE * block_ms / 1000)

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=block_samples,
        ) as stream:
            while not self._stop.is_set():
                if self._paused.is_set():
                    if speech_frames:
                        self._check_phrase(speech_frames, last_trigger_at)
                        speech_frames = []
                        is_speaking = False
                    time.sleep(0.1)
                    continue

                block, _overflow = stream.read(block_samples)
                audio = block[:, 0] if block.ndim > 1 else block
                frame_energy = float(np.sqrt(np.mean(audio ** 2)))

                energy_buffer.append(frame_energy)
                if len(energy_buffer) > buffer_size:
                    energy_buffer.pop(0)

                if len(energy_buffer) > 10:
                    avg_energy = np.mean(energy_buffer[:-1])
                else:
                    avg_energy = frame_energy

                if avg_energy < 0.001:
                    avg_energy = 0.001

                energy_ratio = frame_energy / avg_energy
                self._last_score = energy_ratio

                if energy_ratio > self.energy_threshold and not is_speaking:
                    is_speaking = True
                    speech_start_time = time.monotonic()
                    speech_frames = [audio.copy()]
                elif is_speaking:
                    speech_frames.append(audio.copy())

                    if energy_ratio < self.energy_threshold * 0.5:
                        self._check_phrase(speech_frames, last_trigger_at)
                        speech_frames = []
                        is_speaking = False
                    elif time.monotonic() - speech_start_time > 3.0:
                        self._check_phrase(speech_frames, last_trigger_at)
                        speech_frames = []
                        is_speaking = False

    def _check_phrase(self, frames: list, last_trigger_at: float) -> None:
        """Fallback: quick transcription to verify wake word."""
        if not frames:
            return

        audio = np.concatenate(frames)
        duration = len(audio) / SAMPLE_RATE
        if duration < 0.5 or duration > 6.0:
            return

        now = time.monotonic()
        if now - last_trigger_at < self.cooldown_s:
            return

        # Try quick transcription
        try:
            from faster_whisper import WhisperModel
            model_path = Path(__file__).resolve().parent.parent / "models" / "whisper"
            model_path.mkdir(parents=True, exist_ok=True)
            model = WhisperModel(
                "tiny",
                device="cpu",
                compute_type="int8",
                download_root=str(model_path),
            )
            segments, _ = model.transcribe(audio, beam_size=1, language="en", vad_filter=True)
            text = "".join(seg.text for seg in segments).strip().lower()

            # Check for wake word variants
            wake_phrases = ["lumi", "hey lumi", "ok lumi", "yo lumi", "hey computer", "computer"]
            if any(phrase in text for phrase in wake_phrases):
                match_count = sum(1 for p in wake_phrases if p in text)
                score = min(1.0, match_count * 0.3 + 0.4)
                now = time.monotonic()
                if now - last_trigger_at >= self.cooldown_s:
                    self._last_score = score
                    self._trigger_event.set()
                    try:
                        self._on_trigger(score)
                    except Exception:
                        pass
        except Exception:
            pass  # Silently ignore errors
