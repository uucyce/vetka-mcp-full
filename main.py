"""
VETKA FastAPI Application - PRODUCTION

@file main.py
@status PRODUCTION
@phase Phase 39.8
@lastAudit 2026-01-05

VETKA is now 100% on FastAPI!
Flask migration complete.

Stats:
- 13 REST routers (59 endpoints)
- 7 Socket.IO handler modules (18 events)
- Native async everywhere
- Auto-docs at /docs

Port: 5001 (default)
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
import socketio
import os
import sys
import logging
from typing import Dict
from src.memory.hostess_memory import HostessMemory

# MARKER_118.3: Configure logging — suppress noisy loggers EARLY
# (Previously: basicConfig(INFO) ran before setup_logging → httpx flood)
logging.basicConfig(
    level=logging.WARNING, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
# Set our own logger to INFO (we want to see our messages)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Suppress noisy third-party loggers immediately (before any imports trigger them)
for _noisy in ['httpx', 'httpcore', 'urllib3', 'qdrant_client', 'weaviate', 'ollama', 'grpc']:
    logging.getLogger(_noisy).setLevel(logging.WARNING)

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Phase 56.5: Hostess memory instances per user
hostess_memories: Dict[str, HostessMemory] = {}


def get_hostess_memory(user_id: str) -> HostessMemory:
    """Get or create HostessMemory instance for user."""
    if user_id not in hostess_memories:
        hostess_memories[user_id] = HostessMemory(user_id=user_id)
    return hostess_memories[user_id]


# ============================================================
# LIFESPAN (startup/shutdown)
# ============================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize components on startup, cleanup on shutdown."""
    import asyncio
    import logging

    logger = logging.getLogger(__name__)

    print("\n" + "=" * 60)
    print("  VETKA FASTAPI STARTING (Phase 39.8 - PRODUCTION)")
    print("=" * 60)

    # FIX_95.9: Debug output for watchdog polling mode
    use_polling = os.environ.get('USE_POLLING_OBSERVER', 'NOT_SET')
    print(f"  [DEBUG] USE_POLLING_OBSERVER env = {use_polling}")

    # Parse debug mode from environment
    debug_mode = os.getenv("VETKA_DEBUG", "false").lower() == "true"

    # Initialize all components using existing initialization module
    from src.initialization import initialize_all_components

    # === PHASE 55.2: PERIODIC CLEANUP TASK ===
    async def periodic_approval_cleanup():
        """Run approval cleanup every hour."""
        from src.services.approval_service import get_approval_service

        while True:
            try:
                await asyncio.sleep(3600)  # Wait 1 hour
                service = get_approval_service()
                service.cleanup_old(max_age_hours=24)
            except asyncio.CancelledError:
                logger.info("[Cleanup] Task cancelled")
                break
            except Exception as e:
                logger.error(f"[Cleanup] Failed: {e}")
                await asyncio.sleep(3600)  # Continue after error

    # === MARKER_131.C20A: Heartbeat daemon (60s loop) ===
    # MARKER_133.C33E: Load config from disk
    async def heartbeat_daemon():
        """Run heartbeat tick every N seconds to process @dragon/@doctor tasks."""
        from src.orchestration.mycelium_heartbeat import heartbeat_tick
        from src.api.routes.debug_routes import _load_heartbeat_config

        MCP_DEV_GROUP_ID = "609c0d9a-b5bc-426b-b134-d693023bdac8"

        # MARKER_133.C33E: Load persisted config on startup
        config = _load_heartbeat_config()
        os.environ["VETKA_HEARTBEAT_ENABLED"] = "true" if config.get("enabled", False) else "false"
        os.environ["VETKA_HEARTBEAT_INTERVAL"] = str(config.get("interval", 60))

        # Wait for server to be fully ready
        await asyncio.sleep(10)
        logger.info(f"[Heartbeat] Daemon started (enabled={config.get('enabled')}, interval={config.get('interval')}s)")

        while True:
            try:
                # MARKER_133.C33E: Re-read config each tick (allows runtime changes)
                config = _load_heartbeat_config()
                interval = config.get("interval", 60)
                enabled = config.get("enabled", False)

                await asyncio.sleep(interval)

                if not enabled:
                    logger.debug("[Heartbeat] Daemon disabled via config")
                    continue

                # Run heartbeat tick
                result = await heartbeat_tick(group_id=MCP_DEV_GROUP_ID, dry_run=False)
                tasks_found = len(result.get("results", []))
                if tasks_found > 0:
                    logger.info(f"[Heartbeat] Tick completed: {tasks_found} tasks processed")
                else:
                    logger.debug("[Heartbeat] Tick completed: no tasks")

            except asyncio.CancelledError:
                logger.info("[Heartbeat] Daemon cancelled")
                break
            except Exception as e:
                logger.error(f"[Heartbeat] Daemon error: {e}")
                await asyncio.sleep(HEARTBEAT_INTERVAL)  # Continue after error

    cleanup_task = None
    heartbeat_task = None  # MARKER_131.C20A

    # Create a mock Flask-like app object for compatibility
    # (components_init expects Flask app for app.config access)
    class MockFlaskApp:
        def __init__(self):
            self.config = {}

    mock_app = MockFlaskApp()

    # Initialize components (pass None for socketio - will set up async version)
    components = initialize_all_components(mock_app, None, debug=debug_mode)

    # Store in app.state (FastAPI's equivalent of Flask's app.config)
    app.state.components = components
    app.state.flask_config = mock_app.config  # For compatibility

    # Make individual components accessible
    # Phase 44.5: Use lazy getters for orchestrator/memory_manager (they return None from dict)
    from src.initialization.components_init import (
        get_orchestrator,
        get_memory_manager,
        get_eval_agent,
    )

    try:
        app.state.memory_manager = get_memory_manager()
        if app.state.memory_manager is None:
            logger.error("Memory manager initialization failed")
        else:
            logger.info("Memory manager initialized successfully")
    except Exception as e:
        logger.error(f"Memory manager initialization error: {e}")
        app.state.memory_manager = None
    app.state.model_router = components.get("model_router")
    app.state.metrics_engine = components.get("metrics_engine")
    app.state.orchestrator = get_orchestrator()  # Lazy init
    # api_gateway REMOVED: Phase 103 cleanup (was deprecated Phase 95)
    app.state.qdrant_manager = components.get("qdrant_manager")
    app.state.feedback_loop = components.get("feedback_loop")
    app.state.smart_learner = components.get("smart_learner")
    app.state.hope_enhancer = components.get("hope_enhancer")
    app.state.embeddings_projector = components.get("embeddings_projector")
    app.state.student_level_system = components.get("student_level_system")
    app.state.promotion_engine = components.get("promotion_engine")
    app.state.simpo_loop = components.get("simpo_loop")
    app.state.learner_agent = components.get("learner_agent")
    app.state.eval_agent = get_eval_agent()  # Phase 44.5: Lazy init
    app.state.executor = components.get("executor")

    # Phase 44: Initialize HostessContextBuilder with dependencies
    try:
        from src.orchestration.hostess_context_builder import (
            get_hostess_context_builder,
        )

        app.state.hostess_context_builder = get_hostess_context_builder(
            memory_manager=app.state.memory_manager,
            elisya_middleware=components.get("elisya_middleware"),
        )
        print("  [Phase 44] HostessContextBuilder initialized")
    except Exception as e:
        print(f"  [Phase 44] HostessContextBuilder init failed: {e}")
        app.state.hostess_context_builder = None

    # Store availability flags
    app.state.METRICS_AVAILABLE = components.get("METRICS_AVAILABLE", False)
    app.state.MODEL_ROUTER_V2_AVAILABLE = components.get(
        "MODEL_ROUTER_V2_AVAILABLE", False
    )
    app.state.API_GATEWAY_AVAILABLE = components.get("API_GATEWAY_AVAILABLE", False)
    app.state.QDRANT_AUTO_RETRY_AVAILABLE = components.get(
        "QDRANT_AUTO_RETRY_AVAILABLE", False
    )
    app.state.FEEDBACK_LOOP_V2_AVAILABLE = components.get(
        "FEEDBACK_LOOP_V2_AVAILABLE", False
    )
    app.state.SMART_LEARNER_AVAILABLE = components.get("SMART_LEARNER_AVAILABLE", False)
    app.state.HOPE_ENHANCER_AVAILABLE = components.get("HOPE_ENHANCER_AVAILABLE", False)
    app.state.EMBEDDINGS_PROJECTOR_AVAILABLE = components.get(
        "EMBEDDINGS_PROJECTOR_AVAILABLE", False
    )
    app.state.STUDENT_SYSTEM_AVAILABLE = components.get(
        "STUDENT_SYSTEM_AVAILABLE", False
    )
    app.state.LEARNER_AVAILABLE = components.get("LEARNER_AVAILABLE", False)
    app.state.ELISYA_ENABLED = components.get("ELISYA_ENABLED", False)
    app.state.PARALLEL_MODE = components.get("PARALLEL_MODE", False)

    # Start periodic cleanup task
    cleanup_task = asyncio.create_task(periodic_approval_cleanup())
    logger.info("[Startup] Periodic cleanup task started")

    # MARKER_131.C20B: Auto-resume orphaned tasks on server restart
    try:
        from src.orchestration.task_board import TaskBoard
        board = TaskBoard()
        queue = board.get_queue()
        orphaned = [t for t in queue if t.get("status") in ("running", "claimed")]
        if orphaned:
            for task in orphaned:
                task_id = task.get("id")
                # Reset to pending so heartbeat can re-dispatch
                board.update_task(task_id, status="pending", result_summary="Server restart - task reset")
                logger.info(f"[Startup] Reset orphaned task {task_id} from {task.get('status')} to pending")
            logger.info(f"[Startup] Reset {len(orphaned)} orphaned tasks")
    except Exception as e:
        logger.warning(f"[Startup] Auto-resume check failed: {e}")

    # MARKER_131.C20A: Start heartbeat daemon (60s loop for @dragon/@doctor tasks)
    heartbeat_task = asyncio.create_task(heartbeat_daemon())
    logger.info("[Startup] Heartbeat daemon started (60s interval)")

    # === PHASE 56: Start model health checks ===
    # === PHASE 60.4: Auto-discover Ollama models ===
    # === PHASE 60.5: Auto-discover Voice models ===
    try:
        from src.services.model_registry import get_model_registry

        registry = get_model_registry()

        # Phase 60.4: Discover all local Ollama models
        ollama_count = await registry.discover_ollama_models()

        # Phase 60.5: Discover voice models from OpenRouter
        voice_count = await registry.discover_voice_models()

        total_models = len(registry.get_all())
        logger.info(
            f"[Startup] Discovered {ollama_count} Ollama, {voice_count} voice models (total: {total_models})"
        )

        await registry.start_health_checks(interval=300)  # Every 5 min
        logger.info("[Startup] Model registry health checks started")
        app.state.model_registry = registry
    except Exception as e:
        logger.error(f"[Startup] Model registry init failed: {e}")
        app.state.model_registry = None

    # === PHASE 115 BUG-4: Initialize pinned files service ===
    try:
        from src.api.routes.cam_routes import initialize_pinned_files_service
        await initialize_pinned_files_service()
        logger.info("[Startup] Pinned files service initialized")
    except Exception as e:
        logger.error(f"[Startup] Pinned files service init failed: {e}")

    # === PHASE 56: Initialize group chat manager ===
    try:
        from src.services.group_chat_manager import get_group_chat_manager

        manager = get_group_chat_manager(socketio=sio)
        logger.info("[Startup] Group chat manager initialized")
        app.state.group_chat_manager = manager
        # Load saved groups from JSON
        await manager.load_from_json()
        # ✅ PHASE 56.4: Start periodic cleanup task
        await manager.start_cleanup()
    except Exception as e:
        logger.error(f"[Startup] Group chat manager init failed: {e}")
        app.state.group_chat_manager = None

    # === Phase 111.18: Initialize Qdrant batch manager ===
    try:
        from src.memory.qdrant_batch_manager import init_batch_manager
        batch_manager = await init_batch_manager()
        app.state.qdrant_batch_manager = batch_manager
        logger.info("[Startup] Qdrant batch manager initialized (30s flush interval)")
    except Exception as e:
        logger.error(f"[Startup] Qdrant batch manager init failed: {e}")
        app.state.qdrant_batch_manager = None

    # === PHASE 87: Initialize file watcher with qdrant_client ===
    try:
        from src.scanners.file_watcher import get_watcher

        qdrant_manager = app.state.qdrant_manager
        qdrant_client = None

        # MARKER_90.5.0_START: Wait for QdrantAutoRetry background connection
        # QdrantAutoRetry initializes connection in background thread.
        # We must wait for it to complete before accessing .client attribute.
        if qdrant_manager:
            import time

            max_wait = 5.0  # seconds
            wait_interval = 0.1  # check every 100ms
            waited = 0.0

            logger.info("[Startup] Waiting for Qdrant background connection...")
            while waited < max_wait and not qdrant_manager.is_ready():
                await asyncio.sleep(wait_interval)
                waited += wait_interval

            if qdrant_manager.is_ready():
                qdrant_client = qdrant_manager.client
                logger.info(f"[Startup] Qdrant connection ready after {waited:.1f}s")
            else:
                logger.warning(
                    f"[Startup] Qdrant not ready after {max_wait}s (background thread still connecting)"
                )
                # Don't fail startup - scanner will work once connection completes
        # MARKER_90.5.0_END

        watcher = get_watcher(socketio=sio, qdrant_client=qdrant_client)
        logger.info(
            f"[Startup] File watcher initialized (qdrant_client={'present' if qdrant_client else 'None'})"
        )
        app.state.file_watcher = watcher
    except Exception as e:
        logger.error(f"[Startup] File watcher init failed: {e}")
        app.state.file_watcher = None

    # === PHASE 104: Start TTS server ===
    try:
        from src.voice.tts_server_manager import start_tts_server
        app.state.tts_process = start_tts_server(port=5003, wait_ready=False)
    except Exception as e:
        logger.error(f"[Startup] TTS server start failed: {e}")
        app.state.tts_process = None

    # === MARKER_106e_2: Register async Socket.IO handlers ===
    try:
        from src.api.handlers import register_all_handlers
        await register_all_handlers(sio, app)
        logger.info("[Startup] Socket.IO handlers registered (including MCP)")
    except Exception as e:
        logger.error(f"[Startup] Socket.IO handler registration failed: {e}")

    print("  VETKA FASTAPI READY")
    print("=" * 60 + "\n")

    yield  # App is running

    # Cleanup on shutdown
    print("\n  VETKA FASTAPI SHUTDOWN")

    # Cancel cleanup task
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        logger.info("[Shutdown] Cleanup task cancelled")

    # MARKER_131.C20A: Cancel heartbeat daemon
    if heartbeat_task:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        logger.info("[Shutdown] Heartbeat daemon cancelled")

    # === PHASE 56: Stop model health checks and group chat cleanup ===
    if hasattr(app.state, "model_registry") and app.state.model_registry:
        await app.state.model_registry.stop_health_checks()
        logger.info("[Shutdown] Model registry health checks stopped")

    # ✅ PHASE 56.4: Stop group chat cleanup task
    if hasattr(app.state, "group_chat_manager") and app.state.group_chat_manager:
        await app.state.group_chat_manager.stop_cleanup()
        logger.info("[Shutdown] Group chat cleanup task stopped")

    # Phase 111.18: Stop Qdrant batch manager (flush remaining)
    if hasattr(app.state, "qdrant_batch_manager") and app.state.qdrant_batch_manager:
        await app.state.qdrant_batch_manager.stop()
        logger.info("[Shutdown] Qdrant batch manager stopped (flushed remaining)")

    # === PHASE 104: Stop TTS server ===
    try:
        from src.voice.tts_server_manager import stop_tts_server
        stop_tts_server()
    except Exception as e:
        logger.warning(f"[Shutdown] TTS server stop failed: {e}")

    executor = app.state.executor
    if executor:
        print("  Shutting down executor...")
        executor.shutdown(wait=True)
        print("  Executor shutdown complete")


