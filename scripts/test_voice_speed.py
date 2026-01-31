#!/usr/bin/env python3
"""
PHASE 104.0: Voice Speed Test
=============================
Минимальный тест для проверки real-time voice на M4.

Тестируем:
1. STT (Whisper MLX) - время транскрипции
2. TTS (различные варианты) - время синтеза
3. Round-trip: запись → транскрипция → ответ → синтез → воспроизведение

Запуск:
    python scripts/test_voice_speed.py

@phase: 104.0
@status: test
"""

import time
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np

# ============================================
# ANSI Colors for pretty output
# ============================================
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_result(label, time_ms, threshold_ms=500):
    color = Colors.GREEN if time_ms < threshold_ms else Colors.YELLOW if time_ms < 1000 else Colors.RED
    print(f"  {Colors.CYAN}{label}:{Colors.ENDC} {color}{time_ms:.0f}ms{Colors.ENDC}")

def print_ok(text):
    print(f"  {Colors.GREEN}✓{Colors.ENDC} {text}")

def print_fail(text):
    print(f"  {Colors.RED}✗{Colors.ENDC} {text}")

def print_info(text):
    print(f"  {Colors.BLUE}→{Colors.ENDC} {text}")

# ============================================
# TEST 1: Whisper MLX (STT)
# ============================================
def test_whisper_stt():
    print_header("TEST 1: Whisper MLX (Speech-to-Text)")

    try:
        import mlx_whisper
        print_ok("mlx_whisper imported")
    except ImportError:
        print_fail("mlx_whisper not installed. Run: pip install mlx-whisper")
        return None

    # Test model loading time
    print_info("Loading Whisper base model...")
    start = time.time()

    try:
        # Load model (cached after first load)
        model = "mlx-community/whisper-base-mlx"
        load_time = (time.time() - start) * 1000
        print_result("Model load time", load_time, threshold_ms=5000)

        # Create test audio (3 seconds of silence + beep)
        sample_rate = 16000
        duration = 3.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        # Simple tone at 440Hz for 0.5s
        audio = np.zeros_like(t)
        audio[int(0.5*sample_rate):int(1.0*sample_rate)] = np.sin(2 * np.pi * 440 * t[int(0.5*sample_rate):int(1.0*sample_rate)]) * 0.5
        audio = audio.astype(np.float32)

        # Test transcription speed
        print_info("Transcribing 3s audio...")
        start = time.time()
        result = mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=model,
            language="en"
        )
        transcribe_time = (time.time() - start) * 1000
        print_result("Transcription time (3s audio)", transcribe_time, threshold_ms=1000)

        # Calculate real-time factor
        rtf = transcribe_time / (duration * 1000)
        rtf_color = Colors.GREEN if rtf < 0.3 else Colors.YELLOW if rtf < 1.0 else Colors.RED
        print(f"  {Colors.CYAN}Real-time factor:{Colors.ENDC} {rtf_color}{rtf:.2f}x{Colors.ENDC} (< 0.3x = real-time capable)")

        return {
            "load_time_ms": load_time,
            "transcribe_time_ms": transcribe_time,
            "rtf": rtf,
            "success": True
        }

    except Exception as e:
        print_fail(f"Whisper test failed: {e}")
        return {"success": False, "error": str(e)}

