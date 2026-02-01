#!/usr/bin/env python3
"""
Test script for Phase 104.6 - ELISION STM Integration

Tests:
1. _add_to_stm with large results (compression)
2. _add_to_stm with small results (no compression)
3. _get_stm_summary decompression
4. _get_stm_memory_stats calculation
5. Memory savings logging

MARKER_104_MEMORY_STM
"""

import sys
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.orchestration.agent_pipeline import AgentPipeline
from src.memory.elision import get_elision_compressor


def test_stm_compression():
    """Test STM compression with large results"""
    print("\n" + "="*70)
    print("TEST 1: STM Compression with Large Results")
    print("="*70)

    pipeline = AgentPipeline()

    # Create a large JSON-structured result with keys that compress well
    # ELISION works better with structured JSON
    large_result_dict = {
        "message": "Analysis complete",
        "results": [
            {
                "file_path": "/src/orchestration/agent_pipeline.py",
                "file_type": "python",
                "imports": ["json", "asyncio", "logging", "pathlib"],
                "summary": "Agent pipeline orchestration system"
            } for _ in range(30)  # 30 similar entries
        ],
        "context": {
            "current_file": "/src/memory/elision.py",
            "dependencies": ["json", "re", "dataclasses", "pathlib"],
            "timestamp": "2026-02-01T10:00:00"
        }
    }

    large_result = json.dumps(large_result_dict, indent=2)
    logger.info(f"Input size: {len(large_result)} chars")

    # Add to STM
    pipeline._add_to_stm("step_1_large", large_result)

    # Verify compression
    stm_entry = pipeline.stm[0]
    print(f"\nSTM Entry structure:")
    print(f"  Marker: {stm_entry['marker']}")
    print(f"  Compressed: {stm_entry['compressed']}")

    if stm_entry['compressed']:
        print(f"  Original size: {stm_entry.get('original_size', 0)} chars")
        print(f"  Compressed size: {stm_entry.get('compressed_size', 0)} chars")
        print(f"  Compression ratio: {stm_entry.get('compression_ratio', 0)}x")
        print(f"  Tokens saved: ~{stm_entry.get('tokens_saved', 0)}")
        assert stm_entry.get('level') == 2, "Expected compression level 2"
        # For structured JSON with repeated keys, we should see some savings
        assert stm_entry.get('compression_ratio', 1.0) >= 1.1, "Expected compression ratio >= 1.1x"
        print(f"\n✅ Large result compressed successfully!")
    else:
        print(f"❌ Large result was NOT compressed!")
        return False

    return True


def test_stm_truncation():
    """Test STM truncation with small results"""
    print("\n" + "="*70)
    print("TEST 2: STM Truncation with Small Results")
    print("="*70)

    pipeline = AgentPipeline()

    # Create a small result (< 1000 chars)
    small_result = "This is a small result that should be truncated to 500 chars."

    logger.info(f"Input size: {len(small_result)} chars")

    # Add to STM
    pipeline._add_to_stm("step_1_small", small_result)

    # Verify no compression
    stm_entry = pipeline.stm[0]
    print(f"\nSTM Entry structure:")
    print(f"  Marker: {stm_entry['marker']}")
    print(f"  Compressed: {stm_entry['compressed']}")
    print(f"  Result length: {len(stm_entry['result'])} chars")

    assert not stm_entry['compressed'], "Small results should not be compressed"
    assert len(stm_entry['result']) <= 500, "Result should be truncated to 500 chars"
    print(f"\n✅ Small result handled correctly (no compression)!")

    return True


def test_stm_summary():
    """Test STM summary with decompression"""
    print("\n" + "="*70)
    print("TEST 3: STM Summary with Decompression")
    print("="*70)

    pipeline = AgentPipeline()

    # Add multiple results
    large_result = "This is large. " * 100  # ~1500 chars
    small_result = "Small result"
    another_large = "Another large result. " * 100  # ~2300 chars

    pipeline._add_to_stm("step_1", large_result)
    pipeline._add_to_stm("step_2", small_result)
    pipeline._add_to_stm("step_3", another_large)

    # Get summary
    summary = pipeline._get_stm_summary()
    print(f"\nSTM Summary:\n{summary}")

    # Verify summary structure
    assert "Previous results:" in summary, "Summary should start with header"
    assert "step_1" in summary, "Summary should contain step_1 marker"
    assert "step_2" in summary, "Summary should contain step_2 marker"
    assert "step_3" in summary, "Summary should contain step_3 marker"
    print(f"\n✅ STM summary generated successfully!")

    return True