# ============================================================
# APP CREATION
# ============================================================

app = FastAPI(
    title="VETKA API",
    description="Visual Enhanced Tree Knowledge Architecture - FastAPI Version",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MARKER: PHASE43_REQUEST_ID_MIDDLEWARE
# Request ID middleware for tracing
from src.api.middleware import RequestIDMiddleware

app.add_middleware(RequestIDMiddleware)


# ============================================================
# SOCKET.IO (ASGI)
# ============================================================

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    ping_interval=25,
    ping_timeout=60,
    logger=False,
    engineio_logger=False,
)

# Wrap FastAPI with Socket.IO
socket_app = socketio.ASGIApp(sio, app)

# Phase 54.4: Store socketio in app.state for routes to emit events
app.state.socketio = sio


# ============================================================
# SOCKET.IO HANDLERS (Phase 39.7)
# ============================================================

# Note: Handler registration moved to lifespan() to support async handlers
# Register all migrated Socket.IO handlers is now called in lifespan (MARKER_106e_2)


# === PHASE 55: APPROVAL SOCKET HANDLERS ===


@sio.on("approve_artifact")
async def handle_approve(sid, data):
    """Handle artifact approval from user."""
    from uuid import UUID
    from datetime import datetime
    from src.services.approval_service import get_approval_service
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Validate input
        if not data or "request_id" not in data:
            await sio.emit("approval_error", {"error": "Missing request_id"}, to=sid)
            return

        request_id = data.get("request_id")
        reason = data.get("reason", "User approved via UI")

        # Validate UUID format
        try:
            UUID(request_id)
        except (ValueError, TypeError):
            await sio.emit(
                "approval_error", {"error": f"Invalid UUID: {request_id}"}, to=sid
            )
            return

        # Process approval
        service = get_approval_service()
        if service.approve(request_id, reason):
            # SECURITY: Send only to requester (prevents info leak in multi-user)
            # TODO Phase 56: Implement workflow rooms for team collaboration
            await sio.emit(
                "approval_decided",
                {
                    "request_id": request_id,
                    "status": "approved",
                    "reason": reason,
                    "decided_by": sid,  # Track who approved
                    "timestamp": datetime.now().isoformat(),
                },
                to=sid,
            )

            logger.info(f"[Socket] Approved by {sid}: {request_id}")
        else:
            # Error only to requester
            await sio.emit(
                "approval_error",
                {
                    "request_id": request_id,
                    "error": "Request not found or already decided",
                },
                to=sid,
            )

    except Exception as e:
        logger.error(f"[Socket] Approve failed: {e}")
        await sio.emit("approval_error", {"error": str(e)}, to=sid)


