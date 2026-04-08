"""
MCP State Bridge - Phase 55.1
Extends MemoryService with MCP granular agent state management.

@status: active
@phase: 96
@depends: src.orchestration.services.memory_service.MemoryService, src.mcp.state
@used_by: src.orchestration.orchestrator_with_elisya, src.mcp.tools.workflow_tools
"""

from typing import Dict, Any, Optional, List
import asyncio
from .memory_service import MemoryService


class MCPStateBridge(MemoryService):
    """
    Extends MemoryService with MCP granular state.

    Integration Points:
    - MCP-STATE-001: triple_write() hook
    - MCP-STATE-002: save_agent_output() hook
    - MCP-STATE-003: save_workflow_result() hook
    """

    def __init__(self):
        super().__init__()
        self._mcp_state = None
        print("   • MCPStateBridge: initialized")

    @property
    def mcp_state(self):
        """Lazy load MCPStateManager."""
        if self._mcp_state is None:
            from src.mcp.state import get_mcp_state_manager
            self._mcp_state = get_mcp_state_manager()
        return self._mcp_state

    async def save_agent_state(self, workflow_id: str, agent_type: str,
                                output: str, elisya_state: Any = None,
                                ttl: int = 3600) -> bool:
        """
        Save agent state to MCP + triple-write.
        """
        agent_id = f"{workflow_id}_{agent_type}"

        state_data = {
            "output": output,
            "agent_type": agent_type,
            "workflow_id": workflow_id,
        }

        if elisya_state:
            if hasattr(elisya_state, "to_dict"):
                state_data["elisya_state"] = elisya_state.to_dict()
            elif hasattr(elisya_state, "semantic_path"):
                state_data["semantic_path"] = elisya_state.semantic_path
                state_data["conversation_history_len"] = len(
                    getattr(elisya_state, "conversation_history", [])
                )

        await self.mcp_state.save_state(agent_id, state_data, ttl, workflow_id)

        self.triple_write({
            "type": "mcp_agent_state",
            "agent_id": agent_id,
            "agent_type": agent_type,
            "workflow_id": workflow_id,
            "data": state_data
        })

        return True

    async def get_agent_state(self, workflow_id: str, agent_type: str) -> Optional[Dict[str, Any]]:
        """Get agent state from MCP."""
        agent_id = f"{workflow_id}_{agent_type}"
        return await self.mcp_state.get_state(agent_id)

    async def get_workflow_states(self, workflow_id: str) -> Dict[str, Dict[str, Any]]:
        """Get all agent states for a workflow."""
        return await self.mcp_state.get_all_states(prefix=workflow_id)

    async def merge_parallel_states(self, workflow_id: str,
                                     dev_state: Any, qa_state: Any) -> Dict[str, Any]:
        """
        Merge parallel Dev and QA states.
        Used after parallel execution (WORKFLOW-015).
        """
        merged = {
            "workflow_id": workflow_id,
            "parallel_execution": True,
            "dev": None,
            "qa": None
        }

        if dev_state:
            if hasattr(dev_state, "to_dict"):
                merged["dev"] = dev_state.to_dict()
            else:
                merged["dev"] = {"output": str(dev_state)}

        if qa_state:
            if hasattr(qa_state, "to_dict"):
                merged["qa"] = qa_state.to_dict()
            else:
                merged["qa"] = {"output": str(qa_state)}

        await self.mcp_state.save_state(
            f"{workflow_id}_parallel_merge",
            merged,
            ttl_seconds=3600,
            workflow_id=workflow_id
        )

        return merged

    async def publish_workflow_complete(self, workflow_id: str,
                                         result: Dict[str, Any],
                                         elisya_state: Any = None):
        """
        Publish workflow completion notification.
        Used at WORKFLOW-007.
        """
        complete_data = {
            "status": "complete",
            "workflow_id": workflow_id,
            "result_summary": {
                k: v[:200] if isinstance(v, str) else v
                for k, v in result.items()
                if k not in ("full_context", "raw_outputs")
            }
        }

        if elisya_state and hasattr(elisya_state, "semantic_path"):
            complete_data["final_semantic_path"] = elisya_state.semantic_path

        await self.mcp_state.save_state(
            f"{workflow_id}_complete",
            complete_data,
            ttl_seconds=86400,  # 24 hours
            workflow_id=workflow_id
        )

        self.save_workflow_result(workflow_id, result)


# Singleton
_mcp_state_bridge: Optional[MCPStateBridge] = None

def get_mcp_state_bridge() -> MCPStateBridge:
    """Get singleton MCPStateBridge instance."""
    global _mcp_state_bridge
    if _mcp_state_bridge is None:
        _mcp_state_bridge = MCPStateBridge()
    return _mcp_state_bridge
