"""
Response Management Module.

Handles response emission to Socket.IO clients, summaries, and quick actions.
Extracted from user_message_handler.py (lines 1515-1665, plus emission logic from 1445-1505).

@status: active
@phase: 96
@depends: utils.chat_utils
@used_by: di_container
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
from src.utils.chat_utils import detect_response_type


class ResponseManager:
    """
    Manages response emission to Socket.IO clients.

    Responsibilities:
    - Emit agent responses to clients
    - Generate summaries for multi-agent chains
    - Emit quick actions
    - Save to chat history
    - Emit CAM events for surprise calculation
    """

    def __init__(
        self,
        sio,
        sid: str,
        chat_manager,
        Message,
        save_chat_message_func,
        get_chat_history_manager_func,
        emit_cam_event_func,
        get_agents_func
    ):
        """
        Initialize response manager with dependencies.

        Args:
            sio: SocketIO server instance
            sid: Session ID
            chat_manager: Chat manager instance for session
            Message: Message class for creating message objects
            save_chat_message_func: Function to save chat messages
            get_chat_history_manager_func: Function to get chat history manager
            emit_cam_event_func: Function to emit CAM events
            get_agents_func: Function to get agent instances
        """
        self.sio = sio
        self.sid = sid
        self.chat_manager = chat_manager
        self.Message = Message
        self.save_chat_message = save_chat_message_func
        self.get_chat_history_manager = get_chat_history_manager_func
        self.emit_cam_event = emit_cam_event_func
        self.get_agents = get_agents_func

    async def emit_responses(
        self,
        responses: List[Dict[str, Any]],
        node_path: str,
        file_available: bool,
        pinned_files: Optional[List[str]] = None,
        chat_id: Optional[str] = None,
    ) -> None:
        """
        Emit all agent responses to client.

        Args:
            responses: List of agent response dictionaries
            node_path: Path to the node
            file_available: Whether file context is available
            pinned_files: Optional list of pinned files
            chat_id: Optional stable chat UUID to keep writes in one chat thread
        """
        stable_chat_id = (chat_id or "").strip() or None

        for i, resp in enumerate(responses):
            if i > 0:
                await asyncio.sleep(0.15)

            response_type = detect_response_type(resp['text'])
            force_artifact = len(resp['text']) > 800

            # Emit agent_message (for 3D panel - expects 'content')
            await self.sio.emit('agent_message', {
                'agent': resp['agent'],
                'model': resp['model'],
                'content': resp['text'],  # Frontend expects 'content' not 'text'
                'text': resp['text'],  # Keep for backwards compatibility
                'node_id': resp['node_id'],
                'node_path': resp['node_path'],
                'timestamp': resp['timestamp'],
                'context_provided': file_available,
                'response_type': response_type,
                'force_artifact': force_artifact
            }, to=self.sid)

            # Emit chat_response (for chat panel - expects 'message')
            await self.sio.emit('chat_response', {
                'message': resp['text'],  # Frontend expects 'message' field
                'agent': resp['agent'],
                'model': resp['model'],
                'workflow_id': f"chat_{resp['timestamp']}"
            }, to=self.sid)

            # Add agent response to per-session history
            self.chat_manager.add_message(self.Message(
                role='assistant',
                content=resp['text'],
                agent=resp['agent'],
                node_path=node_path
            ))

            # Save to chat history
            self.save_chat_message(node_path, {
                'role': 'agent',
                'agent': resp['agent'],
                'model': resp['model'],
                'text': resp['text'],
                'node_id': resp['node_id']
            }, pinned_files=pinned_files, chat_id=stable_chat_id or resp.get("chat_id"))

            # Emit message_sent event for surprise calculation
            try:
                chat_history = self.get_chat_history_manager()
                resolved_chat_id = stable_chat_id or resp.get("chat_id")
                if resolved_chat_id:
                    existing = chat_history.get_chat(resolved_chat_id)
                    if not existing:
                        resolved_chat_id = chat_history.get_or_create_chat(
                            node_path,
                            chat_id=resolved_chat_id,
                        )
                else:
                    resolved_chat_id = chat_history.get_or_create_chat(node_path)
                await self.emit_cam_event("message_sent", {
                    "chat_id": resolved_chat_id,
                    "content": resp['text'],
                    "role": "assistant"
                }, source=f"agent_chain_{resp['agent']}")
            except Exception as cam_err:
                print(f"[CAM] Message event error (non-critical): {cam_err}")

            print(f"[SOCKET] Sent {resp['agent']} response ({len(resp['text'])} chars)")

        print(f"[SOCKET] All {len(responses)} agent responses sent")

    async def emit_summary(
        self,
        responses: List[Dict[str, Any]],
        request_node_id: str,
        node_path: str,
        request_timestamp: float,
        single_mode: bool
    ) -> None:
        """
        Generate and emit summary for multi-agent chains or quick actions for single agent.

        Args:
            responses: List of agent response dictionaries
            request_node_id: Node ID for request
            node_path: Path to the node
            request_timestamp: Timestamp of request
            single_mode: Whether in single agent mode
        """
        # Multi-agent summary
        if not single_mode and len(responses) > 1:
            print(f"[SOCKET] Generating summary for multi-agent chain...")
            try:
                summary_text = "\n\n".join([
                    f"**{resp['agent']}**: {resp['text'][:300]}..."
                    for resp in responses
                ])

                summary_prompt = f"""Based on the team's analysis:

