"""
VETKA Phase J-K: Agentic Tools & Smart Routing

This module provides:
1. @mention parsing for model/agent selection
2. ToolExecutor for safe file/bash operations
3. Agentic loop for iterative task completion
4. Config management from data/config.json

@status: active
@phase: 96
@depends: os, re, json, subprocess, pathlib
@used_by: chat_handler, orchestrator, hostess_agent
"""

import os
import re
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# Project root (vetka_live_03)
PROJECT_ROOT = Path(__file__).parent.parent.parent


# ============================================================================
# CONFIGURATION MANAGEMENT
# ============================================================================

_config_cache = None
_config_mtime = 0

def load_config() -> dict:
    """Load config from data/config.json with caching"""
    global _config_cache, _config_mtime

    config_path = PROJECT_ROOT / "data" / "config.json"

    if not config_path.exists():
        return get_default_config()

    # Check if file changed
    current_mtime = config_path.stat().st_mtime
    if _config_cache and current_mtime == _config_mtime:
        return _config_cache

    try:
        with open(config_path, 'r') as f:
            _config_cache = json.load(f)
            _config_mtime = current_mtime
            return _config_cache
    except Exception as e:
        print(f"[CONFIG] Error loading config: {e}")
        return get_default_config()


def save_config(config: dict) -> bool:
    """Save config to data/config.json"""
    global _config_cache, _config_mtime

    config_path = PROJECT_ROOT / "data" / "config.json"

    try:
        config['updated_at'] = datetime.utcnow().isoformat() + 'Z'

        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        _config_cache = config
        _config_mtime = config_path.stat().st_mtime
        return True
    except Exception as e:
        print(f"[CONFIG] Error saving config: {e}")
        return False


def get_default_config() -> dict:
    """Return minimal default config"""
    return {
        "version": "1.0",
        "models": {
            "aliases": {
                "@deepseek": "deepseek/deepseek-chat",
                "@coder": "deepseek/deepseek-coder",
                "@qwen": "ollama:qwen2:7b",
                "@pm": "agent:PM",
                "@dev": "agent:Dev",
                "@qa": "agent:QA",
                "@hostess": "agent:Hostess",
                "@architect": "agent:Architect",
                "@researcher": "agent:Researcher"
            },
            "defaults": {
                "cheap": "deepseek/deepseek-chat",
                "code": "deepseek/deepseek-coder",
                "local": "ollama:qwen2:7b"
            }
        },
        "tools": {
            "enabled": True,
            "allowed": ["read_file", "search_code"]
        }
    }


# ============================================================================
# @MENTION PARSER
# ============================================================================

def parse_mentions(message: str) -> dict:
    """
    Parse @mentions in user message

    Examples:
    - "@deepseek fix main.py" → single model (alias)
    - "@PM @Dev analyze this" → specific team (agents)
    - "@nemotron-3-nano-30b-a3b:free hello" → direct model ID
    - "fix this bug" → Hostess decides (auto mode)

    Returns:
        {
            'mentions': [{'alias': '@deepseek', 'target': 'deepseek/deepseek-chat', 'type': 'model'}],
            'clean_message': 'fix main.py',
            'mode': 'single',  # auto | single | team | agents
            'models': ['deepseek/deepseek-chat'],
            'agents': []
        }
    """
    config = load_config()
    aliases = config.get('models', {}).get('aliases', {})

    # Phase 57.2: Find all @mentions with full model ID support (including : . and /)
    # This captures both aliases (@deepseek) and direct model IDs (@nvidia/nemotron-3-nano-30b-a3b:free)
    mentions = re.findall(r'@([\w\-_.:/]+)', message)

    result = {
        'mentions': [],
        'clean_message': message,
        'mode': 'auto',
        'models': [],
        'agents': []
    }

    for mention in mentions:
        mention_key = f"@{mention.lower()}"
        original_text = f"@{mention}"

        if mention_key in aliases:
            # Known alias - use mapped target
            target = aliases[mention_key]

            # Determine type
            if target.startswith('agent:'):
                mention_type = 'agent'
                agent_name = target.replace('agent:', '')
                result['agents'].append(agent_name)
            elif target.startswith('ollama:'):
                mention_type = 'ollama'
                result['models'].append(target)
            else:
                mention_type = 'model'
                result['models'].append(target)

            result['mentions'].append({
                'alias': mention_key,
                'target': target,
                'type': mention_type
            })

            # Remove mention from message
            result['clean_message'] = result['clean_message'].replace(original_text, '').strip()

        elif '/' in mention or ':' in mention:
            # Phase 57.2: Direct model ID (not an alias but looks like model ID)
            # Examples: nemotron-3-nano-30b-a3b:free, nvidia/nemotron-3:free
            target = mention
            mention_type = 'model'
            result['models'].append(target)

            result['mentions'].append({
                'alias': mention_key,
                'target': target,
                'type': mention_type
            })

            # Remove mention from message
            result['clean_message'] = result['clean_message'].replace(original_text, '').strip()
            print(f"[MENTIONS] Direct model ID detected: {target}")

    # Clean up extra spaces
    result['clean_message'] = ' '.join(result['clean_message'].split())

    # Determine mode
    if len(result['mentions']) == 0:
        result['mode'] = 'auto'
    elif len(result['agents']) > 0 and len(result['models']) == 0:
        result['mode'] = 'agents'
    elif len(result['models']) == 1 and len(result['agents']) == 0:
        result['mode'] = 'single'
    else:
        result['mode'] = 'team'

    return result


