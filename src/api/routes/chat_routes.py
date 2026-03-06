"""
VETKA Chat Routes - FastAPI Version

@file chat_routes.py
@status ACTIVE
@phase Phase 39.5
@lastAudit 2026-01-05

Chat API routes - THE BIG ONE!
Migrated from src/server/routes/chat_routes.py (Flask Blueprint)

Endpoints:
- GET /api/chat/history - Get chat history for a node
- POST /api/chat/clear-history - Clear chat history for a node
- POST /api/chat - Universal Chat API endpoint (THE MAIN ONE!)

Changes from Flask version:
- Blueprint -> APIRouter
- request.get_json() -> Pydantic BaseModel
- request.args.get() -> Query()
- current_app.config -> request.app.state
- return jsonify({}) -> return {}
- def -> async def
"""

import os
import time
import uuid
import json
import hashlib
import asyncio
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List


router = APIRouter(prefix="/api", tags=["chat"])


# ============================================================
# PYDANTIC MODELS
# ============================================================


class ChatRequest(BaseModel):
    """Main chat request - THE BIG ONE."""

    message: str
    conversation_id: Optional[str] = None
    model_override: Optional[str] = None
    model_source: Optional[str] = None  # Phase 111.9: Source for multi-provider routing (poe, polza, etc.)
    system_prompt: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 999999
    node_id: Optional[str] = None
    node_path: Optional[str] = None
    file_path: Optional[str] = None


class ClearHistoryRequest(BaseModel):
    """Request to clear chat history."""

    path: str


class QuickChatRequest(BaseModel):
    """
    Lightweight MCC chat contract.
    Used by MiniChat quick path.
    """

    message: str
    role: str = "architect"
    user_id: str = "danila"
    context: Dict[str, Any] = {}


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def _get_chat_components(request: Request) -> dict:
    """Get chat-related components from app state (DI pattern)."""
    flask_config = getattr(request.app.state, "flask_config", {})
    return {
        "get_memory_manager": flask_config.get("get_memory_manager"),
        "get_orchestrator": flask_config.get("get_orchestrator"),
        "get_hostess": flask_config.get("get_hostess"),
        "get_model_for_task": flask_config.get("get_model_for_task"),
        "is_model_banned": flask_config.get("is_model_banned"),
        "model_router": flask_config.get("model_router"),
        "api_gateway": flask_config.get("api_gateway"),
        "qdrant_manager": flask_config.get("qdrant_manager"),
        "CHAT_HISTORY_DIR": flask_config.get("CHAT_HISTORY_DIR"),
        # Feature flags
        "ELISYA_ENABLED": flask_config.get("ELISYA_ENABLED", False),
        "PARALLEL_MODE": flask_config.get("PARALLEL_MODE", False),
        "HOSTESS_AVAILABLE": flask_config.get("HOSTESS_AVAILABLE", False),
        # "API_GATEWAY_AVAILABLE": flask_config.get("API_GATEWAY_AVAILABLE", False),  # REMOVED: Phase 95
        "MODEL_ROUTER_V2_AVAILABLE": flask_config.get(
            "MODEL_ROUTER_V2_AVAILABLE", False
        ),
        "QDRANT_AUTO_RETRY_AVAILABLE": flask_config.get(
            "QDRANT_AUTO_RETRY_AVAILABLE", False
        ),
    }


def _get_chat_history_file(chat_dir: Path, node_path: str) -> Path:
    """Get chat history file path for a node."""
    if not chat_dir:
        chat_dir = Path("data/chat_history")
        chat_dir.mkdir(parents=True, exist_ok=True)
    path_hash = hashlib.md5(node_path.encode()).hexdigest()[:16]
    return chat_dir / f"{path_hash}.json"


def _load_chat_history(chat_dir: Path, node_path: str) -> list:
    """Load chat history for a specific node."""
    file = _get_chat_history_file(chat_dir, node_path)
    if file.exists():
        try:
            return json.loads(file.read_text())
        except Exception as e:
            print(f"  [Chat] Error loading history: {e}")
            return []
    return []