@sio.on("reject_artifact")
async def handle_reject(sid, data):
    """Handle artifact rejection from user."""
    from uuid import UUID
    from datetime import datetime
    from src.services.approval_service import get_approval_service
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Validate input
        if not data or "request_id" not in data:
            await sio.emit("approval_error", {"error": "Missing request_id"}, to=sid)
            return

        request_id = data.get("request_id")
        reason = data.get("reason", "User rejected via UI")

        # Validate UUID format
        try:
            UUID(request_id)
        except (ValueError, TypeError):
            await sio.emit(
                "approval_error", {"error": f"Invalid UUID: {request_id}"}, to=sid
            )
            return

        # Process rejection
        service = get_approval_service()
        if service.reject(request_id, reason):
            # SECURITY: Send only to requester (prevents info leak in multi-user)
            # TODO Phase 56: Implement workflow rooms for team collaboration
            await sio.emit(
                "approval_decided",
                {
                    "request_id": request_id,
                    "status": "rejected",
                    "reason": reason,
                    "decided_by": sid,
                    "timestamp": datetime.now().isoformat(),
                },
                to=sid,
            )

            logger.info(f"[Socket] Rejected by {sid}: {request_id}")
        else:
            await sio.emit(
                "approval_error",
                {
                    "request_id": request_id,
                    "error": "Request not found or already decided",
                },
                to=sid,
            )

    except Exception as e:
        logger.error(f"[Socket] Reject failed: {e}")
        await sio.emit("approval_error", {"error": str(e)}, to=sid)


