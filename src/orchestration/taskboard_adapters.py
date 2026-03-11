"""
MARKER_175.7.TASKBOARD.ADAPTERS.V1
Adapter layer for generic TaskBoard REST clients.
"""

from typing import Any, Dict, Optional

import src.orchestration.task_board as task_board_module


class BaseAdapter:
    adapter_name = "generic"

    def __init__(self, board: Optional["task_board_module.TaskBoard"] = None):
        self.board = board or task_board_module.get_task_board()

    async def create_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    async def list_tasks(self, filters: Optional[Dict[str, Any]] = None) -> list[Dict[str, Any]]:
        filters = filters or {}
        tasks = list(self.board.get_queue())
        status = str(filters.get("status") or "").strip()
        if status:
            tasks = [task for task in tasks if task.get("status") == status]
        limit = filters.get("limit")
        if isinstance(limit, int) and limit > 0:
            tasks = tasks[:limit]
        return tasks

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.board.get_task(task_id)

    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ok = self.board.update_task(task_id, **updates)
        if not ok:
            return None
        return self.board.get_task(task_id)

    async def dispatch_task(self, task_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        if task_id:
            return await self.board.dispatch_task(task_id, **kwargs)
        return await self.board.dispatch_next(**kwargs)


class GenericRESTAdapter(BaseAdapter):
    adapter_name = "generic"

    async def create_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        task_id = self.board.add_task(
            title=str(data.get("title") or "").strip(),
            description=str(data.get("description") or "").strip(),
            priority=int(data.get("priority", 3) or 3),
            phase_type=str(data.get("phase_type") or "build").strip() or "build",
            preset=data.get("preset"),
            tags=list(data.get("tags") or []),
            source=str(data.get("source") or "api").strip() or "api",
            created_by=str(data.get("created_by") or self.adapter_name).strip() or self.adapter_name,
            module=data.get("module"),
            primary_node_id=data.get("primary_node_id"),
            affected_nodes=list(data.get("affected_nodes") or []),
            workflow_id=data.get("workflow_id"),
            workflow_bank=data.get("workflow_bank"),
            workflow_family=data.get("workflow_family"),
            workflow_selection_origin=data.get("workflow_selection_origin"),
            team_profile=data.get("team_profile"),
            task_origin=data.get("task_origin"),
        )
        return self.board.get_task(task_id) or {"id": task_id}


class ClaudeMCPAdapter(GenericRESTAdapter):
    adapter_name = "claude"


class CursorAdapter(GenericRESTAdapter):
    adapter_name = "cursor"


class VSCodeAdapter(GenericRESTAdapter):
    adapter_name = "vscode"


class OpenCodeAdapter(GenericRESTAdapter):
    adapter_name = "opencode"


def get_taskboard_adapter(
    adapter_name: Optional[str] = None,
    board: Optional["task_board_module.TaskBoard"] = None,
) -> BaseAdapter:
    key = str(adapter_name or "generic").strip().lower()
    mapping = {
        "generic": GenericRESTAdapter,
        "claude": ClaudeMCPAdapter,
        "cursor": CursorAdapter,
        "vscode": VSCodeAdapter,
        "opencode": OpenCodeAdapter,
    }
    adapter_cls = mapping.get(key)
    if adapter_cls is None:
        raise ValueError(f"Unsupported taskboard adapter: {adapter_name}")
    return adapter_cls(board=board)
