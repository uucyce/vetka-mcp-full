"""
Action Registry for VETKA Integration Framework.

Provides centralized registry for actions, supporting registration, lookup by tool/category,
and search functionality across all registered actions.

@status: active
@phase: 96
@depends: typing, src.integrations (Action, ActionCategory)
@used_by: src.orchestration, workflow execution
"""

from typing import List, Dict, Optional, Set
from . import Action, ActionCategory

class ActionRegistry:
    def __init__(self):
        self.actions = {}
        self._index_by_tool = {}
        self._index_by_category = {}
        self._load_default_actions()
    
    def _load_default_actions(self):
        """Load built-in actions"""
        
        # GitHub actions
        self.register(Action(
            name="github_create_issue",
            tool="github",
            description="Create a new GitHub issue",
            category=ActionCategory.DEVELOPMENT,
            parameters={"repo": "str", "title": "str"},
            tags=["github", "issue"]
        ))
        
        self.register(Action(
            name="github_list_issues",
            tool="github",
            description="List issues in repository",
            category=ActionCategory.DEVELOPMENT,
            parameters={"repo": "str"},
            tags=["github", "list"]
        ))
        
        # Slack actions
        self.register(Action(
            name="slack_send_message",
            tool="slack",
            description="Send message to Slack channel",
            category=ActionCategory.COMMUNICATION,
            parameters={"channel": "str", "text": "str"},
            tags=["slack", "messaging"]
        ))
        
        # Database actions
        self.register(Action(
            name="db_query",
            tool="database",
            description="Execute database query",
            category=ActionCategory.DEVOPS,
            parameters={"query": "str"},
            tags=["database", "sql"]
        ))
    
    def register(self, action: Action) -> None:
        """Register an action"""
        self.actions[action.name] = action
        
        if action.tool not in self._index_by_tool:
            self._index_by_tool[action.tool] = []
        self._index_by_tool[action.tool].append(action.name)
        
        if action.category not in self._index_by_category:
            self._index_by_category[action.category] = []
        self._index_by_category[action.category].append(action.name)
    
    def get(self, name: str):
        return self.actions.get(name)
    
    def get_by_tool(self, tool: str) -> List[Action]:
        action_names = self._index_by_tool.get(tool, [])
        return [self.actions[name] for name in action_names]
    
    def get_by_category(self, category: ActionCategory) -> List[Action]:
        action_names = self._index_by_category.get(category, [])
        return [self.actions[name] for name in action_names]
    
    def search(self, query: str) -> List[Action]:
        query_lower = query.lower()
        results = []
        for action in self.actions.values():
            if query_lower in action.name.lower() or query_lower in action.description.lower():
                results.append(action)
        return results
    
    def count(self) -> int:
        return len(self.actions)
    
    def list_all(self) -> List[Action]:
        return list(self.actions.values())
    
    def get_tools(self) -> Set[str]:
        return set(self._index_by_tool.keys())
    
    def __repr__(self) -> str:
        return f"ActionRegistry({self.count()} actions, {len(self.get_tools())} tools)"