# === PHASE 56 -> 57.6: GROUP SOCKET HANDLERS MOVED ===
# All group handlers (join_group, leave_group, group_message, group_typing)
# are now in src/api/handlers/group_message_handler.py
# which uses orchestrator.call_agent() for LLM calls with full Elisya integration
# Room format: group_{group_id} (underscore, not colon)


# group_typing handler also moved to group_message_handler.py


# === PHASE 56.5: CHAT-AS-TREE SOCKET HANDLERS ===


@sio.on("create_chat_node")
async def handle_create_chat_node(sid, data):
    """Create a chat node in the tree from a source file."""
    # 🔐 TODO Phase 57: Add authentication + rate limiting
    # user = await get_session_user(sid)
    # if not user:
    #     await sio.emit('error', {'msg': 'Unauthorized'}, to=sid)
    #     return
    # if not await check_rate_limit(user.id, 'create_chat', max_per_min=10):
    #     await sio.emit('error', {'msg': 'Rate limit exceeded'}, to=sid)
    #     return

    # ✅ PHASE 56.5: Input validation
    if not isinstance(data, dict):
        logger.warning(f"[Socket] Invalid chat_node data format from {sid}")
        await sio.emit("error", {"msg": "Invalid data format"}, to=sid)
        return

    chat_id = (data.get("chatId") or "").strip()
    parent_id = (data.get("parentId") or "").strip()
    name = (data.get("name") or "").strip()
    participants = data.get("participants") or []

    # ✅ Validate required fields
    if not chat_id or not parent_id or not name:
        logger.warning(f"[Socket] Missing required fields for chat_node from {sid}")
        await sio.emit("error", {"msg": "Missing required fields"}, to=sid)
        return

    logger.info(
        f"[Socket] Chat node created: {chat_id} ({name}) with {len(participants)} participants"
    )

    # 📡 Emit back to sender only (frontend already added to local store)
    # This confirms the backend received and processed the request
    # TODO Phase 57: Implement user rooms for multi-user broadcast
    await sio.emit(
        "chat_node_created",
        {
            "chatId": chat_id,
            "parentId": parent_id,
            "name": name,
            "participants": participants,
        },
        to=sid,
    )


