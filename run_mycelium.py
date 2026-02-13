#!/usr/bin/env python3
"""
MYCELIUM Standalone Server — запуск одной командой.

MARKER_140.STANDALONE: Standalone HTTP+WS сервер для Mycelium pipeline.
Не требует Claude Code — работает как обычный сервер.

Запуск:
    python run_mycelium.py

Что делает:
    1. HTTP API на порту 8083 — принимает pipeline задачи
    2. WebSocket на порту 8082 — стримит прогресс в DevPanel
    3. Полный доступ к Dragon Bronze/Silver/Gold

HTTP API:
    POST /pipeline      — запустить pipeline
    POST /call_model    — вызвать LLM
    GET  /health        — статус сервера
    GET  /pipelines     — список активных pipeline
    POST /task_board    — управление задачами

Пример:
    curl -X POST http://localhost:8083/pipeline \\
        -H "Content-Type: application/json" \\
        -d '{"task": "Create hello world", "preset": "dragon_bronze"}'
"""

import sys
import os
import asyncio
import json
import time
import signal
import logging
import uuid
from pathlib import Path
from typing import Dict, Any

# Project root
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

os.environ.setdefault("VETKA_API_URL", "http://localhost:5001")
os.environ.setdefault("PYTHONPATH", _project_root)
os.environ.setdefault("MYCELIUM_WS_PORT", "8082")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='[MYCELIUM] %(asctime)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("mycelium_standalone")

# Suppress noisy loggers
for _noisy in ['httpx', 'httpcore', 'urllib3', 'qdrant_client']:
    logging.getLogger(_noisy).setLevel(logging.WARNING)


def _kill_port(port: int):
    """Kill processes using a port (macOS/Linux)."""
    import subprocess
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True, timeout=5
        )
        pids = result.stdout.strip().split()
        for pid in pids:
            if pid and pid != str(os.getpid()):
                os.kill(int(pid), signal.SIGKILL)
                logger.info(f"Killed old process {pid} on port {port}")
    except Exception:
        pass


# ============================================================
# Global state
# ============================================================
_active_pipelines: Dict[str, asyncio.Task] = {}
_pipeline_results: Dict[str, Dict] = {}
_http_client = None
_ws_broadcaster = None
_start_time = time.time()

HTTP_PORT = int(os.environ.get("MYCELIUM_HTTP_PORT", "8083"))
WS_PORT = int(os.environ.get("MYCELIUM_WS_PORT", "8082"))

# VETKA connection state — Mycelium works WITHOUT VETKA, connects when available
_vetka_connected = False
_heartbeat_task: asyncio.Task = None


# ============================================================
# Component init
# ============================================================
async def _get_http_client():
    global _http_client
    if _http_client is None:
        from src.mcp.mycelium_http_client import get_mycelium_client
        _http_client = get_mycelium_client()
        try:
            await _http_client.start()
        except Exception as e:
            logger.warning(f"HTTP client start failed (VETKA may be down): {e}")
            _http_client = None
    return _http_client


async def _get_ws_broadcaster():
    global _ws_broadcaster
    if _ws_broadcaster is None:
        try:
            from src.mcp.mycelium_ws_server import get_ws_broadcaster
            _ws_broadcaster = get_ws_broadcaster()
            await _ws_broadcaster.start()
            logger.info(f"WebSocket broadcaster started on ws://localhost:{WS_PORT}")
        except ImportError:
            logger.warning("websockets not installed — pip install websockets>=12.0")
        except OSError as e:
            if "Address already in use" in str(e):
                logger.warning(f"Port {WS_PORT} already in use — WS broadcaster skipped (another instance running?)")
            else:
                logger.warning(f"WebSocket failed: {e}")
    return _ws_broadcaster


