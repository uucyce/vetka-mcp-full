"""
HostessRouter - Extracted Hostess Routing Logic.

Handles Hostess agent routing decisions and action execution.
Extracted from user_message_handler.py (lines 912-1315).

Actions supported:
- quick_answer: Direct response without agent calls
- clarify: Ask user for clarification with options
- agent_call: Route to specific agent
- chain_call: Full PM->Dev->QA chain
- search: Knowledge base search
- camera_focus: 3D viewport camera control
- ask_provider: Prompt user for API key provider
- save_api_key, learn_api_key: API key management
- analyze_unknown_key, get_api_key_status: Key analysis

@status: active
@phase: 96
@depends: elisya.key_learner
@used_by: di_container
"""

from typing import Dict, List, Optional, Any, Callable
import time


class HostessRouter:
    """
    Handles Hostess agent routing decisions and executes actions.

    Encapsulates all Hostess-specific routing logic that was previously
    embedded in user_message_handler.py (403 lines).

    Phase 3 Requirements:
    - Implements IHostessRouter protocol
    - Uses dependency injection for Socket.IO emitter
    - Preserves all action types from original code
    - Maintains pending API key state per session
    """

    def __init__(self, sio_emitter: Any):
        """
        Initialize HostessRouter with Socket.IO emitter.

        Args:
            sio_emitter: Socket.IO AsyncServer instance for emitting events
        """
        self.sio = sio_emitter
        self.pending_api_keys: Dict[str, Dict[str, Any]] = {}

    async def process_hostess_decision(
        self,
        sid: str,
        decision: dict,
        context: dict
    ) -> Optional[List[str]]:
        """
        Process Hostess routing decision and determine which agents to call.

        Args:
            sid: Socket.IO session ID
            decision: Hostess decision dict with 'action', 'result', etc.
            context: Request context (node_id, node_path, timestamp, text)

        Returns:
            List of agent names to call ['PM', 'Dev', 'QA'] or None if handled
        """
        action = decision.get('action', '')
        print(f"[HOSTESS] Decision: {action} (confidence: {decision.get('confidence', 0):.2f})")

        # Extract context
        request_node_id = context.get('node_id')
        node_path = context.get('node_path')
        request_timestamp = context.get('timestamp')
        text = context.get('text', '')

        # Handle quick answers
        if action == 'quick_answer':
            print(f"[HOSTESS] Responding directly to user")
            await self.emit_hostess_response(
                sid=sid,
                text=decision['result'],
                node_info={
                    'node_id': request_node_id,
                    'node_path': node_path,
                    'timestamp': request_timestamp
                }
            )
            return None

        # Handle clarification requests
        elif action == 'clarify':
            print(f"[HOSTESS] Asking for clarification")
            options_text = ""
            if decision.get('options'):
                options_text = "\n\nOptions:\n" + "\n".join([f"* {opt}" for opt in decision['options']])

            clarify_text = decision['result'] + options_text
            await self.emit_hostess_response(
                sid=sid,
                text=clarify_text,
                node_info={
                    'node_id': request_node_id,
                    'node_path': node_path,
                    'timestamp': request_timestamp,
                    'response_type': 'clarification'
                }
            )
            return None

        # Handle search requests
        elif action == 'search':
            print(f"[HOSTESS] Routing to knowledge search: {decision['query']}")
            search_text = f"[Search] Looking for: {decision['query']}\n\n(Search feature coming soon)"
            await self.emit_hostess_response(
                sid=sid,
                text=search_text,
                node_info={'response_type': 'text'}
            )
            return None

        # Handle camera focus requests
        elif action == 'camera_focus':
            target = decision.get('target', 'overview')
            zoom = decision.get('zoom', 'medium')
            highlight = decision.get('highlight', True)
            print(f"[HOSTESS] Camera focus: target={target}, zoom={zoom}")

            # Emit camera control event
            await self.sio.emit('camera_control', {
                'action': 'focus',
                'target': target,
                'zoom': zoom,
                'highlight': highlight,
                'animate': True
            }, to=sid)

            # Also send confirmation message
            camera_text = f"Camera focused on: `{target}`..."
            await self.emit_hostess_response(
                sid=sid,
                text=camera_text,
                node_info={'force_artifact': False}
            )
            return None

        # Handle API key - ask provider
        elif action == 'ask_provider':
            return await self._handle_ask_provider(sid, decision, context)

        # Handle API key management actions
        elif action in ('save_api_key', 'learn_api_key', 'analyze_unknown_key', 'get_api_key_status'):
            print(f"[ROUTING] API Key action '{action}' - Hostess handled it")

            # Hostess already executed the tool, emit her response
            hostess_response = decision.get('result', 'API key operation completed.')
            await self.emit_hostess_response(
                sid=sid,
                text=hostess_response,
                node_info={
                    'node_id': request_node_id,
                    'node_path': node_path,
                    'timestamp': request_timestamp
                }
            )
            return None

        # Handle single agent calls
        elif action == 'agent_call':
            specific_agent = decision.get('agent', 'Dev')
            print(f"[ROUTING] Single agent: {specific_agent}")
            return [specific_agent]

        # Handle chain calls (full PM->Dev->QA)
        elif action == 'chain_call':
            print(f"[ROUTING] Full chain: PM -> Dev -> QA")
            return ['PM', 'Dev', 'QA']

        # Handle show_file action
        elif action == 'show_file':
            print(f"[ROUTING] Show file - Dev only")
            return ['Dev']

        # Unknown action
        else:
            print(f"[ROUTING] Unknown action '{action}' - Hostess will respond")
            hostess_response = decision.get(
                'result',
                f"I received your request but I'm not sure how to handle '{action}'. Can you please clarify?"
            )
            await self.emit_hostess_response(
                sid=sid,
                text=hostess_response,
                node_info={
                    'node_id': request_node_id,
                    'node_path': node_path,
                    'timestamp': request_timestamp
                }
            )
            return None

    async def handle_pending_key_response(
        self,
        sid: str,
        text: str,
        context: dict
    ) -> bool:
        """
        Check if user is responding to pending API key question.

        Args:
            sid: Socket.IO session ID
            text: User's message text
            context: Request context (node_id, node_path, timestamp)

        Returns:
            True if handled as pending key response, False otherwise
        """
        if sid not in self.pending_api_keys:
            return False

        pending = self.pending_api_keys[sid]
        pending_key = pending.get('key')

        # Check if message looks like a provider name (short, no key pattern)
        text_lower = text.strip().lower()
        is_provider_response = (
            len(text_lower) < 50 and
            not text_lower.startswith('sk-') and
            not text_lower.startswith('aiza') and
            '-' not in text_lower[:10]  # Not a key pattern
        )

        if not (pending_key and is_provider_response):
            return False

        # User is telling us the provider name!
        provider_name = text.strip().replace('@hostess', '').replace('@Hostess', '').strip()
        print(f"[HOSTESS] 🔑 User provided provider '{provider_name}' for pending key")

        # Remove from pending
        del self.pending_api_keys[sid]

        # Call learn_api_key directly
        try:
            from src.elisya.key_learner import get_key_learner
            learner = get_key_learner()
            success, message = learner.learn_key_type(pending_key, provider_name, save_key=True)

            if success:
                response_text = f"✅ Learned {provider_name} key pattern! Key saved to config."
            else:
                response_text = f"Could not learn key: {message}"

            # Extract context
            request_node_id = context.get('node_id')
            node_path = context.get('node_path')
            request_timestamp = context.get('timestamp')

            await self.sio.emit('agent_message', {
                'agent': 'Hostess',
                'model': 'qwen2.5:0.5b',
                'content': response_text,
                'text': response_text,
                'node_id': request_node_id,
                'node_path': node_path,
                'timestamp': request_timestamp,
                'response_type': 'text',
                'force_artifact': False
            }, to=sid)

            await self.sio.emit('chat_response', {
                'message': response_text,
                'agent': 'Hostess',
                'model': 'qwen2.5:0.5b'
            }, to=sid)

            # Emit key_learned event
            if success:
                await self.sio.emit('key_learned', {
                    'provider': provider_name,
                    'success': True,
                    'message': response_text
                }, to=sid)

            return True
        except Exception as e:
            print(f"[HOSTESS] Error learning key: {e}")
            return False

    async def emit_hostess_response(
        self,
        sid: str,
        text: str,
        node_info: dict
    ) -> None:
        """
        Emit Hostess response to client.

        Args:
            sid: Socket.IO session ID
            text: Response text
            node_info: Node metadata (node_id, node_path, timestamp, etc.)
        """
        response_data = {
            'agent': 'Hostess',
            'model': 'qwen2.5:0.5b',
            'content': text,
            'text': text,
            'response_type': node_info.get('response_type', 'text'),
            'force_artifact': node_info.get('force_artifact', False)
        }

        # Add optional fields if present
        if 'node_id' in node_info:
            response_data['node_id'] = node_info['node_id']
        if 'node_path' in node_info:
            response_data['node_path'] = node_info['node_path']
        if 'timestamp' in node_info:
            response_data['timestamp'] = node_info['timestamp']

        await self.sio.emit('agent_message', response_data, to=sid)
        await self.sio.emit('chat_response', {
            'message': text,
            'agent': 'Hostess',
            'model': 'qwen2.5:0.5b'
        }, to=sid)

    async def _handle_ask_provider(
        self,
        sid: str,
        decision: dict,
        context: dict
    ) -> None:
        """
        Handle ask_provider action - save pending key and prompt user.

        Args:
            sid: Socket.IO session ID
            decision: Hostess decision dict
            context: Request context

        Returns:
            None (action handled, no agents to call)
        """
        print(f"[ROUTING] ask_provider - saving pending key for session {sid[:8]}")

        # Save the pending key for when user responds with provider name
        pending_key = decision.get('pending_key')
        if pending_key:
            self.pending_api_keys[sid] = {
                'key': pending_key,
                'timestamp': time.time()
            }
            print(f"[ROUTING] Saved pending key (prefix: {pending_key[:10]}...) for session {sid[:8]}")

        # Emit Hostess's question to user
        hostess_response = decision.get('result', "I don't recognize this key. What service is it for?")
        await self.emit_hostess_response(
            sid=sid,
            text=hostess_response,
            node_info={
                'node_id': context.get('node_id'),
                'node_path': context.get('node_path'),
                'timestamp': context.get('timestamp')
            }
        )
        return None


# Factory function for dependency injection
def create_hostess_router(sio_emitter: Any) -> HostessRouter:
    """
    Create HostessRouter instance with Socket.IO emitter.

    Args:
        sio_emitter: Socket.IO AsyncServer instance

    Returns:
        Configured HostessRouter instance
    """
    return HostessRouter(sio_emitter)
