"""Text-to-speech for JARVIS — Piper (ONNX runtime).

One responsibility: turn text into spoken audio with low first-chunk latency.

Default device: CPU. Piper's ONNX runtime is already faster-than-real-time on
modest CPUs, and the GPU is busy with Whisper + the floating UI's animations.
Flip `tts.device: cuda` in config.yaml to try CUDA — requires `onnxruntime-gpu`
instead of `onnxruntime`, and your mileage may vary on Windows.

Two playback paths:
  speak(text)              — synthesize whole utterance, then play once
  speak_streaming(text)    — play each chunk as Piper emits it (lower first-audio latency)

Smoke test:
  python -m core.tts --smoke-test            # synth + play 'Voice systems online, sir'
  python -m core.tts --say "any text here"   # speak arbitrary text
  python -m core.tts --to FILE.wav "text"    # synthesize to a WAV instead of speakers
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import wave
from pathlib import Path
from typing import Any, Iterable, Iterator

import numpy as np

try:
    from piper import PiperVoice
except ImportError as e:  # pragma: no cover
    raise SystemExit(
        "piper-tts not installed. Run: pip install -r requirements.txt"
    ) from e

from core.config import PROJECT_ROOT, load_config


# ---------------------------------------------------------------------------
# Text cleaning — strip markdown noise the TTS would read literally
# ---------------------------------------------------------------------------

# Strip markdown fences, bold, italic, code, headers, bullets
_TTS_CLEAN_FENCE = re.compile(r"```[\w]*\n(.*?)```", re.DOTALL)
_TTS_CLEAN_INLINE_CODE = re.compile(r"`([^`\n]+?)`")
_TTS_CLEAN_BOLD = re.compile(r"\*\*(.+?)\*\*")
_TTS_CLEAN_ITALIC = re.compile(r"(?<![*\w])\*([^*\n]+?)\*(?!\*)")
_TTS_CLEAN_HEADER = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_TTS_CLEAN_BULLET = re.compile(r"^[\s]*[-*•]\s+", re.MULTILINE)
_TTS_CLEAN_NUM_LIST = re.compile(r"^[\s]*\d+\.\s+", re.MULTILINE)
_TTS_CLEAN_URL = re.compile(r"\[([^\]]+)\]\([^)]+\)")  # [text](url) → text
_TTS_CLEAN_MULTI_WS = re.compile(r"[ \t]+")
_TTS_CLEAN_REPEAT_PUNCT = re.compile(r"([!?.])\1{2,}")  # !!! → !


def _clean_for_tts(text: str) -> str:
    """Remove markdown formatting that the TTS would read literally."""
    text = _TTS_CLEAN_FENCE.sub(lambda m: m.group(1).strip(), text)
    text = _TTS_CLEAN_INLINE_CODE.sub(r"\1", text)
    text = _TTS_CLEAN_BOLD.sub(r"\1", text)
    text = _TTS_CLEAN_ITALIC.sub(r"\1", text)
    text = _TTS_CLEAN_HEADER.sub("", text)
    text = _TTS_CLEAN_BULLET.sub("", text)
    text = _TTS_CLEAN_NUM_LIST.sub("", text)
    text = _TTS_CLEAN_URL.sub(r"\1", text)
    text = _TTS_CLEAN_REPEAT_PUNCT.sub(r"\1", text)
    text = _TTS_CLEAN_MULTI_WS.sub(" ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# TTS wrapper
# ---------------------------------------------------------------------------

class TTS:
    """Piper voice + playback. Loads once, keeps the model resident."""

    def __init__(self, config: dict[str, Any] | None = None, *, verbose: bool = True) -> None:
        cfg = config or load_config()
        tts_cfg = cfg["tts"]
        self.engine: str = tts_cfg["engine"]
        if self.engine != "piper":
            raise NotImplementedError(f"engine={self.engine!r} not implemented (only piper)")
        self.voice_name: str = tts_cfg["voice"]
        self.device: str = tts_cfg["device"]
        self.speed: float = float(tts_cfg.get("speed", 1.0))

        models_dir = PROJECT_ROOT / "models" / "piper"
        self.model_path = models_dir / f"{self.voice_name}.onnx"
        self.config_path = models_dir / f"{self.voice_name}.onnx.json"
        if not self.model_path.exists() or not self.config_path.exists():
            raise FileNotFoundError(
                f"Piper voice files missing under {models_dir}.\n"
                f"  expected: {self.model_path.name} + {self.config_path.name}"
            )

        if verbose:
            print(f"[tts] loading {self.voice_name} on {self.device}...")
        t0 = time.perf_counter()
        self.voice = PiperVoice.load(
            str(self.model_path),
            config_path=str(self.config_path),
            use_cuda=(self.device == "cuda"),
        )
        if verbose:
            print(f"[tts] voice loaded in {time.perf_counter() - t0:.2f}s "
                  f"(sample_rate={self.sample_rate} Hz)")

    # ---- properties ------------------------------------------------------

    @property
    def sample_rate(self) -> int:
        """Voice's native output sample rate (typically 22050 Hz for libritts_r-medium)."""
        # PiperVoice exposes this via config.sample_rate
        return int(self.voice.config.sample_rate)

    # ---- synthesis -------------------------------------------------------

    def synthesize_iter(self, text: str) -> Iterator[np.ndarray]:
        """Yield float32 numpy arrays as each chunk comes off the model.

        Lower-latency than synthesize_all() because playback can start on the
        first chunk. Each chunk is at self.sample_rate Hz, mono, in [-1, 1].
        """
        for chunk in self.voice.synthesize(text):
            audio_int16 = np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16)
            yield (audio_int16.astype(np.float32) / 32768.0)

    def synthesize_all(self, text: str) -> np.ndarray:
        """Synthesize the whole utterance into one float32 mono array."""
        chunks = list(self.synthesize_iter(text))
        return np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)

    # ---- playback --------------------------------------------------------

    def speak(self, text: str, *, blocking: bool = True) -> None:
        """Synthesize full utterance, then play through default output device."""
        try:
            import sounddevice as sd
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("sounddevice not installed; cannot play audio") from e
        audio = self.synthesize_all(_clean_for_tts(text))
        if audio.size == 0:
            return
        sd.play(audio, self.sample_rate)
        if blocking:
            sd.wait()

    def speak_streaming(self, text: str) -> dict[str, float]:
        """Play audio as Piper emits it. Returns timing dict for instrumentation.

        Uses an OutputStream so chunks queue into the same playback session
        with no gap between them. Blocks until playback finishes.
        """
        try:
            import sounddevice as sd
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("sounddevice not installed; cannot play audio") from e

        t_start = time.perf_counter()
        first_chunk_at: float | None = None
        playback_started_at: float | None = None
        total_samples = 0

        with sd.OutputStream(samplerate=self.sample_rate, channels=1, dtype="float32") as stream:
            for chunk in self.synthesize_iter(text):
                if first_chunk_at is None:
                    first_chunk_at = time.perf_counter() - t_start
                    stream.start()
                    playback_started_at = time.perf_counter() - t_start
                stream.write(chunk)
                total_samples += chunk.size

        end = time.perf_counter() - t_start
        return {
            "first_chunk_s": first_chunk_at or 0.0,
            "playback_started_s": playback_started_at or 0.0,
            "total_s": end,
            "audio_duration_s": total_samples / self.sample_rate,
        }

    def speak_token_stream(self, token_iter: Iterable[str]) -> dict[str, float]:
        """Speak an LLM token stream: synthesize each sentence as it completes.

        Buffers incoming tokens until a sentence terminator (.!?\\n) lands,
        then hands that sentence to Piper and plays it. The result is that
        speech starts ~1 sentence after the LLM begins streaming, rather than
        waiting for the full reply. Returns timing dict for instrumentation.
        """
        try:
            import sounddevice as sd
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("sounddevice not installed; cannot play audio") from e

        t_start = time.perf_counter()
        first_token_at: float | None = None
        first_audio_at: float | None = None
        total_audio_samples = 0
        sentence_count = 0
        buffer = ""

        # Match a sentence ending: . ! ? newline (and the trailing whitespace).
        sentence_end = re.compile(r"([\.\!\?\n]+)(\s+|$)")

        def flush(text: str, stream: Any) -> int:
            samples = 0
            for chunk in self.synthesize_iter(text):
                stream.write(chunk)
                samples += chunk.size
            return samples

        with sd.OutputStream(samplerate=self.sample_rate, channels=1, dtype="float32") as stream:
            stream.start()
            for token in token_iter:
                if first_token_at is None:
                    first_token_at = time.perf_counter() - t_start
                if not token:
                    continue
                buffer += token
                # Drain as many complete sentences from the buffer as possible
                while True:
                    m = sentence_end.search(buffer)
                    if not m:
                        break
                    cut = m.end()
                    sentence = _clean_for_tts(buffer[:cut].strip())
                    buffer = buffer[cut:]
                    if not sentence:
                        continue
                    if first_audio_at is None:
                        first_audio_at = time.perf_counter() - t_start
                    total_audio_samples += flush(sentence, stream)
                    sentence_count += 1

            # Tail: speak whatever's left in the buffer (no terminator arrived)
            tail = _clean_for_tts(buffer.strip())
            if tail:
                if first_audio_at is None:
                    first_audio_at = time.perf_counter() - t_start
                total_audio_samples += flush(tail, stream)
                sentence_count += 1

        return {
            "first_token_s": first_token_at or 0.0,
            "first_audio_s": first_audio_at or 0.0,
            "total_s": time.perf_counter() - t_start,
            "audio_duration_s": total_audio_samples / self.sample_rate,
            "sentences": float(sentence_count),
        }

    def to_wav(self, text: str, out_path: str | Path) -> Path:
        """Synthesize and write a 16-bit PCM WAV at the voice's sample rate."""
        audio = self.synthesize_all(text)
        audio_i16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_i16.tobytes())
        return out


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