# ============================================================
# Pipeline runner (same logic as mycelium_mcp_server.py)
# ============================================================
async def run_pipeline(task: str, preset: str = "dragon_silver",
                       phase_type: str = "build", chat_id: str = None,
                       auto_write: bool = True, provider: str = None) -> str:
    """Run a pipeline task. Returns task_id immediately."""
    task_id = f"myc_{uuid.uuid4().hex[:8]}"

    # Breadcrumb for debugging
    breadcrumb_dir = Path(_project_root) / "data" / "feedback" / "pipeline_runs"
    breadcrumb_dir.mkdir(parents=True, exist_ok=True)
    breadcrumb_file = breadcrumb_dir / f"{task_id}.json"

    def write_breadcrumb(status: str, detail: str = ""):
        try:
            breadcrumb_file.write_text(json.dumps({
                "task_id": task_id, "status": status,
                "task": task[:200], "preset": preset,
                "detail": detail[:500],
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }, indent=2))
        except Exception:
            pass

    async def _run():
        http_client = await _get_http_client()
        ws_broadcaster = await _get_ws_broadcaster()
        write_breadcrumb("started")
        try:
            from src.orchestration.agent_pipeline import AgentPipeline
            pipeline = AgentPipeline(
                chat_id=chat_id,
                auto_write=auto_write,
                provider=provider,
                preset=preset,
                async_mode=True,
                http_client=http_client,
                ws_broadcaster=ws_broadcaster,
            )
            write_breadcrumb("pipeline_created")

            if ws_broadcaster:
                await ws_broadcaster.broadcast_pipeline_activity(
                    role="system",
                    message=f"Pipeline started: {task[:80]}",
                    task_id=task_id,
                    preset=preset,
                )

            result = await pipeline.execute(task, phase_type=phase_type)
            write_breadcrumb("completed", str(result)[:500] if result else "no result")

            _pipeline_results[task_id] = {
                "status": "completed",
                "result": str(result)[:2000] if result else None,
            }

            if ws_broadcaster:
                await ws_broadcaster.broadcast({
                    "type": "pipeline_complete",
                    "task_id": task_id,
                    "success": True,
                    "summary": str(result)[:500] if result else "completed",
                })
            if http_client:
                await http_client.notify_board_update("pipeline_complete", f"Pipeline {task_id} completed")

            logger.info(f"Pipeline {task_id} COMPLETED")

        except Exception as e:
            logger.error(f"Pipeline {task_id} FAILED: {e}", exc_info=True)
            write_breadcrumb("failed", f"{type(e).__name__}: {e}")
            _pipeline_results[task_id] = {
                "status": "failed",
                "error": str(e)[:500],
            }
            if ws_broadcaster:
                await ws_broadcaster.broadcast({
                    "type": "pipeline_failed",
                    "task_id": task_id,
                    "error": str(e)[:300],
                })
        finally:
            _active_pipelines.pop(task_id, None)

    bg_task = asyncio.create_task(_run())
    _active_pipelines[task_id] = bg_task
    return task_id


# ============================================================
# HTTP Server (aiohttp — lightweight)
# ============================================================
async def start_http_server():
    """Start HTTP API server for pipeline control."""
    try:
        from aiohttp import web
    except ImportError:
        logger.error("aiohttp not installed! pip install aiohttp")
        logger.info("Falling back to basic mode (WS only, no HTTP API)")
        return None

    app = web.Application()

    # --- CORS middleware ---
    @web.middleware
    async def cors_middleware(request, handler):
        if request.method == "OPTIONS":
            resp = web.Response(status=200)
        else:
            resp = await handler(request)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return resp

    app.middlewares.append(cors_middleware)

    # --- Routes ---
    async def handle_health(request):
        ws = _ws_broadcaster.get_status() if _ws_broadcaster else None
        return web.json_response({
            "server": "mycelium_standalone",
            "uptime_seconds": round(time.time() - _start_time, 1),
            "active_pipelines": len(_active_pipelines),
            "pipeline_ids": list(_active_pipelines.keys()),
            "websocket": ws,
            "vetka_connected": _vetka_connected,
            "heartbeat_running": _heartbeat_task is not None and not _heartbeat_task.done(),
            "http_port": HTTP_PORT,
            "ws_port": WS_PORT,
        })

    async def handle_pipeline(request):
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        task = body.get("task")
        if not task:
            return web.json_response({"error": "Missing 'task' field"}, status=400)

        task_id = await run_pipeline(
            task=task,
            preset=body.get("preset", "dragon_silver"),
            phase_type=body.get("phase_type", "build"),
            chat_id=body.get("chat_id"),
            auto_write=body.get("auto_write", True),
            provider=body.get("provider"),
        )
        return web.json_response({
            "success": True,
            "task_id": task_id,
            "status": "dispatched",
            "ws_url": f"ws://localhost:{WS_PORT}",
        })

    async def handle_pipelines(request):
        pipelines = {}
        for tid in list(_active_pipelines.keys()):
            pipelines[tid] = {"status": "running"}
        for tid, result in list(_pipeline_results.items()):
            pipelines[tid] = result
        return web.json_response({"pipelines": pipelines})

    async def handle_pipeline_status(request):
        task_id = request.match_info.get("task_id")
        if task_id in _active_pipelines:
            return web.json_response({"task_id": task_id, "status": "running"})
        if task_id in _pipeline_results:
            return web.json_response({"task_id": task_id, **_pipeline_results[task_id]})
        # Check breadcrumb file
        bf = Path(_project_root) / "data" / "feedback" / "pipeline_runs" / f"{task_id}.json"
        if bf.exists():
            return web.json_response(json.loads(bf.read_text()))
        return web.json_response({"error": "Pipeline not found"}, status=404)

    async def handle_call_model(request):
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        from src.mcp.tools.llm_call_tool_async import LLMCallToolAsync
        tool = LLMCallToolAsync()
        result = await tool.execute(body)
        return web.json_response(result, dumps=lambda o: json.dumps(o, default=str))

    async def handle_task_board(request):
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        from src.mcp.tools.task_board_tools import TaskBoardTool
        tool = TaskBoardTool()
        result = tool.execute(body)
        return web.json_response(result, dumps=lambda o: json.dumps(o, default=str))

    # --- Heartbeat control ---
    async def handle_heartbeat_start(request):
        """Start heartbeat daemon — monitors all chats for @dragon/@doctor/@titan."""
        global _heartbeat_task
        if _heartbeat_task and not _heartbeat_task.done():
            return web.json_response({"status": "already_running"})

        try:
            body = await request.json()
        except Exception:
            body = {}
        interval = max(10, body.get("interval", 60))

        async def _heartbeat_loop():
            from src.orchestration.mycelium_heartbeat import heartbeat_tick
            # Default group — MCP Dev Group
            default_group = "609c0d9a-b5bc-426b-b134-d693023bdac8"
            logger.info(f"[Heartbeat] Started (interval={interval}s, monitor_all=True)")
            while True:
                try:
                    result = await heartbeat_tick(
                        group_id=default_group,
                        dry_run=False,
                        monitor_all=True,
                    )
                    tasks_found = len(result.get("results", []))
                    if tasks_found > 0:
                        logger.info(f"[Heartbeat] Tick: {tasks_found} tasks dispatched")
                except asyncio.CancelledError:
                    logger.info("[Heartbeat] Stopped")
                    break
                except Exception as e:
                    logger.error(f"[Heartbeat] Error: {e}")
                await asyncio.sleep(interval)

        _heartbeat_task = asyncio.create_task(_heartbeat_loop())
        return web.json_response({"status": "started", "interval": interval})

    async def handle_heartbeat_stop(request):
        """Stop heartbeat daemon."""
        global _heartbeat_task
        if _heartbeat_task and not _heartbeat_task.done():
            _heartbeat_task.cancel()
            try:
                await _heartbeat_task
            except asyncio.CancelledError:
                pass
            _heartbeat_task = None
            return web.json_response({"status": "stopped"})
        return web.json_response({"status": "not_running"})

    async def handle_heartbeat_status(request):
        """Get heartbeat status."""
        running = _heartbeat_task is not None and not _heartbeat_task.done()
        from src.orchestration.mycelium_heartbeat import get_heartbeat_status
        status = get_heartbeat_status()
        return web.json_response({
            "running": running,
            **status,
        })

    app.router.add_get("/health", handle_health)
    app.router.add_post("/pipeline", handle_pipeline)
    app.router.add_get("/pipelines", handle_pipelines)
    app.router.add_get("/pipeline/{task_id}", handle_pipeline_status)
    app.router.add_post("/call_model", handle_call_model)
    app.router.add_post("/task_board", handle_task_board)
    app.router.add_post("/heartbeat/start", handle_heartbeat_start)
    app.router.add_post("/heartbeat/stop", handle_heartbeat_stop)
    app.router.add_get("/heartbeat/status", handle_heartbeat_status)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", HTTP_PORT)
    await site.start()
    logger.info(f"HTTP API ready on http://localhost:{HTTP_PORT}")
    return runner


