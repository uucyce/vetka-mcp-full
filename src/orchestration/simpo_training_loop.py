"""
VETKA Phase 9.0 - SimPO Training Loop.

Simple Preference Optimization for local model fine-tuning.

SimPO (Superior Instruct Preference Optimization):
- Simplified DPO without reward model
- loss = -log(exp(B * good) / (exp(B * good) + exp(B * bad)))
- Priority: User corrections > User feedback > Teacher distillation

Reference:
- DPO: "Direct Preference Optimization" (Rafailov et al., 2023)
- SimPO: Simplified version for practical use

@status: active
@phase: 96
@depends: dataclasses, json, math
@used_by: src.orchestration.orchestrator_with_elisya
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import math

logger = logging.getLogger(__name__)


@dataclass
class TrainingPair:
    """A single training pair for preference optimization"""
    task: str
    good_output: str
    bad_output: str
    eval_score: float
    weight: float                # 0-1, higher = more important
    source: str                  # user_correction, user_feedback, distillation
    category: str
    timestamp: float
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            'task': self.task,
            'good_output': self.good_output,
            'bad_output': self.bad_output,
            'eval_score': self.eval_score,
            'weight': self.weight,
            'source': self.source,
            'category': self.category,
            'timestamp': self.timestamp,
            'metadata': self.metadata
        }


class SimPOTrainingLoop:
    """
    SimPO Training Loop for preference-based learning.

    Phase 9.0: Collects training pairs from:
    1. User corrections (highest priority)
    2. User feedback (good/bad)
    3. Teacher-student distillation

    No reward model needed - uses simple preference pairs.

    Usage:
        loop = SimPOTrainingLoop(beta=0.2)
        loop.collect_training_pair(task, teacher_out, student_out, feedback, score)
        dataset = loop.get_training_dataset()
        estimate = loop.estimate_training_time()
    """

    # Source priority weights
    SOURCE_WEIGHTS = {
        'user_correction': 1.0,    # Highest - user knows best
        'user_feedback': 0.8,      # High - explicit good/bad
        'distillation': 0.6,       # Medium - teacher example
        'self_improvement': 0.5,   # Lower - student self-correction
        'synthetic': 0.3           # Lowest - generated pairs
    }

    def __init__(
        self,
        beta: float = 0.2,
        min_score_diff: float = 1.0,
        max_pairs: int = 10000
    ):
        """
        Initialize SimPO Training Loop.

        Args:
            beta: Temperature parameter (0.1-0.5)
                  Higher β = stronger preference for "good" outputs
            min_score_diff: Minimum score difference to create pair
            max_pairs: Maximum training pairs to store
        """
        self.beta = beta
        self.min_score_diff = min_score_diff
        self.max_pairs = max_pairs

        self.training_pairs: List[TrainingPair] = []
        self.stats = {
            'total_collected': 0,
            'by_source': {},
            'by_category': {},
            'avg_score_diff': 0.0
        }

        logger.info(f"SimPO Training Loop initialized (β={beta})")

    def collect_training_pair(
        self,
        task: str,
        teacher_output: Optional[str],
        student_output: str,
        user_correction: Optional[str] = None,
        user_feedback: Optional[str] = None,
        eval_score: float = 0.0,
        category: str = "general"
    ) -> Optional[TrainingPair]:
        """
        Collect a training pair from task execution.

        Priority logic:
        1. If user_correction: good=correction, bad=student
        2. If user_feedback="good": good=student, bad=teacher (if available)
        3. If user_feedback="bad": good=teacher, bad=student
        4. Else (distillation): good=teacher, bad=student

        Args:
            task: Task description
            teacher_output: Teacher model's output (if available)
            student_output: Student model's output
            user_correction: User's corrected version (highest priority)
            user_feedback: "good" or "bad"
            eval_score: EvalAgent score
            category: Task category

        Returns:
            Created TrainingPair or None if invalid
        """
        if not task or not student_output:
            return None

        # Determine good/bad outputs and source
        if user_correction:
            # User correction = highest priority
            good_output = user_correction
            bad_output = student_output
            source = 'user_correction'
            weight = self.SOURCE_WEIGHTS['user_correction']

        elif user_feedback == "good":
            # Student did well
            good_output = student_output
            bad_output = teacher_output or student_output
            source = 'user_feedback'
            weight = self.SOURCE_WEIGHTS['user_feedback']

        elif user_feedback == "bad" and teacher_output:
            # Student did poorly, use teacher as good
            good_output = teacher_output
            bad_output = student_output
            source = 'user_feedback'
            weight = self.SOURCE_WEIGHTS['user_feedback']

        elif teacher_output:
            # Standard distillation
            good_output = teacher_output
            bad_output = student_output
            source = 'distillation'
            weight = self.SOURCE_WEIGHTS['distillation']

        else:
            # No valid pair can be formed
            logger.debug("Cannot form training pair - no good output available")
            return None

        # Don't create pair if good == bad
        if good_output == bad_output:
            return None

        # Adjust weight by score
        weight *= min(1.0, eval_score / 10.0 + 0.5)

        pair = TrainingPair(
            task=task,
            good_output=good_output,
            bad_output=bad_output,
            eval_score=eval_score,
            weight=weight,
            source=source,
            category=category,
            timestamp=datetime.now().timestamp()
        )

        self.training_pairs.append(pair)
        self._update_stats(pair)

        # Enforce max pairs limit
        if len(self.training_pairs) > self.max_pairs:
            self._prune_low_priority_pairs()

        logger.debug(f"Collected training pair (source: {source}, weight: {weight:.2f})")

        return pair

    def collect_self_improvement_pair(
        self,
        task: str,
        original_output: str,
        improved_output: str,
        improvement_score: float,
        category: str = "general"
    ) -> Optional[TrainingPair]:
        """
        Collect pair from self-improvement (when student improves own answer).

        Args:
            task: Task description
            original_output: Student's first attempt
            improved_output: Student's improved version
            improvement_score: How much better (0-1)
            category: Task category

        Returns:
            Created TrainingPair or None
        """
        if improvement_score < 0.1:
            # Not enough improvement
            return None

        pair = TrainingPair(
            task=task,
            good_output=improved_output,
            bad_output=original_output,
            eval_score=improvement_score * 10,
            weight=self.SOURCE_WEIGHTS['self_improvement'] * improvement_score,
            source='self_improvement',
            category=category,
            timestamp=datetime.now().timestamp()
        )

        self.training_pairs.append(pair)
        self._update_stats(pair)

        return pair

    def compute_simpo_loss(
        self,
        good_logit: float,
        bad_logit: float
    ) -> float:
        """
        Compute SimPO loss for a single pair.

        loss = -log(exp(β * good) / (exp(β * good) + exp(β * bad)))

        Args:
            good_logit: Log probability of good output
            bad_logit: Log probability of bad output

        Returns:
            Loss value (lower = better)
        """
        # Numerical stability
        max_logit = max(good_logit, bad_logit)
        good_exp = math.exp(self.beta * (good_logit - max_logit))
        bad_exp = math.exp(self.beta * (bad_logit - max_logit))

        loss = -math.log(good_exp / (good_exp + bad_exp))

        return loss

    def compute_batch_loss(
        self,
        pairs: List[Tuple[float, float]]
    ) -> Tuple[float, List[float]]:
        """
        Compute average loss for a batch of pairs.

        Args:
            pairs: List of (good_logit, bad_logit) tuples

        Returns:
            (average_loss, individual_losses)
        """
        losses = [self.compute_simpo_loss(g, b) for g, b in pairs]
        avg_loss = sum(losses) / len(losses) if losses else 0.0

        return avg_loss, losses

    def get_training_dataset(
        self,
        min_weight: float = 0.0,
        categories: List[str] = None,
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """
        Get training dataset for export.

        Args:
            min_weight: Minimum weight threshold
            categories: Filter by categories (None = all)
            limit: Maximum number of pairs

        Returns:
            List of training pair dicts
        """
        # Filter pairs
        filtered = self.training_pairs

        if min_weight > 0:
            filtered = [p for p in filtered if p.weight >= min_weight]

        if categories:
            filtered = [p for p in filtered if p.category in categories]

        # Sort by weight (highest first)
        sorted_pairs = sorted(filtered, key=lambda x: x.weight, reverse=True)

        if limit:
            sorted_pairs = sorted_pairs[:limit]

        logger.info(f"Training dataset: {len(sorted_pairs)} pairs")

        return [p.to_dict() for p in sorted_pairs]

    def get_dataset_by_source(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get training pairs grouped by source."""
        by_source = {}

        for pair in self.training_pairs:
            if pair.source not in by_source:
                by_source[pair.source] = []
            by_source[pair.source].append(pair.to_dict())

        return by_source

    def estimate_training_time(
        self,
        tokens_per_pair: int = 500,
        tokens_per_second: int = 100,
        epochs: int = 3
    ) -> Dict[str, Any]:
        """
        Estimate training time and resources.

        Args:
            tokens_per_pair: Average tokens per training pair
            tokens_per_second: Training throughput
            epochs: Number of training epochs

        Returns:
            Estimation dict
        """
        dataset_size = len(self.training_pairs)
        total_tokens = dataset_size * tokens_per_pair * epochs

        # M4 Mac can do ~6000 tok/min for inference, ~100-200 for training
        estimated_seconds = total_tokens / tokens_per_second
        estimated_minutes = estimated_seconds / 60

        return {
            'dataset_size': dataset_size,
            'total_tokens': total_tokens,
            'epochs': epochs,
            'estimated_seconds': round(estimated_seconds, 1),
            'estimated_minutes': round(estimated_minutes, 1),
            'recommended_batch_size': min(8, max(1, dataset_size // 100)),
            'recommended_learning_rate': 1e-5 if dataset_size > 1000 else 2e-5,
            'source_distribution': self.stats['by_source'],
            'category_distribution': self.stats['by_category']
        }

    def export_for_transformers(self, output_path: str = None) -> Dict[str, Any]:
        """
        Export dataset in format suitable for HuggingFace transformers/trl.

        Args:
            output_path: Optional path to save JSON

        Returns:
            Dataset dict in TRL format
        """
        dataset = {
            'type': 'preference',
            'format': 'trl_dpo',
            'beta': self.beta,
            'pairs': []
        }

        for pair in self.training_pairs:
            dataset['pairs'].append({
                'prompt': pair.task,
                'chosen': pair.good_output,
                'rejected': pair.bad_output,
                'weight': pair.weight
            })

        if output_path:
            with open(output_path, 'w') as f:
                json.dump(dataset, f, indent=2)
            logger.info(f"Dataset exported to {output_path}")

        return dataset

    def _update_stats(self, pair: TrainingPair) -> None:
        """Update internal statistics."""
        self.stats['total_collected'] += 1

        # By source
        if pair.source not in self.stats['by_source']:
            self.stats['by_source'][pair.source] = 0
        self.stats['by_source'][pair.source] += 1

        # By category
        if pair.category not in self.stats['by_category']:
            self.stats['by_category'][pair.category] = 0
        self.stats['by_category'][pair.category] += 1

    def _prune_low_priority_pairs(self) -> int:
        """Remove lowest priority pairs when over limit."""
        if len(self.training_pairs) <= self.max_pairs:
            return 0

        # Sort by weight (ascending) and remove bottom 10%
        sorted_pairs = sorted(self.training_pairs, key=lambda x: x.weight)
        remove_count = len(sorted_pairs) - self.max_pairs

        self.training_pairs = sorted_pairs[remove_count:]

        logger.info(f"Pruned {remove_count} low-priority training pairs")

        return remove_count

    def get_stats(self) -> Dict[str, Any]:
        """Get training loop statistics."""
        return {
            'beta': self.beta,
            'total_pairs': len(self.training_pairs),
            'max_pairs': self.max_pairs,
            'stats': self.stats,
            'avg_weight': sum(p.weight for p in self.training_pairs) / len(self.training_pairs) if self.training_pairs else 0
        }

    def clear(self) -> int:
        """Clear all training pairs. Returns count cleared."""
        count = len(self.training_pairs)
        self.training_pairs.clear()
        self.stats = {
            'total_collected': 0,
            'by_source': {},
            'by_category': {},
            'avg_score_diff': 0.0
        }
        logger.info(f"Cleared {count} training pairs")
        return count


# Factory function
def simpo_training_loop_factory(beta: float = 0.2) -> SimPOTrainingLoop:
    """Create SimPOTrainingLoop instance."""
    return SimPOTrainingLoop(beta=beta)
