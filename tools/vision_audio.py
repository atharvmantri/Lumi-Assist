"""Vision & Audio Intelligence tools utilizing PyTesseract, Whisper STT, and Piper TTS."""
from __future__ import annotations

import os
import subprocess
import re
import time
import json
from pathlib import Path

import numpy as np

from tools import tool


# Configure Windows Tesseract path if found in standard install folders
try:
    import pytesseract
    import sys
    if sys.platform == "win32":
        standard_tesseract_paths = [
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
            Path(os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe")),
        ]
        for p in standard_tesseract_paths:
            if p.exists():
                pytesseract.pytesseract.tesseract_cmd = str(p)
                break
except ImportError:
    pytesseract = None


@tool(
    name="ocr_scan",
    description="Extract text content from an image file using OCR scanning.",
    parameters={
        "type": "object",
        "properties": {
            "image_path": {"type": "string", "description": "Local file path to the image"},
        },
        "required": ["image_path"],
    },
)
def ocr_scan(image_path: str) -> str:
    if pytesseract is None:
        return "error: pytesseract library is not installed. Run `pip install pytesseract`."

    img_file = Path(image_path)
    if not img_file.is_file():
        return f"error: image file not found: {image_path}"

    try:
        from PIL import Image
    except ImportError:
        return "error: Pillow library is required for image scanning. Run `pip install Pillow`."

    try:
        img = Image.open(img_file)
        text = pytesseract.image_to_string(img)
        cleaned = text.strip()
        if not cleaned:
            return "OCR scan executed successfully, but no text could be extracted from this image."
        return cleaned
    except Exception as e:
        return (
            f"error scanning image: {e}\n"
            f"Note: OCR scan requires Tesseract OCR engine installed on your system PATH.\n"
            f"On Windows, download it from UB Mannheim's Tesseract build and verify it's installed."
        )


@tool(
    name="transcribe_audio",
    description="Transcribe an audio file (or extract and transcribe audio from a video) to text.",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Local path to the audio or video file"},
            "language": {"type": "string", "description": "Language code (e.g. 'en', 'es') to force language. Default: auto-detect."},
        },
        "required": ["file_path"],
    },
)
def transcribe_audio(file_path: str, language: str | None = None) -> str:
    path = Path(file_path)
    if not path.is_file():
        return f"error: file not found: {file_path}"

    try:
        from core.stt import STT
    except ImportError:
        return "error: core.stt STT engine is not available."

    # If video, extract audio stream to temp WAV
    ext = path.suffix.lower()
    audio_path = path
    temp_wav = None
    if ext in (".mp4", ".mkv", ".avi", ".mov", ".flv", ".webm"):
        temp_wav = path.with_suffix(".temp_audio.wav")
        try:
            # Extract mono 16kHz WAV using ffmpeg
            cmd = ["ffmpeg", "-y", "-i", str(path), "-vn", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(temp_wav)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != 0:
                return f"error extracting audio from video: {result.stderr.strip()}"
            audio_path = temp_wav
        except Exception as ffmpeg_err:
            return f"error calling ffmpeg to extract video audio: {ffmpeg_err}"

    try:
        stt = STT(verbose=False)
        text, info = stt.transcribe(str(audio_path), language=language)
        
        # Cleanup
        if temp_wav and temp_wav.exists():
            os.remove(temp_wav)
            
        return json.dumps({
            "text": text,
            "detected_language": info.get("language"),
            "probability": info.get("language_probability"),
            "duration_s": info.get("duration"),
        }, indent=2)
    except Exception as e:
        if temp_wav and temp_wav.exists():
            os.remove(temp_wav)
        return f"error transcribing audio: {e}"


@tool(
    name="translate_speech",
    description="Translate speech from an audio file and synthesize a translated audio WAV file.",
    parameters={
        "type": "object",
        "properties": {
            "audio_path": {"type": "string", "description": "Path to the input speech WAV file"},
            "target_language": {"type": "string", "description": "Language to translate to (e.g. 'Spanish', 'French', 'German')"},
            "output_path": {"type": "string", "description": "Optional custom path for output WAV. Defaults to data/translations/translated_<lang>.wav"},
        },
        "required": ["audio_path", "target_language"],
    },
)
def translate_speech(audio_path: str, target_language: str, output_path: str | None = None) -> str:
    path = Path(audio_path)
    if not path.is_file():
        return f"error: audio file not found: {audio_path}"

    try:
        from core.stt import STT
        from core.llm import LLMClient
        from core.tts import TTS
    except ImportError:
        return "error: Lumi speech/LLM engines not importable."

    try:
        # 1. Transcribe speech
        stt = STT(verbose=False)
        text, info = stt.transcribe(str(path))
        if not text:
            return "error: Transcription returned empty text. Could not translate."

        # 2. Translate text via LLM
        client = LLMClient()
        prompt = f"Translate the following speech transcript to {target_language}. Return ONLY the direct translation (no intros/explanations/quotes):\n\n{text}"
        translated_text = client.complete(prompt).strip()
        
        # Strip any leading quotes
        translated_text = translated_text.strip('"\'')

        # 3. Synthesize to output WAV
        dest_folder = Path("data/translations")
        dest_folder.mkdir(parents=True, exist_ok=True)
        
        out_file = Path(output_path) if output_path else dest_folder / f"translated_{target_language.lower()}_{path.stem}.wav"
        
        tts = TTS(verbose=False)
        tts.to_wav(translated_text, out_file)

        return json.dumps({
            "original_text": text,
            "translated_text": translated_text,
            "target_language": target_language,
            "output_path": str(out_file.resolve()),
        }, indent=2)

    except Exception as e:
        return f"error in speech-to-speech translation pipeline: {e}"


@tool(
    name="video_analysis",
    description="Analyze video file metadata and extract frame screenshots at key intervals.",
    parameters={
        "type": "object",
        "properties": {
            "video_path": {"type": "string", "description": "Local path to the video file"},
            "extract_frames": {"type": "boolean", "description": "If true, extracts frame screenshots to data/frames/", "default": False},
            "num_frames": {"type": "integer", "description": "Number of frames to extract (default 3, max 10)", "default": 3},
        },
        "required": ["video_path"],
    },
)
def video_analysis(video_path: str, extract_frames: bool = False, num_frames: int = 3) -> str:
    path = Path(video_path)
    if not path.is_file():
        return f"error: video file not found: {video_path}"

    num_frames = max(1, min(num_frames, 10))
    metadata = {}
    
    # 1. Inspect using ffprobe
    try:
        # Get width, height, duration
        cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,duration,r_frame_rate", "-of", "json", str(path)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            stream = data.get("streams", [{}])[0]
            metadata = {
                "width": stream.get("width"),
                "height": stream.get("height"),
                "duration_s": float(stream.get("duration", 0)),
                "frame_rate": stream.get("r_frame_rate"),
            }
    except Exception as e:
        # Fallback metadata logic
        metadata = {"note": f"ffprobe not available to read metadata: {e}"}

    # 2. Extract frames if requested
    extracted = []
    if extract_frames:
        duration = metadata.get("duration_s", 10.0) or 10.0
        frames_dir = Path("data/frames")
        frames_dir.mkdir(parents=True, exist_ok=True)
        
        # Calculate time checkpoints evenly spaced
        checkpoints = [duration * (i + 1) / (num_frames + 1) for i in range(num_frames)]
        
        for idx, cp in enumerate(checkpoints, 1):
            frame_path = frames_dir / f"{path.stem}_frame_{idx}.jpg"
            try:
                # Seek to time checkpoint and extract 1 frame
                cmd = ["ffmpeg", "-y", "-ss", f"{cp:.2f}", "-i", str(path), "-vframes", "1", "-f", "image2", str(frame_path)]
                res = subprocess.run(cmd, capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
                if res.returncode == 0:
                    extracted.append(str(frame_path.resolve()))
            except Exception:
                pass

    return json.dumps({
        "video_file": path.name,
        "metadata": metadata,
        "frames_extracted": len(extracted),
        "frame_paths": extracted,
    }, indent=2)


@tool(
    name="sentiment_analysis",
    description="Analyze sentiment, emotion, and tone of a text string or audio speech file.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Optional text to analyze"},
            "audio_path": {"type": "string", "description": "Optional path to audio file (text will be transcribed from this if provided)"},
        },
    },
)
def sentiment_analysis(text: str | None = None, audio_path: str | None = None) -> str:
    if not text and not audio_path:
        return "error: Must provide either 'text' or 'audio_path'."

    target_text = text

    # Transcribe audio if provided
    if audio_path:
        path = Path(audio_path)
        if not path.is_file():
            return f"error: audio file not found: {audio_path}"
        try:
            from core.stt import STT
            stt = STT(verbose=False)
            text_result, _ = stt.transcribe(str(path))
            if not text_result:
                return "error: Audio transcription returned empty text."
            target_text = text_result
        except Exception as e:
            return f"error transcribing audio for sentiment analysis: {e}"

    assert target_text is not None

    # Try LLM for advanced sentiment & tone detection
    try:
        from core.llm import LLMClient
        client = LLMClient()
        prompt = (
            "Analyze the sentiment, primary emotion, and tone of the following text.\n"
            "Return a JSON block containing the keys: 'sentiment' (Positive, Negative, or Neutral), "
            "'score' (a float between -1.0 and 1.0), 'primary_emotion' (e.g. Joy, Anger, Fear, Sadness), "
            "and 'tone_analysis' (a short summary explaining the vibe).\n\n"
            f"Text:\n\"\"\"\n{target_text}\n\"\"\""
        )
        response = client.complete(prompt).strip()
        # Clean any markdown block wrapping
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            # Parse to ensure it is valid JSON
            parsed = json.loads(json_match.group(0))
            return json.dumps(parsed, indent=2)
    except Exception:
        pass

    # Local Lexicon-based sentiment fallback
    pos_words = {"good", "great", "love", "happy", "awesome", "excellent", "nice", "glad", "wonderful", "perfect", "enjoy", "smile", "thanks", "best"}
    neg_words = {"bad", "sad", "hate", "angry", "terrible", "worst", "unhappy", "sorry", "afraid", "scared", "fail", "broke", "hurt", "pain", "annoy"}
    
    words = re.findall(r"\b\w+\b", target_text.lower())
    pos_count = sum(1 for w in words if w in pos_words)
    neg_count = sum(1 for w in words if w in neg_words)
    
    score = 0.0
    total = pos_count + neg_count
    if total > 0:
        score = (pos_count - neg_count) / total
        
    sentiment = "Neutral"
    if score > 0.2:
        sentiment = "Positive"
    elif score < -0.2:
        sentiment = "Negative"
        
    emotion = "Neutral"
    if sentiment == "Positive":
        emotion = "Joy"
    elif sentiment == "Negative":
        emotion = "Sadness / Frustration"

    return json.dumps({
        "sentiment": sentiment,
        "score": score,
        "primary_emotion": emotion,
        "tone_analysis": f"Evaluated using local lexical fallback tokenizer. Text contained {pos_count} positive and {neg_count} negative indicator words.",
        "analyzed_text": target_text,
    }, indent=2)
