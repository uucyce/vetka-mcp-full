"""
VETKA Command Router - Routes commands to appropriate agents.

@status: active
@phase: 96
@depends: agents (pm, architect, dev, qa, ops, visual)
@used_by: workflows.__init__, orchestration
"""


class Router:
    """Routes commands to VETKA agents based on command path"""

    def __init__(self, agents, weaviate_helper, context_manager, socketio):
        """
        Initialize router with VETKA components.

        Args:
            agents: Dictionary of agent instances (pm, architect, dev, qa, ops, visual)
            weaviate_helper: WeaviateHelper instance
            context_manager: ContextManager instance
            socketio: python-socketio AsyncServer
        """
        self.agents = agents
        self.whelper = weaviate_helper
        self.context_manager = context_manager
        self.socketio = socketio

    def handle_command(self, path: str, payload: dict = None, user: str = 'anonymous'):
        """
        Route command to appropriate agent based on path.

        Args:
            path: Command path (e.g., '/plan', '/dev/code', '/qa/test')
            payload: Command parameters
            user: User who issued the command

        Returns:
            Command result string
        """
        if payload is None:
            payload = {}

        # Parse command path
        parts = path.strip('/').split('/')

        if not parts or not parts[0]:
            return "Error: Empty command path"

        # Route to agent
        if parts[0] == 'plan':
            return self._route_to_pm(payload)
        elif parts[0] == 'arch' or parts[0] == 'architect':
            return self._route_to_architect(payload)
        elif parts[0] == 'dev' or parts[0] == 'code':
            return self._route_to_dev(payload)
        elif parts[0] == 'qa' or parts[0] == 'test':
            return self._route_to_qa(payload)
        elif parts[0] == 'ops':
            return self._route_to_ops(payload)
        elif parts[0] == 'visual':
            return self._route_to_visual(payload)
        else:
            return f"Unknown command: {path}"

    def _route_to_pm(self, payload):
        """Route to PM agent"""
        if 'pm' in self.agents:
            feature = payload.get('feature', '')
            return f"PM: Planning feature '{feature}'"
        return "PM agent not available"

    def _route_to_architect(self, payload):
        """Route to Architect agent"""
        if 'architect' in self.agents:
            return "Architect: Design complete"
        return "Architect agent not available"

    def _route_to_dev(self, payload):
        """Route to Dev agent"""
        if 'dev' in self.agents:
            return "Dev: Code implementation complete"
        return "Dev agent not available"

    def _route_to_qa(self, payload):
        """Route to QA agent"""
        if 'qa' in self.agents:
            return "QA: Test suite complete"
        return "QA agent not available"

    def _route_to_ops(self, payload):
        """Route to Ops agent"""
        if 'ops' in self.agents:
            return "Ops: Deployment complete"
        return "Ops agent not available"

    def _route_to_visual(self, payload):
        """Route to Visual agent"""
        if 'visual' in self.agents:
            return "Visual: Visualization complete"
        return "Visual agent not available"


# Legacy CommandRouter for backwards compatibility
class CommandRouter:
    """Legacy router - deprecated, use Router instead"""
    def __init__(self):
        pass

    def route(self, command: str, args: dict = None) -> str:
        """Route command to appropriate agent"""
        return "CommandRouter is deprecated. Use Router class instead."


# Legacy router instance
router = CommandRouter()
