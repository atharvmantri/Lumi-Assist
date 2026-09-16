"""Wake-word detection for Lumi.

Preferred path: a trained livekit-wakeword ONNX model when present.
Fallback path: low-cost energy gating followed by a tiny faster-whisper
transcription. The fallback is intentionally available on a fresh install so
reviewers do not need to train a custom model before testing Lumi.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

try:
    from livekit.wakeword import WakeWordModel
    HAS_LIVEKIT_WAKEWORD = True
except ImportError:
    WakeWordModel = None  # type: ignore[assignment]
    HAS_LIVEKIT_WAKEWORD = False

MODEL_DIR = Path(__file__).resolve().parent.parent / "data" / "wakeword_models"
DEFAULT_MODEL = MODEL_DIR / "hey_lumi.onnx"

SAMPLE_RATE = 16000
ENERGY_RATIO_THRESHOLD = 2.5


class WakeWordDetector:
    """Background microphone listener for Lumi's wake phrase."""

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        *,
        on_trigger: Callable[[float], None] | None = None,
        verbose: bool = True,
    ) -> None:
        cfg = config or {}
        lumi_cfg = cfg.get("lumi", cfg.get("jarvis", {}))
        self.wake_word = str(lumi_cfg.get("wake_word", "hey lumi")).strip().lower()
        self.sensitivity = float(lumi_cfg.get("wake_word_sensitivity", 0.5))
        self.threshold = 1.0 - (self.sensitivity * 0.8)
        self.energy_threshold = ENERGY_RATIO_THRESHOLD

        self._on_trigger = on_trigger or (lambda score: None)
        self._trigger_event = threading.Event()
        self._last_score = 0.0
        self._last_trigger_at = 0.0
        self._listener_thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._paused = threading.Event()
        self.cooldown_s = 1.0

        self._model = None
        self._fallback_model = None
        self._use_fallback = False

        if HAS_LIVEKIT_WAKEWORD and DEFAULT_MODEL.exists():
            try:
                if verbose:
                    print(f"[ww] loading custom wake-word model: {DEFAULT_MODEL}")
                self._model = WakeWordModel(models=[str(DEFAULT_MODEL)])
                if verbose:
                    print("[ww] custom wake-word model ready")
            except Exception as exc:  # noqa: BLE001
                if verbose:
                    print(f"[ww] custom model failed ({exc}); using fallback")
                self._use_fallback = True
        else:
            self._use_fallback = True
            if verbose:
                if not HAS_LIVEKIT_WAKEWORD:
                    print("[ww] livekit-wakeword not installed; using fallback")
                else:
                    print(f"[ww] no custom model at {DEFAULT_MODEL}; using fallback")

        if verbose:
            mode = "fallback whisper" if self._use_fallback else "custom model"
            print(
                f"[ww] wake='{self.wake_word}', sensitivity={self.sensitivity:.2f}, "
                f"mode={mode}"
            )

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
            target=self._run,
            name="wake-word-listener",
            daemon=True,
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

        try:
            if self._use_fallback:
                self._run_fallback(sd)
            else:
                self._run_livekit(sd)
        except Exception as exc:  # noqa: BLE001
            # A background-thread exception used to disappear silently and make
            # Lumi look like it was listening when the listener had died.
            print(f"[ww] listener stopped: {type(exc).__name__}: {exc}")

    def _trigger(self, score: float) -> None:
        now = time.monotonic()
        if now - self._last_trigger_at < self.cooldown_s:
            return
        self._last_trigger_at = now
        self._last_score = float(score)
        self._trigger_event.set()
        try:
            self._on_trigger(float(score))
        except Exception:
            pass

    def _run_livekit(self, sd) -> None:
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
                max_score = max((float(score) for score in scores.values()), default=0.0)
                self._last_score = max_score
                if max_score > self.threshold:
                    self._trigger(max_score)

    def _run_fallback(self, sd) -> None:
        """Energy-gate speech, then verify the phrase using tiny Whisper."""
        energy_buffer: list[float] = []
        buffer_size = 100
        speech_frames: list[np.ndarray] = []
        is_speaking = False
        speech_start_time = 0.0

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
                        self._check_phrase(speech_frames)
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

                avg_energy = (
                    float(np.mean(energy_buffer[:-1]))
                    if len(energy_buffer) > 10
                    else frame_energy
                )
                avg_energy = max(avg_energy, 0.001)
                energy_ratio = frame_energy / avg_energy
                self._last_score = energy_ratio

                if energy_ratio > self.energy_threshold and not is_speaking:
                    is_speaking = True
                    speech_start_time = time.monotonic()
                    speech_frames = [audio.copy()]
                    continue

                if not is_speaking:
                    continue

                speech_frames.append(audio.copy())
                ended_by_silence = energy_ratio < self.energy_threshold * 0.5
                timed_out = time.monotonic() - speech_start_time > 3.0
                if ended_by_silence or timed_out:
                    self._check_phrase(speech_frames)
                    speech_frames = []
                    is_speaking = False

    def _get_fallback_model(self):
        if self._fallback_model is None:
            from faster_whisper import WhisperModel

            model_dir = Path(__file__).resolve().parent.parent / "models" / "whisper"
            model_dir.mkdir(parents=True, exist_ok=True)
            self._fallback_model = WhisperModel(
                "tiny",
                device="cpu",
                compute_type="int8",
                download_root=str(model_dir),
            )
        return self._fallback_model

    def _check_phrase(self, frames: list[np.ndarray]) -> None:
        if not frames:
            return

        audio = np.concatenate(frames)
        duration = len(audio) / SAMPLE_RATE
        if duration < 0.35 or duration > 6.0:
            return
        if time.monotonic() - self._last_trigger_at < self.cooldown_s:
            return

        try:
            model = self._get_fallback_model()
            segments, _ = model.transcribe(
                audio,
                beam_size=1,
                language="en",
                vad_filter=True,
            )
            text = "".join(segment.text for segment in segments).strip().lower()

            wake_phrases = {
                self.wake_word,
                "lumi",
                "hey lumi",
                "ok lumi",
                "okay lumi",
                "yo lumi",
                "hey computer",
            }
            matches = [phrase for phrase in wake_phrases if phrase and phrase in text]
            if matches:
                score = min(1.0, 0.55 + 0.15 * (len(matches) - 1))
                self._trigger(score)
        except Exception as exc:  # noqa: BLE001
            # Keep the long-running listener alive, but expose the failure in
            # launch_voice.bat instead of silently swallowing it forever.
            print(f"[ww] fallback phrase check failed: {type(exc).__name__}: {exc}")