def get_available_mentions() -> List[dict]:
    """Get list of available @mentions for UI autocomplete"""
    config = load_config()
    aliases = config.get('models', {}).get('aliases', {})

    descriptions = {
        '@deepseek': 'Fast & cheap general model ($0.0001/1K)',
        '@coder': 'Code specialist ($0.0001/1K)',
        '@claude': 'Complex reasoning ($0.003/1K)',
        '@haiku': 'Fast Claude ($0.00025/1K)',
        '@gemini': 'Google Gemini Flash',
        '@llama': 'Llama 3.1 8B',
        '@qwen': 'Local Ollama Qwen (free)',
        '@local': 'Local Ollama (free)',
        '@pm': 'Project Manager agent',
        '@dev': 'Developer agent',
        '@qa': 'Quality Assurance agent'
    }

    result = []
    for alias, target in aliases.items():
        result.append({
            'alias': alias,
            'target': target,
            'description': descriptions.get(alias, target)
        })

    return sorted(result, key=lambda x: x['alias'])


# ============================================================================
# SCENARIO MATCHER
# ============================================================================

def match_scenario(message: str) -> Optional[dict]:
    """
    Match message to predefined scenario based on patterns

    Returns scenario config or None if no match
    """
    config = load_config()
    scenarios = config.get('scenarios', {})

    message_lower = message.lower()

    for scenario_name, scenario_config in scenarios.items():
        patterns = scenario_config.get('patterns', [])

        for pattern in patterns:
            if pattern.lower() in message_lower:
                return {
                    'name': scenario_name,
                    **scenario_config
                }

    return None


def get_model_for_tier(tier: str) -> str:
    """Get model for given tier (cheap, code, fast, complex)"""
    config = load_config()
    defaults = config.get('models', {}).get('defaults', {})

    return defaults.get(tier, defaults.get('cheap', 'deepseek/deepseek-chat'))


# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

