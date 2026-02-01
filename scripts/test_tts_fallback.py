#!/usr/bin/env python3
"""
Test script for Phase 105 TTS Fallback Chain.

Run with: ./venv_voice/bin/python3 scripts/test_tts_fallback.py
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.voice.tts_engine import (
    TTSEngine,
    TTSConfig,
    TTSResult,
    TTSError,
    TTSProvider,
    get_tts_engine,
    quick_synthesize,
)


async def test_provider_check():
    """Test checking provider availability."""
    print("\n=== Testing Provider Availability ===")

    engine = TTSEngine(primary="edge")
    availability = await engine.check_providers()

    for provider, available in availability.items():
        status = "Available" if available else "Unavailable"
        print(f"  {provider}: {status}")

    await engine.close()


async def test_edge_synthesis():
    """Test Edge TTS synthesis."""
    print("\n=== Testing Edge TTS Synthesis ===")

    config = TTSConfig(primary_provider="edge", language="en")
    engine = TTSEngine(primary="edge", config=config)

    try:
        result = await engine.synthesize_with_result(
            "Hello! This is a test of the TTS fallback chain."
        )
        print(f"  Provider used: {result.provider}")
        print(f"  Latency: {result.latency_ms:.1f}ms")
        print(f"  Audio size: {len(result.audio)} bytes")
        print(f"  Format: {result.format}")
        print("  SUCCESS!")
    except TTSError as e:
        print(f"  ERROR: {e}")
    finally:
        await engine.close()


async def test_piper_synthesis():
    """Test Piper TTS synthesis."""
    print("\n=== Testing Piper TTS Synthesis ===")

    config = TTSConfig(primary_provider="piper", language="en")
    engine = TTSEngine(primary="piper", config=config)

    try:
        result = await engine.synthesize_with_result(
            "Hello from Piper TTS!"
        )
        print(f"  Provider used: {result.provider}")
        print(f"  Latency: {result.latency_ms:.1f}ms")
        print(f"  Audio size: {len(result.audio)} bytes")
        print("  SUCCESS!")
    except TTSError as e:
        print(f"  ERROR: {e}")
    finally:
        await engine.close()


async def test_fallback_chain():
    """Test the fallback chain behavior."""
    print("\n=== Testing Fallback Chain ===")

    # Start with qwen3 (likely unavailable), should fallback to edge
    config = TTSConfig(primary_provider="qwen3", timeout_ms=500, language="en")
    engine = TTSEngine(primary="qwen3", config=config)

    print(f"  Fallback order: {engine.fallback_order}")

    try:
        result = await engine.synthesize_with_result(
            "Testing the fallback chain mechanism."
        )
        print(f"  Provider used: {result.provider}")
        print(f"  Latency: {result.latency_ms:.1f}ms")

        stats = engine.get_stats()
        print(f"  Stats: {stats}")
        print("  SUCCESS!")
    except TTSError as e:
        print(f"  ERROR: {e}")
    finally:
        await engine.close()


async def test_factory_function():
    """Test the factory function."""
    print("\n=== Testing Factory Function ===")

    engine = get_tts_engine(primary="edge", language="en")

    try:
        audio = await engine.synthesize("Factory function test")
        print(f"  Audio size: {len(audio)} bytes")
        print("  SUCCESS!")
    except TTSError as e:
        print(f"  ERROR: {e}")
    finally:
        await engine.close()


async def main():
    """Run all tests."""
    print("=" * 50)
    print("Phase 105: TTS Fallback Chain Tests")
    print("=" * 50)

    # Check providers
    await test_provider_check()

    # Test individual providers
    await test_edge_synthesis()
    await test_piper_synthesis()

    # Test fallback chain
    await test_fallback_chain()

    # Test factory function
    await test_factory_function()

    print("\n" + "=" * 50)
    print("All tests completed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