def test_stm_memory_stats():
    """Test STM memory statistics calculation"""
    print("\n" + "="*70)
    print("TEST 4: STM Memory Statistics")
    print("="*70)

    pipeline = AgentPipeline()

    # Add mixed results with structured JSON for better compression
    large1 = json.dumps({
        "file_path": "/src/orchestration/agent_pipeline.py" * 20,
        "imports": ["json", "asyncio", "logging"] * 30,
        "data": ["entry" * 50 for _ in range(25)]
    })

    large2 = json.dumps({
        "file_path": "/src/memory/elision.py" * 20,
        "functions": ["compress", "expand", "compress_keys"] * 30,
        "results": ["result" * 50 for _ in range(20)]
    })

    small = "Small"

    pipeline._add_to_stm("large_1", large1)
    pipeline._add_to_stm("large_2", large2)
    pipeline._add_to_stm("small_1", small)

    # Get stats
    stats = pipeline._get_stm_memory_stats()

    print(f"\nMemory Statistics:")
    print(f"  Total entries: {stats['num_entries']}")
    print(f"  Compressed entries: {stats['num_compressed']}")
    print(f"  Total original size: {stats['total_original_size']} chars")
    print(f"  Total compressed size: {stats['total_compressed_size']} chars")
    print(f"  Compression ratio: {stats['compression_ratio']}x")
    print(f"  Tokens saved: ~{stats['tokens_saved_estimate']}")

    # Verify stats
    assert stats['num_entries'] == 3, "Should have 3 entries"
    assert stats['num_compressed'] == 2, "Should have 2 compressed entries"
    assert stats['compression_ratio'] > 0, "Should have positive compression ratio"
    # With structured JSON, we should see some compression benefits
    if stats['num_compressed'] > 0:
        assert stats['compression_ratio'] >= 1.0, "Compression ratio should be >= 1.0"

    print(f"\n✅ Memory statistics calculated correctly!")

    return True


def test_stm_eviction():
    """Test STM eviction when limit exceeded"""
    print("\n" + "="*70)
    print("TEST 5: STM Eviction at Limit")
    print("="*70)

    pipeline = AgentPipeline()
    pipeline.stm_limit = 3  # Small limit for testing

    # Add more entries than limit
    for i in range(5):
        result = f"Result {i} " * 100  # ~1000 chars
        pipeline._add_to_stm(f"step_{i}", result)

    print(f"\nSTM limit: {pipeline.stm_limit}")
    print(f"Actual STM entries: {len(pipeline.stm)}")

    # Verify limit enforced
    assert len(pipeline.stm) == 3, f"STM should respect limit, got {len(pipeline.stm)}"

    # Verify correct entries kept (last 3)
    markers = [entry['marker'] for entry in pipeline.stm]
    expected = ['step_2', 'step_3', 'step_4']
    assert markers == expected, f"Expected {expected}, got {markers}"

    print(f"✅ STM eviction working correctly!")
    print(f"   Kept entries: {markers}")

    return True


def test_stm_logging():
    """Test STM memory logging"""
    print("\n" + "="*70)
    print("TEST 6: STM Memory Logging")
    print("="*70)

    pipeline = AgentPipeline()

    # Add some results
    for i in range(3):
        result = f"Result {i} content. " * 80  # ~1600 chars
        pipeline._add_to_stm(f"step_{i}", result)

    # Call logging method
    print(f"\nCalling _log_stm_summary()...")
    pipeline._log_stm_summary()

    # Get stats for validation
    stats = pipeline._get_stm_memory_stats()
    print(f"\nVerification:")
    print(f"  Entries logged: {stats['num_entries']}")
    print(f"  Compressed: {stats['num_compressed']}")
    print(f"  Total tokens saved: ~{stats['tokens_saved_estimate']}")

    assert stats['num_entries'] > 0, "Should have entries to log"
    print(f"\n✅ STM logging working correctly!")

    return True


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("PHASE 104.6 - ELISION STM INTEGRATION TEST SUITE")
    print("="*70)

    tests = [
        ("Compression", test_stm_compression),
        ("Truncation", test_stm_truncation),
        ("Summary", test_stm_summary),
        ("Memory Stats", test_stm_memory_stats),
        ("Eviction", test_stm_eviction),
        ("Logging", test_stm_logging),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*70)

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