TOOL_DEFINITIONS = {
    "read_file": {
        "name": "read_file",
        "description": "Read content of a file. Use for understanding code before making changes.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to file relative to project root"
                },
                "lines": {
                    "type": "string",
                    "description": "Optional: line range like '1-50' or '100-150'"
                }
            },
            "required": ["path"]
        }
    },

    "write_file": {
        "name": "write_file",
        "description": "Write content to a file (creates or overwrites). Use for creating new files.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path relative to project root"},
                "content": {"type": "string", "description": "Full file content"}
            },
            "required": ["path", "content"]
        }
    },

    "edit_file": {
        "name": "edit_file",
        "description": "Replace specific text in file. Use for targeted edits.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_text": {"type": "string", "description": "Exact text to find (must be unique)"},
                "new_text": {"type": "string", "description": "Replacement text"}
            },
            "required": ["path", "old_text", "new_text"]
        }
    },

    "search_code": {
        "name": "search_code",
        "description": "Search for pattern in codebase using grep",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search pattern (regex supported)"},
                "path": {"type": "string", "default": ".", "description": "Directory to search"},
                "file_pattern": {"type": "string", "default": "*.py", "description": "File glob pattern"}
            },
            "required": ["query"]
        }
    },

    "run_bash": {
        "name": "run_bash",
        "description": "Execute bash command. Use for running tests, builds, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Bash command to run"},
                "timeout": {"type": "integer", "default": 30, "description": "Timeout in seconds"}
            },
            "required": ["command"]
        }
    },

    "list_files": {
        "name": "list_files",
        "description": "List files in directory",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "default": ".", "description": "Directory path"},
                "pattern": {"type": "string", "default": "*", "description": "Glob pattern"},
                "recursive": {"type": "boolean", "default": False}
            }
        }
    },

    "get_original_document": {
        "name": "get_original_document",
        "description": "Get original document content from Qdrant by file ID. Use when you need the full source code of a file found in search results.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "File ID from Qdrant (UUID format)"
                },
                "collection": {
                    "type": "string",
                    "default": "vetka_elisya",
                    "description": "Qdrant collection name"
                }
            },
            "required": ["file_id"]
        }
    }
}


def get_tools_for_scenario(scenario: dict) -> List[dict]:
    """Get tool definitions for given scenario"""
    tool_names = scenario.get('tools', [])
    return [TOOL_DEFINITIONS[name] for name in tool_names if name in TOOL_DEFINITIONS]


# ============================================================================
# TOOL EXECUTOR
# ============================================================================