def _smoke_test() -> int:
    phrase = "Voice systems online, sir."
    tts = TTS()
    print(f"[smoke] phrase  : {phrase!r}")
    print(f"[smoke] device  : {tts.device}")
    print(f"[smoke] sr      : {tts.sample_rate} Hz")

    # Cold + warm synthesis timing
    t0 = time.perf_counter()
    audio = tts.synthesize_all(phrase)
    cold = time.perf_counter() - t0
    dur = audio.size / tts.sample_rate
    print(f"[smoke] synth(cold): {cold:.3f}s  for {dur:.2f}s of audio  "
          f"(RTF {cold / dur if dur else float('inf'):.2f}x)")

    t0 = time.perf_counter()
    _ = tts.synthesize_all(phrase)
    warm = time.perf_counter() - t0
    print(f"[smoke] synth(warm): {warm:.3f}s  (RTF {warm / dur if dur else float('inf'):.2f}x)")

    # Save a WAV so we can verify even if speakers are off
    wav_path = PROJECT_ROOT / "logs" / "_tts_smoke.wav"
    tts.to_wav(phrase, wav_path)
    print(f"[smoke] wav     : {wav_path} ({wav_path.stat().st_size} bytes)")

    # Streaming playback with timing
    print(f"[smoke] playing through default output device (streaming)...")
    try:
        timing = tts.speak_streaming(phrase)
        print(f"[smoke] first chunk after : {timing['first_chunk_s'] * 1000:.0f} ms")
        print(f"[smoke] total elapsed     : {timing['total_s']:.2f}s")
        print(f"[smoke] audio duration    : {timing['audio_duration_s']:.2f}s")
    except Exception as e:  # noqa: BLE001
        print(f"[smoke] playback FAILED: {e}")
        print(f"[smoke] (WAV was still written; check {wav_path} to verify synthesis)")
        return 1

    print("[smoke] OK")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="JARVIS TTS (Piper)")
    parser.add_argument("--smoke-test", action="store_true", help="Synthesize + play a known phrase")
    parser.add_argument("--say", metavar="TEXT", help="Speak arbitrary text through speakers")
    parser.add_argument("--to", metavar="WAV", help="Write to a WAV instead of playing")
    parser.add_argument("text", nargs="?", help="Text (when used with --to)")
    args = parser.parse_args()

    if args.smoke_test:
        raise SystemExit(_smoke_test())

    if args.say:
        TTS().speak_streaming(args.say)
        return

    if args.to:
        if not args.text:
            parser.error("--to FILE.wav requires a positional TEXT argument")
        out = TTS().to_wav(args.text, args.to)
        print(f"wrote {out}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
