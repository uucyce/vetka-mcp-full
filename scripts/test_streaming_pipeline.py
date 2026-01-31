#!/usr/bin/env python3
"""
Test script for Streaming LLM → TTS Pipeline.

Measures time to first audio chunk (target: <2s).

Usage:
    python scripts/test_streaming_pipeline.py
    python scripts/test_streaming_pipeline.py --prompt "Tell me about VETKA"
"""

import asyncio
import argparse
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_streaming(prompt: str = "Tell me a short story about a robot"):
    """Test streaming pipeline"""
    from src.voice.streaming_pipeline import get_streaming_pipeline
    from src.api.handlers.jarvis_handler import pcm_to_wav

    print(f"\n=== Testing Streaming Pipeline ===")
    print(f"Prompt: {prompt}")

    pipeline = get_streaming_pipeline()

    start = time.perf_counter()
    first_audio_time = None
    total_audio_bytes = 0
    chunks = []

    print("\nStreaming response:")
    print("-" * 50)

    try:
        async for audio_bytes, text_chunk in pipeline.generate(prompt, user_id="test_user"):
            current_time = time.perf_counter() - start

            if first_audio_time is None:
                first_audio_time = current_time
                print(f"\n  [First audio at {first_audio_time:.2f}s]")

            total_audio_bytes += len(audio_bytes)
            chunks.append((audio_bytes, text_chunk))

            print(f"  [{current_time:.2f}s] {text_chunk}")

    except Exception as e:
        print(f"\nError: {e}")
        return

    total_time = time.perf_counter() - start

    print("-" * 50)
    print(f"\n=== Results ===")
    print(f"First audio: {first_audio_time:.2f}s (target: <2s)")
    print(f"Total time: {total_time:.2f}s")
    print(f"Chunks: {len(chunks)}")
    print(f"Total audio: {total_audio_bytes / 1024:.1f} KB")

    # Calculate improvement
    if first_audio_time:
        # Estimate what non-streaming would be
        estimated_non_streaming = total_time + 2  # LLM would need to finish first
        improvement = ((estimated_non_streaming - first_audio_time) / estimated_non_streaming) * 100
        print(f"\nEstimated improvement: ~{improvement:.0f}% faster perceived response")

    # Save combined audio for testing
    if chunks:
        print("\nSaving combined audio to /tmp/streaming_test.wav...")
        combined_pcm = b''.join([c[0] for c in chunks])
        wav_data = pcm_to_wav(combined_pcm, sample_rate=24000)
        with open("/tmp/streaming_test.wav", "wb") as f:
            f.write(wav_data)
        print(f"Saved {len(wav_data)} bytes")

    await pipeline.close()


async def benchmark(iterations: int = 3):
    """Benchmark streaming vs non-streaming"""
    from src.voice.jarvis_llm import get_jarvis_llm
    from src.voice.streaming_pipeline import get_streaming_pipeline

    print(f"\n=== Benchmarking ({iterations} iterations) ===")

    prompts = [
        "Hello",
        "What is two plus two?",
        "Tell me about AI"
    ]

    streaming_first_audio = []
    non_streaming_total = []

    llm = get_jarvis_llm()
    pipeline = get_streaming_pipeline()

    for i, prompt in enumerate(prompts[:iterations]):
        print(f"\n[{i+1}] Prompt: {prompt}")

        # Test non-streaming (just LLM, no TTS for fair comparison)
        start = time.perf_counter()
        response = await llm.generate(prompt, user_id="bench_user")
        llm_time = time.perf_counter() - start
        non_streaming_total.append(llm_time)
        print(f"    Non-streaming LLM: {llm_time:.2f}s")

        # Test streaming (first audio)
        start = time.perf_counter()
        first_audio = None
        async for audio, text in pipeline.generate(prompt, user_id="bench_user"):
            if first_audio is None:
                first_audio = time.perf_counter() - start
                break  # Just measure first chunk

        if first_audio:
            streaming_first_audio.append(first_audio)
            print(f"    Streaming first audio: {first_audio:.2f}s")

    if streaming_first_audio and non_streaming_total:
        print(f"\n=== Summary ===")
        print(f"Non-streaming avg: {sum(non_streaming_total)/len(non_streaming_total):.2f}s")
        print(f"Streaming first audio avg: {sum(streaming_first_audio)/len(streaming_first_audio):.2f}s")

    await pipeline.close()
    await llm.close()


async def main():
    parser = argparse.ArgumentParser(description="Test Streaming Pipeline")
    parser.add_argument("--prompt", "-p", type=str,
                        default="Tell me a short story about a robot learning to speak",
                        help="Test prompt")
    parser.add_argument("--benchmark", "-b", action="store_true",
                        help="Run benchmark comparison")
    args = parser.parse_args()

    if args.benchmark:
        await benchmark()
    else:
        await test_streaming(args.prompt)


if __name__ == "__main__":
    asyncio.run(main())