def _build_myco_quick_reply(message: str, payload: Dict[str, Any], context: Dict[str, Any]) -> str:
    """
    MARKER_162.P3.MYCO.JEPA_GEMMA_LOCAL_FASTPATH.V1
    Lightweight MYCO response builder with hidden memory payload.
    """
    focus = dict(context or {})
    label = str(
        focus.get("label")
        or focus.get("task_id")
        or focus.get("taskId")
        or focus.get("node_id")
        or focus.get("nodeId")
        or "project"
    )
    user_name = str(payload.get("user_name") or payload.get("user_id") or "operator")
    active_project_id = str(payload.get("active_project_id") or "")
    recent = payload.get("recent_tasks_by_project") or {}
    active_recent = recent.get(active_project_id) if isinstance(recent, dict) and active_project_id else None
    active_recent = active_recent if isinstance(active_recent, list) else []
    active_task = active_recent[0] if active_recent else {}
    active_task_title = str(active_task.get("title") or "").strip()
    fastpath = payload.get("fastpath") or {}
    fast_mode = str(fastpath.get("mode") or "local")
    hidden = payload.get("hidden_index") or {}
    indexed_sources = int(hidden.get("source_count") or 0)

    prompt = str(message or "").strip()
    if prompt.lower() in {"?", "/myco", "/help myco", "help"}:
        return (
            f"MYCO {user_name}, quick guide:\n"
            f"- focus: {label}\n"
            f"- mode: {fast_mode}\n"
            f"- hidden memory sources: {indexed_sources}\n"
            f"- next: double-click node to drill or ask for task dispatch"
        )

    task_line = f"- active task: {active_task_title}" if active_task_title else "- active task: not pinned"
    return (
        f"MYCO {user_name}, context loaded.\n"
        f"- focus: {label}\n"
        f"{task_line}\n"
        f"- project: {active_project_id or 'n/a'}\n"
        f"- hidden memory index: {indexed_sources} sources\n"
        f"- tell me: explain node / plan next action / map dependencies"
    )


# ============================================================
# ROUTES
# ============================================================


@router.get("/chat/history")
async def get_chat_history(
    path: str = Query(..., description="Node path"), request: Request = None
):
    """
    Get chat history for a specific node.

    Returns history with message count.
    """
    components = _get_chat_components(request)
    chat_dir = components.get("CHAT_HISTORY_DIR")

    history = _load_chat_history(chat_dir, path)
    print(f"  [Chat] Loading history for '{path}': {len(history)} messages")

    return {
        "success": True,
        "history": history,
        "node_path": path,
        "count": len(history),
    }


