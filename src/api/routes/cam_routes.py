"""
VETKA CAM Routes - FastAPI Version

@file cam_routes.py
@status active
@phase 98, 99.3
@depends fastapi, pydantic, src.orchestration.cam_engine
@used_by src.api.routes.__init__, client/src/components/chat/ChatPanel

CAM (Constructivist Agentic Memory) API routes.
Links user reactions (emoji) to CAM weight boost for model preference learning.

Endpoints:
- POST /api/cam/reaction - Record user reaction and boost CAM weight
- GET /api/cam/weights - Get all model weights
- GET /api/cam/weights/{model_id} - Get specific model weight
- GET /api/cam/history - Get reaction history
- DELETE /api/cam/reset - Reset all weights
- GET /api/cam/suggestions - Get top N models by weight (Phase 99.3)
- GET /api/cam/model-rank/{model_id} - Get model ranking details (Phase 99.3)
- GET /api/cam/activation - Get hot/warm/cold activation status (Phase 99.3)
- POST /api/cam/pin - Pin file for JARVIS-like context (Phase 99.3)
- GET /api/cam/pinned - Get pinned files list (Phase 99.3)

Emoji weight mapping (from NeurIPS 2025 CAM paper + VETKA adaptation):
- thumbs_up (U+1F44D): +0.1 weight (positive feedback)
- thumbs_down (U+1F44E): -0.1 weight (negative feedback)
- heart (U+2764): +0.15 weight (strong positive)
- fire (U+1F525): +0.2 weight (excellent/impressive)
- lightbulb (U+1F4A1): +0.1 weight (insightful/helpful)
- thinking (U+1F914): 0.0 weight (neutral, tracked for analysis)
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Literal
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger("VETKA_CAM_Routes")

router = APIRouter(prefix="/api/cam", tags=["cam"])


# ============================================================
# PYDANTIC MODELS
# ============================================================

class CamReactionRequest(BaseModel):
    """Request to record a user reaction and boost CAM weight."""
    message_id: str
    reaction: Literal["thumbs_up", "thumbs_down", "heart", "fire", "lightbulb", "thinking"]
    model_id: str
    context: Optional[Dict[str, Any]] = None


class CamReactionResponse(BaseModel):
    """Response from CAM reaction endpoint."""
    success: bool
    weight_delta: float
    new_weight: float
    message_id: str
    model_id: str


# ============================================================
# EMOJI WEIGHT MAPPING
# ============================================================

# Phase 98: CAM-Emoji weight mapping
# Based on TODO_CAM_EMOJI comment in MessageBubble.tsx
EMOJI_WEIGHT_MAP: Dict[str, float] = {
    "thumbs_up": 0.1,     # Positive feedback
    "thumbs_down": -0.1,  # Negative feedback
    "heart": 0.15,        # Strong positive
    "fire": 0.2,          # Excellent/impressive response
    "lightbulb": 0.1,     # Insightful/helpful
    "thinking": 0.0,      # Neutral - tracked for analysis but no weight change
}

# Emoji unicode to reaction name mapping (for frontend flexibility)
EMOJI_TO_REACTION: Dict[str, str] = {
    "\U0001F44D": "thumbs_up",      # U+1F44D
    "\U0001F44E": "thumbs_down",    # U+1F44E
    "\u2764\uFE0F": "heart",        # U+2764 + variation selector
    "\u2764": "heart",              # U+2764 without variation
    "\U0001F525": "fire",           # U+1F525
    "\U0001F4A1": "lightbulb",      # U+1F4A1
    "\U0001F914": "thinking",       # U+1F914
}


# ============================================================
# IN-MEMORY WEIGHT STORAGE
# ============================================================

# Phase 98: Simple in-memory storage for model weights
# In production, this would persist to Qdrant or a database
_model_weights: Dict[str, float] = {}  # model_id -> weight (0.0-1.0)
_reaction_history: list = []  # List of reaction records for analysis

# Phase 99.3: Pinned files for JARVIS-like context suggestions
_pinned_files: Dict[str, dict] = {}  # file_path -> {reason, timestamp}

DEFAULT_MODEL_WEIGHT = 0.5  # Starting weight for new models


def get_model_weight(model_id: str) -> float:
    """Get current weight for a model."""
    return _model_weights.get(model_id, DEFAULT_MODEL_WEIGHT)


def update_model_weight(model_id: str, delta: float) -> float:
    """
    Update model weight by delta.

    Weight is clamped to [0.0, 1.0] range.

    Args:
        model_id: Model identifier
        delta: Weight change (+/-)

    Returns:
        New weight value
    """
    current = get_model_weight(model_id)
    new_weight = max(0.0, min(1.0, current + delta))
    _model_weights[model_id] = new_weight
    return new_weight


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def normalize_reaction(reaction_input: str) -> str:
    """
    Normalize reaction input to canonical name.

    Handles both emoji characters and reaction names.

    Args:
        reaction_input: Emoji character or reaction name

    Returns:
        Canonical reaction name
    """
    # If it's already a valid reaction name, return it
    if reaction_input in EMOJI_WEIGHT_MAP:
        return reaction_input

    # Try to map from emoji character
    if reaction_input in EMOJI_TO_REACTION:
        return EMOJI_TO_REACTION[reaction_input]

    # Handle common variations
    reaction_lower = reaction_input.lower().replace("-", "_").replace(" ", "_")
    if reaction_lower in EMOJI_WEIGHT_MAP:
        return reaction_lower

    # Default to thinking (neutral) if unknown
    logger.warning(f"Unknown reaction: {reaction_input}, defaulting to thinking")
    return "thinking"


def _get_cam_engine(request: Request):
    """Get CAM engine from app state."""
    try:
        flask_config = getattr(request.app.state, 'flask_config', {})
        get_orchestrator = flask_config.get('get_orchestrator')
        if get_orchestrator:
            orchestrator = get_orchestrator()
            if hasattr(orchestrator, 'cam_engine'):
                return orchestrator.cam_engine
    except Exception as e:
        logger.debug(f"Could not get CAM engine from orchestrator: {e}")

    # Fallback to singleton
    try:
        from src.orchestration.cam_engine import get_cam_engine
        return get_cam_engine()
    except Exception as e:
        logger.debug(f"Could not get CAM engine singleton: {e}")

    return None


# ============================================================
# ENDPOINTS
# ============================================================

@router.post("/reaction", response_model=CamReactionResponse)
async def cam_reaction(req: CamReactionRequest, request: Request):
    """
    Record user reaction and boost CAM weight for the model.

    This endpoint links emoji reactions to the CAM weight system,
    allowing user feedback to influence model selection preferences.

    Request body:
    {
        "message_id": "uuid",
        "reaction": "thumbs_up" | "thumbs_down" | "heart" | "fire" | "lightbulb" | "thinking",
        "model_id": "grok-4" | "claude-3" | etc,
        "context": {  # optional
            "topic": "string",
            "tool_used": "string"
        }
    }

    Response:
    {
        "success": true,
        "weight_delta": 0.1,
        "new_weight": 0.85,
        "message_id": "uuid",
        "model_id": "grok-4"
    }
    """
    try:
        # Normalize reaction name
        reaction_name = normalize_reaction(req.reaction)

        # Get weight delta from mapping
        weight_delta = EMOJI_WEIGHT_MAP.get(reaction_name, 0.0)

        # Update model weight
        new_weight = update_model_weight(req.model_id, weight_delta)

        # Record to history for analysis
        reaction_record = {
            "message_id": req.message_id,
            "model_id": req.model_id,
            "reaction": reaction_name,
            "weight_delta": weight_delta,
            "new_weight": new_weight,
            "context": req.context,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        _reaction_history.append(reaction_record)

        # Keep history bounded
        if len(_reaction_history) > 1000:
            _reaction_history.pop(0)

        # Also update CAM engine if available
        cam_engine = _get_cam_engine(request)
        if cam_engine:
            try:
                # Record tool usage for JARVIS-like suggestions
                from src.orchestration.cam_engine import get_cam_tool_memory
                tool_memory = get_cam_tool_memory()
                tool_memory.record_tool_use(
                    tool_name="reaction_feedback",
                    context={
                        "model_id": req.model_id,
                        "reaction": reaction_name,
                        "topic": req.context.get("topic") if req.context else None
                    },
                    success=weight_delta >= 0
                )
            except Exception as e:
                logger.debug(f"CAM tool memory update failed: {e}")

        logger.info(
            f"[CAM] Reaction recorded: {reaction_name} for {req.model_id} "
            f"(delta: {weight_delta:+.2f}, new: {new_weight:.2f})"
        )

        return CamReactionResponse(
            success=True,
            weight_delta=weight_delta,
            new_weight=new_weight,
            message_id=req.message_id,
            model_id=req.model_id
        )

    except Exception as e:
        logger.error(f"[CAM] Reaction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weights")
async def get_weights():
    """
    Get current CAM weights for all models.

    Returns model preference weights learned from user reactions.
    """
    return {
        "success": True,
        "weights": _model_weights.copy(),
        "default_weight": DEFAULT_MODEL_WEIGHT,
        "total_reactions": len(_reaction_history)
    }


@router.get("/weights/{model_id}")
async def get_model_weight_endpoint(model_id: str):
    """
    Get CAM weight for a specific model.

    Args:
        model_id: Model identifier
    """
    weight = get_model_weight(model_id)
    return {
        "success": True,
        "model_id": model_id,
        "weight": weight
    }


@router.get("/history")
async def get_reaction_history(limit: int = 50):
    """
    Get recent reaction history for analysis.

    Args:
        limit: Maximum number of records to return (default: 50)
    """
    return {
        "success": True,
        "history": _reaction_history[-limit:],
        "total_count": len(_reaction_history)
    }


@router.delete("/reset")
async def reset_weights():
    """
    Reset all CAM weights to default.

    Use with caution - clears all learned preferences.
    """
    global _model_weights, _reaction_history
    _model_weights = {}
    _reaction_history = []

    logger.info("[CAM] All weights reset to default")

    return {
        "success": True,
        "message": "All CAM weights have been reset to default"
    }


# ============================================================
# PHASE 99.3: CAM SUGGESTIONS & ACTIVATION ENDPOINTS
# ============================================================

@router.get("/suggestions")
async def get_cam_suggestions(context: str = "", limit: int = 5):
    """
    Return top N models ranked by CAM weight for given context.

    Phase 99.3: JARVIS-like model suggestions based on learned preferences.

    Args:
        context: Optional context string for filtering (unused in Phase 99.3)
        limit: Maximum number of suggestions (default: 5)

    Returns:
        {
            "success": true,
            "suggestions": [
                {"model_id": "grok-4", "weight": 0.85, "rank": 1},
                {"model_id": "claude-3", "weight": 0.72, "rank": 2},
                ...
            ],
            "context": "optional context string"
        }
    """
    try:
        # Sort models by weight descending
        sorted_models = sorted(
            _model_weights.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Take top N
        top_models = sorted_models[:limit]

        # Format suggestions
        suggestions = [
            {
                "model_id": model_id,
                "weight": weight,
                "rank": idx + 1
            }
            for idx, (model_id, weight) in enumerate(top_models)
        ]

        return {
            "success": True,
            "suggestions": suggestions,
            "context": context,
            "total_models": len(_model_weights)
        }

    except Exception as e:
        logger.error(f"[CAM] Suggestions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model-rank/{model_id}")
async def get_model_rank(model_id: str):
    """
    Return ranking info for single model.

    Phase 99.3: Get detailed ranking statistics for a specific model.

    Args:
        model_id: Model identifier

    Returns:
        {
            "success": true,
            "model_id": "grok-4",
            "weight": 0.85,
            "rank": 1,
            "percentile": 95.5,
            "recent_reactions": 15,
            "trend": "up"  # up/down/stable
        }
    """
    try:
        # Get current weight
        weight = get_model_weight(model_id)

        # Calculate rank
        sorted_models = sorted(
            _model_weights.items(),
            key=lambda x: x[1],
            reverse=True
        )
        rank = next(
            (idx + 1 for idx, (mid, _) in enumerate(sorted_models) if mid == model_id),
            None
        )

        # Calculate percentile
        total_models = len(_model_weights)
        percentile = 0.0
        if rank and total_models > 0:
            percentile = ((total_models - rank + 1) / total_models) * 100

        # Count recent reactions (last 50)
        recent_reactions = sum(
            1 for r in _reaction_history[-50:]
            if r.get("model_id") == model_id
        )

        # Calculate trend (compare recent vs older reactions)
        recent_weights = [
            r.get("weight_delta", 0)
            for r in _reaction_history[-10:]
            if r.get("model_id") == model_id
        ]
        older_weights = [
            r.get("weight_delta", 0)
            for r in _reaction_history[-50:-10]
            if r.get("model_id") == model_id
        ]

        avg_recent = sum(recent_weights) / len(recent_weights) if recent_weights else 0
        avg_older = sum(older_weights) / len(older_weights) if older_weights else 0

        if avg_recent > avg_older + 0.05:
            trend = "up"
        elif avg_recent < avg_older - 0.05:
            trend = "down"
        else:
            trend = "stable"

        return {
            "success": True,
            "model_id": model_id,
            "weight": weight,
            "rank": rank,
            "percentile": round(percentile, 1),
            "recent_reactions": recent_reactions,
            "trend": trend
        }

    except Exception as e:
        logger.error(f"[CAM] Model rank error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/activation")
async def get_activation_status(chat_id: Optional[str] = None, node_id: Optional[str] = None):
    """
    Return hot/warm/cold status for context.

    Phase 99.3: CAM activation levels based on weight thresholds.

    Activation levels:
    - hot: weight > 0.7 (frequently used, high preference)
    - warm: weight 0.3-0.7 (moderate usage)
    - cold: weight < 0.3 (rarely used or negative feedback)

    Args:
        chat_id: Optional chat context ID
        node_id: Optional node context ID

    Returns:
        {
            "success": true,
            "hot_models": ["grok-4", "claude-3"],
            "warm_models": ["gpt-4"],
            "cold_models": ["llama-2"],
            "context": {
                "chat_id": "...",
                "node_id": "..."
            }
        }
    """
    try:
        hot_models = []
        warm_models = []
        cold_models = []

        # Classify models by activation level
        for model_id, weight in _model_weights.items():
            if weight > 0.7:
                hot_models.append(model_id)
            elif weight >= 0.3:
                warm_models.append(model_id)
            else:
                cold_models.append(model_id)

        # Sort by weight within each category
        hot_models.sort(key=lambda m: _model_weights.get(m, 0), reverse=True)
        warm_models.sort(key=lambda m: _model_weights.get(m, 0), reverse=True)
        cold_models.sort(key=lambda m: _model_weights.get(m, 0), reverse=True)

        return {
            "success": True,
            "hot_models": hot_models,
            "warm_models": warm_models,
            "cold_models": cold_models,
            "context": {
                "chat_id": chat_id,
                "node_id": node_id
            },
            "counts": {
                "hot": len(hot_models),
                "warm": len(warm_models),
                "cold": len(cold_models)
            }
        }

    except Exception as e:
        logger.error(f"[CAM] Activation status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pin")
async def pin_file_for_context(file_path: str, reason: str = ""):
    """
    Pin file in context for JARVIS-like suggestions.

    Phase 99.3: Pin files to keep them in active context for CAM suggestions.

    Args:
        file_path: Absolute path to file
        reason: Optional reason for pinning

    Returns:
        {
            "success": true,
            "file_path": "/path/to/file.py",
            "reason": "Working on authentication",
            "timestamp": "2026-01-28T..."
        }
    """
    try:
        timestamp = datetime.now(timezone.utc).isoformat()

        # Store pinned file
        _pinned_files[file_path] = {
            "reason": reason,
            "timestamp": timestamp
        }

        logger.info(f"[CAM] File pinned: {file_path} (reason: {reason})")

        return {
            "success": True,
            "file_path": file_path,
            "reason": reason,
            "timestamp": timestamp
        }

    except Exception as e:
        logger.error(f"[CAM] Pin file error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pinned")
async def get_pinned_files():
    """
    Return list of pinned files.

    Phase 99.3: Get all files currently pinned in context.

    Returns:
        {
            "success": true,
            "pinned": [
                {
                    "file_path": "/path/to/file.py",
                    "reason": "Working on authentication",
                    "timestamp": "2026-01-28T..."
                },
                ...
            ],
            "count": 3
        }
    """
    try:
        # Format pinned files
        pinned_list = [
            {
                "file_path": file_path,
                "reason": data.get("reason", ""),
                "timestamp": data.get("timestamp", "")
            }
            for file_path, data in _pinned_files.items()
        ]

        # Sort by timestamp (most recent first)
        pinned_list.sort(key=lambda x: x["timestamp"], reverse=True)

        return {
            "success": True,
            "pinned": pinned_list,
            "count": len(pinned_list)
        }

    except Exception as e:
        logger.error(f"[CAM] Get pinned files error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