# ============================================
# TEST 2: TTS Options
# ============================================
def test_tts_options():
    print_header("TEST 2: TTS Options")

    results = {}

    # Option A: macOS say command (built-in, fast but robotic)
    print(f"\n{Colors.BOLD}Option A: macOS 'say' command{Colors.ENDC}")
    try:
        import subprocess
        test_text = "Hello, I am Jarvis, your AI assistant."

        start = time.time()
        subprocess.run(
            ["say", "-v", "Samantha", "-o", "/tmp/test_voice.aiff", test_text],
            capture_output=True,
            timeout=10
        )
        say_time = (time.time() - start) * 1000
        print_result("Synthesis time", say_time, threshold_ms=500)
        print_ok("macOS say available (built-in, fast, but robotic)")
        results["macos_say"] = {"time_ms": say_time, "available": True}
    except Exception as e:
        print_fail(f"macOS say failed: {e}")
        results["macos_say"] = {"available": False}

    # Option B: pyttsx3 (cross-platform, uses system voices)
    print(f"\n{Colors.BOLD}Option B: pyttsx3{Colors.ENDC}")
    try:
        import pyttsx3
        engine = pyttsx3.init()

        start = time.time()
        engine.save_to_file(test_text, "/tmp/test_pyttsx3.mp3")
        engine.runAndWait()
        pyttsx3_time = (time.time() - start) * 1000
        print_result("Synthesis time", pyttsx3_time, threshold_ms=500)
        print_ok("pyttsx3 available")
        results["pyttsx3"] = {"time_ms": pyttsx3_time, "available": True}
    except ImportError:
        print_fail("pyttsx3 not installed. Run: pip install pyttsx3")
        results["pyttsx3"] = {"available": False}
    except Exception as e:
        print_fail(f"pyttsx3 failed: {e}")
        results["pyttsx3"] = {"available": False}

    # Option C: Coqui TTS (open source, good quality)
    print(f"\n{Colors.BOLD}Option C: Coqui TTS{Colors.ENDC}")
    try:
        from TTS.api import TTS

        print_info("Loading Coqui TTS model (first load downloads ~500MB)...")
        start = time.time()
        tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False)
        load_time = (time.time() - start) * 1000
        print_result("Model load time", load_time, threshold_ms=10000)

        start = time.time()
        tts.tts_to_file(text=test_text, file_path="/tmp/test_coqui.wav")
        synth_time = (time.time() - start) * 1000
        print_result("Synthesis time", synth_time, threshold_ms=2000)
        print_ok("Coqui TTS available (good quality, medium speed)")
        results["coqui"] = {"load_ms": load_time, "synth_ms": synth_time, "available": True}
    except ImportError:
        print_fail("Coqui TTS not installed. Run: pip install TTS")
        results["coqui"] = {"available": False}
    except Exception as e:
        print_fail(f"Coqui TTS failed: {e}")
        results["coqui"] = {"available": False}

    # Option D: OpenAI TTS via API (best quality, requires API key)
    print(f"\n{Colors.BOLD}Option D: OpenAI TTS API{Colors.ENDC}")
    try:
        import openai

        # Check for API key
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            print_info("Testing OpenAI TTS...")
            client = openai.OpenAI()

            start = time.time()
            response = client.audio.speech.create(
                model="tts-1",  # or tts-1-hd for higher quality
                voice="alloy",
                input=test_text
            )
            api_time = (time.time() - start) * 1000
            response.stream_to_file("/tmp/test_openai.mp3")
            print_result("API call + synthesis", api_time, threshold_ms=2000)
            print_ok("OpenAI TTS available (best quality, API cost)")
            results["openai"] = {"time_ms": api_time, "available": True}
        else:
            print_info("OPENAI_API_KEY not set, skipping")
            results["openai"] = {"available": False, "reason": "no_api_key"}
    except ImportError:
        print_fail("openai not installed. Run: pip install openai")
        results["openai"] = {"available": False}
    except Exception as e:
        print_fail(f"OpenAI TTS failed: {e}")
        results["openai"] = {"available": False}

    # Option E: Edge TTS (free, uses Microsoft Edge voices)
    print(f"\n{Colors.BOLD}Option E: Edge TTS (Microsoft){Colors.ENDC}")
    try:
        import edge_tts

        async def test_edge():
            communicate = edge_tts.Communicate(test_text, "en-US-AriaNeural")
            start = time.time()
            await communicate.save("/tmp/test_edge.mp3")
            return (time.time() - start) * 1000

        edge_time = asyncio.run(test_edge())
        print_result("Synthesis time", edge_time, threshold_ms=1500)
        print_ok("Edge TTS available (good quality, free, requires internet)")
        results["edge"] = {"time_ms": edge_time, "available": True}
    except ImportError:
        print_fail("edge-tts not installed. Run: pip install edge-tts")
        results["edge"] = {"available": False}
    except Exception as e:
        print_fail(f"Edge TTS failed: {e}")
        results["edge"] = {"available": False}

    return results

