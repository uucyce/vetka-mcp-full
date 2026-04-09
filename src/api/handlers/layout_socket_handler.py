"""
MARKER_110_BACKEND_CONFIG
Layout configuration socket handlers for DevPanel integration.
Receives config from frontend, triggers layout recalculation.

Phase 110: Backend Config Integration
- Stores layout config in global state
- Provides socket handlers for update_layout_config and get_layout_config
- Emits tree_refresh_needed when apply_immediately is set

@status active
@phase 110
@depends socketio, typing, logging
@used_by main.py, fan_layout.py
"""

from socketio import AsyncServer
from typing import Dict, Any
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)

# MARKER_110_BACKEND_CONFIG: Global config storage (will be passed to fan_layout)
_layout_config: Dict[str, Any] = {
    'Y_WEIGHT_TIME': 0.5,
    'Y_WEIGHT_KNOWLEDGE': 0.5,
    'MIN_Y_FLOOR': 20,
    'MAX_Y_CEILING': 5000,
    'FALLBACK_THRESHOLD': 0.5,
    'USE_SEMANTIC_FALLBACK': True,
}


def get_layout_config() -> Dict[str, Any]:
    """
    Get current layout configuration.

    Returns a copy to prevent external mutation.
    Used by fan_layout.py to get dynamic config values.
    """
    return _layout_config.copy()


def update_layout_config(config: Dict[str, Any]) -> None:
    """
    Update layout configuration.

    Only updates provided keys, preserves others.
    Logs the update for debugging.
    """
    global _layout_config
    _layout_config.update(config)
    logger.info(f"[LAYOUT_CONFIG] Updated: {config}")


def register_layout_socket_handlers(sio: AsyncServer, app=None):
    """
    Register socket handlers for layout configuration.

    Events:
    - update_layout_config: Receive config changes from DevPanel
    - get_layout_config: Return current config to client

    Args:
        sio: AsyncServer instance
        app: FastAPI app (optional, for app.state access)
    """

    @sio.on('update_layout_config')
    async def handle_update_layout_config(sid, data):
        """
        Handle DevPanel config changes from frontend.

        MARKER_110_BACKEND_CONFIG: Main handler for config updates.

        Expected data format:
        {
            'Y_WEIGHT_TIME': float,
            'Y_WEIGHT_KNOWLEDGE': float,
            'MIN_Y_FLOOR': int,
            'MAX_Y_CEILING': int,
            'FALLBACK_THRESHOLD': float,
            'USE_SEMANTIC_FALLBACK': bool,
            'apply_immediately': bool  # If true, trigger tree refresh
        }
        """
        try:
            print(f"[LAYOUT_CONFIG] *** RECEIVED CONFIG UPDATE ***: {data}")
            logger.info(f"[LAYOUT_CONFIG] Received update from {sid}: {data}")

            # Validate data is a dict
            if not isinstance(data, dict):
                await sio.emit('layout_config_updated', {
                    'success': False,
                    'error': 'Invalid data format: expected object'
                }, to=sid)
                return

            # Extract apply_immediately flag before updating config
            apply_immediately = data.pop('apply_immediately', False)

            # Update the global config
            update_layout_config(data)

            # Emit confirmation to sender
            await sio.emit('layout_config_updated', {
                'success': True,
                'config': get_layout_config()
            }, to=sid)

            # If apply_immediately, broadcast to trigger refresh
            if apply_immediately:
                logger.info("[LAYOUT_CONFIG] Broadcasting tree_refresh_needed")
                await sio.emit('tree_refresh_needed', {
                    'reason': 'layout_config_changed',
                    'config': get_layout_config()
                })

        except Exception as e:
            logger.error(f"[LAYOUT_CONFIG] Error handling update: {e}", exc_info=True)
            await sio.emit('layout_config_updated', {
                'success': False,
                'error': str(e)
            }, to=sid)

    @sio.on('get_layout_config')
    async def handle_get_layout_config(sid, data=None):
        """
        Return current layout configuration to client.

        MARKER_110_BACKEND_CONFIG: Config retrieval handler.
        """
        try:
            config = get_layout_config()
            logger.debug(f"[LAYOUT_CONFIG] Sending config to {sid}: {config}")
            await sio.emit('layout_config', config, to=sid)
        except Exception as e:
            logger.error(f"[LAYOUT_CONFIG] Error getting config: {e}")
            await sio.emit('layout_config', {
                'error': str(e)
            }, to=sid)

    # Phase 113.1: Persistent Spatial Memory — position save/load handlers
    POSITIONS_FILE = Path("data/node_positions.json")

    @sio.on('save_positions')
    async def handle_save_positions(sid, data):
        """Save node positions from frontend drag operations."""
        try:
            if not isinstance(data, dict) or 'positions' not in data:
                await sio.emit('positions_saved', {'success': False, 'error': 'Invalid format'}, to=sid)
                return

            POSITIONS_FILE.parent.mkdir(exist_ok=True)
            with POSITIONS_FILE.open('w') as f:
                json.dump(data, f)

            count = len(data.get('positions', {}))
            logger.info(f"[POSITIONS] Saved {count} positions from {sid}")
            await sio.emit('positions_saved', {'success': True, 'count': count}, to=sid)

        except Exception as e:
            logger.error(f"[POSITIONS] Save error: {e}", exc_info=True)
            await sio.emit('positions_saved', {'success': False, 'error': str(e)}, to=sid)

    @sio.on('load_positions')
    async def handle_load_positions(sid, data=None):
        """Return saved positions to client."""
        try:
            if not POSITIONS_FILE.exists():
                await sio.emit('positions_loaded', {'positions': {}, 'ts': 0}, to=sid)
                return

            with POSITIONS_FILE.open('r') as f:
                positions_data = json.load(f)

            logger.info(f"[POSITIONS] Loaded {len(positions_data.get('positions', {}))} positions for {sid}")
            await sio.emit('positions_loaded', positions_data, to=sid)

        except Exception as e:
            logger.error(f"[POSITIONS] Load error: {e}", exc_info=True)
            await sio.emit('positions_loaded', {'positions': {}, 'ts': 0}, to=sid)

    logger.info("[LAYOUT_CONFIG] Socket handlers registered (+ Phase 113.1 positions)")