@sio.on("get_hostess_memory")
async def handle_get_hostess_memory(sid, data):
    """Get hostess memory tree visualization data."""
    logger.info(f"[Socket] Hostess memory requested by {sid}")

    try:
        user_id = (data or {}).get("user_id", sid)
        memory = get_hostess_memory(user_id)
        tree_data = memory.get_visual_tree_data()
        await sio.emit("hostess_memory_tree", tree_data, to=sid)
    except Exception as e:
        logger.error(f"[Socket] get_hostess_memory error: {e}")
        await sio.emit("hostess_memory_tree", {"nodes": []}, to=sid)


# === PHASE 56.2: DISCONNECT HANDLER ===


@sio.event
async def disconnect(sid):
    """Clean up session on disconnect."""
    logger.info(f"[Socket] Client {sid} disconnected")

    try:
        # Get user's active groups and leave them
        from src.services.group_chat_manager import get_group_chat_manager

        manager = get_group_chat_manager()

        # Get all groups and check which ones have this user
        all_groups = manager.get_all_groups()
        for group in all_groups:
            group_id = group.get("id")
            if group_id:
                try:
                    await sio.leave_room(sid, f"group_{group_id}")
                    logger.debug(f"[Socket] {sid} left group {group_id} on disconnect")
                except Exception as e:
                    logger.debug(f"[Socket] Failed to leave room: {e}")

    except Exception as e:
        logger.error(f"[Socket] Disconnect cleanup failed: {e}")


