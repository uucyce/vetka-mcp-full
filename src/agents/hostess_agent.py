"""
Hostess Agent - Fast router with tool calling.

Uses local Qwen model for quick intelligent decisions on request routing.
Implements tool calling for routing, quick answers, API key management,
camera focus, and knowledge search.

@file hostess_agent.py
@status: active
@phase: 96
@depends: requests, json, re, os, src.agents.tools.SaveAPIKeyTool,
          src.elisya.key_learner, src.elisya.api_key_detector
@used_by: src/api/handlers/user_message_handler.py,
          src/api/handlers/user_message_handler_v2.py

Uses Qwen 0.5B/1.5B or 2B for quick intelligent decisions on how to handle user requests.
Implements tool calling to decide between:
- Quick answers (simple questions, greetings)
- Clarification (ambiguous requests)
- Single agent calls (PM, Dev, QA)
- Full chain execution (PM->Dev->QA)
- Knowledge search (Qdrant/Weaviate)
- File operations
- API key management (save, learn, status, analyze)
- Camera focus for 3D visualization

Think of Hostess as a smart receptionist who directs visitors to the right department.
"""

import json
import re
from typing import Optional, Dict, Any, List
import requests
import os


class HostessAgent:
    """
    Fast, lightweight agent that routes requests using tool calling.

    Uses smallest available Qwen model for speed while maintaining routing accuracy.
    Makes quick decisions on which agent(s) to invoke for each user request.
    """

    def __init__(self, agents_registry: Dict = None, ollama_url: str = None):
        """
        Initialize HostessAgent.

        Args:
            agents_registry: Dictionary of available agents {name: instance}
            ollama_url: Ollama API endpoint (default: http://localhost:11434)
        """
        self.agents = agents_registry or {}
        self.ollama_url = ollama_url or os.getenv(
            "OLLAMA_URL", "http://localhost:11434"
        )

        # Try models in order of preference (speed)
        self.model = self._find_available_model()

        print(f"[HOSTESS] Initialized with model: {self.model}")

        # Define available tools for decision-making
        self.tools = [
            {
                "name": "quick_answer",
                "description": "Answer simple questions directly without calling other agents. Use for greetings, simple facts, clarifications about the system, or short factual questions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "answer": {
                            "type": "string",
                            "description": "Direct answer to user question",
                        }
                    },
                    "required": ["answer"],
                },
            },
            {
                "name": "clarify_question",
                "description": "Ask user for clarification when request is ambiguous, incomplete, or missing critical details.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "Clarifying question to ask user",
                        },
                        "options": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional: suggested options for user to choose from",
                        },
                    },
                    "required": ["question"],
                },
            },
            {
                "name": "call_single_agent",
                "description": "Call one specific agent for focused task. PM for planning/architecture, Dev for coding/implementation, QA for testing/quality.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent": {
                            "type": "string",
                            "enum": ["PM", "Dev", "QA"],
                            "description": "Which agent to call",
                        },
                        "task": {
                            "type": "string",
                            "description": "Specific task description for the agent",
                        },
                    },
                    "required": ["agent", "task"],
                },
            },
            {
                "name": "call_agent_chain",
                "description": "Call full agent chain PM→Dev→QA for complex tasks requiring strategic analysis, implementation and review.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "Complex task for full analysis and implementation",
                        }
                    },
                    "required": ["task"],
                },
            },
            {
                "name": "search_knowledge",
                "description": "Search project knowledge base for relevant files, documentation, or previous solutions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "What to search for",
                        },
                        "type": {
                            "type": "string",
                            "enum": ["files", "docs", "all"],
                            "description": "Search scope",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "show_file",
                "description": "Show contents of a specific file from the project.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to file in project",
                        }
                    },
                    "required": ["file_path"],
                },
            },
            # MARKER-77-03: Phase 77 Memory Sync dialog tool
            {
                "name": "memory_sync_dialog",
                "description": "Ask user about memory sync decisions when filesystem changes are detected. Use to decide whether to keep, trash, or compress changed files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "changes_summary": {
                            "type": "string",
                            "description": "Summary of detected changes (added/modified/deleted files)",
                        },
                        "options": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Available actions: keep, trash, compress, delete",
                        },
                    },
                    "required": ["changes_summary", "options"],
                },
            },
            {
                "name": "camera_focus",
                "description": "Move 3D camera to focus on a file/folder in the visualization. Use when user asks to 'show', 'focus on', 'navigate to', 'look at', or 'zoom to' a file or folder.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "File/folder path to focus on, or 'overview' for tree overview",
                        },
                        "zoom": {
                            "type": "string",
                            "enum": ["close", "medium", "far"],
                            "description": "Zoom level",
                        },
                        "highlight": {
                            "type": "boolean",
                            "description": "Whether to highlight the target node",
                        },
                    },
                    "required": ["target"],
                },
            },
            {
                "name": "save_api_key",
                "description": "Save API key with auto-detection. Use when user pastes an API key (starts with sk-, AIza, gsk_, hf_, etc.). Automatically detects provider (OpenRouter, Anthropic, Gemini, OpenAI, etc.).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "The API key to save"},
                        "provider": {
                            "type": "string",
                            "description": "Optional: force specific provider",
                        },
                    },
                    "required": ["key"],
                },
            },
            # Phase 57.9: API Key Learning Tools
            {
                "name": "learn_api_key",
                "description": "Learn a new API key type that isn't auto-detected. Use when save_api_key fails to detect provider. Ask user for provider name first, then call this.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "The API key to learn from",
                        },
                        "provider": {
                            "type": "string",
                            "description": "Name of the provider (e.g., 'tavily', 'serper')",
                        },
                    },
                    "required": ["key", "provider"],
                },
            },
            {
                "name": "get_api_key_status",
                "description": "Check status of API keys and configured providers. Use when user asks 'what keys do I have?', 'which providers are configured?'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "description": "Optional: specific provider to check",
                        }
                    },
                },
            },
            {
                "name": "analyze_unknown_key",
                "description": "Analyze an unknown API key to identify its pattern. Use when a key doesn't match known providers to help identify it.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "The API key to analyze",
                        }
                    },
                    "required": ["key"],
                },
            },
        ]

    def _find_available_model(self) -> str:
        """Find first available Qwen model, with fallback chain"""
        candidates = [
            "qwen2.5:0.5b",  # Smallest and fastest
            "qwen2.5:1.5b",  # Fallback
            "qwen2:0.5b",  # Older version
            "qwen2:1.5b",  # Older version
            "qwen2:7b",  # Already installed in this setup
            "llama3.2:1b",  # Other fast model
        ]

        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                available_models = [m["name"] for m in data.get("models", [])]
                available_bases = [m.split(":")[0] for m in available_models]

                print(f"[HOSTESS] Available models: {available_models[:5]}")

                # Find first candidate available (exact match or base match)
                for candidate in candidates:
                    # Try exact match first
                    if candidate in available_models:
                        print(f"[HOSTESS] Using model: {candidate}")
                        return candidate

                    # Try base match (e.g., "qwen2" for "qwen2:7b")
                    base = candidate.split(":")[0]
                    for model in available_models:
                        if model.startswith(base):
                            print(f"[HOSTESS] Using model: {model} (matched {base})")
                            return model
        except Exception as e:
            print(f"[HOSTESS] Could not check available models: {e}")

        # Default fallback - use qwen2:7b if available, else llama3.2:1b
        print(f"[HOSTESS] Using default fallback model")
        return "qwen2:7b"

    def process(self, user_message: str, context: Dict = None) -> Dict[str, Any]:
        """
        Main entry point. Process user message and decide action.

        Args:
            user_message: The user's request
            context: Additional context {node_path, node_id, etc.}

        Returns:
            Dictionary with action, result, confidence, etc.
            {
                "action": "quick_answer|clarify|agent_call|chain_call|search|show_file",
                "result": <action result or task description>,
                "tool_used": <tool name>,
                "confidence": 0.0-1.0,
                "agent": <agent name if applicable>,
                "task": <task description if applicable>
            }
        """

        # Build system prompt with available tools and rich context (Phase 44)
        system_prompt = self._build_system_prompt(context)

        # Get Qwen's tool decision
        response_text = self._call_ollama_with_tools(
            system_prompt, user_message, context
        )

        # Parse which tool Qwen selected
        tool_call = self._parse_tool_call(response_text)

        if not tool_call:
            # No valid tool call parsed - fallback to chain
            print(f"[HOSTESS] Could not parse tool call from: {response_text[:100]}")
            return {
                "action": "chain_call",
                "task": user_message,
                "tool_used": "fallback",
                "confidence": 0.4,
                "reason": "No tool call detected",
            }

        # Execute the selected tool
        result = self._execute_tool(tool_call, user_message, context)

        return result

    def _build_system_prompt(self, context: Dict = None) -> str:
        """
        Build system prompt that describes all available tools.

        Phase 44: Enhanced with rich context for better routing decisions.

        Args:
            context: Rich context from HostessContextBuilder

        Returns:
            System prompt string
        """

        base_prompt = """You are a tool calling router. Analyze the user message and respond ONLY with JSON.

TOOLS:
1. quick_answer - For greetings, simple questions, info requests
2. clarify_question - For ambiguous or incomplete requests
3. call_single_agent - For focused tasks (Dev=coding, QA=testing, PM=design)
4. call_agent_chain - For complex multi-step tasks
5. search_knowledge - For finding information
6. show_file - For viewing file contents
7. camera_focus - Move 3D camera to focus on file/folder. Use for "show me", "focus on", "look at", "zoom to", "navigate to", "покажи", "перейди к", "подлети к"
8. save_api_key - Save API key with auto-detection. Use when message contains known API key (sk-or-*, sk-ant-*, AIza*, gsk_*, hf_*, r8_*, fw_*, nvapi-*, etc.)
9. analyze_unknown_key - Analyze unknown API key pattern. Use when key doesn't match known patterns.
10. learn_api_key - Learn new key type after user confirms provider. Use after analyze_unknown_key.
11. get_api_key_status - Check configured API keys. Use when user asks "what keys?", "which providers?"

RULES:
- "hello", "hi", "привет" = quick_answer
- Ask to code/write = call_single_agent with Dev
- Ask to test = call_single_agent with QA
- Ask to design/plan = call_single_agent with PM
- Multi-step tasks = call_agent_chain
- Unclear requests = clarify_question
- Complex requests = call_agent_chain
- "show me X", "focus on X", "look at X", "подлети к X", "покажи X" = camera_focus with target=X
- Known API key (sk-or-*, sk-ant-*, AIza*, gsk_*, hf_*) = save_api_key with key=<the key>
- Unknown API key pattern = analyze_unknown_key first, then ask user for provider, then learn_api_key
- "what keys", "which providers", "какие ключи" = get_api_key_status
"""

        # Add rich context if available (Phase 44)
        if context:
            context_summary = context.get("context_summary", "")
            if (
                context_summary
                and context_summary != "No additional context available."
            ):
                base_prompt += f"""
CURRENT CONTEXT:
{context_summary}
"""

            # Add file preview if user is viewing a file
            if context.get("has_file_context"):
                file_type = context.get("file_type", "")
                file_preview = context.get("file_content", "")[:500]
                if file_preview:
                    base_prompt += f"""
FILE PREVIEW ({file_type}):
{file_preview}...
"""

            # Add related files hint for search decisions
            related = context.get("related_files", [])[:3]
            if related:
                base_prompt += f"""
RELATED FILES: {", ".join(related)}
"""

        base_prompt += """
RESPOND ONLY WITH JSON:
{"tool": "tool_name", "params": {...}}

Examples:
User: "hello" → {"tool": "quick_answer", "params": {"answer": "Hi! How can I help?"}}
User: "write function" → {"tool": "call_single_agent", "params": {"agent": "Dev", "task": "write function"}}
User: "design database" → {"tool": "call_single_agent", "params": {"agent": "PM", "task": "design database"}}
User: "code, test, review" → {"tool": "call_agent_chain", "params": {"task": "code, test, review"}}
User: "подлети к main.py" → {"tool": "camera_focus", "params": {"target": "main.py", "zoom": "close"}}
User: "покажи src/agents" → {"tool": "camera_focus", "params": {"target": "src/agents", "zoom": "medium"}}
User: "focus on tools.py" → {"tool": "camera_focus", "params": {"target": "tools.py", "zoom": "close"}}
User: "sk-or-v1-abc123..." → {"tool": "save_api_key", "params": {"key": "sk-or-v1-abc123..."}}
User: "save key AIzaSy..." → {"tool": "save_api_key", "params": {"key": "AIzaSy..."}}
User: "tvly-dev-xxx..." (unknown prefix) → {"tool": "analyze_unknown_key", "params": {"key": "tvly-dev-xxx..."}}
User: "it's for Tavily" (after unknown key) → {"tool": "learn_api_key", "params": {"key": "tvly-dev-xxx...", "provider": "tavily"}}
User: "what keys do I have?" → {"tool": "get_api_key_status", "params": {}}
User: "какие ключи настроены?" → {"tool": "get_api_key_status", "params": {}}
"""
        return base_prompt

    def _call_ollama_with_tools(
        self, system_prompt: str, user_msg: str, context: Dict
    ) -> str:
        """
        Call Ollama API with tool decision request.

        Args:
            system_prompt: System prompt with tool descriptions
            user_msg: User's message
            context: Additional context

        Returns:
            Qwen's response (should contain JSON tool call)
        """

        # Build context string
        context_str = ""
        if context:
            if context.get("node_path"):
                context_str += f"\nFile: {context['node_path']}"
            if context.get("available_files"):
                context_str += f"\nFiles: {', '.join(context['available_files'][:3])}"

        # Prepare request - use simpler, more direct prompt
        full_prompt = f"""{system_prompt}

USER MESSAGE:
{user_msg}{context_str}

RESPOND WITH ONLY JSON, NO OTHER TEXT:"""

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Very low for consistent JSON
                "top_p": 0.5,  # Focus on most likely tokens
                "num_predict": 250,  # Short response
                "stop": ["\n\n"],  # Stop at double newline
            },
        }

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate", json=payload, timeout=20
            )
            if resp.status_code == 200:
                result = resp.json()
                response_text = result.get("response", "").strip()
                print(f"[HOSTESS] Ollama response: {response_text[:100]}")
                return response_text
            else:
                print(f"[HOSTESS] Ollama error: {resp.status_code}")
                return ""
        except requests.exceptions.Timeout:
            print(f"[HOSTESS] Ollama timeout")
            return ""
        except Exception as e:
            print(f"[HOSTESS] Ollama error: {e}")
            return ""

    def _parse_tool_call(self, response: str) -> Optional[Dict]:
        """
        Parse JSON tool call from Qwen's response.

        Looks for JSON object containing 'tool' and 'params' keys.
        Very resilient - tries multiple patterns.
        """
        if not response:
            return None

        try:
            # Try 1: Direct JSON parse
            try:
                parsed = json.loads(response)
                if "tool" in parsed and "params" in parsed:
                    return parsed
            except:
                pass

            # Try 2: Find JSON object with tool field
            json_patterns = [
                r'\{[^{}]*"tool"[^{}]*"params"[^{}]*\}',  # With both fields
                r'\{[^{}]*"tool"[^{}]*\}',  # Just tool field
                r'\{"tool"[^}]*\}',  # Strict format
            ]

            for pattern in json_patterns:
                match = re.search(pattern, response, re.DOTALL)
                if match:
                    json_str = match.group()
                    try:
                        parsed = json.loads(json_str)
                        if "tool" in parsed:
                            # Add empty params if missing
                            if "params" not in parsed:
                                parsed["params"] = {}
                            return parsed
                    except:
                        continue

            # Try 3: Extract and reconstruct
            # Look for patterns like: tool_name, or agent: PM, etc.
            tool_match = re.search(r'"tool"\s*:\s*"([^"]+)"', response)
            if tool_match:
                tool_name = tool_match.group(1)

                # Try to extract params
                params = {}

                if tool_name == "quick_answer":
                    answer_match = re.search(r'"answer"\s*:\s*"([^"]+)"', response)
                    if answer_match:
                        params["answer"] = answer_match.group(1)

                elif tool_name == "call_single_agent":
                    agent_match = re.search(r'"agent"\s*:\s*"([^"]+)"', response)
                    task_match = re.search(r'"task"\s*:\s*"([^"]+)"', response)
                    if agent_match:
                        params["agent"] = agent_match.group(1)
                    if task_match:
                        params["task"] = task_match.group(1)

                elif tool_name == "clarify_question":
                    question_match = re.search(r'"question"\s*:\s*"([^"]+)"', response)
                    if question_match:
                        params["question"] = question_match.group(1)

                elif tool_name == "camera_focus":
                    target_match = re.search(r'"target"\s*:\s*"([^"]+)"', response)
                    zoom_match = re.search(r'"zoom"\s*:\s*"([^"]+)"', response)
                    if target_match:
                        params["target"] = target_match.group(1)
                    if zoom_match:
                        params["zoom"] = zoom_match.group(1)
                    # Default target if not found - try to extract from user message
                    if not params.get("target"):
                        params["target"] = "overview"

                elif tool_name == "save_api_key":
                    key_match = re.search(r'"key"\s*:\s*"([^"]+)"', response)
                    provider_match = re.search(r'"provider"\s*:\s*"([^"]+)"', response)
                    if key_match:
                        params["key"] = key_match.group(1)
                    if provider_match:
                        params["provider"] = provider_match.group(1)

                if params:  # Only return if we extracted something
                    return {"tool": tool_name, "params": params}

        except Exception as e:
            print(f"[HOSTESS] Parse error: {e}")

        return None

    def _execute_tool(self, tool_call: Dict, user_msg: str, context: Dict) -> Dict:
        """
        Execute the tool selected by Qwen and return structured result.

        Args:
            tool_call: {"tool": "...", "params": {...}}
            user_msg: Original user message
            context: Additional context

        Returns:
            Execution result with action, confidence, etc.
        """

        tool_name = tool_call.get("tool", "")
        params = tool_call.get("params", {})

        # Route to specific tool handler
        if tool_name == "quick_answer":
            return {
                "action": "quick_answer",
                "result": params.get("answer", "I can help with that."),
                "tool_used": "quick_answer",
                "confidence": 0.95,
            }

        elif tool_name == "clarify_question":
            return {
                "action": "clarify",
                "result": params.get("question", "Could you provide more details?"),
                "options": params.get("options", []),
                "tool_used": "clarify_question",
                "confidence": 0.9,
            }

        elif tool_name == "call_single_agent":
            agent = params.get("agent", "Dev")
            task = params.get("task", user_msg)

            # Validate agent name
            if agent not in ["PM", "Dev", "QA"]:
                agent = "Dev"

            return {
                "action": "agent_call",
                "agent": agent,
                "task": task,
                "tool_used": "call_single_agent",
                "confidence": 0.9,
            }

        elif tool_name == "call_agent_chain":
            return {
                "action": "chain_call",
                "task": params.get("task", user_msg),
                "tool_used": "call_agent_chain",
                "confidence": 0.85,
            }

        elif tool_name == "search_knowledge":
            return {
                "action": "search",
                "query": params.get("query", user_msg),
                "search_type": params.get("type", "all"),
                "tool_used": "search_knowledge",
                "confidence": 0.85,
            }

        elif tool_name == "show_file":
            return {
                "action": "show_file",
                "file_path": params.get("file_path", ""),
                "tool_used": "show_file",
                "confidence": 0.9,
            }

        elif tool_name == "camera_focus":
            return {
                "action": "camera_focus",
                "target": params.get("target", "overview"),
                "zoom": params.get("zoom", "medium"),
                "highlight": params.get("highlight", True),
                "tool_used": "camera_focus",
                "confidence": 0.95,
            }

        elif tool_name == "save_api_key":
            # Execute the SaveAPIKeyTool
            key = params.get("key", "")
            provider = params.get("provider", "auto")

            if not key:
                return {
                    "action": "quick_answer",
                    "result": "I didn't catch the API key. Please paste your API key and I'll save it for you.",
                    "tool_used": "save_api_key",
                    "confidence": 0.5,
                }

            # Import and execute the tool
            try:
                from src.agents.tools import SaveAPIKeyTool
                import asyncio

                tool = SaveAPIKeyTool()

                # Run async tool without blocking
                try:
                    result = asyncio.run(tool.execute(key=key, provider=provider))
                except Exception as e:
                    print(f"[HOSTESS] Error saving API key: {e}")
                    result = None

                if result.success:
                    return {
                        "action": "save_api_key",
                        "result": result.result,
                        "tool_used": "save_api_key",
                        "confidence": 0.95,
                    }
                else:
                    return {
                        "action": "quick_answer",
                        "result": f"Could not save key: {result.error}",
                        "tool_used": "save_api_key",
                        "confidence": 0.8,
                    }
            except Exception as e:
                print(f"[HOSTESS] Error saving API key: {e}")
                return {
                    "action": "quick_answer",
                    "result": f"Error saving API key: {str(e)[:100]}",
                    "tool_used": "save_api_key",
                    "confidence": 0.5,
                }

        # Phase 57.9: API Key Learning Tools
        elif tool_name == "learn_api_key":
            key = params.get("key", "")
            provider = params.get("provider", "")

            if not key or not provider:
                return {
                    "action": "quick_answer",
                    "result": "I need both the API key and the provider name. What service is this key for?",
                    "tool_used": "learn_api_key",
                    "confidence": 0.6,
                }

            try:
                # Use KeyLearner directly (sync) to avoid event loop issues
                from src.elisya.key_learner import get_key_learner

                learner = get_key_learner()
                success, message = learner.learn_key_type(key, provider, save_key=True)

                if success:
                    return {
                        "action": "learn_api_key",
                        "result": f"✅ Learned {provider} key pattern! Key saved to config.",
                        "provider": provider,
                        "tool_used": "learn_api_key",
                        "confidence": 0.95,
                    }
                else:
                    return {
                        "action": "quick_answer",
                        "result": f"Could not learn key: {message}",
                        "tool_used": "learn_api_key",
                        "confidence": 0.7,
                    }
            except Exception as e:
                print(f"[HOSTESS] Error learning API key: {e}")
                return {
                    "action": "quick_answer",
                    "result": f"Error learning key: {str(e)[:100]}",
                    "tool_used": "learn_api_key",
                    "confidence": 0.5,
                }

        elif tool_name == "get_api_key_status":
            provider_name = params.get("provider", None)

            try:
                # Use config and KeyLearner directly (sync) to avoid event loop issues
                import json
                from pathlib import Path
                from src.elisya.key_learner import get_key_learner

                config_file = Path(__file__).parent.parent / "data" / "config.json"

                config = {}
                if config_file.exists():
                    with open(config_file, "r", encoding="utf-8") as f:
                        config = json.load(f)

                api_keys = config.get("api_keys", {})

                # Helper to count keys
                def count_keys(value) -> int:
                    if value is None:
                        return 0
                    if isinstance(value, str):
                        return 1 if value else 0
                    if isinstance(value, list):
                        return len([k for k in value if k])
                    if isinstance(value, dict):
                        total = 0
                        if value.get("paid"):
                            total += 1
                        if isinstance(value.get("free"), list):
                            total += len(value["free"])
                        return total
                    return 0

                if provider_name:
                    # Check specific provider
                    provider_name = provider_name.lower().strip()
                    keys_data = api_keys.get(provider_name)
                    key_count = count_keys(keys_data)

                    learner = get_key_learner()
                    is_learned = provider_name in learner.get_learned_providers()

                    response = f"{provider_name.title()}: {key_count} key(s) configured"
                    if is_learned:
                        response += " (learned pattern)"

                    return {
                        "action": "get_api_key_status",
                        "result": response,
                        "tool_used": "get_api_key_status",
                        "confidence": 0.95,
                    }
                else:
                    # Get all providers
                    status = {}
                    for p, keys_data in api_keys.items():
                        key_count = count_keys(keys_data)
                        status[p] = {"count": key_count, "active": key_count > 0}

                    # Add learned providers
                    learner = get_key_learner()
                    for learned_p in learner.get_learned_providers():
                        if learned_p not in status:
                            status[learned_p] = {
                                "count": 0,
                                "active": False,
                                "learned": True,
                            }
                        else:
                            status[learned_p]["learned"] = True

                    providers_with_keys = [
                        p for p, s in status.items() if s.get("active")
                    ]

                    if providers_with_keys:
                        response = f"Configured providers: {', '.join(providers_with_keys)}. ({len(providers_with_keys)}/{len(status)} active)"
                    else:
                        response = "No API keys configured yet."

                    return {
                        "action": "get_api_key_status",
                        "result": response,
                        "status": status,
                        "tool_used": "get_api_key_status",
                        "confidence": 0.95,
                    }

            except Exception as e:
                print(f"[HOSTESS] Error getting key status: {e}")
                return {
                    "action": "quick_answer",
                    "result": f"Error checking keys: {str(e)[:100]}",
                    "tool_used": "get_api_key_status",
                    "confidence": 0.5,
                }

        elif tool_name == "analyze_unknown_key":
            key = params.get("key", "")

            if not key:
                return {
                    "action": "quick_answer",
                    "result": "Please paste the API key you want me to analyze.",
                    "tool_used": "analyze_unknown_key",
                    "confidence": 0.5,
                }

            try:
                # Use KeyLearner directly (sync) to avoid event loop issues
                from src.elisya.key_learner import get_key_learner
                from src.elisya.api_key_detector import detect_api_key

                learner = get_key_learner()

                # First check if it matches a learned pattern
                learned_match = learner.check_learned_pattern(key)
                if learned_match:
                    return {
                        "action": "save_api_key",
                        "result": f"Recognized as {learned_match['display_name']}! Saving now...",
                        "provider": learned_match["provider"],
                        "key": key,
                        "tool_used": "analyze_unknown_key",
                        "confidence": learned_match.get("confidence", 0.9),
                    }

                # Try main detector
                detected = detect_api_key(key)
                if detected:
                    return {
                        "action": "save_api_key",
                        "result": f"Recognized as {detected['display_name']}! Saving now...",
                        "provider": detected["provider"],
                        "key": key,
                        "tool_used": "analyze_unknown_key",
                        "confidence": detected.get("confidence", 0.9),
                    }

                # Unknown - need user to identify
                analysis = learner.analyze_key(key)
                prefix = analysis.get("prefix", "unknown")

                # Build hints
                hints = []
                if analysis["prefix"]:
                    hints.append(f"prefix '{analysis['prefix']}'")
                hints.append(f"length {analysis['length']}")
                hints.append(f"charset: {analysis['charset']}")

                return {
                    "action": "ask_provider",
                    "result": f"I don't recognize this key (prefix: {prefix}). What service is it for?",
                    "analysis": analysis,
                    "hints": hints,
                    "pending_key": key,  # Remember key for learn_api_key
                    "tool_used": "analyze_unknown_key",
                    "confidence": 0.8,
                }

            except Exception as e:
                print(f"[HOSTESS] Error analyzing key: {e}")
                return {
                    "action": "quick_answer",
                    "result": f"Error analyzing key: {str(e)[:100]}",
                    "tool_used": "analyze_unknown_key",
                    "confidence": 0.5,
                }

        # Unknown tool - use chain as safe default
        print(f"[HOSTESS] Unknown tool: {tool_name}, falling back to chain")
        return {
            "action": "chain_call",
            "task": user_msg,
            "tool_used": "fallback",
            "confidence": 0.5,
            "reason": f"Unknown tool: {tool_name}",
        }


# Global singleton instance
_hostess_instance = None
_hostess_lock = None


def get_hostess(agents_registry: Dict = None, ollama_url: str = None) -> HostessAgent:
    """
    Get or create the Hostess agent singleton.

    Args:
        agents_registry: Dictionary of available agents
        ollama_url: Ollama API endpoint

    Returns:
        HostessAgent instance
    """
    global _hostess_instance

    # Initialize lock if needed
    import threading

    global _hostess_lock
    if _hostess_lock is None:
        _hostess_lock = threading.Lock()

    if _hostess_instance is None:
        with _hostess_lock:
            # Double-check after lock
            if _hostess_instance is None:
                _hostess_instance = HostessAgent(
                    agents_registry=agents_registry, ollama_url=ollama_url
                )

    return _hostess_instance


def reset_hostess():
    """Reset the hostess singleton (for testing)"""
    global _hostess_instance
    _hostess_instance = None
