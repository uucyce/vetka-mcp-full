"""
VETKA Phase 9.0 - Student Level System
Multilevel competency tracking for local models (Teacher-Student Distillation)

Levels: Novice (0) -> Learner (1) -> Apprentice (2) -> Assistant (3) -> Senior (4) -> Specialist (5)

Architecture:
- Teacher (API): Claude/GPT-4o via OpenRouter - teaches patterns
- Student (Local): DeepSeek/Qwen/Llama - learns and improves
- User: Provides feedback, corrections (highest priority)

@status: active
@phase: 96
@depends: logging, dataclasses
@used_by: learner_initializer, student_portfolio
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


class StudentLevel(Enum):
    """Student competency levels (0-5)"""
    NOVICE = 0          # Just starting - needs teacher for everything
    LEARNER = 1         # Learning from examples - can repeat patterns
    APPRENTICE = 2      # Stable repetition - solves similar tasks
    ASSISTANT = 3       # Solves without teacher - independent work
    SENIOR = 4          # Self-correction - improves own answers
    SPECIALIST = 5      # Optimal local model - production ready


class PromotionMetric(Enum):
    """Metrics used for level promotion"""
    CONSISTENCY = "consistency"           # Solution stability across runs
    TEACHER_STUDENT_GAP = "gap"          # Quality gap with teacher
    SELF_CORRECTION = "self_correction"  # Can improve own answers
    USER_SATISFACTION = "satisfaction"   # User feedback score


@dataclass
class StudentMetrics:
    """Student performance metrics"""
    level: StudentLevel = StudentLevel.NOVICE
    consistency_score: float = 0.0        # 0-1 (identical outputs on same input)
    teacher_gap: float = 1.0              # 0-1 (lower = closer to teacher)
    self_correction_rate: float = 0.0     # 0-1 (improvement after hint)
    user_satisfaction: float = 0.0        # 0-1 (positive feedback ratio)
    total_attempts: int = 0               # Total task attempts
    successful_tasks: int = 0             # Tasks completed successfully
    portfolio_size: int = 0               # Examples in portfolio
    exam_results: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'level': self.level.name,
            'level_value': self.level.value,
            'consistency_score': self.consistency_score,
            'teacher_gap': self.teacher_gap,
            'self_correction_rate': self.self_correction_rate,
            'user_satisfaction': self.user_satisfaction,
            'total_attempts': self.total_attempts,
            'successful_tasks': self.successful_tasks,
            'portfolio_size': self.portfolio_size,
            'exam_results': self.exam_results
        }


@dataclass
class PromotionThreshold:
    """Thresholds for level promotion"""
    level: StudentLevel
    next_level: StudentLevel
    consistency_threshold: float      # Min consistency score
    gap_threshold: float              # Max teacher gap (lower = better)
    satisfaction_threshold: float     # Min user satisfaction
    required_attempts: int            # Min attempts before promotion


class StudentLevelSystem:
    """
    Manages student levels, metrics, and promotion eligibility.

    Phase 9.0: Hierarchical learning with automatic level progression.

    Usage:
        system = StudentLevelSystem(memory_manager=memory)
        system.initialize_student("deepseek", "DeepSeek-LLM", "deepseek-llm:7b")
        system.update_metrics("deepseek", consistency=0.85, satisfaction=0.75)
        eligibility = system.check_promotion_eligibility("deepseek")
    """

    # Promotion thresholds for each level
    PROMOTION_THRESHOLDS = {
        StudentLevel.NOVICE: PromotionThreshold(
            level=StudentLevel.NOVICE,
            next_level=StudentLevel.LEARNER,
            consistency_threshold=0.70,
            gap_threshold=0.40,
            satisfaction_threshold=0.50,
            required_attempts=10
        ),
        StudentLevel.LEARNER: PromotionThreshold(
            level=StudentLevel.LEARNER,
            next_level=StudentLevel.APPRENTICE,
            consistency_threshold=0.80,
            gap_threshold=0.35,
            satisfaction_threshold=0.60,
            required_attempts=30
        ),
        StudentLevel.APPRENTICE: PromotionThreshold(
            level=StudentLevel.APPRENTICE,
            next_level=StudentLevel.ASSISTANT,
            consistency_threshold=0.85,
            gap_threshold=0.25,
            satisfaction_threshold=0.70,
            required_attempts=50
        ),
        StudentLevel.ASSISTANT: PromotionThreshold(
            level=StudentLevel.ASSISTANT,
            next_level=StudentLevel.SENIOR,
            consistency_threshold=0.90,
            gap_threshold=0.20,
            satisfaction_threshold=0.75,
            required_attempts=100
        ),
        StudentLevel.SENIOR: PromotionThreshold(
            level=StudentLevel.SENIOR,
            next_level=StudentLevel.SPECIALIST,
            consistency_threshold=0.92,
            gap_threshold=0.15,
            satisfaction_threshold=0.85,
            required_attempts=150
        ),
    }

    # Level descriptions for UI
    LEVEL_DESCRIPTIONS = {
        StudentLevel.NOVICE: "Just starting - needs teacher guidance for all tasks",
        StudentLevel.LEARNER: "Learning patterns - can repeat demonstrated solutions",
        StudentLevel.APPRENTICE: "Stable execution - solves similar tasks reliably",
        StudentLevel.ASSISTANT: "Independent - solves new tasks without teacher",
        StudentLevel.SENIOR: "Self-improving - corrects and optimizes own answers",
        StudentLevel.SPECIALIST: "Production-ready - optimal local model performance"
    }

    def __init__(self, memory_manager=None):
        """
        Initialize Student Level System.

        Args:
            memory_manager: Optional MemoryManager for persistence
        """
        self.memory = memory_manager
        self.students: Dict[str, StudentMetrics] = {}
        self._student_profiles: Dict[str, Dict[str, Any]] = {}

        logger.info("Student Level System initialized")

    def initialize_student(
        self,
        student_id: str,
        student_name: str,
        model_name: str,
        initial_level: StudentLevel = StudentLevel.NOVICE
    ) -> StudentMetrics:
        """
        Initialize a new student (local model).

        Args:
            student_id: Unique identifier (e.g., "deepseek", "qwen")
            student_name: Human-readable name
            model_name: Ollama model name (e.g., "deepseek-llm:7b")
            initial_level: Starting level (default: NOVICE)

        Returns:
            StudentMetrics for the initialized student
        """
        if student_id in self.students:
            logger.warning(f"Student {student_id} already exists, returning existing metrics")
            return self.students[student_id]

        metrics = StudentMetrics(level=initial_level)
        self.students[student_id] = metrics

        # Store profile
        self._student_profiles[student_id] = {
            'student_id': student_id,
            'student_name': student_name,
            'model_name': model_name,
            'initialized_at': datetime.now().isoformat(),
            'initial_level': initial_level.name
        }

        # Persist to memory
        if self.memory:
            try:
                self.memory.triple_write({
                    'type': 'student_profile',
                    'student_id': student_id,
                    'student_name': student_name,
                    'model_name': model_name,
                    'level': initial_level.name,
                    'initialized_at': datetime.now().isoformat()
                })
            except Exception as e:
                logger.warning(f"Failed to persist student profile: {e}")

        logger.info(f"Student initialized: {student_name} ({model_name}) at level {initial_level.name}")

        return metrics

    def update_metrics(
        self,
        student_id: str,
        consistency: Optional[float] = None,
        gap: Optional[float] = None,
        self_correction: Optional[float] = None,
        satisfaction: Optional[float] = None,
        attempt_success: bool = False
    ) -> Optional[StudentMetrics]:
        """
        Update student metrics with new data.

        Uses exponential moving average for smooth updates.

        Args:
            student_id: Student identifier
            consistency: New consistency measurement (0-1)
            gap: New teacher-student gap (0-1, lower = better)
            self_correction: Self-correction success (0-1)
            satisfaction: User satisfaction (0-1)
            attempt_success: Whether this attempt was successful

        Returns:
            Updated StudentMetrics or None if student not found
        """
        if student_id not in self.students:
            logger.error(f"Student not found: {student_id}")
            return None

        metrics = self.students[student_id]
        n = metrics.total_attempts

        # Exponential moving average (α = 0.1 for smooth updates)
        alpha = 0.1 if n > 10 else 0.3  # Faster learning early on

        if consistency is not None:
            if n == 0:
                metrics.consistency_score = consistency
            else:
                metrics.consistency_score = alpha * consistency + (1 - alpha) * metrics.consistency_score

        if gap is not None:
            if n == 0:
                metrics.teacher_gap = gap
            else:
                metrics.teacher_gap = alpha * gap + (1 - alpha) * metrics.teacher_gap

        if self_correction is not None:
            if n == 0:
                metrics.self_correction_rate = self_correction
            else:
                metrics.self_correction_rate = alpha * self_correction + (1 - alpha) * metrics.self_correction_rate

        if satisfaction is not None:
            if n == 0:
                metrics.user_satisfaction = satisfaction
            else:
                metrics.user_satisfaction = alpha * satisfaction + (1 - alpha) * metrics.user_satisfaction

        # Update counters
        metrics.total_attempts += 1
        if attempt_success:
            metrics.successful_tasks += 1

        logger.debug(f"Updated {student_id}: consistency={metrics.consistency_score:.2f}, "
                    f"gap={metrics.teacher_gap:.2f}, satisfaction={metrics.user_satisfaction:.2f}")

        return metrics

    def check_promotion_eligibility(self, student_id: str) -> Dict[str, Any]:
        """
        Check if student is eligible for promotion.

        Returns detailed status with all metrics and thresholds.

        Args:
            student_id: Student identifier

        Returns:
            {
                'eligible': bool,
                'current_level': str,
                'next_level': str | None,
                'metrics_status': {...},
                'checks': {...},
                'recommendation': str
            }
        """
        if student_id not in self.students:
            return {'error': f'Student not found: {student_id}'}

        metrics = self.students[student_id]
        threshold = self.PROMOTION_THRESHOLDS.get(metrics.level)

        if not threshold:
            return {
                'eligible': False,
                'current_level': metrics.level.name,
                'next_level': None,
                'message': f'Maximum level reached: {metrics.level.name}',
                'recommendation': 'Student has reached SPECIALIST level - no further promotion available'
            }

        # Check all thresholds
        checks = {
            'consistency': metrics.consistency_score >= threshold.consistency_threshold,
            'gap': metrics.teacher_gap <= threshold.gap_threshold,
            'satisfaction': metrics.user_satisfaction >= threshold.satisfaction_threshold,
            'attempts': metrics.total_attempts >= threshold.required_attempts
        }

        eligible = all(checks.values())

        # Generate recommendation
        failed_checks = [k for k, v in checks.items() if not v]
        if eligible:
            recommendation = f"Ready for promotion to {threshold.next_level.name}! Run exams to confirm."
        elif len(failed_checks) == 1:
            recommendation = f"Almost ready! Need to improve: {failed_checks[0]}"
        else:
            recommendation = f"Need improvement in: {', '.join(failed_checks)}"

        return {
            'eligible': eligible,
            'current_level': metrics.level.name,
            'current_level_value': metrics.level.value,
            'next_level': threshold.next_level.name if eligible else None,
            'metrics_status': {
                'consistency': {
                    'current': round(metrics.consistency_score, 3),
                    'threshold': threshold.consistency_threshold,
                    'passed': checks['consistency']
                },
                'gap': {
                    'current': round(metrics.teacher_gap, 3),
                    'threshold': threshold.gap_threshold,
                    'passed': checks['gap']
                },
                'satisfaction': {
                    'current': round(metrics.user_satisfaction, 3),
                    'threshold': threshold.satisfaction_threshold,
                    'passed': checks['satisfaction']
                },
                'attempts': {
                    'current': metrics.total_attempts,
                    'threshold': threshold.required_attempts,
                    'passed': checks['attempts']
                }
            },
            'checks': checks,
            'recommendation': recommendation
        }

    def promote_student(self, student_id: str, force: bool = False) -> Optional[StudentLevel]:
        """
        Promote student to next level.

        Args:
            student_id: Student identifier
            force: Skip eligibility check (use with caution)

        Returns:
            New StudentLevel or None if promotion failed
        """
        if not force:
            eligibility = self.check_promotion_eligibility(student_id)
            if not eligibility.get('eligible'):
                logger.warning(f"Student {student_id} not eligible for promotion")
                return None

        metrics = self.students[student_id]
        old_level = metrics.level

        threshold = self.PROMOTION_THRESHOLDS.get(old_level)
        if not threshold:
            logger.warning(f"Student {student_id} already at max level")
            return None

        # Promote
        new_level = threshold.next_level
        metrics.level = new_level

        logger.info(f"PROMOTED: {student_id} from {old_level.name} to {new_level.name}")

        # Persist promotion event
        if self.memory:
            try:
                self.memory.triple_write({
                    'type': 'student_promotion',
                    'student_id': student_id,
                    'old_level': old_level.name,
                    'new_level': new_level.name,
                    'promoted_at': datetime.now().isoformat(),
                    'metrics_snapshot': {
                        'consistency': metrics.consistency_score,
                        'gap': metrics.teacher_gap,
                        'satisfaction': metrics.user_satisfaction,
                        'attempts': metrics.total_attempts
                    }
                })
            except Exception as e:
                logger.warning(f"Failed to persist promotion: {e}")

        return new_level

    def demote_student(self, student_id: str, reason: str = "drift") -> Optional[StudentLevel]:
        """
        Demote student one level (e.g., due to performance drift).

        Args:
            student_id: Student identifier
            reason: Reason for demotion

        Returns:
            New StudentLevel or None if already at minimum
        """
        if student_id not in self.students:
            return None

        metrics = self.students[student_id]
        old_level = metrics.level

        if old_level == StudentLevel.NOVICE:
            logger.warning(f"Student {student_id} already at minimum level")
            return None

        # Find previous level
        new_level = StudentLevel(old_level.value - 1)
        metrics.level = new_level

        logger.warning(f"DEMOTED: {student_id} from {old_level.name} to {new_level.name} (reason: {reason})")

        return new_level

    def get_student_status(self, student_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete student status.

        Args:
            student_id: Student identifier

        Returns:
            Complete status dict or None if not found
        """
        if student_id not in self.students:
            return None

        metrics = self.students[student_id]
        profile = self._student_profiles.get(student_id, {})
        eligibility = self.check_promotion_eligibility(student_id)

        return {
            'student_id': student_id,
            'profile': profile,
            'current_level': {
                'name': metrics.level.name,
                'value': metrics.level.value,
                'description': self.LEVEL_DESCRIPTIONS.get(metrics.level, "")
            },
            'metrics': metrics.to_dict(),
            'progress': {
                'total_attempts': metrics.total_attempts,
                'successful_tasks': metrics.successful_tasks,
                'success_rate': metrics.successful_tasks / metrics.total_attempts if metrics.total_attempts > 0 else 0,
                'portfolio_size': metrics.portfolio_size
            },
            'promotion': eligibility
        }

    def get_all_students(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all registered students."""
        return {
            student_id: self.get_student_status(student_id)
            for student_id in self.students.keys()
        }

    def get_level_distribution(self) -> Dict[str, int]:
        """Get distribution of students across levels."""
        distribution = {level.name: 0 for level in StudentLevel}
        for metrics in self.students.values():
            distribution[metrics.level.name] += 1
        return distribution


# Factory function
def student_level_system_factory(memory_manager=None) -> StudentLevelSystem:
    """Create StudentLevelSystem instance."""
    return StudentLevelSystem(memory_manager=memory_manager)