# ============================================================
# HEALTH CHECK ROUTES
# ============================================================


@app.get("/api/health")
async def health_check(request: Request):
    """Health check endpoint with component status."""
    components_status = {}

    # Check component availability from app.state
    if hasattr(request.app.state, "METRICS_AVAILABLE"):
        components_status = {
            "metrics_engine": request.app.state.METRICS_AVAILABLE,
            "model_router": request.app.state.MODEL_ROUTER_V2_AVAILABLE,
            # api_gateway REMOVED: Phase 103 cleanup
            "qdrant": request.app.state.QDRANT_AUTO_RETRY_AVAILABLE,
            "feedback_loop": request.app.state.FEEDBACK_LOOP_V2_AVAILABLE,
            "smart_learner": request.app.state.SMART_LEARNER_AVAILABLE,
            "hope_enhancer": request.app.state.HOPE_ENHANCER_AVAILABLE,
            "embeddings_projector": request.app.state.EMBEDDINGS_PROJECTOR_AVAILABLE,
            "student_system": request.app.state.STUDENT_SYSTEM_AVAILABLE,
            "learner": request.app.state.LEARNER_AVAILABLE,
            "elisya": request.app.state.ELISYA_ENABLED,
        }

    # MARKER_C21B: Enhanced health status
    import os
    heartbeat_status = {
        "running": heartbeat_task is not None and not heartbeat_task.done() if 'heartbeat_task' in dir() else False,
        "interval": int(os.getenv("VETKA_HEARTBEAT_INTERVAL", "60")),
        "enabled": os.getenv("VETKA_HEARTBEAT_ENABLED", "false").lower() == "true",
    }

    bmad_status = {
        "approval_mode": "mycelium",
        "l2_scout": "active",
        "auto_write": os.getenv("VETKA_AUTO_WRITE", "false").lower() == "true",
    }

    pipeline_safety = {
        "verify_before_write": True,  # MARKER_130.6
        "language_validation": True,  # MARKER_130.C19D
        "safe_directories": ["src/vetka_out", "data/vetka_staging", "data/artifacts"],
    }

    return {
        "status": "healthy",
        "version": "2.0.0",
        "framework": "FastAPI",
        "phase": "131",
        "components": components_status,
        "heartbeat_daemon": heartbeat_status,
        "bmad": bmad_status,
        "pipeline_safety": pipeline_safety,
    }


@app.get("/")
async def root():
    """Root endpoint - redirect to docs during migration."""
    return {
        "message": "VETKA API v2.0 - FastAPI",
        "docs": "/docs",
        "health": "/api/health",
        "migration_status": "Phase 39.8 - PRODUCTION (Flask migration complete)",
    }


@app.get("/3d")
async def redirect_3d():
    """Redirect to 3D view."""
    # TODO: Serve 3D frontend directly when mounted
    return {
        "message": "3D view available at http://localhost:3000 (frontend dev server)"
    }


# ============================================================
# STATIC FILES (for future use)
# ============================================================

# Mount static files when ready
# app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Mount artifact panel React app
app.mount(
    "/artifact-panel",
    StaticFiles(directory="app/artifact-panel/dist", html=True),
    name="artifact-panel",
)


