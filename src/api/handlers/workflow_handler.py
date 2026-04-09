"""
VETKA Workflow Handler - Agent Chain and Summary Logic

@file workflow_handler.py
@status ACTIVE
@phase Phase 64.4
@extracted_from user_message_handler.py
@lastAudit 2026-01-17

@calledBy:
  - src.api.handlers.user_message_handler (generate_simple_summary, determine_agents_to_call, emit_*)
  - src.api.handlers.__init__ (re-export)

Handles workflow-related logic:
- Agent chain coordination (PM → Dev → QA)
- Hostess action routing and decision parsing
- Summary generation (LLM and simple fallback)
- Response emitting helpers
- Quick actions emitting

No external dependencies - pure Python with Socket.IO emit helpers.
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple


def generate_simple_summary(responses: List[Dict[str, Any]]) -> str:
    """
    Generate simple summary without LLM - clean English output.

    Args:
        responses: List of agent response dicts with 'text' and 'agent' keys

    Returns:
        Formatted summary string
    """
    parts = []
    for resp in responses:
        response = resp.get('text', '')
        agent = resp.get('agent', 'Unknown')
        first_sentence = response.split('.')[0].strip()
        if first_sentence and not first_sentence.endswith(('.', '!', '?')):
            first_sentence += '.'
        parts.append(f"**{agent}**: {first_sentence}")
    return "**Team Summary:**\n" + '\n'.join(parts)


def parse_llm_summary(response_text: str) -> str:
    """
    Safely parse LLM response, handling JSON and text formats.

    Some LLMs return JSON even when asked for plain text.
    This function extracts the actual summary content.

    Args:
        response_text: Raw LLM response

    Returns:
        Extracted summary text
    """
    if not response_text:
        return "Unable to generate summary"

    text = str(response_text).strip()

    # If it's plain text, return as-is
    if not text.startswith('{'):
        return text

    # Try to parse as JSON
    try:
        json_match = re.search(r'\{[^{}]*\}', text)
        if json_match:
            data = json.loads(json_match.group())
            return data.get('summary', data.get('text', data.get('content', text)))
    except (json.JSONDecodeError, ValueError):
        pass

    # Try first line as JSON
    try:
        first_line = text.split('\n')[0]
        if first_line.startswith('{'):
            data = json.loads(first_line)
            return data.get('summary', data.get('text', str(data)))
    except (json.JSONDecodeError, ValueError):
        pass

    return text


def build_summary_prompt(responses: List[Dict[str, Any]]) -> str:
    """
    Build prompt for LLM to generate summary of agent responses.

    Args:
        responses: List of agent response dicts

    Returns:
        Formatted prompt for summary generation
    """
    summary_text = "\n\n".join([
        f"**{resp['agent']}**: {resp['text'][:300]}..."
        for resp in responses
    ])

    return f"""Based on the team's analysis:

{summary_text}

Write a brief summary (3-4 sentences) covering:
- Main recommendations
- Key risks
- Action items

