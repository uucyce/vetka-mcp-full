"""
Model Routing Service

@file routing_service.py
@status ACTIVE
@phase Phase 54.1 (Refactored from orchestrator_with_elisya.py)
@lastAudit 2026-01-08

Handles:
- Model routing decisions
- Task type mapping
- Provider selection
- Routing statistics
"""

from typing import Dict, Any
from src.elisya.model_router_v2 import ModelRouter, Provider, TaskType


class RoutingService:
    """Manages model routing and selection."""

    def __init__(self, default_provider: Provider = Provider.OLLAMA):
        """
        Initialize routing service.

        Args:
            default_provider: Default provider for routing
        """
        self.model_router = ModelRouter(default_provider=default_provider)
        print(f"   • ModelRouter: initialized ({len(self.model_router.models)} models)")

    def get_routing_for_task(self, task: str, agent_type: str) -> Dict[str, Any]:
        """
        Get LLM routing for task.

        Args:
            task: Task description
            agent_type: Agent name (PM, Dev, QA, Architect)

        Returns:
            Routing dict with model, provider, task_type
        """
        # Map agent type to task type (Phase 57.6: Use correct TaskType enum values)
        task_type = TaskType.UNKNOWN

        if agent_type == 'PM':
            task_type = TaskType.PM_PLANNING
        elif agent_type == 'Dev':
            task_type = TaskType.DEV_CODING
        elif agent_type == 'QA':
            task_type = TaskType.QA_TESTING
        elif agent_type == 'Architect':
            task_type = TaskType.ARCHITECTURE

        # Get routing decision from ModelRouter
        routing = self.model_router.route(task)

        print(f"   🚀 {agent_type} routing:")
        print(f"      Model: {routing['model']}")
        print(f"      Provider: {routing['provider']}")
        print(f"      Task type: {routing['task_type']}")

        return routing

    def get_model_routing(self, task: str) -> Dict[str, Any]:
        """
        Get model routing decision for task.

        Args:
            task: Task description

        Returns:
            Routing decision dict
        """
        return self.model_router.route(task)