# ============================================================
# ROUTES
# ============================================================

# Phase 39.7: Register ALL migrated routes
from src.api.routes import register_all_routers

register_all_routers(app)

# === PHASE 55: APPROVAL ROUTES ===
from src.api.routes.approval_routes import router as approval_router

app.include_router(approval_router)

# === PHASE 80.41: MCP CONSOLE ROUTES ===
from src.api.routes.mcp_console_routes import router as mcp_console_router

app.include_router(mcp_console_router)

# === PHASE 133: HEARTBEAT HEALTH & CONFIG PERSISTENCE ===
from src.api.routes.heartbeat_health import router as heartbeat_health_router
app.include_router(heartbeat_health_router)

# === PHASE 133: PIPELINE RUN HISTORY ===
from src.api.routes.pipeline_history import router as pipeline_history_router
app.include_router(pipeline_history_router)

# === PHASE 133: TASK TRACKER ===
from src.api.routes.task_tracker_routes import router as task_tracker_router
app.include_router(task_tracker_router)

# === PHASE 57: API KEYS MANAGEMENT ===
from fastapi import Request
from fastapi.responses import JSONResponse


@app.get("/api/keys")
async def get_api_keys():
    """Get all API keys (masked) and their status."""
    from src.orchestration.services.api_key_service import APIKeyService

    api_service = APIKeyService()
    keys_raw = api_service.list_keys()
    # Extract keys from nested structure
    keys_data = keys_raw.get("keys", {})

    # Check Ollama status
    ollama_running = False
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:11434/api/tags", timeout=2.0)
            ollama_running = resp.status_code == 200
    except:
        pass

    # Format providers for frontend
    providers = []

    # Helper to extract masked keys from key records
    def extract_keys(provider_data: list, provider_name: str) -> list:
        result = []
        for i, k in enumerate(provider_data):
            # k is a dict with masked, alias, active, available, cooldown_hours, etc.
            masked = k.get("masked", "") if isinstance(k, dict) else str(k)
            status = "active" if i == 0 and k.get("available", True) else "backup"
            if isinstance(k, dict) and k.get("cooldown_hours"):
                status = "rate_limited"
            result.append(
                {
                    "id": f"{provider_name}_{i}",
                    "provider": provider_name,
                    "key": masked,
                    "status": status,
                }
            )
        return result

    # OpenRouter keys
    or_keys = keys_data.get("openrouter", [])
    providers.append(
        {
            "provider": "OpenRouter",
            "keys": extract_keys(or_keys, "openrouter"),
            "isLocal": False,
        }
    )

    # Gemini keys
    gemini_keys = keys_data.get("gemini", [])
    providers.append(
        {
            "provider": "Gemini",
            "keys": extract_keys(gemini_keys, "gemini"),
            "isLocal": False,
        }
    )

    # NanoGPT keys
    nanogpt_keys = keys_data.get("nanogpt", [])
    providers.append(
        {
            "provider": "NanoGPT",
            "keys": extract_keys(nanogpt_keys, "nanogpt"),
            "isLocal": False,
        }
    )

    # Ollama (local)
    providers.append(
        {
            "provider": "Ollama",
            "keys": [],
            "isLocal": True,
            "status": "running" if ollama_running else "stopped",
        }
    )

    return {"providers": providers}


@app.post("/api/keys")
async def add_api_key(request: Request):
    """Add a new API key."""
    from src.orchestration.services.api_key_service import APIKeyService

    data = await request.json()
    provider = data.get("provider", "").lower()
    key = data.get("key", "")

    if not provider or not key:
        return JSONResponse({"error": "Missing provider or key"}, status_code=400)

    # Validate key format
    if provider == "openrouter" and not key.startswith("sk-or-"):
        return JSONResponse(
            {"error": "Invalid OpenRouter key format (should start with sk-or-)"},
            status_code=400,
        )

    if provider == "gemini" and not key.startswith("AIza"):
        return JSONResponse(
            {"error": "Invalid Gemini key format (should start with AIza)"},
            status_code=400,
        )

    api_service = APIKeyService()
    result = api_service.add_key(provider, key)

    if result.get("success"):
        return {
            "status": "added",
            "provider": provider,
            "masked_key": result.get("masked_key"),
        }
    else:
        return JSONResponse(
            {"error": result.get("error", "Failed to add key")}, status_code=400
        )


