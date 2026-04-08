"""
VETKA Phase 7.9 - Base Learner Interface
Abstract base class for all learning agents - enables pluggable LLM architecture

@file base_learner.py
@status: active
@phase: 99
@depends: abc, typing
@used_by: pixtral_learner, qwen_learner, learner_factory, arc_solver_agent
@lastAudit 2026-01-28

FIX_99.4: Restored from DEPRECATED - actively used by 4+ modules.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseLearner(ABC):
    """
    Abstract base class for learning agents

    All learners must implement:
    - analyze_workflow: Extract lessons from completed workflows
    - get_model_info: Return model metadata
    - model_name: Unique identifier for the model
    """

    @abstractmethod
    def analyze_workflow(self, workflow_data: Dict) -> Dict[str, Any]:
        """
        Analyze workflow and extract structured lesson

        Args:
            workflow_data: Dictionary containing workflow information
                - feature: Task description
                - pm_plan: Planning phase output
                - architecture: Architecture phase output
                - implementation: Implementation phase output
                - score: Feedback score (0-10)

        Returns:
            Dictionary with lesson structure:
                - task_description: Generalized task description
                - approach: Technical approach used
                - success_factors: List of success factors
                - failure_factors: List of potential pitfalls
                - semantic_tags: Tags for semantic search
                - relationships: Related concepts
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, str]:
        """
        Return model metadata and capabilities

        Returns:
            Dictionary with:
                - name: Model name
                - type: Model type (text-only, multimodal, etc.)
                - vision: Vision capability (enabled/disabled)
                - parameters: Model size
                - source: Source (local, api, ollama, etc.)
                - loaded/available: Availability status
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """
        Return unique model identifier

        Returns:
            String identifier (e.g., 'pixtral-12b', 'qwen2-7b')
        """
        pass

    def learn_from_workflow(self, workflow_id: str) -> bool:
        """
        Main learning loop - can be overridden for custom behavior

        Default implementation:
        1. Fetch workflow data
        2. Check feedback score
        3. Analyze with analyze_workflow()
        4. Store lesson in memory

        Args:
            workflow_id: ID of workflow to learn from

        Returns:
            bool: True if lesson was learned and stored
        """
        raise NotImplementedError(
            "Subclass must implement learn_from_workflow or use provided implementation"
        )
