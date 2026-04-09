"""
Socket handlers for API key management
Phase 57.9: Auto-learn API keys via Hostess

Handles socket events for:
- Adding new API keys
- Learning unknown key types
- Getting key status

@file key_handlers.py
@status ACTIVE
@phase Phase 57.9
@lastUpdate 2026-01-10
"""

from socketio import AsyncServer
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def register_key_handlers(sio: AsyncServer, app=None):
    """
    Register socket handlers for API key management.

    Events handled:
    - add_api_key: Add a new API key (with auto-detection)
    - learn_key_type: Learn a new key type from user input
    - get_key_status: Get status of configured keys
    """

    @sio.on('add_api_key')
    async def handle_add_key(sid, data):
        """
        Handle adding a new API key.
        If type unknown, emit 'unknown_key_type' for user to identify.

        Event data:
        {
            "key": "tvly-dev-xxx..."
        }

        Emits:
        - key_saved: If key type was detected and saved
        - unknown_key_type: If key type is unknown, needs user input
        - key_error: If error occurred
        """
        key = data.get('key', '').strip()

        if not key:
            await sio.emit('key_error', {
                'error': 'No key provided'
            }, room=sid)
            return

        # Security: mask key in logs
        key_preview = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"
        logger.info(f"[KeyHandler] add_api_key: {key_preview}")

        try:
            # Try to detect provider
            # Phase 57.12: Check both static patterns AND learned patterns
            from src.elisya.api_key_detector import detect_api_key
            from src.elisya.key_learner import get_key_learner

            detected = detect_api_key(key)

            # If not detected by static patterns, check learned patterns
            if not detected or not detected.get('provider'):
                learner = get_key_learner()
                learned = learner.check_learned_pattern(key)
                if learned:
                    detected = learned
                    logger.info(f"[KeyHandler] Matched learned pattern: {learned.get('provider')}")

            if detected and detected.get('provider'):
                # Known type - save directly
                provider = detected['provider']

                from src.elisya.key_learner import get_key_learner
                learner = get_key_learner()
                learner._save_key_to_config(provider, key)

                await sio.emit('key_saved', {
                    'provider': provider,
                    'display_name': detected.get('display_name', provider.title()),
                    'confidence': detected.get('confidence', 1.0),
                    'message': f"✅ {detected.get('display_name', provider)} key saved!"
                }, room=sid)

                logger.info(f"[KeyHandler] Saved {provider} key")
            else:
                # Unknown type - analyze and ask user
                from src.elisya.key_learner import get_key_learner
                learner = get_key_learner()
                analysis = learner.analyze_key(key)

                await sio.emit('unknown_key_type', {
                    'key_preview': analysis.get('masked', key_preview),
                    'analysis': {
                        'prefix': analysis.get('prefix'),
                        'length': analysis.get('length'),
                        'charset': analysis.get('charset'),
                        'separator': analysis.get('separator')
                    },
                    'message': f"I don't recognize this key (prefix: {analysis.get('prefix') or 'unknown'}). What service is it for?"
                }, room=sid)

                logger.info(f"[KeyHandler] Unknown key type: {key_preview}")

        except Exception as e:
            logger.error(f"[KeyHandler] Error adding key: {e}")
            await sio.emit('key_error', {
                'error': str(e)
            }, room=sid)

    @sio.on('learn_key_type')
    async def handle_learn_key(sid, data):
        """
        Learn a new key type from user input.
        Called after user identifies an unknown key.

        Event data:
        {
            "key": "tvly-dev-xxx...",
            "provider": "tavily"
        }

        Emits:
        - key_learned: Successfully learned and saved
        - key_error: If error occurred
        """
        key = data.get('key', '').strip()
        provider = data.get('provider', '').strip()

        if not key or not provider:
            await sio.emit('key_error', {
                'error': 'Key and provider are required'
            }, room=sid)
            return

        key_preview = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"
        logger.info(f"[KeyHandler] learn_key_type: {provider} ({key_preview})")

        try:
            from src.elisya.key_learner import get_key_learner

            learner = get_key_learner()
            success, message = learner.learn_key_type(key, provider, save_key=True)

            if success:
                await sio.emit('key_learned', {
                    'provider': provider,
                    'display_name': provider.replace('_', ' ').title(),
                    'success': True,
                    'message': f"✅ Learned {provider}! Key saved."
                }, room=sid)

                logger.info(f"[KeyHandler] Learned {provider} pattern")
            else:
                await sio.emit('key_error', {
                    'error': message
                }, room=sid)

        except Exception as e:
            logger.error(f"[KeyHandler] Error learning key: {e}")
            await sio.emit('key_error', {
                'error': str(e)
            }, room=sid)

    @sio.on('get_key_status')
    async def handle_get_status(sid, data):
        """
        Get status of all API keys.

        Event data:
        {
            "provider": "optional_provider_name"
        }

        Emits:
        - key_status: Status of providers
        - key_error: If error occurred
        """
        provider = data.get('provider', '').strip() if data else ''

        logger.info(f"[KeyHandler] get_key_status: {provider or 'all'}")

        try:
            import json
            from pathlib import Path

            config_file = Path(__file__).parent.parent.parent.parent / "data" / "config.json"

            config = {}
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            api_keys = config.get('api_keys', {})

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
                    if value.get('paid'):
                        total += 1
                    if isinstance(value.get('free'), list):
                        total += len(value['free'])
                    return total
                return 0

            # Build status
            status = {}
            for p, keys_data in api_keys.items():
                key_count = count_keys(keys_data)
                status[p] = {
                    'count': key_count,
                    'active': key_count > 0
                }

            # Add learned providers
            from src.elisya.key_learner import get_key_learner
            learner = get_key_learner()
            for learned_p in learner.get_learned_providers():
                if learned_p not in status:
                    status[learned_p] = {
                        'count': 0,
                        'active': False,
                        'learned': True
                    }
                else:
                    status[learned_p]['learned'] = True

            providers_with_keys = [p for p, s in status.items() if s.get('active')]

            await sio.emit('key_status', {
                'providers': status,
                'providers_with_keys': providers_with_keys,
                'total': len(status),
                'active': len(providers_with_keys)
            }, room=sid)

        except Exception as e:
            logger.error(f"[KeyHandler] Error getting status: {e}")
            await sio.emit('key_error', {
                'error': str(e)
            }, room=sid)

    logger.info("[KeyHandler] Key handlers registered (Phase 57.9)")
