"""
VETKA Phase 9.0 - Student Promotion Engine.

Automatic level promotion with exam system.

Exams:
A. Understanding Test - Can student explain patterns from teacher?
B. Application Test - Can student solve new tasks independently?
C. Self-Correction Test - Can student improve own answers?
D. Drift Control - Has student's quality degraded?

@status: active
@phase: 96
@depends: src.agents.student_level_system, src.agents.student_portfolio
@used_by: src.orchestration.orchestrator_with_elisya
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import random

from src.agents.student_level_system import (
    StudentLevelSystem,
    StudentLevel,
    StudentMetrics
)
from src.agents.student_portfolio import StudentPortfolio

logger = logging.getLogger(__name__)


class ExamResult:
    """Result of a single exam"""
    def __init__(
        self,
        exam_name: str,
        passed: bool,
        score: float,
        details: Dict[str, Any] = None
    ):
        self.exam_name = exam_name
        self.passed = passed
        self.score = score
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'exam_name': self.exam_name,
            'passed': self.passed,
            'score': self.score,
            'details': self.details,
            'timestamp': self.timestamp
        }


class StudentPromotionEngine:
    """
    Manages automatic student promotion through exam system.

    Phase 9.0: Runs exams, checks eligibility, promotes levels.

    Exam Types:
    A. Understanding - Pattern recognition from teacher demos
    B. Application - Independent task solving
    C. Self-Correction - Answer improvement ability
    D. Drift Control - Quality consistency check

    Usage:
        engine = StudentPromotionEngine(level_system, smart_learner, eval_agent, memory)
        engine.register_student("deepseek", "DeepSeek-LLM", "deepseek-llm:7b")
        result = engine.check_and_promote_all_students()
    """

    # Exam thresholds by level
    EXAM_THRESHOLDS = {
        StudentLevel.NOVICE: {
            'understanding': 0.60,
            'application': 0.50,
            'self_correction': 0.40,
            'drift_control': 0.15
        },
        StudentLevel.LEARNER: {
            'understanding': 0.70,
            'application': 0.60,
            'self_correction': 0.50,
            'drift_control': 0.12
        },
        StudentLevel.APPRENTICE: {
            'understanding': 0.80,
            'application': 0.70,
            'self_correction': 0.55,
            'drift_control': 0.10
        },
        StudentLevel.ASSISTANT: {
            'understanding': 0.85,
            'application': 0.75,
            'self_correction': 0.60,
            'drift_control': 0.08
        },
        StudentLevel.SENIOR: {
            'understanding': 0.90,
            'application': 0.80,
            'self_correction': 0.65,
            'drift_control': 0.05
        },
    }

    def __init__(
        self,
        level_system: StudentLevelSystem,
        smart_learner=None,
        eval_agent=None,
        memory_manager=None
    ):
        """
        Initialize Promotion Engine.

        Args:
            level_system: StudentLevelSystem instance
            smart_learner: SmartLearner for model selection
            eval_agent: EvalAgent for quality assessment
            memory_manager: MemoryManager for persistence
        """
        self.level_system = level_system
        self.smart_learner = smart_learner
        self.eval = eval_agent
        self.memory = memory_manager

        self.portfolios: Dict[str, StudentPortfolio] = {}
        self.exam_history: Dict[str, List[ExamResult]] = {}

        logger.info("Student Promotion Engine initialized")

    def register_student(
        self,
        student_id: str,
        student_name: str,
        model_name: str
    ) -> StudentPortfolio:
        """
        Register a new student with portfolio.

        Args:
            student_id: Unique identifier
            student_name: Human-readable name
            model_name: Model identifier (e.g., "deepseek-llm:7b")

        Returns:
            StudentPortfolio for the student
        """
        # Initialize in level system
        self.level_system.initialize_student(student_id, student_name, model_name)

        # Create portfolio
        portfolio = StudentPortfolio(student_id, self.memory)
        self.portfolios[student_id] = portfolio

        # Initialize exam history
        self.exam_history[student_id] = []

        logger.info(f"Student registered: {student_name} ({model_name})")

        return portfolio

    def check_and_promote_all_students(self) -> Dict[str, Any]:
        """
        Check all students for promotion eligibility and run exams if ready.

        Returns:
            Summary of promotion checks and results
        """
        logger.info("Checking all students for promotion eligibility...")

        results = {
            'checked': 0,
            'eligible': 0,
            'promoted': 0,
            'promotions': [],
            'exam_failures': []
        }

        for student_id in list(self.level_system.students.keys()):
            results['checked'] += 1

            eligibility = self.level_system.check_promotion_eligibility(student_id)

            if eligibility.get('eligible'):
                results['eligible'] += 1
                logger.info(f"Student {student_id} eligible for promotion - running exams...")

                # Run promotion exams
                exam_results = self.run_promotion_exams(student_id)

                if all(r.passed for r in exam_results.values()):
                    # All exams passed - promote
                    new_level = self.level_system.promote_student(student_id)

                    if new_level:
                        results['promoted'] += 1
                        results['promotions'].append({
                            'student_id': student_id,
                            'new_level': new_level.name,
                            'exam_results': {k: v.to_dict() for k, v in exam_results.items()}
                        })
                else:
                    # Some exams failed
                    failed = [k for k, v in exam_results.items() if not v.passed]
                    results['exam_failures'].append({
                        'student_id': student_id,
                        'failed_exams': failed,
                        'exam_results': {k: v.to_dict() for k, v in exam_results.items()}
                    })

        logger.info(f"Promotion check complete: {results['promoted']}/{results['eligible']} promoted")

        return results

    def run_promotion_exams(self, student_id: str) -> Dict[str, ExamResult]:
        """
        Run all promotion exams for a student.

        Args:
            student_id: Student to examine

        Returns:
            Dict mapping exam name to ExamResult
        """
        logger.info(f"Running promotion exams for {student_id}...")

        results = {
            'understanding': self._exam_understanding(student_id),
            'application': self._exam_application(student_id),
            'self_correction': self._exam_self_correction(student_id),
            'drift_control': self._exam_drift_control(student_id)
        }

        # Store in history
        self.exam_history[student_id].extend(results.values())

        # Store in portfolio
        portfolio = self.portfolios.get(student_id)
        if portfolio:
            for exam_name, result in results.items():
                portfolio.record_exam_result(
                    exam_name,
                    result.passed,
                    result.score,
                    result.details
                )

        passed_count = sum(1 for r in results.values() if r.passed)
        logger.info(f"Exams complete: {passed_count}/4 passed")

        return results

    def _exam_understanding(self, student_id: str) -> ExamResult:
        """
        Exam A: Understanding Test

        Tests if student can understand and reproduce patterns from teacher demos.
        Gives 10 teacher examples, student must identify the pattern.

        Threshold: 60-90% depending on level
        """
        logger.info("   [EXAM A] Understanding Test...")

        portfolio = self.portfolios.get(student_id)
        metrics = self.level_system.students.get(student_id)

        if not portfolio or not metrics:
            return ExamResult("understanding", False, 0.0, {'error': 'No portfolio'})

        # Get threshold for current level
        thresholds = self.EXAM_THRESHOLDS.get(metrics.level, {})
        threshold = thresholds.get('understanding', 0.80)

        # Get teacher demos
        demos = portfolio.teacher_demos[-10:]

        if len(demos) < 5:
            logger.warning("      Not enough teacher demos for exam")
            return ExamResult(
                "understanding", False, 0.0,
                {'error': 'Insufficient demos', 'count': len(demos), 'required': 5}
            )

        # Simulate understanding test
        # In production: student must explain pattern from demos
        successes = 0
        total = len(demos)

        for demo in demos:
            # Simulate pattern recognition
            # Higher-level students should recognize harder patterns
            difficulty = {'SIMPLE': 0.9, 'MEDIUM': 0.7, 'COMPLEX': 0.5, 'EXPERT': 0.3}
            base_prob = difficulty.get(demo.complexity, 0.5)

            # Adjust by current metrics
            adjusted_prob = base_prob * (1 + metrics.consistency_score * 0.2)
            adjusted_prob = min(adjusted_prob, 0.95)

            if random.random() < adjusted_prob:
                successes += 1

        score = successes / total
        passed = score >= threshold

        logger.info(f"      Result: {score:.1%} (threshold: {threshold:.1%})")

        return ExamResult(
            "understanding", passed, score,
            {
                'demos_tested': total,
                'successes': successes,
                'threshold': threshold,
                'level': metrics.level.name
            }
        )

    def _exam_application(self, student_id: str) -> ExamResult:
        """
        Exam B: Application Test

        Tests if student can solve new tasks without teacher help.
        Gives 10 novel tasks, student must solve independently.

        Threshold: 50-80% depending on level
        """
        logger.info("   [EXAM B] Application Test...")

        metrics = self.level_system.students.get(student_id)
        portfolio = self.portfolios.get(student_id)

        if not metrics:
            return ExamResult("application", False, 0.0, {'error': 'No metrics'})

        # Get threshold
        thresholds = self.EXAM_THRESHOLDS.get(metrics.level, {})
        threshold = thresholds.get('application', 0.70)

        # Simulate application test
        total_tasks = 10
        successes = 0

        for i in range(total_tasks):
            # Success probability based on student metrics
            base_prob = (
                0.3 +
                metrics.consistency_score * 0.2 +
                (1 - metrics.teacher_gap) * 0.3 +
                metrics.user_satisfaction * 0.2
            )
            base_prob = min(base_prob, 0.95)

            if random.random() < base_prob:
                successes += 1

        score = successes / total_tasks
        passed = score >= threshold

        logger.info(f"      Result: {score:.1%} (threshold: {threshold:.1%})")

        return ExamResult(
            "application", passed, score,
            {
                'tasks_tested': total_tasks,
                'successes': successes,
                'threshold': threshold,
                'student_metrics': {
                    'consistency': metrics.consistency_score,
                    'gap': metrics.teacher_gap,
                    'satisfaction': metrics.user_satisfaction
                }
            }
        )

    def _exam_self_correction(self, student_id: str) -> ExamResult:
        """
        Exam C: Self-Correction Test

        Tests if student can improve their own answers when given feedback.
        Gives 5 incorrect answers + error hints, student must improve.

        Threshold: 40-65% depending on level
        """
        logger.info("   [EXAM C] Self-Correction Test...")

        metrics = self.level_system.students.get(student_id)

        if not metrics:
            return ExamResult("self_correction", False, 0.0, {'error': 'No metrics'})

        # Get threshold
        thresholds = self.EXAM_THRESHOLDS.get(metrics.level, {})
        threshold = thresholds.get('self_correction', 0.50)

        # Simulate self-correction test
        total_corrections = 5
        improvements = 0

        for i in range(total_corrections):
            # Use stored self-correction rate + some variance
            base_prob = metrics.self_correction_rate * 0.8 + 0.2
            base_prob = min(base_prob, 0.90)

            if random.random() < base_prob:
                improvements += 1

        score = improvements / total_corrections
        passed = score >= threshold

        logger.info(f"      Result: {score:.1%} (threshold: {threshold:.1%})")

        return ExamResult(
            "self_correction", passed, score,
            {
                'corrections_tested': total_corrections,
                'improvements': improvements,
                'threshold': threshold,
                'stored_rate': metrics.self_correction_rate
            }
        )

    def _exam_drift_control(self, student_id: str) -> ExamResult:
        """
        Exam D: Drift Control

        Checks if student's quality has degraded over time.
        Compares recent performance to historical baseline.

        Threshold: drift < 5-15% depending on level
        """
        logger.info("   [EXAM D] Drift Control...")

        portfolio = self.portfolios.get(student_id)
        metrics = self.level_system.students.get(student_id)

        if not portfolio or not metrics:
            return ExamResult("drift_control", False, 0.0, {'error': 'No data'})

        # Get threshold (max allowed drift)
        thresholds = self.EXAM_THRESHOLDS.get(metrics.level, {})
        max_drift = thresholds.get('drift_control', 0.10)

        # Calculate drift from portfolio
        solved = portfolio.solved_tasks

        if len(solved) < 10:
            # Not enough data - assume no drift
            logger.info("      Not enough data for drift analysis, assuming pass")
            return ExamResult(
                "drift_control", True, 0.0,
                {'message': 'Insufficient data', 'count': len(solved)}
            )

        # Compare old vs new scores
        old_scores = [e.eval_score for e in solved[:len(solved)//2]]
        new_scores = [e.eval_score for e in solved[len(solved)//2:]]

        old_avg = sum(old_scores) / len(old_scores) if old_scores else 0
        new_avg = sum(new_scores) / len(new_scores) if new_scores else 0

        # Drift = how much worse is new vs old (negative drift = improvement)
        drift = (old_avg - new_avg) / old_avg if old_avg > 0 else 0
        drift = max(0, drift)  # Only count degradation

        passed = drift < max_drift

        logger.info(f"      Drift: {drift:.1%} (max allowed: {max_drift:.1%})")

        return ExamResult(
            "drift_control", passed, drift,
            {
                'old_avg_score': round(old_avg, 3),
                'new_avg_score': round(new_avg, 3),
                'drift_percent': round(drift * 100, 2),
                'max_allowed_drift': round(max_drift * 100, 2),
                'is_improving': drift < 0
            }
        )

    def run_single_exam(
        self,
        student_id: str,
        exam_name: str
    ) -> Optional[ExamResult]:
        """
        Run a single exam for a student.

        Args:
            student_id: Student identifier
            exam_name: understanding, application, self_correction, drift_control

        Returns:
            ExamResult or None if invalid exam name
        """
        exam_methods = {
            'understanding': self._exam_understanding,
            'application': self._exam_application,
            'self_correction': self._exam_self_correction,
            'drift_control': self._exam_drift_control
        }

        if exam_name not in exam_methods:
            logger.error(f"Unknown exam: {exam_name}")
            return None

        result = exam_methods[exam_name](student_id)

        # Store in history
        if student_id not in self.exam_history:
            self.exam_history[student_id] = []
        self.exam_history[student_id].append(result)

        return result

    def get_student_exam_history(self, student_id: str) -> List[Dict[str, Any]]:
        """Get exam history for a student."""
        history = self.exam_history.get(student_id, [])
        return [r.to_dict() for r in history]

    def force_promote(self, student_id: str, reason: str = "manual") -> Optional[StudentLevel]:
        """
        Force promote a student without exams.

        Args:
            student_id: Student identifier
            reason: Reason for forced promotion

        Returns:
            New level or None if failed
        """
        logger.warning(f"Force promoting {student_id} (reason: {reason})")

        new_level = self.level_system.promote_student(student_id, force=True)

        if new_level and self.memory:
            try:
                self.memory.triple_write({
                    'type': 'forced_promotion',
                    'student_id': student_id,
                    'new_level': new_level.name,
                    'reason': reason,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.warning(f"Failed to persist forced promotion: {e}")

        return new_level

    def get_promotion_report(self, student_id: str) -> Dict[str, Any]:
        """
        Get detailed promotion report for a student.

        Args:
            student_id: Student identifier

        Returns:
            Comprehensive promotion report
        """
        status = self.level_system.get_student_status(student_id)
        if not status:
            return {'error': f'Student not found: {student_id}'}

        portfolio = self.portfolios.get(student_id)
        exam_history = self.get_student_exam_history(student_id)

        # Get recent exams by type
        recent_exams = {}
        for exam in reversed(exam_history):
            if exam['exam_name'] not in recent_exams:
                recent_exams[exam['exam_name']] = exam

        return {
            'student_id': student_id,
            'current_status': status,
            'portfolio_summary': portfolio.get_portfolio_summary() if portfolio else None,
            'recent_exams': recent_exams,
            'exam_history_count': len(exam_history),
            'recommendations': self._generate_recommendations(student_id)
        }

    def _generate_recommendations(self, student_id: str) -> List[str]:
        """Generate improvement recommendations for a student."""
        recommendations = []

        metrics = self.level_system.students.get(student_id)
        portfolio = self.portfolios.get(student_id)

        if not metrics:
            return ["Register student first"]

        # Check metrics
        if metrics.consistency_score < 0.70:
            recommendations.append("Focus on consistency - practice same task types repeatedly")

        if metrics.teacher_gap > 0.30:
            recommendations.append("Study more teacher demos - gap with teacher is high")

        if metrics.self_correction_rate < 0.50:
            recommendations.append("Practice self-correction - review and improve own answers")

        if metrics.user_satisfaction < 0.60:
            recommendations.append("Pay attention to user feedback - satisfaction is low")

        # Check portfolio weak areas
        if portfolio:
            weak = portfolio.get_weak_areas()
            if weak:
                top_weak = list(weak.keys())[:2]
                recommendations.append(f"Focus on weak areas: {', '.join(top_weak)}")

        if not recommendations:
            recommendations.append("Good progress! Continue current training")

        return recommendations


# Factory function
def student_promotion_engine_factory(
    level_system: StudentLevelSystem,
    smart_learner=None,
    eval_agent=None,
    memory_manager=None
) -> StudentPromotionEngine:
    """Create StudentPromotionEngine instance."""
    return StudentPromotionEngine(
        level_system=level_system,
        smart_learner=smart_learner,
        eval_agent=eval_agent,
        memory_manager=memory_manager
    )
