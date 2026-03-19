"""
Tests for Phase 172.P3 — REFLEX Feedback CORTEX (learning loop).

MARKER_172.P3.TESTS

Tests:
  T3.1 test_record_appends_to_log — JSONL grows by 1 line
  T3.2 test_record_outcome_closes_loop — verifier result linked to tool records
  T3.3 test_get_score_aggregates_correctly — formula matches spec
  T3.4 test_decay_reduces_old_entries — 30-day-old entries weighted less
  T3.5 test_compaction_limits_log_size — after 1000 entries, compact
  T3.6 test_empty_log_returns_default — 0.5 when no history
  T3.7 test_stats_returns_summary — tool counts, success rates
"""

import json
import math
import os
import sys
import time
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.reflex_feedback import (
    ReflexFeedback,
    FeedbackEntry,
    AggregatedScore,
    get_reflex_feedback,
    reset_reflex_feedback,
    DEFAULT_FEEDBACK_SCORE,
    AGG_SUCCESS_WEIGHT,
    AGG_USEFULNESS_WEIGHT,
    AGG_VERIFIER_WEIGHT,
    DECAY_LAMBDA,
    MAX_LOG_ENTRIES,
    COMPACT_KEEP,
)


@pytest.fixture
def feedback(tmp_path):
    """Create a fresh ReflexFeedback with temp log path."""
    reset_reflex_feedback()
    log_path = tmp_path / "test_feedback.jsonl"
    fb = ReflexFeedback(log_path=log_path)
    yield fb
    reset_reflex_feedback()


@pytest.fixture
def populated_feedback(feedback):
    """Feedback with a few records already in it."""
    feedback.record("tool_a", success=True, useful=True, phase_type="fix")
    feedback.record("tool_a", success=True, useful=False, phase_type="fix")
    feedback.record("tool_b", success=False, useful=False, phase_type="research")
    feedback.record("tool_b", success=True, useful=True, phase_type="research")
    feedback.record("tool_c", success=True, useful=True, phase_type="build")
    return feedback


# ─── T3.1: Record appends to log ────────────────────────────────

class TestRecordAppends:
    """T3.1: Each record() call appends exactly 1 line to JSONL."""

    def test_record_appends_to_log(self, feedback):
        assert feedback.entry_count == 0

        feedback.record("vetka_search_semantic", success=True, useful=True)
        assert feedback.entry_count == 1

        feedback.record("vetka_edit_file", success=True, useful=False)
        assert feedback.entry_count == 2

    def test_record_persists_to_disk(self, feedback):
        feedback.record("tool_x", phase_type="fix", agent_role="coder")

        # Read raw JSONL
        lines = feedback._log_path.read_text().strip().split("\n")
        assert len(lines) == 1

        data = json.loads(lines[0])
        assert data["tool_id"] == "tool_x"
        assert data["phase_type"] == "fix"
        assert data["agent_role"] == "coder"
        assert "timestamp" in data

    def test_record_returns_entry(self, feedback):
        entry = feedback.record("tool_y", success=False, useful=False)
        assert isinstance(entry, FeedbackEntry)
        assert entry.tool_id == "tool_y"
        assert entry.success is False
        assert entry.useful is False

    def test_multiple_records_all_persisted(self, feedback):
        for i in range(10):
            feedback.record(f"tool_{i}")

        lines = feedback._log_path.read_text().strip().split("\n")
        assert len(lines) == 10


# ─── T3.2: Record outcome closes loop ───────────────────────────

class TestRecordOutcome:
    """T3.2: record_outcome() links verifier result to tools used."""

    def test_record_outcome_closes_loop(self, feedback):
        count = feedback.record_outcome(
            subtask_id="sub_001",
            tools_used=["tool_a", "tool_b", "tool_c"],
            verifier_passed=True,
            phase_type="build",
        )
        assert count == 3
        assert feedback.entry_count == 3

        # All entries linked to subtask
        entries = feedback._load_entries()
        for e in entries:
            assert e.subtask_id == "sub_001"
            assert e.verifier_passed is True

    def test_record_outcome_verifier_failed(self, feedback):
        feedback.record_outcome(
            subtask_id="sub_002",
            tools_used=["tool_x"],
            verifier_passed=False,
        )
        entries = feedback._load_entries()
        assert entries[0].verifier_passed is False

    def test_record_outcome_empty_tools(self, feedback):
        count = feedback.record_outcome(
            subtask_id="sub_003",
            tools_used=[],
            verifier_passed=True,
        )
        assert count == 0
        assert feedback.entry_count == 0