# ============================================================
# Main
# ============================================================
async def main():
    shutdown_event = asyncio.Event()

    def _signal_handler(sig, frame):
        logger.info(f"Signal {sig} — shutting down...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # Auto-kill old processes on our ports
    _kill_port(HTTP_PORT)
    _kill_port(WS_PORT)
    await asyncio.sleep(0.5)  # Let OS release ports

    print(f"""
╔══════════════════════════════════════════════════╗
║  🍄 MYCELIUM — Independent Build Server          ║
║                                                  ║
║  HTTP API:   http://localhost:{HTTP_PORT}              ║
║  WebSocket:  ws://localhost:{WS_PORT}                  ║
║                                                  ║
║  POST /pipeline         — запустить Dragon       ║
║  POST /heartbeat/start  — мониторить @mentions   ║
║  POST /heartbeat/stop   — остановить мониторинг  ║
║  GET  /health           — статус сервера         ║
║  GET  /heartbeat/status — статус heartbeat       ║
║                                                  ║
║  VETKA не требуется для старта.                  ║
║  Подключится к VETKA когда она появится.         ║
║  Ctrl+C — остановить                             ║
╚══════════════════════════════════════════════════╝
""")

    # Start WS broadcaster
    await _get_ws_broadcaster()

    # Start HTTP server
    http_runner = await start_http_server()

    # VETKA watchdog — periodically check if VETKA backend is alive
    async def _vetka_watchdog():
        global _vetka_connected
        import httpx
        while True:
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.get("http://localhost:5001/api/system/health")
                    _vetka_connected = resp.status_code == 200
            except Exception:
                _vetka_connected = False
            if _vetka_connected:
                logger.debug("VETKA connected")
            await asyncio.sleep(15)

    watchdog_task = asyncio.create_task(_vetka_watchdog())

    # Wait for shutdown
    await shutdown_event.wait()
    watchdog_task.cancel()

    # Cleanup
    logger.info("Shutting down...")

    # Stop heartbeat
    if _heartbeat_task and not _heartbeat_task.done():
        _heartbeat_task.cancel()
        try:
            await _heartbeat_task
        except asyncio.CancelledError:
            pass

    for task_id, task in list(_active_pipelines.items()):
        logger.info(f"Cancelling pipeline {task_id}")
        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass

    if _ws_broadcaster:
        await _ws_broadcaster.stop()
    if _http_client:
        await _http_client.stop()
    if http_runner:
        await http_runner.cleanup()

    logger.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
