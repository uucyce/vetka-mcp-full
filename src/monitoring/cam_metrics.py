"""
VETKA CAM Metrics — Monitoring & Performance Tracking.

Phase 16: CAM Engine Metrics.
Tracks performance metrics for CAM operations:
- Branching speed (goal: <1000ms per artifact)
- Merge accuracy (goal: >85% correct identification)
- Accommodation FPS (goal: 60 FPS smooth)
- Collision rate (goal: <5%)

@status: active
@phase: 96
@depends: logging, time, typing, datetime, dataclasses, collections, statistics
@used_by: orchestration.cam_engine
"""

import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field
from collections import deque
import statistics

logger = logging.getLogger("VETKA_CAM_Metrics")


@dataclass
class MetricSnapshot:
    """Single metric measurement."""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class CAMMetrics:
    """
    Metrics tracker for CAM operations.

    Tracks and analyzes performance of all CAM operations to ensure
    they meet Phase 16 success criteria.
    """

    # Success criteria from Phase 16 spec
    GOAL_BRANCH_TIME_MS = 1000.0      # <1 second per artifact
    GOAL_MERGE_ACCURACY = 0.85         # >85% correct identification
    GOAL_ACCOMMODATION_FPS = 60.0      # 60 FPS smooth
    GOAL_COLLISION_RATE = 0.05         # <5% collisions

    def __init__(self, max_history: int = 1000):
        """
        Initialize metrics tracker.

        Args:
            max_history: Maximum number of historical measurements to keep
        """
        self.max_history = max_history

        # Metric storage (deques for efficient append/pop)
        self.branch_times: deque = deque(maxlen=max_history)
        self.prune_times: deque = deque(maxlen=max_history)
        self.merge_times: deque = deque(maxlen=max_history)
        self.accommodate_times: deque = deque(maxlen=max_history)

        # Accuracy tracking
        self.merge_proposals: deque = deque(maxlen=max_history)  # (proposed, user_accepted)
        self.prune_proposals: deque = deque(maxlen=max_history)  # (proposed, user_accepted)

        # Animation tracking
        self.accommodation_fps: deque = deque(maxlen=max_history)
        self.collision_events: deque = deque(maxlen=max_history)  # (total_frames, collision_frames)

        logger.info("CAM Metrics tracker initialized")

    def track_branch_creation(self, artifact_path: str, time_ms: float):
        """
        Track branching operation time.

        Goal: <1000ms per artifact

        Args:
            artifact_path: Path to artifact
            time_ms: Operation duration in milliseconds
        """
        self.branch_times.append(MetricSnapshot(
            timestamp=datetime.now(timezone.utc),
            value=time_ms,
            metadata={'path': artifact_path}
        ))

        # Check goal
        if time_ms > self.GOAL_BRANCH_TIME_MS:
            logger.warning(
                f"Branch creation slow: {time_ms:.0f}ms (goal: <{self.GOAL_BRANCH_TIME_MS:.0f}ms) "
                f"for {artifact_path}"
            )
        else:
            logger.debug(f"Branch created in {time_ms:.0f}ms for {artifact_path}")

    def track_merge_accuracy(self, proposed_merge: bool, user_accepted: bool):
        """
        Track merge proposal accuracy.

        Goal: >85% correct identification

        Args:
            proposed_merge: Whether CAM proposed a merge
            user_accepted: Whether user accepted the proposal
        """
        self.merge_proposals.append(MetricSnapshot(
            timestamp=datetime.now(timezone.utc),
            value=1.0 if (proposed_merge == user_accepted) else 0.0,
            metadata={
                'proposed': proposed_merge,
                'accepted': user_accepted
            }
        ))

        # Calculate running accuracy
        if len(self.merge_proposals) >= 10:
            recent_accuracy = statistics.mean([m.value for m in list(self.merge_proposals)[-20:]])
            if recent_accuracy < self.GOAL_MERGE_ACCURACY:
                logger.warning(
                    f"Merge accuracy below goal: {recent_accuracy:.1%} "
                    f"(goal: >{self.GOAL_MERGE_ACCURACY:.0%})"
                )

    def track_prune_accuracy(self, proposed_prune: bool, user_accepted: bool):
        """
        Track pruning proposal accuracy.

        Goal: >85% correct identification

        Args:
            proposed_prune: Whether CAM proposed pruning
            user_accepted: Whether user accepted the proposal
        """
        self.prune_proposals.append(MetricSnapshot(
            timestamp=datetime.now(timezone.utc),
            value=1.0 if (proposed_prune == user_accepted) else 0.0,
            metadata={
                'proposed': proposed_prune,
                'accepted': user_accepted
            }
        ))

    def track_accommodation_fps(self, fps: float):
        """
        Track accommodation animation FPS.

        Goal: 60 FPS smooth

        Args:
            fps: Frames per second achieved
        """
        self.accommodation_fps.append(MetricSnapshot(
            timestamp=datetime.now(timezone.utc),
            value=fps
        ))

        if fps < self.GOAL_ACCOMMODATION_FPS * 0.9:  # Allow 10% tolerance
            logger.warning(f"Accommodation FPS low: {fps:.1f} (goal: {self.GOAL_ACCOMMODATION_FPS})")

    def track_collision_rate(self, total_frames: int, collision_frames: int):
        """
        Track collision rate during accommodation.

        Goal: <5% collisions

        Args:
            total_frames: Total animation frames
            collision_frames: Number of frames with collisions
        """
        collision_rate = collision_frames / total_frames if total_frames > 0 else 0.0

        self.collision_events.append(MetricSnapshot(
            timestamp=datetime.now(timezone.utc),
            value=collision_rate,
            metadata={
                'total_frames': total_frames,
                'collision_frames': collision_frames
            }
        ))

        if collision_rate > self.GOAL_COLLISION_RATE:
            logger.warning(
                f"Collision rate high: {collision_rate:.1%} "
                f"(goal: <{self.GOAL_COLLISION_RATE:.0%})"
            )

    def get_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics summary.

        Returns:
            Dictionary with all metrics and goal comparisons
        """
        def summarize_times(snapshots: deque) -> Dict[str, Any]:
            """Summarize timing measurements."""
            if not snapshots:
                return {
                    'count': 0,
                    'avg': 0,
                    'min': 0,
                    'max': 0,
                    'p95': 0
                }

            values = [s.value for s in snapshots]
            sorted_values = sorted(values)
            p95_idx = int(len(sorted_values) * 0.95)

            return {
                'count': len(values),
                'avg': statistics.mean(values),
                'min': min(values),
                'max': max(values),
                'p95': sorted_values[p95_idx] if sorted_values else 0
            }

        def summarize_accuracy(snapshots: deque) -> Dict[str, Any]:
            """Summarize accuracy measurements."""
            if not snapshots:
                return {
                    'count': 0,
                    'accuracy': 0.0,
                    'meets_goal': False
                }

            values = [s.value for s in snapshots]
            accuracy = statistics.mean(values)

            return {
                'count': len(values),
                'accuracy': accuracy,
                'meets_goal': accuracy >= self.GOAL_MERGE_ACCURACY
            }

        # Branch timing
        branch_summary = summarize_times(self.branch_times)
        branch_summary['meets_goal'] = (
            branch_summary['avg'] < self.GOAL_BRANCH_TIME_MS
            if branch_summary['count'] > 0 else False
        )

        # Merge accuracy
        merge_accuracy = summarize_accuracy(self.merge_proposals)

        # Prune accuracy
        prune_accuracy = summarize_accuracy(self.prune_proposals)

        # Accommodation FPS
        if self.accommodation_fps:
            avg_fps = statistics.mean([s.value for s in self.accommodation_fps])
            fps_meets_goal = avg_fps >= self.GOAL_ACCOMMODATION_FPS * 0.9
        else:
            avg_fps = 0
            fps_meets_goal = False

        # Collision rate
        if self.collision_events:
            avg_collision_rate = statistics.mean([s.value for s in self.collision_events])
            collision_meets_goal = avg_collision_rate < self.GOAL_COLLISION_RATE
        else:
            avg_collision_rate = 0
            collision_meets_goal = False

        return {
            'branching': {
                **branch_summary,
                'goal': f"<{self.GOAL_BRANCH_TIME_MS}ms"
            },
            'merge_accuracy': {
                **merge_accuracy,
                'goal': f">{self.GOAL_MERGE_ACCURACY:.0%}"
            },
            'prune_accuracy': {
                **prune_accuracy,
                'goal': f">{self.GOAL_MERGE_ACCURACY:.0%}"
            },
            'accommodation_fps': {
                'avg': avg_fps,
                'count': len(self.accommodation_fps),
                'meets_goal': fps_meets_goal,
                'goal': f"{self.GOAL_ACCOMMODATION_FPS} FPS"
            },
            'collision_rate': {
                'avg': avg_collision_rate,
                'count': len(self.collision_events),
                'meets_goal': collision_meets_goal,
                'goal': f"<{self.GOAL_COLLISION_RATE:.0%}"
            },
            'overall_status': (
                branch_summary.get('meets_goal', False) and
                merge_accuracy.get('meets_goal', False) and
                fps_meets_goal and
                collision_meets_goal
            )
        }

    def get_recent_events(self, limit: int = 10) -> Dict[str, List[Dict]]:
        """
        Get recent CAM events.

        Args:
            limit: Number of recent events to retrieve

        Returns:
            Dictionary with recent events by type
        """
        def snapshot_to_dict(snapshot: MetricSnapshot) -> Dict:
            return {
                'timestamp': snapshot.timestamp.isoformat(),
                'value': snapshot.value,
                'metadata': snapshot.metadata
            }

        return {
            'branch_operations': [
                snapshot_to_dict(s) for s in list(self.branch_times)[-limit:]
            ],
            'merge_proposals': [
                snapshot_to_dict(s) for s in list(self.merge_proposals)[-limit:]
            ],
            'prune_proposals': [
                snapshot_to_dict(s) for s in list(self.prune_proposals)[-limit:]
            ],
            'accommodations': [
                snapshot_to_dict(s) for s in list(self.accommodation_fps)[-limit:]
            ]
        }

    def check_goals(self) -> Dict[str, bool]:
        """
        Check if all Phase 16 success criteria are met.

        Returns:
            Dictionary mapping goal names to pass/fail status
        """
        summary = self.get_summary()

        return {
            'branching_speed': summary['branching'].get('meets_goal', False),
            'merge_accuracy': summary['merge_accuracy'].get('meets_goal', False),
            'prune_accuracy': summary['prune_accuracy'].get('meets_goal', False),
            'accommodation_fps': summary['accommodation_fps'].get('meets_goal', False),
            'collision_rate': summary['collision_rate'].get('meets_goal', False),
            'overall': summary['overall_status']
        }

    def reset_metrics(self):
        """Reset all metrics (useful for testing)."""
        self.branch_times.clear()
        self.prune_times.clear()
        self.merge_times.clear()
        self.accommodate_times.clear()
        self.merge_proposals.clear()
        self.prune_proposals.clear()
        self.accommodation_fps.clear()
        self.collision_events.clear()
        logger.info("Metrics reset")


# Global metrics instance (singleton)
_metrics_instance: Optional[CAMMetrics] = None


def get_cam_metrics() -> CAMMetrics:
    """
    Get global CAM metrics instance (singleton pattern).

    Returns:
        Global CAMMetrics instance
    """
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = CAMMetrics()
    return _metrics_instance