@router.post("/chat/clear-history")
async def clear_chat_history(req: ClearHistoryRequest, request: Request):
    """
    Clear chat history for a specific node.
    """
    try:
        components = _get_chat_components(request)
        chat_dir = components.get("CHAT_HISTORY_DIR")

        file = _get_chat_history_file(chat_dir, req.path)
        if file.exists():
            file.unlink()
            return {"success": True, "message": "History cleared"}
        else:
            return {"success": True, "message": "No history to clear"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/quick")
async def api_chat_quick(req: QuickChatRequest, request: Request):
    """
    MARKER_162.P3.MYCO.JEPA_GEMMA_LOCAL_FASTPATH.V1
    MARKER_162.P3.MYCO.ENGRAM_USER_TASK_MEMORY.V1
    Lightweight chat endpoint for MCC MiniChat.
    """
    msg = str(req.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="message is required")

    role = str(req.role or "architect").strip().lower()
    context = dict(req.context or {})
    helper_mode = str(context.get("helper_mode") or context.get("helperMode") or "").strip().lower()
    is_myco = role == "helper_myco" or helper_mode in {"passive", "active"} or msg.lower() in {"?", "/myco", "/help myco", "help"}

    if is_myco:
        try:
            from src.services.project_config import ProjectConfig
            from src.services.myco_memory_bridge import build_myco_memory_payload
            from src.orchestration.context_packer import get_context_packer

            cfg = ProjectConfig.load()
            payload = build_myco_memory_payload(
                user_id=str(req.user_id or "danila"),
                active_project_id=str(getattr(cfg, "project_id", "") or ""),
                focus=context,
            )

            # Optional JEPA summary signal from context packer when prompt/context is verbose.
            packed: Dict[str, Any] = {}
            try:
                packer = get_context_packer()
                packed = packer.pack_context(
                    user_message=msg,
                    context_data={
                        "myco_focus": context,
                        "myco_payload": {
                            "user_name": payload.get("user_name"),
                            "active_project_id": payload.get("active_project_id"),
                            "recent_tasks_by_project": payload.get("recent_tasks_by_project"),
                        },
                    },
                    max_context_chars=2200,
                ) or {}
            except Exception:
                packed = {}

            response = _build_myco_quick_reply(msg, payload, context)
            return {
                "success": True,
                "response": response,
                "role": "helper_myco",
                "mode": "local_fastpath",
                "fastpath": payload.get("fastpath"),
                "hidden_index": payload.get("hidden_index"),
                "packed_meta": packed.get("meta", {}),
                "marker": "MARKER_162.P3.MYCO.JEPA_GEMMA_LOCAL_FASTPATH.V1",
            }
        except Exception as e:
            return {
                "success": True,
                "response": f"MYCO helper fallback: {str(e)[:160]}",
                "role": "helper_myco",
                "mode": "fallback",
            }

    # Architect quick path fallback: route to regular /chat pipeline.
    try:
        chat_req = ChatRequest(
            message=msg,
            node_id=str(context.get("node_id") or context.get("nodeId") or ""),
            node_path=str(context.get("focus_scope_key") or context.get("focusScopeKey") or ""),
            file_path=str(context.get("file_path") or ""),
        )
        result = await api_chat(chat_req, request)
        if isinstance(result, dict):
            result.setdefault("success", True)
            return result
        return {"success": True, "response": str(result)}
    except Exception as e:
        return {
            "success": True,
            "response": f"⚠ quick architect fallback: {str(e)[:160]}",
            "role": "assistant",
            "mode": "fallback",
        }


@router.post("/chat")
async def api_chat(req: ChatRequest, request: Request):
    """
    Universal Chat API endpoint - THE BIG ONE!

    Handles:
    1. Hostess routing (decides which agent/model)
    2. Agent orchestration (PM -> Architect -> Dev -> QA)
    3. Memory persistence (triple write)
    4. Evaluation scoring
    5. Response generation

    Flow:
    User Message -> Hostess Decision ->
    If simple: Direct LLM response
    If complex: Orchestrator workflow
    -> EvalAgent scoring -> Memory save -> Response
    """
    try:
        # === PHASE 80.3: MCP AGENT HANDLING ===
        # MCP agents are external - forward to team messaging
        if req.model_override and req.model_override.startswith("mcp/"):
            agent_id = req.model_override.replace("mcp/", "")
            conversation_id = req.conversation_id or str(uuid.uuid4())

            # Forward to team messages for Claude Code / Browser Haiku
            from src.api.routes.debug_routes import team_messages, KNOWN_AGENTS

            agent_info = KNOWN_AGENTS.get(agent_id, {})
            agent_name = agent_info.get("name", agent_id)

            # Add message to team buffer
            team_messages.append(
                {
                    "id": str(uuid.uuid4()),
                    "from": "user",
                    "to": agent_id,
                    "message": req.message,
                    "conversation_id": conversation_id,
                    "timestamp": time.time(),
                    "node_path": req.node_path,
                    "pending": True,
                }
            )

            # Keep buffer reasonable
            if len(team_messages) > 100:
                team_messages.pop(0)

            print(f"  [MCP] Message forwarded to {agent_name} via team messaging")

            # Return stub response
            if agent_id == "claude_code":
                stub_response = (
                    f"📨 Сообщение отправлено в **{agent_name}**.\n\n"
                    "Claude Code работает через MCP в терминале.\n"
                    "Проверьте терминал для ответа или используйте:\n"
                    "```\ncurl http://localhost:8000/api/debug/team-messages\n```"
                )
            elif agent_id == "browser_haiku":
                stub_response = (
                    f"📨 Сообщение отправлено в **{agent_name}**.\n\n"
                    "Browser Haiku работает в Chrome Console.\n"
                    "Используйте `vetkaAPI.getTeamMessages()` в консоли браузера."
                )
            else:
                stub_response = (
                    f"📨 Сообщение отправлено агенту **{agent_name}**.\n\n"
                    "MCP агенты работают вне VETKA. Проверьте соответствующий интерфейс."
                )

            return {
                "conversation_id": conversation_id,
                "response": stub_response,
                "model": req.model_override,
                "provider": "mcp",
                "processing_time_ms": 0,
                "agent": agent_name,
                "action": "mcp_forward",
                "mcp_pending": True,
                "timestamp": time.time(),
            }

        # Get components via DI
        components = _get_chat_components(request)
        get_memory_manager = components["get_memory_manager"]
        get_orchestrator = components["get_orchestrator"]
        get_hostess = components.get("get_hostess")
        get_model_for_task = components.get("get_model_for_task")
        is_model_banned = components.get("is_model_banned")
        model_router = components.get("model_router")
        api_gateway = components.get("api_gateway")
        qdrant_manager = components.get("qdrant_manager")

        # Feature flags
        ELISYA_ENABLED = components.get("ELISYA_ENABLED", False)
        PARALLEL_MODE = components.get("PARALLEL_MODE", False)
        HOSTESS_AVAILABLE = components.get("HOSTESS_AVAILABLE", False)
        # API_GATEWAY_AVAILABLE = components.get("API_GATEWAY_AVAILABLE", False)  # REMOVED: Phase 95
        MODEL_ROUTER_V2_AVAILABLE = components.get("MODEL_ROUTER_V2_AVAILABLE", False)
        QDRANT_AUTO_RETRY_AVAILABLE = components.get(
            "QDRANT_AUTO_RETRY_AVAILABLE", False
        )

        # Import EvalAgent
        from src.agents.eval_agent import EvalAgent

        # Extract parameters
        user_message = req.message.strip()
        conversation_id = req.conversation_id or str(uuid.uuid4())
        model_override = req.model_override
        model_source = req.model_source  # Phase 111.10: Multi-provider routing
        system_prompt = req.system_prompt
        temperature = req.temperature
        max_tokens = req.max_tokens
        node_id = req.node_id
        node_path = req.node_path
        file_path = req.file_path

        # Build user_data for orchestrator
        user_data = None
        if node_id or node_path or file_path or model_source:
            user_data = {
                "node_id": node_id,
                "node_path": node_path or file_path,
                "file_path": file_path or node_path,
                "model_source": model_source,  # Phase 111.10
            }

        # Validate
        if not user_message:
            raise HTTPException(status_code=400, detail="Message is required")

        if len(user_message) > 10000:
            raise HTTPException(
                status_code=400, detail="Message too long (max 10000 chars)"
            )

        print(f"\n{'=' * 70}")
        print(f"  [Chat] REQUEST: {conversation_id}")
        print(f"  [Chat] Message: {user_message[:100]}...")
        if user_data:
            print(f"  [Chat] Node: {user_data.get('node_path', 'unknown')}")
        print(f"{'=' * 70}")

        # Get managers
        memory = get_memory_manager() if get_memory_manager else None
        orchestrator = get_orchestrator() if get_orchestrator else None
        eval_agent = EvalAgent(memory_manager=memory) if memory else None

        # ============ UNIFIED MODEL ROUTING ============
        if get_model_for_task:
            selected_model = model_override or get_model_for_task("default", "cheap")
        else:
            selected_model = model_override or "deepseek/deepseek-chat"
        provider_info = {}

        # Check if model is banned
        if is_model_banned and is_model_banned(selected_model):
            print(f"  [Chat] Model {selected_model} is BANNED! Using deepseek instead.")
            selected_model = (
                get_model_for_task("default", "cheap")
                if get_model_for_task
                else "deepseek/deepseek-chat"
            )

        if MODEL_ROUTER_V2_AVAILABLE and model_router:
            try:
                complexity = "MEDIUM" if len(user_message.split()) > 20 else "LOW"
                routed_model, metadata = model_router.select_model("chat", complexity)
                if routed_model and (
                    not is_model_banned or not is_model_banned(routed_model)
                ):
                    selected_model = routed_model
                    provider_info = metadata or {}
                elif routed_model and is_model_banned and is_model_banned(routed_model):
                    print(
                        f"  [Chat] Router suggested banned model {routed_model}, using cheap default"
                    )
                print(f"  [Chat] Model Router v2 selected: {selected_model}")
            except Exception as e:
                print(f"  [Chat] Model Router error (using fallback): {e}")

        # Prepare context
        context = {
            "conversation_id": conversation_id,
            "user_message": user_message,
            "model": selected_model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "system_prompt": system_prompt or "You are a helpful AI assistant.",
            "timestamp": time.time(),
        }

        # ============ HOSTESS ROUTING ============
        hostess_decision = None
        hostess_start = time.time()

        if HOSTESS_AVAILABLE and get_hostess:
            try:
                hostess = get_hostess()
                hostess_decision = hostess.process(
                    user_message,
                    context={
                        "node_path": node_path,
                        "conversation_id": conversation_id,
                    },
                )
                hostess_time_ms = (time.time() - hostess_start) * 1000
                print(
                    f"  [Hostess] Decision: {hostess_decision['action']} (confidence: {hostess_decision['confidence']:.2f}, {hostess_time_ms:.0f}ms)"
                )

                # Handle quick_answer - respond immediately
                if hostess_decision["action"] == "quick_answer":
                    print(f"  [Hostess] Quick answer - bypassing orchestrator")
                    return {
                        "conversation_id": conversation_id,
                        "response": hostess_decision.get("result", ""),
                        "model": "hostess-qwen",
                        "provider": "ollama-local",
                        "processing_time_ms": round(hostess_time_ms, 2),
                        "eval_score": None,
                        "eval_feedback": None,
                        "metrics": {
                            "input_tokens": len(user_message.split()),
                            "output_tokens": len(
                                hostess_decision.get("result", "").split()
                            ),
                            "agent_scores": {
                                "hostess": hostess_decision.get("confidence", 0.9)
                            },
                        },
                        "agent": "Hostess",
                        "action": "quick_answer",
                        "timestamp": time.time(),
                    }

                # Handle clarify
                elif hostess_decision["action"] == "clarify":
                    print(f"  [Hostess] Clarification needed")
                    options_text = ""
                    if hostess_decision.get("options"):
                        options_text = "\n\nOptions:\n" + "\n".join(
                            [f"- {opt}" for opt in hostess_decision["options"]]
                        )

                    return {
                        "conversation_id": conversation_id,
                        "response": hostess_decision.get("result", "") + options_text,
                        "model": "hostess-qwen",
                        "provider": "ollama-local",
                        "processing_time_ms": round(hostess_time_ms, 2),
                        "needs_clarification": True,
                        "options": hostess_decision.get("options", []),
                        "agent": "Hostess",
                        "action": "clarify",
                        "timestamp": time.time(),
                    }

                # Handle search
                elif hostess_decision["action"] == "search":
                    query = hostess_decision.get("query", user_message)
                    print(f"  [Hostess] Search request: {query[:50]}...")

                    search_results = []
                    try:
                        if memory:
                            search_results = memory.semantic_search(query, limit=50)
                    except Exception as se:
                        print(f"  [Hostess] Search error: {se}")

                    if search_results:
                        result_text = f"Found {len(search_results)} results:\n\n"
                        for i, r in enumerate(search_results[:3], 1):
                            result_text += (
                                f"{i}. {r.get('title', r.get('path', 'Unknown'))}\n"
                            )
                            result_text += f"   {r.get('snippet', r.get('content', '')[:100])}...\n\n"
                    else:
                        result_text = f"No results found for: {query}"

                    return {
                        "conversation_id": conversation_id,
                        "response": result_text,
                        "model": "hostess-qwen",
                        "provider": "ollama-local",
                        "processing_time_ms": round(
                            (time.time() - hostess_start) * 1000, 2
                        ),
                        "agent": "Hostess",
                        "action": "search",
                        "search_results": search_results[:5] if search_results else [],
                        "timestamp": time.time(),
                    }

                # Handle show_file
                elif hostess_decision["action"] == "show_file":
                    file_to_show = hostess_decision.get("file_path", node_path)
                    print(f"  [Hostess] Show file: {file_to_show}")

                    file_content = ""
                    try:
                        if file_to_show and os.path.exists(file_to_show):
                            with open(file_to_show, "r", encoding="utf-8") as f:
                                file_content = f.read(10000)
                    except Exception as fe:
                        file_content = f"Error reading file: {fe}"

                    return {
                        "conversation_id": conversation_id,
                        "response": f"```\n{file_content}\n```"
                        if file_content
                        else f"File not found: {file_to_show}",
                        "model": "hostess-qwen",
                        "provider": "ollama-local",
                        "processing_time_ms": round(
                            (time.time() - hostess_start) * 1000, 2
                        ),
                        "agent": "Hostess",
                        "action": "show_file",
                        "file_path": file_to_show,
                        "timestamp": time.time(),
                    }

                # agent_call and chain_call continue to orchestrator
                elif hostess_decision["action"] == "agent_call":
                    print(
                        f"  [Hostess] Single agent: {hostess_decision.get('agent', 'Dev')} - continuing to orchestrator"
                    )

                elif hostess_decision["action"] == "chain_call":
                    print(
                        f"  [Hostess] Full chain requested - continuing to orchestrator"
                    )

            except Exception as he:
                print(f"  [Hostess] Error: {he}, continuing with orchestrator")
                hostess_decision = None

        # ============ PARALLEL AGENT PROCESSING ============
        agent_response = None
        processing_time = 0
        agent_scores = {}

        if ELISYA_ENABLED and PARALLEL_MODE and orchestrator:
            try:
                start_time = time.time()

                # Execute through orchestrator with parallel agents
                workflow_id = conversation_id
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: asyncio.run(
                        orchestrator.execute_full_workflow_streaming(
                            user_message, workflow_id, user_data=user_data
                        )
                    ),
                )

                processing_time = time.time() - start_time
                agent_response = result.get("dev_result", {}).get(
                    "content", ""
                ) or result.get("pm_result", {}).get("content", "")
                agent_scores = {
                    "pm": result.get("pm_score", 0),
                    "dev": result.get("dev_score", 0),
                    "qa": result.get("qa_score", 0),
                    "eval": result.get("eval_score", 0),
                }

                print(
                    f"  [Chat] Parallel orchestrator processed in {processing_time:.2f}s"
                )

            except Exception as e:
                print(f"  [Chat] Parallel orchestrator error: {e}")
                agent_response = None

        # Fallback: Direct API call via API Gateway or Ollama
        if not agent_response:
            start_time = time.time()

            try:
                # REMOVED: API Gateway v2 (Phase 95) - replaced by direct_api_calls.py
                # if API_GATEWAY_AVAILABLE and api_gateway:
                #     try:
                #         print(f"  [Chat] Calling API Gateway v2...")
                #         full_prompt = (
                #             f"{context['system_prompt']}\n\nUser: {user_message}"
                #         )
                #         api_result = api_gateway.call_model(
                #             task_type="chat", prompt=full_prompt, complexity="MEDIUM"
                #         )
                #         if api_result.success:
                #             agent_response = api_result.response
                #             print(
                #                 f"  [Chat] API Gateway v2 response received ({api_result.model})"
                #             )
                #         else:
                #             print(f"  [Chat] API Gateway v2 failed: {api_result.error}")
                #             agent_response = None
                #     except Exception as api_err:
                #         print(f"  [Chat] API Gateway v2 error: {api_err}")
                #         agent_response = None

                # Fallback to Ollama (now primary fallback)
                if not agent_response:
                    try:
                        print(f"  [Chat] Calling Ollama fallback...")
                        import ollama

                        ollama_response = ollama.chat(
                            model="qwen2:7b",
                            messages=[
                                {"role": "system", "content": context["system_prompt"]},
                                {"role": "user", "content": user_message},
                            ],
                            stream=False,
                        )
                        agent_response = ollama_response.get("message", {}).get(
                            "content", ""
                        )
                        print(f"  [Chat] Ollama response received")
                    except Exception as ollama_err:
                        print(f"  [Chat] Ollama error: {ollama_err}")
                        agent_response = f"[Fallback] Unable to process (tried API Gateway and Ollama)"

                processing_time = time.time() - start_time

            except Exception as e:
                print(f"  [Chat] All API fallbacks failed: {e}")
                agent_response = f"[Error] Could not process: {str(e)[:100]}"
                processing_time = time.time() - start_time

        # ============ MEMORY PERSISTENCE (TRIPLE WRITE) ============
        conversation_entry = {
            "conversation_id": conversation_id,
            "role": "user",
            "content": user_message,
            "model": selected_model,
            "timestamp": context["timestamp"],
            "metadata": {
                "source": "api_chat",
                "processing_time": processing_time,
                "provider": provider_info.get("provider", "unknown"),
            },
        }

        response_entry = {
            "conversation_id": conversation_id,
            "role": "assistant",
            "content": agent_response or "(No response)",
            "model": selected_model,
            "timestamp": time.time(),
            "metadata": {
                "source": "api_chat",
                "processing_time": processing_time,
                "agent_scores": agent_scores,
            },
        }

        # Save to memory (Weaviate)
        if memory:
            try:
                memory.triple_write({**conversation_entry, "type": "conversation"})
                memory.triple_write({**response_entry, "type": "conversation"})
                print(f"  [Chat] Saved to Weaviate + ChangeLog (triple_write)")
            except Exception as e:
                print(f"  [Chat] Weaviate save error: {e}")

        # Save to Qdrant if available
        if QDRANT_AUTO_RETRY_AVAILABLE and qdrant_manager:
            try:
                qdrant_manager.add_conversation_vector(
                    conversation_id=conversation_id,
                    user_message=user_message,
                    response=agent_response or "",
                    model=selected_model,
                    agent_scores=agent_scores,
                )
                print(f"  [Chat] Saved to Qdrant")
            except Exception as e:
                print(f"  [Chat] Qdrant save error: {e}")

        # ============ EVALAGENT SCORING ============
        eval_score = None
        eval_feedback = {}

        if eval_agent:
            try:
                eval_result = eval_agent.evaluate(
                    original_task=user_message,
                    agent_output=agent_response or "",
                    agent_name="chat",
                    complexity="MEDIUM",
                )
                eval_score = eval_result.get("score", 0)
                eval_feedback = eval_result.get(
                    "feedback", eval_result.get("reasoning", "")
                )
                print(f"  [Chat] EvalAgent score: {eval_score:.2f}/10")
            except Exception as e:
                print(f"  [Chat] EvalAgent error: {e}")

        # ============ RESPONSE ASSEMBLY ============
        api_response = {
            "conversation_id": conversation_id,
            "response": agent_response or "(Processing error)",
            "model": selected_model,
            "provider": provider_info.get("provider", "unknown"),
            "processing_time_ms": round(processing_time * 1000, 2),
            "eval_score": round(eval_score, 2) if eval_score is not None else None,
            "eval_feedback": eval_feedback,
            "metrics": {
                "input_tokens": len(user_message.split()),
                "output_tokens": len((agent_response or "").split()),
                "agent_scores": agent_scores,
            },
            "timestamp": time.time(),
        }

        print(f"\n  [Chat] RESPONSE: {conversation_id}")
        print(f"     Model: {selected_model}")
        print(f"     Time: {processing_time * 1000:.1f}ms")
        eval_score_display = f"{eval_score:.2f}" if eval_score is not None else "N/A"
        print(f"     Score: {eval_score_display}")
        print(f"{'=' * 70}\n")

        return api_response

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        error_msg = str(e)
        print(f"\n  [Chat] ERROR: {error_msg}")
        print(traceback.format_exc())
        print(f"{'=' * 70}\n")
        raise HTTPException(status_code=500, detail=error_msg)
