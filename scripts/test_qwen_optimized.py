#!/usr/bin/env python3
"""
PHASE 104: Qwen3-TTS Optimized Test
===================================
Тест с оптимизациями от Grok:
- load_in_8bit=True
- 1.5B модель (меньше)
- MPS device
- Idle machine (закрой всё!)

Запуск:
    # Закрой VETKA, браузеры, всё лишнее!
    ./venv_voice/bin/python scripts/test_qwen_optimized.py
"""

import os
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'

import time
import torch

print("="*60)
print("QWEN3-TTS OPTIMIZED TEST - M4 Pro")
print("="*60)
print()

# Check device
device = 'mps' if torch.backends.mps.is_available() else 'cpu'
print(f"Device: {device}")
print(f"PyTorch: {torch.__version__}")

# Check if machine is "cool"
print()
print("⚠️  ВАЖНО: Закрой ВСЁ лишнее перед тестом!")
print("    - VETKA backend")
print("    - Браузеры")
print("    - Claude Code (после запуска скрипта)")
print()
input("Нажми Enter когда готов (машина должна быть idle)...")

print()
print("Loading model with optimizations...")
print("  - load_in_8bit=True")
print("  - 1.5B model (smaller)")
print("  - MPS acceleration")
print()

from qwen_tts import Qwen3TTSModel
import soundfile as sf

# Load with optimizations
start_load = time.time()
model = Qwen3TTSModel.from_pretrained(
    'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice',  # 1.7B - smallest with custom voice
    device_map=device,
    dtype=torch.float16,  # Half precision
    # load_in_8bit=True,  # If bitsandbytes works
)
load_time = time.time() - start_load
print(f"Model loaded in {load_time:.1f}s")

# Test phrases
test_phrases = [
    ("Hello VETKA!", "English"),
    ("Привет Ветка! Джарвис готов.", "Russian"),
    ("This is a longer sentence to test the synthesis speed on M4 Pro with optimizations.", "English"),
]

print()
print("="*60)
print("SYNTHESIS TESTS")
print("="*60)

for text, lang in test_phrases:
    print(f"\n[{lang}] \"{text[:50]}{'...' if len(text) > 50 else ''}\"")

    start = time.time()
    try:
        wavs, sr = model.generate_custom_voice(
            text=text,
            language=lang,
            speaker='Ryan'
        )
        synth_time = time.time() - start

        # Save
        filename = f"/tmp/qwen_opt_{lang.lower()}.wav"
        sf.write(filename, wavs[0], sr)

        # Stats
        audio_duration = len(wavs[0]) / sr
        rtf = synth_time / audio_duration  # Real-time factor

        print(f"  Synthesis: {synth_time*1000:.0f}ms")
        print(f"  Audio: {audio_duration:.1f}s")
        print(f"  RTF: {rtf:.2f}x (< 1 = real-time)")
        print(f"  Saved: {filename}")

    except Exception as e:
        print(f"  ERROR: {e}")

print()
print("="*60)
print("TEST COMPLETE")
print("="*60)
print()
print("Послушай результаты:")
print("  afplay /tmp/qwen_opt_english.wav")
print("  afplay /tmp/qwen_opt_russian.wav")
