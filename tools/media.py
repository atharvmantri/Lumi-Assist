"""Screen recording and audio capture."""
from __future__ import annotations

import subprocess
import time
from datetime import datetime
from pathlib import Path

from core.config import PROJECT_ROOT
from tools import tool

RECORDINGS_DIR = PROJECT_ROOT / "data" / "recordings"


@tool(
    name="record_screen",
    description="Start recording the screen. Returns the output file path. Requires ffmpeg installed.",
    parameters={
        "type": "object",
        "properties": {
            "duration": {
                "type": "integer",
                "description": "Recording duration in seconds (0 for indefinite, default 30)",
            },
            "region": {
                "type": "array",
                "description": "Optional [x, y, width, height] for sub-region recording",
                "items": {"type": "integer"},
            },
        },
        "required": [],
    },
)
def record_screen(duration: int = 30, region: list[int] | None = None) -> str:
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RECORDINGS_DIR / f"screen_{ts}.mp4"

    cmd = ["ffmpeg", "-y", "-f", "gdigrab", "-framerate", "30"]
    if region and len(region) == 4:
        cmd.extend(["-offset_x", str(region[0]), "-offset_y", str(region[1]),
                     "-video_size", f"{region[2]}x{region[3]}"])
    cmd.extend(["-i", "desktop", "-c:v", "libx264", "-preset", "ultrafast",
                str(output_path)])

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        if duration > 0:
            time.sleep(duration)
            proc.terminate()
            proc.wait(timeout=5)
            return f"Screen recording saved: {output_path} ({duration}s)"
        else:
            return f"Screen recording started (indefinite). PID: {proc.pid}. Use taskkill /PID {proc.pid} to stop."
    except FileNotFoundError:
        return "error: ffmpeg not found. Install from https://ffmpeg.org/"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="record_audio",
    description="Record audio from the microphone. Requires ffmpeg installed.",
    parameters={
        "type": "object",
        "properties": {
            "duration": {
                "type": "integer",
                "description": "Recording duration in seconds (default 10)",
            },
        },
        "required": [],
    },
)
def record_audio(duration: int = 10) -> str:
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RECORDINGS_DIR / f"audio_{ts}.wav"

    cmd = ["ffmpeg", "-y", "-f", "dshow", "-i", "audio=Microphone",
           "-t", str(duration), "-acodec", "pcm_s16le", "-ar", "44100",
           str(output_path)]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=duration + 10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return f"Audio recording saved: {output_path} ({duration}s)"
        return f"error recording audio: {result.stderr[:200]}"
    except FileNotFoundError:
        return "error: ffmpeg not found"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="convert_media",
    description="Convert audio/video files to different formats using ffmpeg.",
    parameters={
        "type": "object",
        "properties": {
            "input_path": {
                "type": "string",
                "description": "Path to the input media file",
            },
            "output_format": {
                "type": "string",
                "description": "Output format: 'mp3', 'wav', 'mp4', 'gif', 'webm'",
            },
        },
        "required": ["input_path", "output_format"],
    },
)
def convert_media(input_path: str, output_format: str) -> str:
    input_p = Path(input_path)
    if not input_p.exists():
        return f"error: file not found: {input_path}"

    output_path = input_p.with_suffix(f".{output_format}")

    cmd = ["ffmpeg", "-y", "-i", str(input_p)]

    if output_format == "mp3":
        cmd.extend(["-codec:a", "libmp3lame", "-q:a", "2"])
    elif output_format == "wav":
        cmd.extend(["-acodec", "pcm_s16le", "-ar", "44100"])
    elif output_format == "gif":
        cmd.extend(["-vf", "scale=480:-1", "-f", "gif"])

    cmd.append(str(output_path))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=120,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            size_kb = output_path.stat().st_size / 1024
            return f"Converted: {input_p.name} → {output_path.name} ({size_kb:.0f} KB)"
        return f"error converting: {result.stderr[:200]}"
    except FileNotFoundError:
        return "error: ffmpeg not found"
    except Exception as e:
        return f"error: {e}"
