"""
VETKA Phase 9.0 - Student Portfolio
Training history and experience storage for local models

Stores:
- Solved tasks with teacher reasoning
- Failed tasks for improvement
- Teacher demonstrations
- Exam results
- Few-shot examples for inference

@status: active
@phase: 96
@depends: logging, dataclasses, json
@used_by: student_level_system, distillation
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class PortfolioEntry:
    """Single entry in student portfolio"""
    task: str
    teacher_reasoning: Optional[str]
    student_attempt: str
    eval_score: float
    user_feedback: Optional[str]
    category: str                 # reasoning, code, vision, etc.
    success: bool
    timestamp: float
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            'task': self.task,
            'teacher_reasoning': self.teacher_reasoning,
            'student_attempt': self.student_attempt,
            'eval_score': self.eval_score,
            'user_feedback': self.user_feedback,
            'category': self.category,
            'success': self.success,
            'timestamp': self.timestamp,
            'metadata': self.metadata
        }


@dataclass
class TeacherDemo:
    """Demonstration from teacher model"""
    task: str
    reasoning: str
    category: str
    complexity: str              # SIMPLE, MEDIUM, COMPLEX, EXPERT
    timestamp: float
    teacher_model: str = "claude-3.5-sonnet"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StudentPortfolio:
    """
    Portfolio for a single student - stores learning history and examples.

    Phase 9.0: Maintains training data for distillation and few-shot learning.

    Features:
    - Solved/failed task tracking
    - Teacher demonstration storage
    - Few-shot example retrieval by category
    - Weak area identification
    - Exam result history
    """

    def __init__(self, student_id: str, memory_manager=None):
        """
        Initialize portfolio for a student.

        Args:
            student_id: Unique student identifier
            memory_manager: Optional MemoryManager for persistence
        """
        self.student_id = student_id
        self.memory = memory_manager

        self.solved_tasks: List[PortfolioEntry] = []
        self.failed_tasks: List[PortfolioEntry] = []
        self.teacher_demos: List[TeacherDemo] = []
        self.exam_results: Dict[str, Dict[str, Any]] = {}
        self.category_stats: Dict[str, Dict[str, int]] = {}

        logger.info(f"Portfolio created for student: {student_id}")

    def add_solved_task(
        self,
        task: str,
        student_attempt: str,
        teacher_reasoning: Optional[str] = None,
        eval_score: float = 0.0,
        user_feedback: Optional[str] = None,
        category: str = "general",
        metadata: Dict[str, Any] = None
    ) -> PortfolioEntry:
        """
        Add a successfully solved task to portfolio.

        Args:
            task: Task description
            student_attempt: Student's solution
            teacher_reasoning: Optional teacher's reasoning for comparison
            eval_score: EvalAgent score (0-10)
            user_feedback: Optional user feedback
            category: Task category (reasoning, code, vision, etc.)
            metadata: Additional metadata

        Returns:
            Created PortfolioEntry
        """
        entry = PortfolioEntry(
            task=task,
            teacher_reasoning=teacher_reasoning,
            student_attempt=student_attempt,
            eval_score=eval_score,
            user_feedback=user_feedback,
            category=category,
            success=True,
            timestamp=datetime.now().timestamp(),
            metadata=metadata or {}
        )

        self.solved_tasks.append(entry)
        self._update_category_stats(category, success=True)

        # Persist to memory
        if self.memory:
            try:
                self.memory.triple_write({
                    'type': 'portfolio_entry',
                    'student_id': self.student_id,
                    'task': task[:200],
                    'category': category,
                    'eval_score': eval_score,
                    'success': True,
                    'timestamp': entry.timestamp
                })
            except Exception as e:
                logger.warning(f"Failed to persist portfolio entry: {e}")

        logger.debug(f"Added solved task to portfolio (score: {eval_score:.2f}, category: {category})")

        return entry

    def add_failed_task(
        self,
        task: str,
        student_attempt: str,
        eval_score: float = 0.0,
        user_feedback: Optional[str] = None,
        category: str = "general",
        failure_reason: str = ""
    ) -> PortfolioEntry:
        """
        Add a failed task for future improvement.

        Args:
            task: Task description
            student_attempt: Student's failed attempt
            eval_score: EvalAgent score
            user_feedback: User's feedback on failure
            category: Task category
            failure_reason: Why the task failed

        Returns:
            Created PortfolioEntry
        """
        entry = PortfolioEntry(
            task=task,
            teacher_reasoning=None,
            student_attempt=student_attempt,
            eval_score=eval_score,
            user_feedback=user_feedback,
            category=category,
            success=False,
            timestamp=datetime.now().timestamp(),
            metadata={'failure_reason': failure_reason}
        )

        self.failed_tasks.append(entry)
        self._update_category_stats(category, success=False)

        logger.debug(f"Added failed task to portfolio (score: {eval_score:.2f}, category: {category})")

        return entry

    def add_teacher_demo(
        self,
        task: str,
        teacher_reasoning: str,
        category: str,
        complexity: str = "MEDIUM",
        teacher_model: str = "claude-3.5-sonnet"
    ) -> TeacherDemo:
        """
        Add a teacher demonstration for learning.

        Args:
            task: Task description
            teacher_reasoning: Teacher's solution with reasoning
            category: Task category
            complexity: SIMPLE, MEDIUM, COMPLEX, EXPERT
            teacher_model: Which teacher model produced this

        Returns:
            Created TeacherDemo
        """
        demo = TeacherDemo(
            task=task,
            reasoning=teacher_reasoning,
            category=category,
            complexity=complexity,
            timestamp=datetime.now().timestamp(),
            teacher_model=teacher_model
        )

        self.teacher_demos.append(demo)

        logger.debug(f"Added teacher demo ({category}, {complexity})")

        return demo

    def get_few_shot_examples(
        self,
        category: str,
        limit: int = 5,
        min_score: float = 7.0
    ) -> List[Dict[str, Any]]:
        """
        Get high-quality examples for few-shot prompting.

        Args:
            category: Task category to filter by
            limit: Maximum number of examples
            min_score: Minimum eval score threshold

        Returns:
            List of example dicts with task, solution, score, hint
        """
        # Filter by category and minimum score
        filtered = [
            e for e in self.solved_tasks
            if e.category == category and e.eval_score >= min_score
        ]

        # Sort by score (highest first)
        sorted_examples = sorted(filtered, key=lambda x: x.eval_score, reverse=True)

        return [
            {
                'task': e.task,
                'solution': e.student_attempt,
                'score': e.eval_score,
                'teacher_hint': e.teacher_reasoning,
                'timestamp': e.timestamp
            }
            for e in sorted_examples[:limit]
        ]

    def get_teacher_demos_for_category(
        self,
        category: str,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get teacher demonstrations for a category.

        Args:
            category: Task category
            limit: Maximum number of demos

        Returns:
            List of demo dicts
        """
        filtered = [d for d in self.teacher_demos if d.category == category]
        # Sort by recency
        sorted_demos = sorted(filtered, key=lambda x: x.timestamp, reverse=True)

        return [d.to_dict() for d in sorted_demos[:limit]]

    def get_weak_areas(self) -> Dict[str, Dict[str, Any]]:
        """
        Identify weak areas based on failure patterns.

        Returns:
            Dict mapping category to failure stats
        """
        weak_areas = {}

        for entry in self.failed_tasks:
            category = entry.category
            if category not in weak_areas:
                weak_areas[category] = {
                    'failure_count': 0,
                    'avg_score': 0.0,
                    'scores': [],
                    'common_issues': []
                }

            weak_areas[category]['failure_count'] += 1
            weak_areas[category]['scores'].append(entry.eval_score)

            # Track failure reasons
            if entry.metadata and entry.metadata.get('failure_reason'):
                weak_areas[category]['common_issues'].append(
                    entry.metadata['failure_reason']
                )

        # Calculate averages and sort
        for category, data in weak_areas.items():
            if data['scores']:
                data['avg_score'] = sum(data['scores']) / len(data['scores'])
            del data['scores']  # Remove raw scores

        # Sort by failure count (most failures first)
        return dict(sorted(
            weak_areas.items(),
            key=lambda x: x[1]['failure_count'],
            reverse=True
        ))

    def get_improvement_areas(self) -> List[Dict[str, Any]]:
        """
        Get prioritized list of areas to improve.

        Returns:
            List of improvement recommendations
        """
        weak_areas = self.get_weak_areas()
        improvements = []

        for category, stats in weak_areas.items():
            # Calculate priority based on failures and success rate
            total = self.category_stats.get(category, {})
            success_count = total.get('success', 0)
            fail_count = total.get('failure', 0)
            total_count = success_count + fail_count

            if total_count > 0:
                success_rate = success_count / total_count
                priority = (1 - success_rate) * fail_count  # Higher = more urgent

                improvements.append({
                    'category': category,
                    'priority': round(priority, 2),
                    'success_rate': round(success_rate, 3),
                    'failure_count': fail_count,
                    'avg_failed_score': round(stats['avg_score'], 2),
                    'recommendation': self._get_improvement_recommendation(category, success_rate)
                })

        # Sort by priority
        return sorted(improvements, key=lambda x: x['priority'], reverse=True)

    def _get_improvement_recommendation(self, category: str, success_rate: float) -> str:
        """Generate improvement recommendation based on category and rate."""
        if success_rate < 0.3:
            return f"Critical: Focus on {category} with teacher demos"
        elif success_rate < 0.5:
            return f"High priority: More practice needed in {category}"
        elif success_rate < 0.7:
            return f"Moderate: Review failed {category} tasks"
        else:
            return f"Good progress in {category}, maintain practice"

    def _update_category_stats(self, category: str, success: bool) -> None:
        """Update category statistics."""
        if category not in self.category_stats:
            self.category_stats[category] = {'success': 0, 'failure': 0}

        if success:
            self.category_stats[category]['success'] += 1
        else:
            self.category_stats[category]['failure'] += 1

    def record_exam_result(
        self,
        exam_name: str,
        passed: bool,
        score: float,
        details: Dict[str, Any] = None
    ) -> None:
        """
        Record exam result.

        Args:
            exam_name: Name of the exam
            passed: Whether exam was passed
            score: Exam score (0-1)
            details: Additional exam details
        """
        self.exam_results[exam_name] = {
            'passed': passed,
            'score': score,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }

        status = "PASSED" if passed else "FAILED"
        logger.info(f"Exam {exam_name}: {status} (score: {score:.2f})")

    def get_exam_history(self) -> Dict[str, Dict[str, Any]]:
        """Get all exam results."""
        return self.exam_results

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Get complete portfolio summary.

        Returns:
            Summary dict with all portfolio statistics
        """
        total_tasks = len(self.solved_tasks) + len(self.failed_tasks)
        success_rate = len(self.solved_tasks) / total_tasks if total_tasks > 0 else 0

        avg_solved_score = (
            sum(e.eval_score for e in self.solved_tasks) / len(self.solved_tasks)
            if self.solved_tasks else 0
        )

        return {
            'student_id': self.student_id,
            'summary': {
                'total_solved': len(self.solved_tasks),
                'total_failed': len(self.failed_tasks),
                'total_tasks': total_tasks,
                'success_rate': round(success_rate, 3),
                'avg_solved_score': round(avg_solved_score, 2),
                'teacher_demos': len(self.teacher_demos)
            },
            'categories': self.category_stats,
            'weak_areas': self.get_weak_areas(),
            'improvement_areas': self.get_improvement_areas()[:3],  # Top 3
            'exams': {
                'total': len(self.exam_results),
                'passed': sum(1 for e in self.exam_results.values() if e['passed']),
                'results': self.exam_results
            },
            'recent_activity': {
                'last_solved': self.solved_tasks[-1].to_dict() if self.solved_tasks else None,
                'last_failed': self.failed_tasks[-1].to_dict() if self.failed_tasks else None,
                'last_demo': self.teacher_demos[-1].to_dict() if self.teacher_demos else None
            }
        }

    def export_for_training(self) -> List[Dict[str, Any]]:
        """
        Export portfolio data for SimPO/DPO training.

        Returns:
            List of training examples with good/bad pairs
        """
        training_data = []

        # Use solved tasks with teacher reasoning as positive examples
        for entry in self.solved_tasks:
            if entry.teacher_reasoning:
                training_data.append({
                    'task': entry.task,
                    'good_output': entry.teacher_reasoning,
                    'student_output': entry.student_attempt,
                    'eval_score': entry.eval_score,
                    'category': entry.category,
                    'source': 'distillation'
                })

        # Use user-corrected tasks as high-priority examples
        for entry in self.solved_tasks + self.failed_tasks:
            if entry.user_feedback and entry.user_feedback.startswith("corrected:"):
                correction = entry.user_feedback.replace("corrected:", "").strip()
                training_data.append({
                    'task': entry.task,
                    'good_output': correction,
                    'student_output': entry.student_attempt,
                    'eval_score': entry.eval_score,
                    'category': entry.category,
                    'source': 'user_correction',
                    'priority': 'high'
                })

        return training_data

    def clear_old_entries(self, max_age_days: int = 30) -> int:
        """
        Clear entries older than max_age_days.

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of entries removed
        """
        import time
        cutoff = time.time() - (max_age_days * 24 * 60 * 60)

        old_solved = len(self.solved_tasks)
        old_failed = len(self.failed_tasks)

        self.solved_tasks = [e for e in self.solved_tasks if e.timestamp > cutoff]
        self.failed_tasks = [e for e in self.failed_tasks if e.timestamp > cutoff]

        removed = (old_solved - len(self.solved_tasks)) + (old_failed - len(self.failed_tasks))

        if removed > 0:
            logger.info(f"Cleared {removed} old portfolio entries")

        return removed


# Factory function
def student_portfolio_factory(student_id: str, memory_manager=None) -> StudentPortfolio:
    """Create StudentPortfolio instance."""
    return StudentPortfolio(student_id=student_id, memory_manager=memory_manager)
