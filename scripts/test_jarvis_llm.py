#!/usr/bin/env python3
"""
Test script for Jarvis LLM integration.

Usage:
    python scripts/test_jarvis_llm.py
    python scripts/test_jarvis_llm.py --prompt "What is VETKA?"
    python scripts/test_jarvis_llm.py --stream

Phase 104.6: Tests Ollama connection and LLM response generation.
"""

import asyncio
import argparse
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_ollama_connection():
    """Test basic Ollama connectivity"""
    from src.voice.jarvis_llm import get_jarvis_llm

    print("\n=== Testing Ollama Connection ===")
    llm = get_jarvis_llm()

    is_ready = await llm.check_ollama()
    if is_ready:
        print("Ollama is running and model is available!")
        return True
    else:
        print("Ollama is not available. Please run:")
        print("  ollama serve")
        print("  ollama pull qwen2.5:3b")
        return False


async def test_generation(prompt: str = "Hello, how are you?"):
    """Test non-streaming generation"""
    from src.voice.jarvis_llm import get_jarvis_llm

    print(f"\n=== Testing Generation ===")
    print(f"Prompt: {prompt}")

    llm = get_jarvis_llm()

    start = time.perf_counter()
    response = await llm.generate(prompt, user_id="test_user")
    duration = time.perf_counter() - start

    print(f"\nResponse ({duration:.2f}s):")
    print(f"  {response}")

    return response


async def test_streaming(prompt: str = "Tell me a short joke"):
    """Test streaming generation"""
    from src.voice.jarvis_llm import get_jarvis_llm

    print(f"\n=== Testing Streaming ===")
    print(f"Prompt: {prompt}")
    print("\nResponse (streaming):")

    llm = get_jarvis_llm()

    start = time.perf_counter()
    first_token_time = None

    async for chunk in llm.generate_stream(prompt, user_id="test_user"):
        if first_token_time is None:
            first_token_time = time.perf_counter() - start
            print(f"  [First token: {first_token_time:.2f}s]")
        print(chunk, end="", flush=True)

    total_time = time.perf_counter() - start
    print(f"\n  [Total: {total_time:.2f}s]")


async def test_with_context():
    """Test generation with VETKA memory context"""
    from src.voice.jarvis_llm import get_jarvis_llm, get_jarvis_context

    print("\n=== Testing with Memory Context ===")

    # First, add something to STM
    try:
        from src.memory.stm_buffer import get_stm_buffer
        stm = get_stm_buffer()
        stm.add_message("We were discussing the VETKA 3D knowledge graph", source="user")
        stm.add_message("VETKA uses a tree metaphor for organizing information", source="agent")
        print("Added test context to STM")
    except Exception as e:
        print(f"Could not add to STM: {e}")

    # Get context
    context = await get_jarvis_context("test_user", "What were we talking about?")
    print(f"\nContext retrieved:")
    for key, value in context.items():
        print(f"  {key}: {str(value)[:100]}...")

    # Generate with context
    llm = get_jarvis_llm()
    response = await llm.generate(
        "What were we just discussing?",
        user_id="test_user",
        context=context
    )
    print(f"\nResponse with context:")
    print(f"  {response}")


async def benchmark(iterations: int = 5):
    """Benchmark LLM latency"""
    from src.voice.jarvis_llm import get_jarvis_llm

    print(f"\n=== Benchmarking ({iterations} iterations) ===")

    llm = get_jarvis_llm()
    prompts = [
        "Hello",
        "What time is it?",
        "Tell me about VETKA",
        "How's the weather?",
        "What can you help me with?"
    ]

    times = []
    for i, prompt in enumerate(prompts[:iterations]):
        start = time.perf_counter()
        await llm.generate(prompt, user_id="bench_user")
        duration = time.perf_counter() - start
        times.append(duration)
        print(f"  [{i+1}] {prompt[:30]}: {duration:.2f}s")

    avg = sum(times) / len(times)
    print(f"\nAverage: {avg:.2f}s")
    print(f"Min: {min(times):.2f}s")
    print(f"Max: {max(times):.2f}s")


async def main():
    parser = argparse.ArgumentParser(description="Test Jarvis LLM")
    parser.add_argument("--prompt", "-p", type=str, default="Hello, how are you?",
                        help="Test prompt")
    parser.add_argument("--stream", "-s", action="store_true",
                        help="Test streaming mode")
    parser.add_argument("--context", "-c", action="store_true",
                        help="Test with memory context")
    parser.add_argument("--benchmark", "-b", action="store_true",
                        help="Run benchmark")
    parser.add_argument("--check", action="store_true",
                        help="Only check Ollama connection")
    args = parser.parse_args()

    # Always check Ollama first
    is_ready = await test_ollama_connection()

    if args.check:
        return

    if not is_ready:
        print("\nCannot proceed without Ollama. Exiting.")
        return

    if args.benchmark:
        await benchmark()
    elif args.context:
        await test_with_context()
    elif args.stream:
        await test_streaming(args.prompt)
    else:
        await test_generation(args.prompt)

    # Cleanup
    from src.voice.jarvis_llm import get_jarvis_llm
    llm = get_jarvis_llm()
    await llm.close()


if __name__ == "__main__":
    asyncio.run(main())