# ============================================
# TEST 3: Audio Recording (microphone)
# ============================================
def test_audio_recording():
    print_header("TEST 3: Audio Recording")

    try:
        import sounddevice as sd
        print_ok("sounddevice available")

        # List audio devices
        print_info("Available input devices:")
        devices = sd.query_devices()
        for i, d in enumerate(devices):
            if d['max_input_channels'] > 0:
                print(f"    [{i}] {d['name']} ({d['max_input_channels']} channels)")

        # Test short recording
        print_info("Recording 1 second of audio...")
        start = time.time()
        audio = sd.rec(int(16000 * 1), samplerate=16000, channels=1, dtype='float32')
        sd.wait()
        record_time = (time.time() - start) * 1000
        print_result("Recording time (1s)", record_time, threshold_ms=1200)

        return {"available": True, "record_time_ms": record_time}

    except ImportError:
        print_fail("sounddevice not installed. Run: pip install sounddevice")
        return {"available": False}
    except Exception as e:
        print_fail(f"Audio recording failed: {e}")
        return {"available": False, "error": str(e)}

# ============================================
# TEST 4: Full Round-Trip (simulated)
# ============================================
def test_full_roundtrip():
    print_header("TEST 4: Full Round-Trip Simulation")

    print_info("Simulating: Record → Transcribe → Generate → Speak")

    # Typical timings based on previous tests
    timings = {
        "record": 3000,  # 3 seconds of speech
        "transcribe": 500,  # Whisper on M4
        "llm_response": 1500,  # OpenRouter API call
        "tts_synthesis": 800,  # Best TTS option
        "playback": 2000,  # 2 seconds of response audio
    }

    total = sum(timings.values())

    print(f"\n  {Colors.BOLD}Estimated latencies:{Colors.ENDC}")
    for step, ms in timings.items():
        print(f"    {step}: {ms}ms")

    print(f"\n  {Colors.BOLD}Total round-trip:{Colors.ENDC} {Colors.CYAN}{total}ms{Colors.ENDC}")
    print(f"  {Colors.BOLD}User-perceived delay:{Colors.ENDC} {Colors.CYAN}{total - timings['record'] - timings['playback']}ms{Colors.ENDC}")

    perceived_delay = total - timings['record'] - timings['playback']
    if perceived_delay < 1500:
        print(f"\n  {Colors.GREEN}✓ Real-time conversation POSSIBLE!{Colors.ENDC}")
    elif perceived_delay < 3000:
        print(f"\n  {Colors.YELLOW}~ Acceptable delay for voice assistant{Colors.ENDC}")
    else:
        print(f"\n  {Colors.RED}✗ Too slow for real-time conversation{Colors.ENDC}")

    return {"total_ms": total, "perceived_delay_ms": perceived_delay}

# ============================================
# MAIN
# ============================================
def main():
    print(f"""
{Colors.BOLD}{Colors.HEADER}
╔═══════════════════════════════════════════════════════════╗
║           VETKA Voice Module Speed Test                   ║
║                   Phase 104.0                             ║
╚═══════════════════════════════════════════════════════════╝
{Colors.ENDC}
Testing voice capabilities on your machine...
""")

    results = {}

    # Run tests
    results["stt"] = test_whisper_stt()
    results["tts"] = test_tts_options()
    results["recording"] = test_audio_recording()
    results["roundtrip"] = test_full_roundtrip()

    # Summary
    print_header("SUMMARY & RECOMMENDATIONS")

    # Best TTS option
    tts_results = results.get("tts", {})
    available_tts = [(k, v) for k, v in tts_results.items() if v.get("available")]

    if available_tts:
        print(f"\n{Colors.BOLD}Available TTS options:{Colors.ENDC}")
        for name, data in available_tts:
            time_ms = data.get("time_ms") or data.get("synth_ms", "N/A")
            print(f"  • {name}: {time_ms}ms")

        # Recommend based on speed
        fastest = min(available_tts, key=lambda x: x[1].get("time_ms") or x[1].get("synth_ms", 99999))
        print(f"\n{Colors.GREEN}Recommended TTS: {fastest[0]}{Colors.ENDC}")

    # Overall verdict
    stt_ok = results.get("stt", {}).get("success", False)
    tts_ok = len(available_tts) > 0
    rec_ok = results.get("recording", {}).get("available", False)

    print(f"\n{Colors.BOLD}Components ready:{Colors.ENDC}")
    print(f"  STT (Whisper MLX): {'✓' if stt_ok else '✗'}")
    print(f"  TTS: {'✓' if tts_ok else '✗'}")
    print(f"  Audio Recording: {'✓' if rec_ok else '✗'}")

    if stt_ok and tts_ok and rec_ok:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 All components ready! Voice module can proceed.{Colors.ENDC}")
    else:
        print(f"\n{Colors.YELLOW}Some components missing. See details above.{Colors.ENDC}")

    return results

if __name__ == "__main__":
    main()
