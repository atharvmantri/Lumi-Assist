import sys
import os
import json
from pathlib import Path

# Configure UTF-8 encoding for stdout on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add workspace to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.intelligence import run_local_llm, embed_text, fine_tune_model, model_benchmark, prompt_optimizer
from tools.vision_audio import ocr_scan, transcribe_audio, translate_speech, video_analysis, sentiment_analysis

def test_model_ops():
    print("Testing Model Operations...")
    
    # 1. run_local_llm (will output server connection error/note since Ollama isn't running)
    print("  Testing run_local_llm...")
    res = run_local_llm("test prompt", base_url="http://localhost:9999")
    print(f"    Result contains error message: {'error' in res}")

    # 2. embed_text (should execute fallback lexical hashing)
    print("  Testing embed_text...")
    res = embed_text("Hello world, this is a test.", base_url="http://localhost:9999")
    data = json.loads(res)
    print(f"    Dimensions: {data['dimensions']}, Source: {data['source']}")

    # 3. fine_tune_model (uses PyTorch local classifier)
    print("  Testing fine_tune_model (PyTorch)...")
    dataset = [
        {"text": "I love this product", "label": 1},
        {"text": "This is excellent and amazing", "label": 1},
        {"text": "Bad service and terrible quality", "label": 0},
        {"text": "I hate this item, it broke", "label": 0}
    ]
    ds_path = "data/test_tune_ds.json"
    model_path = "data/test_tune_model.pt"
    
    Path("data").mkdir(parents=True, exist_ok=True)
    with open(ds_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f)
        
    tune_res = fine_tune_model(ds_path, epochs=3, output_model_path=model_path)
    print(f"    Fine-tune output:\n{tune_res}")
    print(f"    Model saved: {Path(model_path).is_file()}")

    # 4. model_benchmark (queries proxy models)
    print("  Testing model_benchmark...")
    bench_res = model_benchmark("Explain AI in one sentence", models=["meta-llama/Llama-3-70b-instruct"])
    print(f"    Benchmark results contains table: {'Model' in bench_res}")

    # 5. prompt_optimizer
    print("  Testing prompt_optimizer...")
    opt_res = prompt_optimizer("write python code to load file", use_case="code generation")
    print(f"    Optimizer returned text length: {len(opt_res)}")


def test_vision_audio():
    print("\n" + "="*50 + "\n")
    print("Testing Vision & Audio Intelligence...")
    
    # 1. ocr_scan (mock PIL image check)
    print("  Testing ocr_scan...")
    try:
        from PIL import Image, ImageDraw
        # Create a dummy image
        img_path = "data/dummy_text.png"
        img = Image.new("RGB", (200, 50), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((10, 10), "HELLO", fill=(0, 0, 0))
        img.save(img_path)
        
        ocr_res = ocr_scan(img_path)
        print(f"    OCR Result: {ocr_res}")
    except Exception as e:
        print(f"    OCR image creation/run bypassed: {e}")

    # 2. transcribe_audio & translate_speech
    print("  Testing speech pipeline (transcribe + translate_speech)...")
    
    # Let's synthesize a short speech WAV using Windows SAPI TTS if available
    test_wav = "data/speech_test.wav"
    from core.stt import _synthesize_test_wav
    
    print("    Synthesizing SAPI speech file...")
    success = _synthesize_test_wav(Path(test_wav), "Hello, how are you today?")
    if success and Path(test_wav).is_file():
        # Transcribe
        print("    Transcribing audio...")
        trans_res = transcribe_audio(test_wav)
        trans_data = json.loads(trans_res)
        print(f"      Transcript: {trans_data.get('text')}")
        
        # Translate Speech-to-Speech
        print("    Translating speech...")
        trans_speech_res = translate_speech(test_wav, "Spanish")
        trans_speech_data = json.loads(trans_speech_res)
        print(f"      Translated text: {trans_speech_data.get('translated_text')}")
        print(f"      Output audio: {trans_speech_data.get('output_path')}")
    else:
        print("    SAPI synthesis not available, skipping speech round-trip.")

    # 3. video_analysis
    print("  Testing video_analysis...")
    # Test on a dummy path (should report missing/metadata error gracefully)
    vid_res = video_analysis("data/non_existent.mp4")
    print(f"    Video analysis result contains error: {'error' in vid_res}")

    # 4. sentiment_analysis
    print("  Testing sentiment_analysis...")
    sent_res = sentiment_analysis(text="I love this assistant! It is absolutely wonderful.")
    sent_data = json.loads(sent_res)
    print(f"    Sentiment: {sent_data.get('sentiment')}, Score: {sent_data.get('score')}")


if __name__ == "__main__":
    test_model_ops()
    test_vision_audio()
