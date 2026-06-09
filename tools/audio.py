"""Text-to-speech alternatives and audio tools."""
from __future__ import annotations

import subprocess

from tools import tool


@tool(
    name="windows_voice_speak",
    description="Speak text using Windows built-in SAPI voice (no Piper needed). Faster than Piper but less natural.",
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to speak",
            },
            "rate": {
                "type": "integer",
                "description": "Speech rate -10 to 10 (default 0 = normal)",
            },
        },
        "required": ["text"],
    },
)
def windows_voice_speak(text: str, rate: int = 0) -> str:
    ps_text = text.replace("'", "''")
    ps_cmd = f"""
    Add-Type -AssemblyName System.Speech
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $synth.Rate = {rate}
    $synth.Speak('{ps_text}')
    """
    try:
        subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return f"Spoke text using Windows SAPI voice"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="list_system_voices",
    description="List available text-to-speech voices on the system.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def list_system_voices() -> str:
    ps_cmd = """
    Add-Type -AssemblyName System.Speech
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $synth.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name + ' (' + $_.VoiceInfo.Culture + ')' }
    """
    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        voices = [v.strip() for v in result.stdout.strip().split("\n") if v.strip()]
        if not voices:
            return "No system voices found."
        lines = [f"System Voices ({len(voices)}):"]
        for v in voices:
            lines.append(f"  {v}")
        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"


@tool(
    name="beep",
    description="Play a beep sound at a specific frequency and duration.",
    parameters={
        "type": "object",
        "properties": {
            "frequency": {
                "type": "integer",
                "description": "Frequency in Hz (default 1000, range 37-32767)",
            },
            "duration": {
                "type": "integer",
                "description": "Duration in milliseconds (default 200)",
            },
        },
        "required": [],
    },
)
def beep(frequency: int = 1000, duration: int = 200) -> str:
    try:
        import winsound
        winsound.Beep(frequency, duration)
        return f"Played beep at {frequency}Hz for {duration}ms"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="play_system_sound",
    description="Play a Windows system sound.",
    parameters={
        "type": "object",
        "properties": {
            "sound": {
                "type": "string",
                "description": "Sound type: 'asterisk', 'exclamation', 'hand', 'ok', 'menu'",
                "enum": ["asterisk", "exclamation", "hand", "ok", "menu"],
            },
        },
        "required": [],
    },
)
def play_system_sound(sound: str = "ok") -> str:
    try:
        import winsound
        sounds = {
            "asterisk": winsound.MB_ICONASTERISK,
            "exclamation": winsound.MB_ICONEXCLAMATION,
            "hand": winsound.MB_ICONHAND,
            "ok": winsound.MB_OK,
            "menu": None,
        }
        if sound == "menu":
            winsound.MessageBeep()
        else:
            winsound.MessageBeep(sounds[sound])
        return f"Played system sound: {sound}"
    except Exception as e:
        return f"error: {e}"
