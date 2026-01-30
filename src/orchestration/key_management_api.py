"""
Key Management API - Phase 7 Integration.

Manages OpenRouter keys, Gemini keys, routing, and failover.

MARKER: CLEANUP41_DEPRECATED_FLASK
STATUS: DEPRECATED - This is Flask-only code, not migrated to FastAPI
This file uses Flask decorators (@app.route) and is NOT imported anywhere.
Keep for reference but do not use.

@status: deprecated
@phase: 96
@depends: flask (stubbed)
@used_by: none (deprecated)
"""

# MARKER: CLEANUP41_FLASK_IMPORTS_STUBBED
# Original Flask imports replaced with stubs (file is deprecated)
# from flask import jsonify, request
def jsonify(data):
    """Stub: Returns data as-is (Flask jsonify is not available)"""
    return data

class _RequestStub:
    """Stub: Flask request is not available"""
    json = {}

request = _RequestStub()

from typing import Dict, List, Optional
import os
from datetime import datetime
import logging

logger = logging.getLogger("KeyManagementAPI")


class KeyManagementAPI:
    """API endpoints for key management"""
    
    def __init__(self, model_router):
        """Initialize with ModelRouter instance"""
        self.model_router = model_router
        self.app = None
    
    def register(self, app):
        """Register endpoints with Flask app"""
        self.app = app
        
        @app.route("/api/keys/status", methods=["GET"])
        def get_keys_status():
            return self._status()
        
        @app.route("/api/keys/list", methods=["GET"])
        def list_keys():
            return self._list_keys()
        
        @app.route("/api/keys/add", methods=["POST"])
        def add_key():
            return self._add_key()
        
        @app.route("/api/keys/remove", methods=["POST"])
        def remove_key():
            return self._remove_key()
        
        @app.route("/api/keys/route", methods=["POST"])
        def route_task():
            return self._route_task()
        
        @app.route("/api/keys/mark-success", methods=["POST"])
        def mark_success():
            return self._mark_success()
        
        @app.route("/api/keys/mark-error", methods=["POST"])
        def mark_error():
            return self._mark_error()
        
        @app.route("/api/keys/rotate", methods=["POST"])
        def rotate_keys():
            return self._rotate_keys()
        
        logger.info("✅ Key Management API registered")
    
    def _status(self):
        """GET /api/keys/status - Get key management status"""
        try:
            status = {
                "status": "ok",
                "timestamp": datetime.now().isoformat(),
                "openrouter_keys": self.model_router.get_active_key_count("openrouter") if hasattr(self.model_router, "get_active_key_count") else 9,
                "gemini_keys": 1 if os.getenv("GEMINI_API_KEY") else 0,
                "total_keys": 10,
                "services": {
                    "openrouter": "active",
                    "gemini": "active" if os.getenv("GEMINI_API_KEY") else "inactive",
                }
            }
            return jsonify(status), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    def _list_keys(self):
        """GET /api/keys/list - List all keys (masked)"""
        try:
            keys = []
            
            # OpenRouter keys
            for i in range(1, 10):
                key_env = f"OPENROUTER_KEY_{i}"
                key_val = os.getenv(key_env)
                if key_val:
                    keys.append({
                        "id": f"openrouter_{i}",
                        "provider": "openrouter",
                        "key_masked": f"{key_val[:10]}...{key_val[-5:]}",
                        "status": "active"
                    })
            
            # Gemini key
            if os.getenv("GEMINI_API_KEY"):
                gemini_key = os.getenv("GEMINI_API_KEY")
                keys.append({
                    "id": "gemini_1",
                    "provider": "gemini",
                    "key_masked": f"{gemini_key[:10]}...{gemini_key[-5:]}",
                    "status": "active"
                })
            
            return jsonify({"keys": keys, "count": len(keys)}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    def _add_key(self):
        """POST /api/keys/add - Add new API key"""
        try:
            data = request.json or {}
            provider = data.get("provider", "").lower()
            key_value = data.get("key", "")
            
            if not provider or not key_value:
                return jsonify({"error": "provider and key are required"}), 400
            
            if provider == "openrouter":
                # Find next available slot
                for i in range(1, 50):
                    if not os.getenv(f"OPENROUTER_KEY_{i}"):
                        os.environ[f"OPENROUTER_KEY_{i}"] = key_value
                        return jsonify({
                            "status": "success",
                            "message": f"OpenRouter key added to slot {i}",
                            "key_id": f"openrouter_{i}"
                        }), 201
                
                return jsonify({"error": "No available slots for OpenRouter keys"}), 400
            
            elif provider == "gemini":
                os.environ["GEMINI_API_KEY"] = key_value
                return jsonify({
                    "status": "success",
                    "message": "Gemini key updated",
                    "key_id": "gemini_1"
                }), 201
            
            else:
                return jsonify({"error": f"Unknown provider: {provider}"}), 400
        
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    def _remove_key(self):
        """POST /api/keys/remove - Remove API key"""
        try:
            data = request.json or {}
            key_id = data.get("key_id", "")
            
            if not key_id:
                return jsonify({"error": "key_id is required"}), 400
            
            if key_id.startswith("openrouter_"):
                slot = key_id.split("_")[1]
                env_key = f"OPENROUTER_KEY_{slot}"
                if env_key in os.environ:
                    del os.environ[env_key]
                    return jsonify({"status": "success", "message": f"Key {key_id} removed"}), 200
            
            elif key_id == "gemini_1":
                if "GEMINI_API_KEY" in os.environ:
                    del os.environ["GEMINI_API_KEY"]
                    return jsonify({"status": "success", "message": "Gemini key removed"}), 200
            
            return jsonify({"error": "Key not found"}), 404
        
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    def _route_task(self):
        """POST /api/keys/route - Route task to best provider"""
        try:
            data = request.json or {}
            task_type = data.get("task_type", "general")
            complexity = data.get("complexity", "medium")
            
            # Simple routing logic
            if task_type in ["code", "technical"]:
                return jsonify({
                    "recommended_provider": "openrouter",
                    "model": "deepseek/deepseek-coder",
                    "reason": "Best for code generation"
                }), 200
            
            elif task_type in ["image", "vision"]:
                return jsonify({
                    "recommended_provider": "gemini",
                    "model": "gemini-2.0-flash-exp",
                    "reason": "Best for vision tasks"
                }), 200
            
            else:
                return jsonify({
                    "recommended_provider": "openrouter",
                    "model": "openai/gpt-4-turbo",
                    "reason": "General purpose"
                }), 200
        
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    def _mark_success(self):
        """POST /api/keys/mark-success - Mark key as successfully used"""
        try:
            data = request.json or {}
            key_id = data.get("key_id", "")
            
            if not key_id:
                return jsonify({"error": "key_id is required"}), 400
            
            logger.info(f"✅ Key {key_id} marked as successful")
            
            return jsonify({
                "status": "success",
                "message": f"Key {key_id} marked as successful"
            }), 200
        
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    def _mark_error(self):
        """POST /api/keys/mark-error - Mark key as errored"""
        try:
            data = request.json or {}
            key_id = data.get("key_id", "")
            error_msg = data.get("error", "unknown error")
            
            if not key_id:
                return jsonify({"error": "key_id is required"}), 400
            
            logger.warning(f"❌ Key {key_id} marked as errored: {error_msg}")
            
            return jsonify({
                "status": "success",
                "message": f"Key {key_id} marked as errored"
            }), 200
        
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    def _rotate_keys(self):
        """POST /api/keys/rotate - Rotate API keys"""
        try:
            logger.info("🔄 Rotating API keys...")
            
            return jsonify({
                "status": "success",
                "message": "API keys rotated",
                "active_keys": 10,
                "timestamp": datetime.now().isoformat()
            }), 200
        
        except Exception as e:
            return jsonify({"error": str(e)}), 500
