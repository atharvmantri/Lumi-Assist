"""Volume mixer and audio device management."""
from __future__ import annotations

import subprocess

from tools import tool


@tool(
    name="audio_devices",
    description="List all audio input and output devices.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def audio_devices() -> str:
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        default_in = sd.default.device[0]
        default_out = sd.default.device[1]

        lines = ["Audio Devices:"]
        for i, d in enumerate(devices):
            marker = ""
            if i == default_out:
                marker = " [DEFAULT OUTPUT]"
            if i == default_in:
                marker += " [DEFAULT INPUT]"
            if d.get('max_input_channels', 0) > 0:
                lines.append(f"  #{i} {d['name']}{marker} (INPUT)")
            if d.get('max_output_channels', 0) > 0:
                lines.append(f"  #{i} {d['name']}{marker} (OUTPUT)")

        return "\n".join(lines)
    except ImportError:
        return "error: sounddevice not installed"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="set_default_audio",
    description="Switch the default audio output device.",
    parameters={
        "type": "object",
        "properties": {
            "device_id": {
                "type": "integer",
                "description": "Device ID from audio_devices list",
            },
        },
        "required": ["device_id"],
    },
)
def set_default_audio(device_id: int) -> str:
    try:
        import sounddevice as sd
        sd.default.device = (sd.default.device[0], device_id)
        devices = sd.query_devices()
        name = devices[device_id]['name'] if device_id < len(devices) else f"#{device_id}"
        return f"Default audio output set to: {name}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="open_volume_mixer",
    description="Open the Windows Volume Mixer.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def open_volume_mixer() -> str:
    try:
        import subprocess
        subprocess.Popen(
            ["sndvol"],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return "Opened Windows Volume Mixer"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="open_sound_settings",
    description="Open Windows Sound Settings.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def open_sound_settings() -> str:
    try:
        import subprocess
        subprocess.Popen(
            ["start", "ms-settings:sound"],
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return "Opened Windows Sound Settings"
    except Exception as e:
        return f"error: {e}"
