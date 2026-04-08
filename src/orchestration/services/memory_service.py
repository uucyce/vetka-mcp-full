"""
Memory Management Service

@file memory_service.py
@status ACTIVE
@phase Phase 54.1 (Refactored from orchestrator_with_elisya.py)
@lastAudit 2026-01-08

Handles:
- MemoryManager operations
- Workflow result storage
- Agent output storage
- Triple-write coordination
"""

from typing import Dict, Any
from src.orchestration.memory_manager import MemoryManager


class MemoryService:
    """Manages memory operations and storage."""

    def __init__(self):
        """Initialize the memory service."""
        self.memory = MemoryManager()
        print("   • MemoryService: initialized")

    def save_agent_output(
        self,
        agent_type: str,
        output: str,
        workflow_id: str,
        category: str
    ):
        """
        Save agent output to memory.

        Args:
            agent_type: Agent name (PM, Dev, QA, Architect)
            output: Agent's output text
            workflow_id: Workflow identifier
            category: Output category (planning, design, implementation, testing)
        """
        self.memory.save_agent_output(agent_type, output, workflow_id, category)

    def save_workflow_result(self, workflow_id: str, result: Dict[str, Any]):
        """
        Save complete workflow result.

        Args:
            workflow_id: Workflow identifier
            result: Complete workflow result dict
        """
        self.memory.save_workflow_result(workflow_id, result)

    def log_error(self, workflow_id: str, component: str, error: str):
        """
        Log error to memory.

        Args:
            workflow_id: Workflow identifier
            component: Component name where error occurred
            error: Error message
        """
        self.memory.log_error(workflow_id, component, error)

    def triple_write(self, data: Dict[str, Any]):
        """
        Perform triple-write to all storage backends.

        Args:
            data: Data dict to write
        """
        self.memory.triple_write(data)

    def get_workflow_history(self, limit: int = 10):
        """
        Get workflow execution history from memory.

        Args:
            limit: Maximum number of workflows to return

        Returns:
            List of workflow records
        """
        return self.memory.get_workflow_history(limit)

    def get_agent_stats(self, agent_type: str) -> Dict[str, Any]:
        """
        Get statistics for specific agent.

        Args:
            agent_type: Agent name

        Returns:
            Dict with agent statistics
        """
        return self.memory.get_agent_stats(agent_type)

    def save_performance_metrics(
        self,
        workflow_id: str,
        timings: Dict[str, float],
        total_time: float,
        execution_mode: str
    ):
        """
        Save workflow performance metrics.

        Args:
            workflow_id: Workflow identifier
            timings: Dict of phase timings
            total_time: Total workflow duration
            execution_mode: 'parallel' or 'sequential'
        """
        try:
            self.memory.triple_write({
                'type': 'performance_metrics',
                'workflow_id': workflow_id,
                'timings': timings,
                'total_time': total_time,
                'execution_mode': execution_mode,
                'speaker': 'orchestrator'
            })
        except Exception as e:
            print(f"   ⚠️  Could not save performance metrics: {e}")