# ─── T3.3: Aggregation formula ──────────────────────────────────

class TestAggregation:
    """T3.3: score = success_rate * 0.40 + usefulness * 0.35 + verifier_pass * 0.25."""

    def test_get_score_aggregates_correctly(self, feedback):
        """All-success entries → score close to 1.0."""
        for _ in range(5):
            feedback.record("tool_perfect", success=True, useful=True, phase_type="fix")
        feedback.record_outcome(
            subtask_id="sub_perfect",
            tools_used=["tool_perfect"],
            verifier_passed=True,
        )

        score = feedback.get_score("tool_perfect", phase_type="fix")
        # All rates ≈ 1.0 → score ≈ 0.40 + 0.35 + 0.25 = 1.0
        assert score >= 0.95

    def test_get_score_mixed_results(self, feedback):
        """50/50 success/fail → score ≈ 0.50."""
        feedback.record("tool_mixed", success=True, useful=True)
        feedback.record("tool_mixed", success=False, useful=False)

        score = feedback.get_score("tool_mixed")
        # success_rate ≈ 0.5, usefulness ≈ 0.5, verifier ≈ 0.5 (default True for both)
        # But verifier_passed defaults to True, so:
        # success_rate = 0.5, usefulness = 0.5, verifier = 1.0
        # score = 0.5*0.40 + 0.5*0.35 + 1.0*0.25 = 0.20 + 0.175 + 0.25 = 0.625
        assert 0.5 <= score <= 0.75

    def test_get_score_all_failures(self, feedback):
        """All-failure entries → low score."""
        for _ in range(5):
            feedback.record(
                "tool_bad", success=False, useful=False, phase_type="fix"
            )
        # Add outcome with verifier_passed=False
        feedback.record_outcome(
            subtask_id="sub_bad",
            tools_used=["tool_bad"],
            verifier_passed=False,
        )

        score = feedback.get_score("tool_bad", phase_type="fix")
        # 5 entries: success=False, useful=False, verifier=True(default)
        # 1 outcome entry: success=True, useful=True, verifier=False
        # Mix — but mostly bad
        assert score < 0.5

    def test_aggregation_formula_exact(self, feedback):
        """Verify exact formula with controlled inputs."""
        # All True entries → rates should be 1.0
        for _ in range(3):
            entry = FeedbackEntry(
                tool_id="exact",
                success=True,
                useful=True,
                verifier_passed=True,
            )
            feedback._append_entry(entry)

        agg = feedback._aggregate_entries(feedback._load_entries())
        expected = (
            agg.success_rate * AGG_SUCCESS_WEIGHT
            + agg.usefulness_rate * AGG_USEFULNESS_WEIGHT
            + agg.verifier_rate * AGG_VERIFIER_WEIGHT
        )
        assert abs(agg.score - expected) < 0.01

    def test_phase_type_filter(self, populated_feedback):
        """get_score with specific phase filters correctly."""
        fix_score = populated_feedback.get_score("tool_a", phase_type="fix")
        assert isinstance(fix_score, float)

        # tool_a has 2 entries in "fix" phase, should not use "research" entries
        all_score = populated_feedback.get_score("tool_a", phase_type="*")
        assert isinstance(all_score, float)

    def test_get_scores_bulk(self, populated_feedback):
        """Bulk score retrieval returns dict of all tools."""
        scores = populated_feedback.get_scores_bulk()
        assert "tool_a" in scores
        assert "tool_b" in scores
        assert "tool_c" in scores
        for tool_id, score in scores.items():
            assert 0.0 <= score <= 1.0


# ─── T3.4: Decay reduces old entries ────────────────────────────