class ToolExecutor:
    """
    Safe executor for agent tools.
    All operations are sandboxed to project root.
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.root = Path(project_root) if project_root else PROJECT_ROOT

        config = load_config()
        tools_config = config.get('tools', {})

        self.allowed_extensions = tools_config.get('allowed_extensions',
            ['.py', '.js', '.json', '.md', '.txt', '.html', '.css'])
        self.blocked_commands = tools_config.get('blocked_commands',
            ['rm -rf', 'sudo', 'chmod 777', '> /dev', 'mkfs', 'dd if='])
        self.max_file_size = tools_config.get('max_file_size_kb', 500) * 1024
        self.max_output = tools_config.get('max_output_chars', 10000)

    def execute(self, tool_name: str, params: dict) -> dict:
        """Execute tool and return result"""
        method = getattr(self, f"_exec_{tool_name}", None)

        if not method:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

        try:
            result = method(params)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _safe_path(self, path: str) -> Path:
        """Ensure path is within project root"""
        # Handle absolute paths
        if path.startswith('/'):
            full_path = Path(path)
        else:
            full_path = (self.root / path).resolve()

        # Security: ensure path is within project
        try:
            full_path.relative_to(self.root)
        except ValueError:
            raise ValueError(f"Path escape blocked: {path}")

        return full_path

    def _exec_read_file(self, params: dict) -> str:
        path = self._safe_path(params['path'])

        if not path.exists():
            raise FileNotFoundError(f"File not found: {params['path']}")

        if path.stat().st_size > self.max_file_size:
            raise ValueError(f"File too large: {path.stat().st_size} bytes")

        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        # Handle line range
        if 'lines' in params and params['lines']:
            try:
                parts = params['lines'].split('-')
                start = int(parts[0]) - 1  # Convert to 0-indexed
                end = int(parts[1]) if len(parts) > 1 else start + 1

                lines = content.split('\n')
                content = '\n'.join(lines[start:end])
            except (ValueError, IndexError):
                pass  # Ignore invalid range

        return content[:self.max_output]

    def _exec_write_file(self, params: dict) -> str:
        path = self._safe_path(params['path'])

        # Safety: only allowed extensions
        ext = path.suffix.lower()
        if ext and ext not in self.allowed_extensions:
            raise ValueError(f"Cannot write to {ext} files (not in allowed list)")

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        content = params['content']
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        return f"Written {len(content)} bytes to {params['path']}"

    def _exec_edit_file(self, params: dict) -> str:
        path = self._safe_path(params['path'])

        if not path.exists():
            raise FileNotFoundError(f"File not found: {params['path']}")

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        old_text = params['old_text']
        new_text = params['new_text']

        if old_text not in content:
            # Provide helpful error with nearby context
            raise ValueError(f"Text not found in file. First 200 chars: {content[:200]}...")

        # Count occurrences
        count = content.count(old_text)
        if count > 1:
            raise ValueError(f"Text found {count} times - must be unique. Add more context.")

        new_content = content.replace(old_text, new_text, 1)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return f"Replaced text in {params['path']} ({len(old_text)} -> {len(new_text)} chars)"

    def _exec_search_code(self, params: dict) -> str:
        query = params['query']
        search_path = params.get('path', '.')
        file_pattern = params.get('file_pattern', '*.py')

        # Use safe path
        if search_path != '.':
            search_path = str(self._safe_path(search_path))
        else:
            search_path = str(self.root)

        cmd = f"grep -rn '{query}' {search_path} --include='{file_pattern}' 2>/dev/null | head -30"

        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(self.root),
            timeout=30
        )

        output = result.stdout.strip()
        return output[:self.max_output] if output else "No matches found"

    def _exec_run_bash(self, params: dict) -> str:
        cmd = params['command']
        timeout = params.get('timeout', 30)

        # Safety: block dangerous commands
        for blocked in self.blocked_commands:
            if blocked in cmd:
                raise ValueError(f"Blocked dangerous command pattern: {blocked}")

        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(self.root),
            timeout=min(timeout, 120)  # Max 2 minutes
        )

        output = result.stdout + result.stderr
        return output[:self.max_output]

    def _exec_list_files(self, params: dict) -> str:
        path = self._safe_path(params.get('path', '.'))
        pattern = params.get('pattern', '*')
        recursive = params.get('recursive', False)

        if recursive:
            files = list(path.rglob(pattern))[:100]
        else:
            files = list(path.glob(pattern))[:50]

        # Format output
        result = []
        for f in sorted(files):
            rel_path = f.relative_to(self.root)
            if f.is_dir():
                result.append(f"{rel_path}/")
            else:
                size = f.stat().st_size
                result.append(f"{rel_path} ({size} bytes)")

        return '\n'.join(result) if result else "No files found"

    def _exec_get_original_document(self, params: dict) -> str:
        """Get original document from Qdrant by file ID"""
        file_id = params['file_id']
        collection = params.get('collection', 'vetka_elisya')

        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(host="localhost", port=6333)

            # Retrieve point by ID
            points = client.retrieve(
                collection_name=collection,
                ids=[file_id],
                with_payload=True
            )

            if not points:
                return f"File not found: {file_id}"

            point = points[0]
            payload = point.payload

            # Return file content and metadata
            result = {
                "path": payload.get("path", "unknown"),
                "name": payload.get("name", "unknown"),
                "content": payload.get("content", "")[:self.max_output],
                "parent_folder": payload.get("parent_folder", ""),
                "depth": payload.get("depth", 0)
            }

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            return f"Error retrieving document: {str(e)}"


# ============================================================================
# AGENTIC LOOP
# ============================================================================

async def agentic_loop(
    message: str,
    model: str,
    tools: List[str],
    max_iterations: int = 5,
    call_llm_func = None
) -> dict:
    """
    Run agent with tools until task complete or max iterations.

    Args:
        message: User message / task
        model: Model to use (e.g., 'deepseek/deepseek-chat')
        tools: List of tool names to enable
        max_iterations: Max tool-use cycles
        call_llm_func: Async function to call LLM (injected dependency)

    Returns:
        {
            'response': 'Final response text',
            'iterations': 3,
            'tool_calls': [
                {'iteration': 1, 'tool': 'read_file', 'params': {...}, 'result': {...}},
                ...
            ],
            'success': True
        }
    """
    executor = ToolExecutor()

    # Build tool definitions
    tool_defs = [TOOL_DEFINITIONS[t] for t in tools if t in TOOL_DEFINITIONS]

    messages = [{"role": "user", "content": message}]
    iterations = 0
    tool_history = []
    final_response = ""

    while iterations < max_iterations:
        iterations += 1
        print(f"[AGENTIC] Iteration {iterations}/{max_iterations}")

        # Call LLM with tools
        if call_llm_func:
            response = await call_llm_func(
                model=model,
                messages=messages,
                tools=tool_defs
            )
        else:
            # Fallback: no LLM function provided
            return {
                'response': f"[ERROR] No LLM function provided for agentic loop",
                'iterations': iterations,
                'tool_calls': tool_history,
                'success': False
            }

        # Check for tool calls
        tool_calls = response.get('tool_calls', [])

        if tool_calls:
            tool_results = []

            for tool_call in tool_calls:
                tool_name = tool_call.get('function', {}).get('name', '')

                try:
                    tool_params = json.loads(tool_call.get('function', {}).get('arguments', '{}'))
                except json.JSONDecodeError:
                    tool_params = {}

                print(f"[TOOL] {tool_name}({json.dumps(tool_params)[:100]}...)")

                # Execute tool
                result = executor.execute(tool_name, tool_params)

                tool_history.append({
                    'iteration': iterations,
                    'tool': tool_name,
                    'params': tool_params,
                    'result': result
                })

                tool_results.append({
                    'tool_call_id': tool_call.get('id', f'call_{iterations}'),
                    'role': 'tool',
                    'content': json.dumps(result)
                })

            # Add to conversation
            messages.append(response.get('message', {'role': 'assistant', 'content': ''}))
            messages.extend(tool_results)

        else:
            # No tool calls - agent is done
            final_response = response.get('message', {}).get('content', '')
            break

    return {
        'response': final_response,
        'iterations': iterations,
        'tool_calls': tool_history,
        'success': True
    }


def sync_agentic_loop(
    message: str,
    model: str,
    tools: List[str],
    max_iterations: int = 5,
    call_llm_func = None
) -> dict:
    """
    Synchronous wrapper for agentic_loop.
    Use this when calling from non-async context.
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        agentic_loop(message, model, tools, max_iterations, call_llm_func)
    )


