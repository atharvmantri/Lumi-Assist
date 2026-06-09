"""Record voice samples for training a custom Lumi wake word model.

This script helps you record your own voice saying the wake word
and ambient noise, which can be used to fine-tune the model.

Usage:
    python record_wake_samples.py
"""
from __future__ import annotations

import os
import time
import wave
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16000
DURATION = 2.0
NUM_POSITIVE = 20
NUM_NEGATIVE = 10

OUTPUT_DIR = Path(__file__).resolve().parent / "data" / "wake_samples"


def record_sample(output_path: Path, duration: float, label: str, countdown: bool = True) -> bool:
    """Record audio from microphone and save as WAV."""
    try:
        import sounddevice as sd
    except ImportError:
        print("ERROR: sounddevice not installed. Run: pip install sounddevice")
        return False

    print(f"\n  Recording: {label}")
    if countdown:
        print("  Get ready...")
        for i in range(3, 0, -1):
            print(f"  {i}...")
            time.sleep(0.5)
        print("  RECORDING NOW - SAY THE PHRASE!")
    else:
        print("  Recording ambient noise... stay quiet or have normal background noise.")

    audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="float32")
    sd.wait()

    # Convert to int16
    audio_i16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_i16.tobytes())

    print(f"  Saved: {output_path.name}")
    return True


def main():
    print("=" * 60)
    print("  Lumi Wake Word Sample Recorder")
    print("=" * 60)
    print()
    print("This records your voice to train a custom wake word model.")
    print("The model will learn YOUR voice saying the wake word.")
    print()

    print("Phrases to record:")
    print("  - hey lumi")
    print("  - ok lumi")
    print("  - yo lumi")
    print("  - lumi")
    print()

    phrases = ["hey lumi", "ok lumi", "yo lumi", "lumi"]
    samples_per_phrase = NUM_POSITIVE // len(phrases)

    for phrase in phrases:
        print(f"\n{'='*40}")
        print(f"  Recording '{phrase}' ({samples_per_phrase} times)")
        print(f"{'='*40}")

        positive_dir = OUTPUT_DIR / "positive" / phrase.replace(" ", "_")
        for i in range(samples_per_phrase):
            path = positive_dir / f"{phrase.replace(' ', '_')}_{i:03d}.wav"
            if not record_sample(path, DURATION, f"'{phrase}' #{i+1}/{samples_per_phrase}"):
                return
            time.sleep(0.5)

    print(f"\n{'='*40}")
    print(f"  Recording ambient noise ({NUM_NEGATIVE} samples)")
    print(f"{'='*40}")

    negative_dir = OUTPUT_DIR / "negative"
    for i in range(NUM_NEGATIVE):
        path = negative_dir / f"ambient_{i:03d}.wav"
        if not record_sample(path, DURATION, f"ambient #{i+1}/{NUM_NEGATIVE}", countdown=False):
            return
        time.sleep(0.5)

    # Generate training instructions
    instructions = OUTPUT_DIR / "TRAINING.md"
    instructions.write_text(f"""# Custom Wake Word Model Training

## Samples Collected
- **Positive samples:** {NUM_POSITIVE} recordings across {len(phrases)} phrases
- **Negative samples:** {NUM_NEGATIVE} ambient noise recordings
- **Location:** `{OUTPUT_DIR}`

## Training with livekit-wakeword

### 1. Install dependencies
```bash
pip install livekit-wakeword[train,eval,export,listener]
```

### 2. Add your samples to the training config
Edit `configs/lumi.yaml` and add your sample directory:

```yaml
# Add this section
user_samples:
  positive_dir: data/wake_samples/positive
  negative_dir: data/wake_samples/negative
```

### 3. Run training
```bash
livekit-wakeword run configs/lumi.yaml
```

This will:
- Generate synthetic samples using TTS
- Augment with your real voice samples
- Train the Conv-Attention model
- Export to ONNX

### 4. The trained model will be at:
`data/wakeword_models/hey_lumi.onnx`

### 5. Update Lumi to use your model
Edit `core/wake_word.py` and set:
```python
MODEL_PATH = Path(__file__).parent.parent / "data" / "wakeword_models" / "hey_lumi.onnx"
```

## Tips for Better Accuracy
1. Record in the environment where you'll use Lumi (background noise matters)
2. Say the wake word naturally - don't over-enunciate
3. Include variations in pitch, speed, and volume
4. Record some false positives (similar-sounding phrases) as negatives
5. Aim for 100+ positive samples for best results
""")

    print(f"\n{'=' * 60}")
    print(f"  Done! Collected {NUM_POSITIVE} positive + {NUM_NEGATIVE} negative samples")
    print(f"  Saved to: {OUTPUT_DIR}")
    print(f"  Training instructions: {instructions}")
    print(f"{'=' * 60}")
    print()
    print("Next steps:")
    print("  1. Run: pip install livekit-wakeword[train,eval,export,listener]")
    print("  2. Run: livekit-wakeword run configs/lumi.yaml")
    print("  3. Update core/wake_word.py to use your custom model")


if __name__ == "__main__":
    main()