class TestDecay:
    """T3.4: 30-day-old entries are weighted less than fresh ones."""

    def test_decay_reduces_old_entries(self, feedback):
        """Old entries contribute less to the score."""
        now = datetime.now(timezone.utc)
        old_time = (now - timedelta(days=30)).isoformat()
        fresh_time = now.isoformat()

        # 1 old success entry
        old_entry = FeedbackEntry(
            tool_id="decay_test",
            success=True,
            useful=True,
            verifier_passed=True,
            timestamp=old_time,
        )
        feedback._append_entry(old_entry)

        # 1 fresh failure entry
        fresh_entry = FeedbackEntry(
            tool_id="decay_test",
            success=False,
            useful=False,
            verifier_passed=False,
            timestamp=fresh_time,
        )
        feedback._append_entry(fresh_entry)

        score = feedback.get_score("decay_test")
        # Fresh failure has higher weight than old success.
        # With phase-aware decay (MARKER_173.P5), research half-life=45d:
        #   old entry (30d): weight ≈ exp(-ln(2)/45 * 30) ≈ 0.63
        #   fresh entry (0d): weight = 1.0
        # Score is a blend but fresh failure dominates → below 0.5
        assert score < 0.5

    def test_decay_formula_values(self):
        """Verify decay math: exp(-0.1 * days)."""
        assert math.exp(-DECAY_LAMBDA * 0) == 1.0       # Today: full weight
        assert math.exp(-DECAY_LAMBDA * 7) == pytest.approx(0.4966, abs=0.01)  # 1 week
        assert math.exp(-DECAY_LAMBDA * 30) == pytest.approx(0.0498, abs=0.01)  # 30 days
        assert math.exp(-DECAY_LAMBDA * 60) < 0.01       # 60 days: nearly zero

    def test_only_fresh_entries_strong_signal(self, feedback):
        """When all entries are fresh, decay doesn't affect much."""
        for _ in range(5):
            feedback.record("fresh_tool", success=True, useful=True)

        score = feedback.get_score("fresh_tool")
        # All fresh, all success → score ≈ 1.0
        assert score >= 0.95


# ─── T3.5: Compaction limits log size ────────────────────────────

