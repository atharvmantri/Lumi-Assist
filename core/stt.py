"""Speech-to-text for Lumi — faster-whisper on CUDA.

Two responsibilities:
  - Load a Whisper model once, keep it warm in VRAM
  - Transcribe either (a) a WAV file path or (b) a raw int16/float32 numpy buffer

The audio-recording loop (record-until-silence from the mic) lives here too,
because it shares the same sample-rate contract with the model.

Smoke test:
  python -m core.stt --smoke-test           # synthesizes a test phrase via SAPI and round-trips it
  python -m core.stt --transcribe FILE.wav  # transcribe a specific file
  python -m core.stt --record               # record from mic until silence, transcribe, print
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import wave
from pathlib import Path
from typing import Any

import numpy as np


def _register_nvidia_dll_dirs() -> None:
    """ctranslate2 on Windows needs cuBLAS + cuDNN DLLs visible to the loader.
    We installed them via the `nvidia-cublas-cu12` / `nvidia-cudnn-cu12` pip
    wheels, but their bin folders aren't on PATH.

    Two-pronged registration: prepend each bin dir to PATH (so the OS loader
    finds them no matter who calls LoadLibrary), AND call os.add_dll_directory
    for Python's own dependency walker. PATH-prepend alone covers C extensions
    that don't pass LOAD_LIBRARY_SEARCH_USER_DIRS.
    No-op on non-Windows.
    """
    if sys.platform != "win32":
        return
    try:
        import importlib.util
    except ImportError:
        return
    bin_dirs: list[str] = []
    for pkg in ("nvidia.cublas", "nvidia.cudnn", "nvidia.cuda_nvrtc"):
        spec = importlib.util.find_spec(pkg)
        if spec is None or not spec.submodule_search_locations:
            continue
        for base in spec.submodule_search_locations:
            bin_dir = Path(base) / "bin"
            if bin_dir.is_dir():
                bin_dirs.append(str(bin_dir))
                try:
                    os.add_dll_directory(str(bin_dir))
                except (OSError, FileNotFoundError):
                    pass
    if bin_dirs:
        os.environ["PATH"] = os.pathsep.join(bin_dirs) + os.pathsep + os.environ.get("PATH", "")


_register_nvidia_dll_dirs()

# faster-whisper / ctranslate2 are the only heavy imports — defer them so
# `--help` is fast and import errors are surfaced with a useful message.
try:
    from faster_whisper import WhisperModel
except ImportError as e:  # pragma: no cover
    raise SystemExit(
        "faster-whisper not installed. Run: pip install -r requirements.txt"
    ) from e

from core.config import PROJECT_ROOT, load_config

SAMPLE_RATE = 16000   # Whisper expects 16 kHz mono; everything in the pipeline runs at this rate
CHANNELS = 1
DTYPE = "int16"


# ---------------------------------------------------------------------------
# Model wrapper
# ---------------------------------------------------------------------------

class STT:
    """Wraps a faster-whisper model with project-wide config + audio helpers."""

    def __init__(self, config: dict[str, Any] | None = None, *, verbose: bool = True) -> None:
        cfg = config or load_config()
        stt_cfg = cfg["stt"]
        self.model_name: str = stt_cfg["model"]
        self.device: str = stt_cfg["device"]
        self.compute_type: str = stt_cfg["compute_type"]
        self.silence_threshold_ms: int = int(stt_cfg["silence_threshold_ms"])
        self.language: str | None = stt_cfg.get("language")

        cache_dir = PROJECT_ROOT / "models" / "whisper"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Prefer a pre-downloaded snapshot at models/whisper/Systran--faster-whisper-<name>/
        # over re-downloading via the model_name shortcut.
        local_snapshot = cache_dir / f"Systran--faster-whisper-{self.model_name}"
        model_target: str = str(local_snapshot) if local_snapshot.is_dir() else self.model_name

        if verbose:
            print(f"[stt] loading {self.model_name} on {self.device} ({self.compute_type})...")
            if model_target != self.model_name:
                print(f"[stt] using local snapshot: {local_snapshot}")
            else:
                print(f"[stt] cache dir (will download if missing): {cache_dir}")
        t0 = time.perf_counter()
        self.model = WhisperModel(
            model_target,
            device=self.device,
            compute_type=self.compute_type,
            download_root=str(cache_dir),
        )
        if verbose:
            print(f"[stt] model loaded in {time.perf_counter() - t0:.1f}s")

    # ---- transcription ---------------------------------------------------

    def transcribe(
        self,
        audio: str | Path | np.ndarray,
        *,
        language: str | None = None,
        beam_size: int = 5,
    ) -> tuple[str, dict[str, Any]]:
        """Transcribe audio (file path or numpy buffer). Returns (text, info_dict).

        For numpy buffers: expects mono 16 kHz, either int16 or float32 in [-1, 1].
        """
        if isinstance(audio, (str, Path)):
            audio_arg: Any = str(audio)
        elif isinstance(audio, np.ndarray):
            audio_arg = _to_float32_mono(audio)
        else:
            raise TypeError(f"audio must be path or numpy array, got {type(audio).__name__}")

        lang = language or self.language  # None = auto-detect
        segments_iter, info = self.model.transcribe(
            audio_arg,
            beam_size=beam_size,
            language=lang,
            vad_filter=True,         # built-in silero VAD — cuts cost on quiet audio
        )
        # The iterator is lazy; consume it to get real text
        text = "".join(seg.text for seg in segments_iter).strip()
        info_dict = {
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
        }
        return text, info_dict

    # ---- mic capture -----------------------------------------------------

    def record_until_silence(
        self,
        *,
        max_seconds: float = 30.0,
        silence_rms_threshold: float = 0.012,
        show_meter: bool = False,
    ) -> np.ndarray:
        """Record from default mic, stop after silence_threshold_ms of quiet.

        Returns a float32 mono numpy array at SAMPLE_RATE. Imports sounddevice
        lazily so STT() construction doesn't require it.

        With show_meter=True, prints a one-line RMS bar that updates in place
        so you can confirm the mic is actually picking up your voice.
        """
        try:
            import sounddevice as sd
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("sounddevice not installed; cannot record from mic") from e

        block_ms = 30
        block_samples = int(SAMPLE_RATE * block_ms / 1000)
        silence_blocks_needed = max(1, self.silence_threshold_ms // block_ms)
        max_blocks = int(max_seconds * 1000 / block_ms)

        captured: list[np.ndarray] = []
        silent_streak = 0
        heard_voice = False
        peak_rms = 0.0

        print(f"[stt] recording (max {max_seconds:.0f}s, stop after {self.silence_threshold_ms}ms of silence)...")
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            blocksize=block_samples,
        ) as stream:
            for _ in range(max_blocks):
                block, _overflow = stream.read(block_samples)
                block_mono = block[:, 0] if block.ndim > 1 else block
                captured.append(block_mono.copy())

                rms = float(np.sqrt(np.mean(block_mono ** 2)))
                peak_rms = max(peak_rms, rms)
                if show_meter:
                    # 30-char bar, scale RMS so a normal voice fills ~half
                    bar_len = min(30, int(rms / 0.05 * 30))
                    bar = "█" * bar_len + " " * (30 - bar_len)
                    state = "•" if rms > silence_rms_threshold else " "
                    sys.stdout.write(f"\r  mic [{bar}] rms={rms:.3f} {state}")
                    sys.stdout.flush()

                if rms > silence_rms_threshold:
                    heard_voice = True
                    silent_streak = 0
                elif heard_voice:
                    silent_streak += 1
                    if silent_streak >= silence_blocks_needed:
                        break
        if show_meter:
            sys.stdout.write("\r" + " " * 60 + "\r")
            sys.stdout.flush()
        audio = np.concatenate(captured) if captured else np.zeros(0, dtype=np.float32)
        print(f"[stt] captured {len(audio) / SAMPLE_RATE:.2f}s of audio  (peak rms {peak_rms:.3f}, heard_voice={heard_voice})")
        return audio


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

def _to_float32_mono(arr: np.ndarray) -> np.ndarray:
    """Coerce numpy buffer to float32 mono in [-1, 1], whatever it came in as."""
    if arr.ndim > 1:
        arr = arr.mean(axis=1)
    if arr.dtype == np.float32:
        return arr
    if arr.dtype == np.int16:
        return (arr.astype(np.float32) / 32768.0).clip(-1.0, 1.0)
    if arr.dtype == np.float64:
        return arr.astype(np.float32)
    raise TypeError(f"unsupported audio dtype: {arr.dtype}")


def write_wav(path: str | Path, audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    """Write a mono float32 array as a 16-bit PCM WAV."""
    if audio.dtype != np.int16:
        audio_i16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    else:
        audio_i16 = audio
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_i16.tobytes())


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

def _synthesize_test_wav(out_path: Path, phrase: str) -> bool:
    """Use Windows SAPI to TTS a known phrase to a WAV. Returns True on success."""
    try:
        import comtypes.client as cc
    except ImportError:
        # Fall back to win32com if comtypes isn't here
        try:
            import win32com.client as cc  # type: ignore[no-redef]
        except ImportError:
            return False
    try:
        speaker = cc.CreateObject("SAPI.SpVoice")
        stream = cc.CreateObject("SAPI.SpFileStream")
        # SAFT16kHz16BitMono = 6 → 16kHz / 16-bit / mono, perfect for Whisper
        SSFMCreateForWrite = 3
        stream.Format.Type = 6
        stream.Open(str(out_path), SSFMCreateForWrite)
        speaker.AudioOutputStream = stream
        speaker.Speak(phrase)
        stream.Close()
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[stt] SAPI synthesis failed: {e}")
        return False


def _smoke_test() -> int:
    """Synthesize a phrase via Windows SAPI, transcribe it, check the result."""
    test_wav = PROJECT_ROOT / "logs" / "_stt_smoke.wav"
    phrase = "The quick brown fox jumps over the lazy dog."
    print(f"[smoke] synthesizing test phrase via SAPI: {phrase!r}")
    if not _synthesize_test_wav(test_wav, phrase):
        print("[smoke] FAILED: could not synthesize a test WAV. "
              "Try `python -m core.stt --transcribe SOMEWAV.wav` with your own file.")
        return 1
    print(f"[smoke] wrote {test_wav} ({test_wav.stat().st_size} bytes)")

    stt = STT()
    print(f"[smoke] transcribing...")
    t0 = time.perf_counter()
    text, info = stt.transcribe(test_wav)
    elapsed = time.perf_counter() - t0
    rtf = elapsed / info["duration"] if info["duration"] else float("inf")

    print(f"[smoke] heard      : {text!r}")
    print(f"[smoke] language   : {info['language']} (prob {info['language_probability']:.2f})")
    print(f"[smoke] duration   : {info['duration']:.2f}s")
    print(f"[smoke] transcribe : {elapsed:.2f}s  (RTF {rtf:.2f}×)")

    # Loose match — SAPI voices vary, Whisper may capitalize/punctuate differently.
    expected_words = {"quick", "brown", "fox", "lazy", "dog"}
    heard_words = {w.strip(".,!?").lower() for w in text.split()}
    overlap = expected_words & heard_words
    print(f"[smoke] word overlap: {len(overlap)}/{len(expected_words)} → {sorted(overlap)}")
    if len(overlap) < 4:
        print("[smoke] FAILED: transcription doesn't match expected phrase")
        return 1
    if rtf > 1.0:
        print(f"[smoke] WARNING: RTF {rtf:.2f}× — slower than real-time, check GPU usage")
    print("[smoke] OK")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Lumi STT (faster-whisper on CUDA)")
    parser.add_argument("--smoke-test", action="store_true", help="Synthesize a test phrase via SAPI and round-trip it")
    parser.add_argument("--transcribe", metavar="WAV", help="Transcribe a specific WAV file")
    parser.add_argument("--record", action="store_true", help="Record from mic until silence, then transcribe")
    args = parser.parse_args()

    if args.smoke_test:
        raise SystemExit(_smoke_test())

    if args.transcribe:
        stt = STT()
        t0 = time.perf_counter()
        text, info = stt.transcribe(args.transcribe)
        print(f"\n{text}\n")
        print(f"[lang={info['language']} dur={info['duration']:.2f}s rt={time.perf_counter() - t0:.2f}s]")
        return

    if args.record:
        stt = STT()
        audio = stt.record_until_silence()
        if audio.size == 0:
            print("(no audio captured)")
            return
        text, info = stt.transcribe(audio)
        print(f"\n{text}\n")
        print(f"[lang={info['language']} dur={info['duration']:.2f}s]")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