{summary_text}

Write a brief summary (3-4 sentences) covering:
- Main recommendations
- Key risks
- Action items

IMPORTANT: Return ONLY plain text. Do NOT use JSON format. Do NOT use markdown code blocks."""

                agents = self.get_agents()
                if agents and agents.get('Dev'):
                    loop = asyncio.get_event_loop()
                    summary_response = await loop.run_in_executor(
                        None,
                        lambda: agents['Dev']['instance'].call_llm(
                            prompt=summary_prompt,
                            max_tokens=200
                        )
                    )

                    if isinstance(summary_response, dict):
                        summary_response = summary_response.get('response', summary_response.get('content', str(summary_response)))

                    summary_text = self._parse_llm_summary(summary_response)
                else:
                    summary_text = f"Summary of {len(responses)} agent analyses completed."

                await self.sio.emit('agent_message', {
                    'agent': 'Summary',
                    'model': 'auto',
                    'content': summary_text,
                    'text': summary_text,
                    'node_id': request_node_id,
                    'node_path': node_path,
                    'timestamp': request_timestamp,
                    'response_type': 'summary',
                    'force_artifact': False
                }, to=self.sid)

                await self.sio.emit('chat_response', {
                    'message': summary_text,
                    'agent': 'Summary',
                    'model': 'auto'
                }, to=self.sid)

                print(f"[SOCKET] Summary generated ({len(summary_text)} chars)")

                # Emit quick actions for summary
                await asyncio.sleep(0.2)
                await self.sio.emit('quick_actions', {
                    'node_path': node_path,
                    'agent': 'Summary',
                    'options': [
                        {'label': 'Accept', 'action': 'accept', 'emoji': 'check'},
                        {'label': 'Refine', 'action': 'refine', 'emoji': 'edit'},
                        {'label': 'Reject', 'action': 'reject', 'emoji': 'x'}
                    ]
                }, to=self.sid)

            except Exception as e:
                print(f"[SOCKET] Error generating summary: {e}, attempting simple fallback")

                summary_text = self._generate_simple_summary(responses)

                await self.sio.emit('agent_message', {
                    'agent': 'Summary',
                    'model': 'fallback',
                    'content': summary_text,
                    'text': summary_text,
                    'node_id': request_node_id,
                    'node_path': node_path,
                    'timestamp': request_timestamp,
                    'response_type': 'summary',
                    'force_artifact': False
                }, to=self.sid)

                await self.sio.emit('chat_response', {
                    'message': summary_text,
                    'agent': 'Summary',
                    'model': 'fallback'
                }, to=self.sid)

        # Single agent quick actions
        if single_mode and len(responses) > 0:
            print(f"[SOCKET] Emitting quick actions for single agent response")
            await self.sio.emit('quick_actions', {
                'node_path': node_path,
                'agent': responses[0]['agent'],
                'options': [
                    {'label': 'Details', 'action': 'detailed_analysis', 'emoji': 'search'},
                    {'label': 'Improve', 'action': 'improve', 'emoji': 'edit'},
                    {'label': 'Tests', 'action': 'run_tests', 'emoji': 'test'},
                    {'label': 'Full Team', 'action': 'full_chain', 'emoji': 'users'}
                ]
            }, to=self.sid)

    def _generate_simple_summary(self, responses: List[Dict[str, Any]]) -> str:
        """
        Simple summary without LLM - clean English output.

        Args:
            responses: List of agent response dictionaries

        Returns:
            Simple summary text
        """
        parts = []
        for resp in responses:
            response = resp['text']
            agent = resp['agent']
            first_sentence = response.split('.')[0].strip()
            if first_sentence and not first_sentence.endswith(('.', '!', '?')):
                first_sentence += '.'
            parts.append(f"**{agent}**: {first_sentence}")
        return "**Team Summary:**\n" + '\n'.join(parts)

    def _parse_llm_summary(self, response_text: str) -> str:
        """
        Safely parse LLM response, handling JSON and text.

        Args:
            response_text: Raw LLM response

        Returns:
            Parsed summary text
        """
        if not response_text:
            return "Unable to generate summary"

        text = str(response_text).strip()

        if not text.startswith('{'):
            return text

        try:
            import re
            json_match = re.search(r'\{[^{}]*\}', text)
            if json_match:
                data = json.loads(json_match.group())
                return data.get('summary', data.get('text', data.get('content', text)))
        except:
            pass

        try:
            first_line = text.split('\n')[0]
            if first_line.startswith('{'):
                data = json.loads(first_line)
                return data.get('summary', data.get('text', str(data)))
        except:
            pass

        return text