IMPORTANT: Return ONLY plain text. Do NOT use JSON format. Do NOT use markdown code blocks."""


def determine_agents_to_call(
    hostess_decision: Optional[Dict[str, Any]],
    parsed_mentions: Optional[Dict[str, Any]] = None
) -> Tuple[List[str], bool]:
    """
    Determine which agents to call based on Hostess decision and @mentions.

    Args:
        hostess_decision: Hostess routing decision dict
        parsed_mentions: Parsed @mentions from user message

    Returns:
        Tuple of (agents_to_call list, single_mode bool)
    """
    # Default: full chain
    agents_to_call = ['PM', 'Dev', 'QA']
    single_mode = False

    # Check @mentions first (they take priority)
    if parsed_mentions and parsed_mentions.get('mode') == 'agents':
        mention_agents = parsed_mentions.get('agents', [])

        # Filter out Hostess from agent list
        if 'Hostess' in mention_agents:
            mention_agents = [a for a in mention_agents if a != 'Hostess']

        if mention_agents:
            agents_to_call = mention_agents
            single_mode = len(agents_to_call) == 1
            return agents_to_call, single_mode

    # Check Hostess decision
    if hostess_decision:
        action = hostess_decision.get('action', '')

        if action == 'quick_answer':
            return [], False

        elif action == 'show_file':
            return ['Dev'], True

        elif action == 'agent_call':
            specific_agent = hostess_decision.get('agent', 'Dev')
            return [specific_agent], True

        elif action == 'chain_call':
            return ['PM', 'Dev', 'QA'], False

        elif action == 'clarify':
            return [], False

        elif action == 'search':
            return [], False

        elif action in ('ask_provider', 'save_api_key', 'learn_api_key',
                       'analyze_unknown_key', 'get_api_key_status'):
            return [], False

    return agents_to_call, single_mode


def get_max_tokens_for_agent(agent_name: str, role_prompts_available: bool) -> int:
    """
    Get max tokens limit for specific agent.

    Args:
        agent_name: Agent name (PM, Dev, QA)
        role_prompts_available: Whether role_prompts module is available

    Returns:
        Max tokens limit
    """
    if role_prompts_available:
        return 1500 if agent_name == 'Dev' else 800
    return 500


def build_agent_response_dict(
    agent_name: str,
    model_name: str,
    response_text: str,
    node_id: str,
    node_path: str,
    timestamp: float
) -> Dict[str, Any]:
    """
    Build standardized agent response dictionary.

    Args:
        agent_name: Agent name
        model_name: Model identifier
        response_text: Response content
        node_id: Node ID
        node_path: File path
        timestamp: Request timestamp

    Returns:
        Standardized response dict
    """
    return {
        'agent': agent_name,
        'model': model_name,
        'text': response_text,
        'node_id': node_id,
        'node_path': node_path,
        'timestamp': timestamp
    }


async def emit_hostess_response(
    sio,
    sid: str,
    response_text: str,
    node_id: str,
    node_path: str,
    timestamp: float,
    response_type: str = 'text'
) -> None:
    """
    Emit Hostess response to client.

    Args:
        sio: Socket.IO server instance
        sid: Session ID
        response_text: Response content
        node_id: Node ID
        node_path: File path
        timestamp: Request timestamp
        response_type: Type of response
    """
    await sio.emit('agent_message', {
        'agent': 'Hostess',
        'model': 'qwen2.5:0.5b',
        'content': response_text,
        'text': response_text,
        'node_id': node_id,
        'node_path': node_path,
        'timestamp': timestamp,
        'response_type': response_type,
        'force_artifact': False
    }, to=sid)

    await sio.emit('chat_response', {
        'message': response_text,
        'agent': 'Hostess',
        'model': 'qwen2.5:0.5b'
    }, to=sid)


async def emit_agent_response(
    sio,
    sid: str,
    response: Dict[str, Any],
    file_available: bool,
    response_type: str = 'text'
) -> None:
    """
    Emit agent response to client via both events.

    Args:
        sio: Socket.IO server instance
        sid: Session ID
        response: Response dict with agent, model, text, etc.
        file_available: Whether file context was available
        response_type: Type of response
    """
    force_artifact = len(response.get('text', '')) > 800

    # Emit agent_message (for 3D panel)
    await sio.emit('agent_message', {
        'agent': response['agent'],
        'model': response['model'],
        'content': response['text'],
        'text': response['text'],
        'node_id': response['node_id'],
        'node_path': response['node_path'],
        'timestamp': response['timestamp'],
        'context_provided': file_available,
        'response_type': response_type,
        'force_artifact': force_artifact
    }, to=sid)

    # Emit chat_response (for chat panel)
    await sio.emit('chat_response', {
        'message': response['text'],
        'agent': response['agent'],
        'model': response['model'],
        'workflow_id': f"chat_{response['timestamp']}"
    }, to=sid)


async def emit_summary_response(
    sio,
    sid: str,
    summary_text: str,
    node_id: str,
    node_path: str,
    timestamp: float
) -> None:
    """
    Emit summary response to client.

    Args:
        sio: Socket.IO server instance
        sid: Session ID
        summary_text: Summary content
        node_id: Node ID
        node_path: File path
        timestamp: Request timestamp
    """
    await sio.emit('agent_message', {
        'agent': 'Summary',
        'model': 'auto',
        'content': summary_text,
        'text': summary_text,
        'node_id': node_id,
        'node_path': node_path,
        'timestamp': timestamp,
        'response_type': 'summary',
        'force_artifact': False
    }, to=sid)

    await sio.emit('chat_response', {
        'message': summary_text,
        'agent': 'Summary',
        'model': 'auto'
    }, to=sid)


async def emit_quick_actions(
    sio,
    sid: str,
    node_path: str,
    agent: str,
    is_summary: bool = False
) -> None:
    """
    Emit quick action buttons to client.

    Args:
        sio: Socket.IO server instance
        sid: Session ID
        node_path: File path
        agent: Agent name for context
        is_summary: Whether this is for summary (different options)
    """
    if is_summary:
        options = [
            {'label': 'Accept', 'action': 'accept', 'emoji': 'check'},
            {'label': 'Refine', 'action': 'refine', 'emoji': 'edit'},
            {'label': 'Reject', 'action': 'reject', 'emoji': 'x'}
        ]
    else:
        options = [
            {'label': 'Details', 'action': 'detailed_analysis', 'emoji': 'search'},
            {'label': 'Improve', 'action': 'improve', 'emoji': 'edit'},
            {'label': 'Tests', 'action': 'run_tests', 'emoji': 'test'},
            {'label': 'Full Team', 'action': 'full_chain', 'emoji': 'users'}
        ]

    await sio.emit('quick_actions', {
        'node_path': node_path,
        'agent': agent,
        'options': options
    }, to=sid)


# Export all utilities
__all__ = [
    'generate_simple_summary',
    'parse_llm_summary',
    'build_summary_prompt',
    'determine_agents_to_call',
    'get_max_tokens_for_agent',
    'build_agent_response_dict',
    'emit_hostess_response',
    'emit_agent_response',
    'emit_summary_response',
    'emit_quick_actions',
]
