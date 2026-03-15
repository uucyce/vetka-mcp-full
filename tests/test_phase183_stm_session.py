"""
Phase 183.3 — STM Buffer Session ID Metadata Tests

Tests:
1. add_message with session_id metadata stores correctly
2. get_entries_for_session filters by session_id
3. Pipeline source entries carry session_id + run_id
4. Entries without session_id don't appear in session queries
5. to_dict preserves metadata including session_id
"""

import pytest
from pathlib import Path
from datetime import datetime


def test_stm_add_message_with_session_metadata():
    """STM add_message stores session_id in metadata."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.memory.stm_buffer import STMBuffer

    stm = STMBuffer(max_size=10)
    stm.add_message(
        "Pipeline completed: 3 subtasks",
        source="pipeline",
        metadata={
            "session_id": "sess_1234567890123_abcd1234",
            "run_id": "run_1234567890123_tb_12345678_ef567890",
            "task_id": "tb_1234567890_1",
            "phase_type": "build",
        }
    )

    assert len(stm) == 1
    entry = stm.get_all()[0]
    assert entry.metadata["session_id"] == "sess_1234567890123_abcd1234"
    assert entry.metadata["run_id"].startswith("run_")
    assert entry.source == "pipeline"


def test_get_entries_for_session():
    """get_entries_for_session filters by session_id."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.memory.stm_buffer import STMBuffer

    stm = STMBuffer(max_size=10)

    sid_a = "sess_1111111111111_aaaa1111"
    sid_b = "sess_2222222222222_bbbb2222"

    stm.add_message("Task A done", source="pipeline", metadata={"session_id": sid_a})
    stm.add_message("Task B done", source="pipeline", metadata={"session_id": sid_a})
    stm.add_message("Task C done", source="pipeline", metadata={"session_id": sid_b})
    stm.add_message("User message", source="user")  # no metadata

    results = stm.get_entries_for_session(sid_a)
    assert len(results) == 2
    assert all("Task" in e.content for e in results)

    results_b = stm.get_entries_for_session(sid_b)
    assert len(results_b) == 1
    assert "Task C" in results_b[0].content


def test_session_query_empty():
    """Querying non-existent session returns empty."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.memory.stm_buffer import STMBuffer

    stm = STMBuffer(max_size=10)
    stm.add_message("Hello", source="user")

    results = stm.get_entries_for_session("sess_nonexistent_12345678")
    assert results == []


def test_to_dict_preserves_session_metadata():
    """Serialization preserves session_id in metadata."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.memory.stm_buffer import STMBuffer

    stm = STMBuffer(max_size=10)
    stm.add_message(
        "Pipeline result",
        source="pipeline",
        metadata={"session_id": "sess_test_12345678", "run_id": "run_test"}
    )

    data = stm.to_dict()
    assert len(data["entries"]) == 1
    entry_data = data["entries"][0]
    assert entry_data["metadata"]["session_id"] == "sess_test_12345678"

    # Roundtrip
    stm2 = STMBuffer.from_dict(data)
    assert len(stm2) == 1
    restored = stm2.get_all()[0]
    assert restored.metadata["session_id"] == "sess_test_12345678"


def test_pipeline_metadata_fields():
    """Pipeline STM entries carry task_id and phase_type."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.memory.stm_buffer import STMBuffer

    stm = STMBuffer(max_size=10)
    stm.add_message(
        "Pipeline tb_123 (build): 5 subtasks",
        source="pipeline",
        metadata={
            "session_id": "sess_9999_aabbccdd",
            "run_id": "run_9999_tb_12345_ff001122",
            "task_id": "tb_123",
            "phase_type": "build",
        }
    )

    entry = stm.get_all()[0]
    assert entry.metadata["task_id"] == "tb_123"
    assert entry.metadata["phase_type"] == "build"
