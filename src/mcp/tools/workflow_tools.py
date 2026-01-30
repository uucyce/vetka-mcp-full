"""MCP Workflow Tools - Full workflow execution: PM -> Architect -> Dev -> QA.

Provides tools for executing multi-agent workflows through the orchestrator:
- vetka_execute_workflow: Execute full VETKA workflow with configurable stages
- vetka_workflow_status: Get status of a workflow execution by ID

Workflow types:
- "pm_to_qa": PM -> Architect -> Dev -> QA (default, full pipeline)
- "pm_only": Just PM planning stage
- "dev_qa": Dev -> QA (skip planning, direct implementation)

Integration:
- Uses orchestrator_with_elisya._execute_parallel() for multi-agent coordination
- Saves state via MCPStateBridge for persistence and monitoring
- Supports timeout configuration (max 600s) for long-running workflows

@status: active
@phase: 96
@depends: src/mcp/tools/base_tool.py, src/orchestration/orchestrator_with_elisya.py, src/orchestration/services/mcp_state_bridge.py, src/mcp/state/mcp_state_manager.py
@used_by: src/mcp/vetka_mcp_bridge.py, src/mcp/tools/__init__.py
"""

from typing import Dict, Any, List, Optional
import uuid
import asyncio
from pathlib import Path

from .base_tool import BaseMCPTool

PROJECT_ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


class ExecuteWorkflowTool(BaseMCPTool):
    """Execute full VETKA workflow (PM -> Architect -> Dev -> QA)"""

    @property
    def name(self) -> str:
        return "vetka_execute_workflow"

    @property
    def description(self) -> str:
        return """Execute full VETKA workflow.

Workflow types:
- "pm_to_qa": PM -> Architect -> Dev -> QA (default)
- "pm_only": Just PM planning
- "dev_qa": Dev -> QA (skip planning)

Integration:
- Uses orchestrator_with_elisya._execute_parallel()
- Saves state via MCPStateBridge"""

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "request": {
                    "type": "string",
                    "description": "Feature request to execute"
                },
                "workflow_type": {
                    "type": "string",
                    "enum": ["pm_to_qa", "pm_only", "dev_qa"],
                    "default": "pm_to_qa",
                    "description": "Type of workflow to execute"
                },
                "include_eval": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include evaluation step"
                },
                "timeout": {
                    "type": "integer",
                    "default": 300,
                    "description": "Timeout in seconds (max 600)"
                }
            },
            "required": ["request"]
        }

    def validate_arguments(self, args: Dict[str, Any]) -> Optional[str]:
        if not args.get("request"):
            return "Missing required argument: request"
        timeout = args.get("timeout", 300)
        if not isinstance(timeout, int):
            return "Timeout must be an integer"
        if timeout < 1 or timeout > 600:
            return "Timeout must be between 1 and 600 seconds"
        workflow_type = args.get("workflow_type", "pm_to_qa")
        if workflow_type not in ["pm_to_qa", "pm_only", "dev_qa"]:
            return f"Unknown workflow type: {workflow_type}"
        return None

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow synchronously (wraps async implementation)"""
        request = arguments.get("request")
        workflow_type = arguments.get("workflow_type", "pm_to_qa")
        include_eval = arguments.get("include_eval", True)
        timeout = min(arguments.get("timeout", 300), 600)

        workflow_id = f"wf_{uuid.uuid4().hex[:8]}"

        try:
            # Run async function in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    asyncio.wait_for(
                        self._execute_async(request, workflow_type, workflow_id, include_eval),
                        timeout=timeout
                    )
                )
                return result
            finally:
                loop.close()
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Workflow timed out after {timeout}s",
                "result": {
                    "workflow_id": workflow_id,
                    "workflow_type": workflow_type,
                    "status": "timeout"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "result": {
                    "workflow_id": workflow_id,
                    "workflow_type": workflow_type,
                    "status": "error"
                }
            }

    async def _execute_async(
        self,
        request: str,
        workflow_type: str,
        workflow_id: str,
        include_eval: bool
    ) -> Dict[str, Any]:
        """Async workflow execution"""
        try:
            from src.orchestration.orchestrator_with_elisya import OrchestratorWithElisya
            from src.orchestration.services import get_mcp_state_bridge

            orchestrator = OrchestratorWithElisya()
            mcp_bridge = get_mcp_state_bridge()

            if workflow_type == "pm_to_qa":
                result = await orchestrator._execute_parallel(
                    feature_request=request,
                    workflow_id=workflow_id,
                )
            elif workflow_type == "pm_only":
                # Execute only PM agent
                result = await self._run_pm_only(orchestrator, request, workflow_id)
            elif workflow_type == "dev_qa":
                # Skip PM/Architect, run Dev -> QA directly
                result = await self._run_dev_qa(orchestrator, request, workflow_id)
            else:
                return {
                    "success": False,
                    "error": f"Unknown workflow type: {workflow_type}",
                    "result": None
                }

            # Publish completion to MCP bridge
            await mcp_bridge.publish_workflow_complete(workflow_id, result)

            return {
                "success": True,
                "result": {
                    "workflow_id": workflow_id,
                    "workflow_type": workflow_type,
                    "status": "complete",
                    "data": result
                },
                "error": None
            }

        except ImportError as e:
            return {
                "success": False,
                "error": f"Import error: {str(e)}",
                "result": {
                    "workflow_id": workflow_id,
                    "status": "import_error"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "result": {
                    "workflow_id": workflow_id,
                    "status": "error"
                }
            }

    async def _run_pm_only(
        self,
        orchestrator,
        request: str,
        workflow_id: str
    ) -> Dict[str, Any]:
        """Run only the PM agent for planning"""
        # Use orchestrator's PM agent directly
        pm_result = await orchestrator._call_agent_async(
            agent_type="PM",
            prompt=request,
            workflow_id=workflow_id
        )
        return {"pm_plan": pm_result}

    async def _run_dev_qa(
        self,
        orchestrator,
        request: str,
        workflow_id: str
    ) -> Dict[str, Any]:
        """Run Dev -> QA workflow (skip planning)"""
        # Call Dev first
        dev_result = await orchestrator._call_agent_async(
            agent_type="Dev",
            prompt=request,
            workflow_id=workflow_id
        )
        # Then QA
        qa_result = await orchestrator._call_agent_async(
            agent_type="QA",
            prompt=f"Review the following implementation:\n{dev_result}",
            workflow_id=workflow_id
        )
        return {
            "dev_result": dev_result,
            "qa_result": qa_result
        }


class WorkflowStatusTool(BaseMCPTool):
    """Get status of a workflow execution"""

    @property
    def name(self) -> str:
        return "vetka_workflow_status"

    @property
    def description(self) -> str:
        return "Get status of a workflow execution by workflow ID"

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "workflow_id": {
                    "type": "string",
                    "description": "The workflow ID to check status for"
                }
            },
            "required": ["workflow_id"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get workflow status synchronously"""
        workflow_id = arguments.get("workflow_id")

        if not workflow_id:
            return {
                "success": False,
                "error": "Missing required argument: workflow_id",
                "result": None
            }

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    self._get_status_async(workflow_id)
                )
                return result
            finally:
                loop.close()
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "result": None
            }

    async def _get_status_async(self, workflow_id: str) -> Dict[str, Any]:
        """Async status retrieval"""
        try:
            from src.mcp.state import get_mcp_state_manager

            mcp = get_mcp_state_manager()

            states = await mcp.get_all_states(prefix=workflow_id)
            complete_state = await mcp.get_state(f"{workflow_id}_complete")

            return {
                "success": True,
                "result": {
                    "workflow_id": workflow_id,
                    "is_complete": complete_state is not None,
                    "agent_states": list(states.keys()) if states else [],
                    "completion_data": complete_state
                },
                "error": None
            }
        except ImportError as e:
            return {
                "success": False,
                "error": f"Import error: {str(e)}",
                "result": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "result": None
            }