@app.delete("/api/keys/{provider}/{key_id}")
async def remove_api_key(provider: str, key_id: str):
    """Remove an API key."""
    from src.orchestration.services.api_key_service import APIKeyService

    api_service = APIKeyService()

    # Parse index from key_id (e.g., "openrouter_0" -> 0)
    try:
        index = int(key_id.split("_")[-1])
    except ValueError:
        return JSONResponse({"error": "Invalid key ID"}, status_code=400)

    result = api_service.remove_key(provider.lower(), index)

    if result.get("success"):
        return {"status": "removed"}
    else:
        return JSONResponse(
            {"error": result.get("error", "Failed to remove key")}, status_code=400
        )


# ============================================================
# Phase 57.1: API Key Auto-Detection Endpoints
# ============================================================


@app.post("/api/keys/detect")
async def detect_api_key_provider(request: Request):
    """
    Auto-detect API key provider from key format.
    Phase 57.1: Smart detection for 45+ providers.
    """
    from src.elisya.api_key_detector import detect_api_key, APIKeyDetector

    data = await request.json()
    key = data.get("key", "")

    if not key or len(key) < 10:
        return {"detected": None, "error": "Key too short"}

    detected = detect_api_key(key)

    return {
        "detected": detected,
        "supported_providers": APIKeyDetector.get_provider_count(),
    }


@app.get("/api/keys/providers")
async def get_supported_providers():
    """
    Get all supported API key providers grouped by category.
    Phase 57.1: Returns 45+ providers with metadata.
    """
    from src.elisya.api_key_detector import APIKeyDetector

    return {
        "providers": APIKeyDetector.get_all_providers(),
        "categories": APIKeyDetector.get_categories(),
        "total": APIKeyDetector.get_provider_count(),
    }


@app.post("/api/keys/add-smart")
async def add_api_key_smart(request: Request):
    """
    Add API key with auto-detection.
    Phase 57.1: Detects provider automatically, validates, and saves.
    """
    from src.elisya.api_key_detector import detect_api_key
    from src.orchestration.services.api_key_service import APIKeyService

    data = await request.json()
    key = data.get("key", "").strip()
    force_provider = data.get("provider")  # Optional: override detection

    if not key or len(key) < 10:
        return JSONResponse({"error": "Key too short"}, status_code=400)

    # Detect provider
    if force_provider:
        provider = force_provider.lower()
        confidence = 1.0
        display_name = force_provider.title()
    else:
        detected = detect_api_key(key)
        if not detected:
            return JSONResponse(
                {
                    "error": "Could not detect provider. Please specify manually.",
                    "detected": None,
                },
                status_code=400,
            )

        provider = detected["provider"]
        confidence = detected["confidence"]
        display_name = detected["display_name"]

        # Warn if low confidence
        if confidence < 0.5:
            return JSONResponse(
                {
                    "error": f"Low confidence ({confidence * 100:.0f}%). Please specify provider.",
                    "detected": detected,
                },
                status_code=400,
            )

    # Map detected provider to supported providers in KeyManager
    provider_mapping = {
        "openrouter": "openrouter",
        "gemini": "gemini",
        "nanogpt": "nanogpt",  # NanoGPT - собственный провайдер
        "anthropic": "openrouter",  # Route Claude keys through OpenRouter
        "openai": "openrouter",  # Route OpenAI keys through OpenRouter
        "openai_legacy": "openrouter",
        "groq": "openrouter",  # Groq also works via OpenRouter
        "mistral": "openrouter",
        "deepseek": "openrouter",
        # Add more mappings as needed
    }

    mapped_provider = provider_mapping.get(provider, "openrouter")

    # Save the key
    api_service = APIKeyService()
    result = api_service.add_key(mapped_provider, key)

    if result.get("success"):
        return {
            "status": "added",
            "detected_provider": display_name,
            "saved_as": mapped_provider,
            "confidence": confidence,
            "masked_key": result.get("masked_key"),
        }
    else:
        return JSONResponse(
            {
                "error": result.get("error", "Failed to add key"),
                "detected_provider": display_name,
            },
            status_code=400,
        )


# Phase 39.8 - MIGRATION COMPLETE!
# Flask is deprecated - VETKA is now 100% on FastAPI


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    import uvicorn

    # Port 5001 is production default (frontend configured for this)
    port = int(os.getenv("VETKA_PORT", 5001))
    host = os.getenv("VETKA_HOST", "0.0.0.0")

    print(f"\n  Starting VETKA FastAPI on {host}:{port}")
    print(f"  Docs: http://localhost:{port}/docs")
    print(f"  Health: http://localhost:{port}/api/health\n")

    uvicorn.run(
        "main:socket_app",  # socket_app includes both FastAPI and Socket.IO
        host=host,
        port=port,
        reload=True,
        log_level="info",
    )
