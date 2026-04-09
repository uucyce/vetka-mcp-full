import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.orchestration.task_board import get_task_board
import logging

# Import CUT route routers
from src.api.routes.cut_routes import router as cut_router
from src.api.routes.cut_routes_audio import audio_router
from src.api.routes.cut_routes_export import export_router
from src.api.routes.cut_routes_generation import generation_router
from src.api.routes.cut_routes_import import import_router
from src.api.routes.cut_routes_media import media_router
from src.api.routes.cut_routes_pulse import pulse_router
from src.api.routes.cut_routes_render import render_router
from src.api.routes.cut_routes_workers import worker_router

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="VETKA CUT API", version="1.0.0")

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize SocketIO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins="*",
    ping_timeout=60,
    ping_interval=25,
)
socket_app = socketio.ASGIApp(sio, app)

# Mount CUT API routers (cut_router already has /api/cut prefix)
app.include_router(cut_router)  # Already has prefix="/api/cut"
app.include_router(audio_router, prefix="/api/cut")
app.include_router(export_router, prefix="/api/cut")
app.include_router(generation_router, prefix="/api/cut")
app.include_router(import_router, prefix="/api/cut")
app.include_router(media_router, prefix="/api/cut")
app.include_router(pulse_router, prefix="/api/cut")
app.include_router(render_router, prefix="/api/cut")
app.include_router(worker_router, prefix="/api/cut")

# MARKER_102_2_START
@sio.event
async def new_task(sid, data):
    """Handle new_task event by triggering pipeline dispatch immediately"""
    logger.info(f"[SocketIO] Received new_task event from {sid}: {data}")
    
    # Get task board instance
    board = get_task_board()
    
    # Extract task parameters from data
    task_id = data.get("task_id")
    chat_id = data.get("chat_id")
    selected_key = data.get("selected_key")
    
    # Dispatch the task immediately
    if task_id:
        result = await board.dispatch_task(task_id, chat_id=chat_id, selected_key=selected_key)
    else:
        result = await board.dispatch_next(chat_id=chat_id, selected_key=selected_key)
    
    # Emit result back to client
    await sio.emit('task_result', {'result': result}, room=sid)
# MARKER_102_2_END