# file: src/api/main.py

import socketio
from fastapi import FastAPI
from src.orchestration.task_board import get_task_board
import logging

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Initialize SocketIO server
sio = socketio.AsyncServer(cors_allowed_origins=[])
socket_app = socketio.ASGIApp(sio)

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