# Standalone async functions for direct usage (non-class based)
async def vetka_execute_workflow(
    request: str,
    workflow_type: str = "pm_to_qa",
    include_eval: bool = True,
    timeout: int = 300
) -> Dict[str, Any]:
    """
    Execute full VETKA workflow.

    Workflow types:
    - "pm_to_qa": PM -> Architect -> Dev -> QA (default)
    - "pm_only": Just PM planning
    - "dev_qa": Dev -> QA (skip planning)

    Integration:
    - Uses orchestrator_with_elisya._execute_parallel()
    - Saves state via MCPStateBridge
    """
    tool = ExecuteWorkflowTool()
    return tool.execute({
        "request": request,
        "workflow_type": workflow_type,
        "include_eval": include_eval,
        "timeout": timeout
    })


async def vetka_workflow_status(workflow_id: str) -> Dict[str, Any]:
    """Get status of a workflow."""
    tool = WorkflowStatusTool()
    return tool.execute({"workflow_id": workflow_id})


def register_workflow_tools(tool_list: List[Dict[str, Any]]):
    """Register workflow tools with MCP bridge."""
    execute_tool = ExecuteWorkflowTool()
    status_tool = WorkflowStatusTool()

    tool_list.extend([
        {
            "name": execute_tool.name,
            "description": execute_tool.description,
            "parameters": execute_tool.schema,
            "handler": vetka_execute_workflow
        },
        {
            "name": status_tool.name,
            "description": status_tool.description,
            "parameters": status_tool.schema,
            "handler": vetka_workflow_status
        }
    ])


# Export tool classes for registration in __init__.py
__all__ = [
    "ExecuteWorkflowTool",
    "WorkflowStatusTool",
    "vetka_execute_workflow",
    "vetka_workflow_status",
    "register_workflow_tools"
]