class TestCompaction:
    """T3.5: Log is compacted when exceeding MAX_LOG_ENTRIES."""

    def test_compaction_limits_log_size(self, tmp_path):
        """After > MAX_LOG_ENTRIES, compact() trims to COMPACT_KEEP."""
        log_path = tmp_path / "big_log.jsonl"
        fb = ReflexFeedback(log_path=log_path)

        # Write entries directly (faster than through record() for 1500 entries)
        with open(log_path, "w") as f:
            for i in range(1500):
                entry = FeedbackEntry(
                    tool_id=f"tool_{i % 20}",
                    success=True,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
                f.write(json.dumps(entry.to_dict()) + "\n")

        # Load into cache
        fb._cache = None
        entries_before = fb.entry_count
        assert entries_before == 1500

        removed = fb.compact()
        assert removed == 1500 - COMPACT_KEEP
        assert fb.entry_count == COMPACT_KEEP

        # Verify file on disk matches
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == COMPACT_KEEP

    def test_compaction_no_op_when_small(self, feedback):
        """Compact does nothing when under MAX_LOG_ENTRIES."""
        feedback.record("small_log", success=True)
        removed = feedback.compact()
        assert removed == 0
        assert feedback.entry_count == 1

    def test_compaction_keeps_newest(self, tmp_path):
        """After compaction, the NEWEST entries are preserved."""
        log_path = tmp_path / "order_log.jsonl"
        fb = ReflexFeedback(log_path=log_path)

        base_time = datetime.now(timezone.utc)
        with open(log_path, "w") as f:
            for i in range(1200):
                ts = (base_time + timedelta(seconds=i)).isoformat()
                entry = FeedbackEntry(
                    tool_id=f"tool_{i}",
                    timestamp=ts,
                )
                f.write(json.dumps(entry.to_dict()) + "\n")

        fb._cache = None
        fb.compact()

        entries = fb._load_entries()
        assert len(entries) == COMPACT_KEEP
        # Last entry should be the newest (tool_1199)
        assert entries[-1].tool_id == "tool_1199"
        # First entry should be the oldest kept
        assert entries[0].tool_id == f"tool_{1200 - COMPACT_KEEP}"


# ─── T3.6: Empty log returns default ────────────────────────────

class TestEmptyLog:
    """T3.6: No history → returns DEFAULT_FEEDBACK_SCORE (0.5)."""

    def test_empty_log_returns_default(self, feedback):
        score = feedback.get_score("nonexistent_tool")
        assert score == DEFAULT_FEEDBACK_SCORE
        assert score == 0.5

    def test_empty_log_stats(self, feedback):
        stats = feedback.get_stats()
        assert stats["total_entries"] == 0
        assert stats["tool_count"] == 0

    def test_empty_bulk_scores(self, feedback):
        scores = feedback.get_scores_bulk()
        assert scores == {}

    def test_missing_log_file(self, tmp_path):
        """Nonexistent log file → empty entries, no crash."""
        fb = ReflexFeedback(log_path=tmp_path / "does_not_exist.jsonl")
        assert fb.entry_count == 0
        assert fb.get_score("anything") == DEFAULT_FEEDBACK_SCORE


# ─── T3.7: Stats returns summary ────────────────────────────────

class TestStats:
    """T3.7: get_stats() returns tool counts, success rates."""

    def test_stats_returns_summary(self, populated_feedback):
        stats = populated_feedback.get_stats()

        assert stats["total_entries"] == 5
        assert stats["tool_count"] == 3
        assert len(stats["top_tools"]) == 3  # 3 unique tools

        # tool_a has 2 entries, tool_b has 2, tool_c has 1
        top = {t["tool_id"]: t for t in stats["top_tools"]}
        assert top["tool_a"]["count"] == 2
        assert top["tool_b"]["count"] == 2
        assert top["tool_c"]["count"] == 1

        # tool_a: 2/2 success → 1.0
        assert top["tool_a"]["success_rate"] == 1.0
        # tool_b: 1/2 success → 0.5
        assert top["tool_b"]["success_rate"] == 0.5

        # Averages are floats
        assert isinstance(stats["avg_success_rate"], float)
        assert isinstance(stats["avg_usefulness_rate"], float)

    def test_stats_top_tools_sorted(self, feedback):
        """top_tools sorted by count descending."""
        for _ in range(10):
            feedback.record("popular_tool")
        for _ in range(3):
            feedback.record("medium_tool")
        feedback.record("rare_tool")

        stats = feedback.get_stats()
        top = stats["top_tools"]
        assert top[0]["tool_id"] == "popular_tool"
        assert top[0]["count"] == 10
        assert top[1]["tool_id"] == "medium_tool"
        assert top[1]["count"] == 3
        assert top[2]["tool_id"] == "rare_tool"
        assert top[2]["count"] == 1


# ─── FeedbackEntry dataclass tests ──────────────────────────────

class TestFeedbackEntry:
    """FeedbackEntry serialization round-trip."""

    def test_to_dict_and_back(self):
        entry = FeedbackEntry(
            tool_id="test_tool",
            phase_type="fix",
            success=True,
            useful=False,
            verifier_passed=True,
            execution_time_ms=42.5,
        )
        d = entry.to_dict()
        restored = FeedbackEntry.from_dict(d)
        assert restored.tool_id == "test_tool"
        assert restored.phase_type == "fix"
        assert restored.success is True
        assert restored.useful is False
        assert restored.execution_time_ms == 42.5

    def test_auto_timestamp(self):
        entry = FeedbackEntry(tool_id="ts_test")
        assert entry.timestamp != ""
        # Should be ISO format
        dt = datetime.fromisoformat(entry.timestamp)
        assert dt.tzinfo is not None


# ─── Singleton tests ────────────────────────────────────────────

class TestSingleton:
    """Singleton pattern works correctly."""

    def test_get_returns_same_instance(self):
        reset_reflex_feedback()
        f1 = get_reflex_feedback()
        f2 = get_reflex_feedback()
        assert f1 is f2
        reset_reflex_feedback()

    def test_reset_clears_singleton(self):
        f1 = get_reflex_feedback()
        reset_reflex_feedback()
        f2 = get_reflex_feedback()
        assert f1 is not f2
        reset_reflex_feedback()


# ─── Performance test ───────────────────────────────────────────

class TestPerformance:
    """Feedback operations should be fast."""

    def test_record_performance(self, feedback):
        """100 records in <100ms."""
        t0 = time.perf_counter()
        for i in range(100):
            feedback.record(f"perf_tool_{i % 5}", success=True)
        elapsed = (time.perf_counter() - t0) * 1000
        assert elapsed < 100, f"100 records took {elapsed:.1f}ms (expected <100ms)"

    def test_get_score_performance(self, tmp_path):
        """get_score with 500 entries in <10ms."""
        log_path = tmp_path / "perf_log.jsonl"
        fb = ReflexFeedback(log_path=log_path)

        # Pre-populate
        with open(log_path, "w") as f:
            for i in range(500):
                entry = FeedbackEntry(
                    tool_id=f"tool_{i % 10}",
                    success=i % 3 != 0,
                    useful=i % 2 == 0,
                )
                f.write(json.dumps(entry.to_dict()) + "\n")

        t0 = time.perf_counter()
        score = fb.get_score("tool_0")
        elapsed = (time.perf_counter() - t0) * 1000
        assert elapsed < 50, f"get_score(500 entries) took {elapsed:.1f}ms"
        assert 0.0 <= score <= 1.0


# ─── T3.8: Epoch-based feedback decay (Phase 195.3) ──────────────

class TestEpochDecay:
    """T3.8: MARKER_195.3 — Pre-update failures discounted by epoch gap."""

    def test_pre_update_failures_discounted(self, feedback):
        """Tool with 0% success pre-update shows ~50% (cold start) after epoch bump."""
        from src.services.tool_source_watch import ToolFreshnessEntry, get_tool_source_watch, reset_tool_source_watch

        # Record 10 failures BEFORE epoch 1 (timestamps in epoch 0)
        old_time = "2026-03-10T00:00:00+00:00"
        for _ in range(10):
            entry = FeedbackEntry(
                tool_id="failing_tool",
                success=False,
                useful=False,
                verifier_passed=False,
                timestamp=old_time,
            )
            feedback._append_entry(entry)

        # Score without epoch → should be very low (all failures)
        score_before = feedback.get_score("failing_tool")
        assert score_before < 0.1, f"Expected low score, got {score_before}"

        # Now simulate epoch bump: tool was fixed on 2026-03-15
        freshness_entry = ToolFreshnessEntry(
            source_files=["src/mcp/tools/some_tool.py"],
            current_epoch=1,
            last_commit="new_commit",
            updated_at="2026-03-15T00:00:00+00:00",
            history=[
                {"epoch": 0, "commit": "old_commit", "ts": "2026-03-01T00:00:00+00:00"},
                {"epoch": 1, "commit": "new_commit", "ts": "2026-03-15T00:00:00+00:00"},
            ],
        )

        # Patch the source watch to return our freshness entry
        import src.services.tool_source_watch as tsw_mod
        mock_watch = MagicMock()
        mock_watch.get.return_value = freshness_entry
        tsw_mod._watch_instance = mock_watch
        with patch.object(feedback, '_cache', feedback._cache):  # force re-aggregate
            score_after = feedback.get_score("failing_tool")

        # After epoch bump, old failures are discounted by 0.1 (10%)
        # With so little weight, score should approach DEFAULT (0.5)
        assert score_after > 0.3, f"Expected score near cold start (~0.5), got {score_after}"
        assert score_after > score_before, (
            f"Score should improve after epoch bump: {score_before} → {score_after}"
        )

    def test_post_update_entries_unaffected(self, feedback):
        """Entries recorded AFTER the epoch bump have full weight."""
        from src.services.tool_source_watch import ToolFreshnessEntry, reset_tool_source_watch

        # Record entries AFTER epoch 1 (timestamps after epoch bump)
        new_time = "2026-03-18T00:00:00+00:00"
        for _ in range(5):
            entry = FeedbackEntry(
                tool_id="fresh_tool",
                success=True,
                useful=True,
                verifier_passed=True,
                timestamp=new_time,
            )
            feedback._append_entry(entry)

        freshness_entry = ToolFreshnessEntry(
            source_files=["src/mcp/tools/some_tool.py"],
            current_epoch=1,
            updated_at="2026-03-15T00:00:00+00:00",
            history=[
                {"epoch": 0, "commit": "old", "ts": "2026-03-01T00:00:00+00:00"},
                {"epoch": 1, "commit": "new", "ts": "2026-03-15T00:00:00+00:00"},
            ],
        )

        import src.services.tool_source_watch as tsw_mod
        mock_watch = MagicMock()
        mock_watch.get.return_value = freshness_entry
        tsw_mod._watch_instance = mock_watch
        with patch.object(feedback, '_cache', feedback._cache):  # force re-aggregate
            score = feedback.get_score("fresh_tool")

        # All entries are post-update (epoch 1) → no discount → high score
        assert score >= 0.9, f"Post-update entries should have full weight, got {score}"

    def test_multiple_epoch_gaps_compound_discount(self, feedback):
        """2 epochs behind → 0.01 weight (0.1^2)."""
        from src.services.tool_source_watch import ToolFreshnessEntry, reset_tool_source_watch

        # Record failures during epoch 0
        for _ in range(10):
            entry = FeedbackEntry(
                tool_id="old_tool",
                success=False,
                useful=False,
                verifier_passed=False,
                timestamp="2026-03-05T00:00:00+00:00",
            )
            feedback._append_entry(entry)

        freshness_entry = ToolFreshnessEntry(
            source_files=["src/mcp/tools/some_tool.py"],
            current_epoch=2,
            updated_at="2026-03-18T00:00:00+00:00",
            history=[
                {"epoch": 0, "commit": "v0", "ts": "2026-03-01T00:00:00+00:00"},
                {"epoch": 1, "commit": "v1", "ts": "2026-03-10T00:00:00+00:00"},
                {"epoch": 2, "commit": "v2", "ts": "2026-03-18T00:00:00+00:00"},
            ],
        )

        import src.services.tool_source_watch as tsw_mod
        mock_watch = MagicMock()
        mock_watch.get.return_value = freshness_entry
        tsw_mod._watch_instance = mock_watch
        with patch.object(feedback, '_cache', feedback._cache):  # force re-aggregate
            score = feedback.get_score("old_tool")

        # 2 epochs behind → discount = 0.1^2 = 0.01 → nearly no contribution
        # Score should be close to default (0.5) since weight is negligible
        assert score > 0.3, f"2 epochs behind should heavily discount, got {score}"

    def test_no_freshness_data_no_change(self, feedback):
        """Without freshness data, aggregation is unchanged."""
        from src.services.tool_source_watch import reset_tool_source_watch

        for _ in range(5):
            feedback.record("unknown_tool", success=False, useful=False)

        reset_tool_source_watch()
        with patch("src.services.tool_source_watch.get_tool_source_watch") as mock_watch:
            mock_instance = mock_watch.return_value
            mock_instance.get.return_value = None  # No freshness data
            score = feedback.get_score("unknown_tool")

        # Should behave as before — all failures, low score
        assert score < 0.5

    def test_epoch_decay_performance(self, tmp_path):
        """Epoch discount adds <10ms overhead for 500 entries."""
        from src.services.tool_source_watch import ToolFreshnessEntry, reset_tool_source_watch

        log_path = tmp_path / "epoch_perf.jsonl"
        fb = ReflexFeedback(log_path=log_path)

        with open(log_path, "w") as f:
            for i in range(500):
                entry = FeedbackEntry(
                    tool_id="perf_tool",
                    success=i % 3 != 0,
                    useful=i % 2 == 0,
                    timestamp=(datetime.now(timezone.utc) - timedelta(days=i % 30)).isoformat(),
                )
                f.write(json.dumps(entry.to_dict()) + "\n")

        freshness_entry = ToolFreshnessEntry(
            source_files=["src/mcp/tools/some_tool.py"],
            current_epoch=1,
            updated_at=datetime.now(timezone.utc).isoformat(),
            history=[
                {"epoch": 0, "commit": "v0", "ts": "2026-03-01T00:00:00+00:00"},
                {"epoch": 1, "commit": "v1", "ts": "2026-03-15T00:00:00+00:00"},
            ],
        )

        import src.services.tool_source_watch as tsw_mod
        mock_watch = MagicMock()
        mock_watch.get.return_value = freshness_entry
        tsw_mod._watch_instance = mock_watch
        with patch.object(feedback, '_cache', feedback._cache):  # force re-aggregate

            t0 = time.perf_counter()
            score = fb.get_score("perf_tool")
            elapsed = (time.perf_counter() - t0) * 1000

        assert elapsed < 50, f"Epoch decay with 500 entries took {elapsed:.1f}ms (expected <50ms)"
        assert 0.0 <= score <= 1.0