# ============================================================================
# HOSTESS DECISION LOGIC
# ============================================================================

def hostess_decide(message: str, parsed_mentions: dict) -> dict:
    """
    Hostess decides how to handle the message.

    Returns:
        {
            'mode': 'single' | 'parallel' | 'sequential',
            'models': ['model1', ...],
            'agents': ['PM', 'Dev', ...],
            'tools': ['read_file', ...],
            'scenario': 'code_fix',
            'max_iterations': 3
        }
    """
    config = load_config()

    # If explicit mentions, use them
    if parsed_mentions['mode'] != 'auto':
        return {
            'mode': parsed_mentions['mode'],
            'models': parsed_mentions['models'] or [get_model_for_tier('cheap')],
            'agents': parsed_mentions['agents'],
            'tools': ['read_file', 'search_code'],  # Default safe tools
            'scenario': 'explicit_mention',
            'max_iterations': 3
        }

    # Match scenario
    scenario = match_scenario(message)

    if scenario:
        model_tier = scenario.get('model_tier', 'cheap')

        return {
            'mode': scenario.get('agents', 'single'),
            'models': [get_model_for_tier(model_tier)],
            'agents': scenario.get('team', [scenario.get('preferred_agent', 'Dev')]),
            'tools': scenario.get('tools', []),
            'scenario': scenario['name'],
            'max_iterations': scenario.get('max_iterations', 3)
        }

    # Default: single cheap model, no tools
    return {
        'mode': 'single',
        'models': [get_model_for_tier('cheap')],
        'agents': [],
        'tools': [],
        'scenario': 'default',
        'max_iterations': 1
    }


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Config
    'load_config',
    'save_config',

    # Mentions
    'parse_mentions',
    'get_available_mentions',

    # Scenarios
    'match_scenario',
    'get_model_for_tier',

    # Tools
    'TOOL_DEFINITIONS',
    'get_tools_for_scenario',
    'ToolExecutor',

    # Agentic
    'agentic_loop',
    'sync_agentic_loop',

    # Hostess
    'hostess_decide',

    # Constants
    'PROJECT_ROOT'
]
