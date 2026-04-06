"""
src/services/model_router.py
MARKER_211.MODEL_ROUTER: Dynamic model selection by task_type + urgency.

Routes tasks to optimal model tier based on:
- task_type: classify, enrich, vision, code_review, embed
- urgency: low (best quality), medium (balanced), high (fastest)
- available models on Ollama

Built on GEMMA-210 benchmark findings:
- Drone tier (sub-second): phi4-mini, gemma4:e2b for classification
- Plane tier (Sherpa ops): gemma4:e4b for enrichment, code review
- Vision tier: gemma4:e4b for screenshots, qwen2.5vl:3b for speed

@status: active
@phase: 211
@depends: model_policy, provider_registry
@used_by: sherpa, scout, agent_pipeline
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class ModelRoute:
    """Result of model routing decision."""
    model_id: str
    tier: str          # drone | plane | plane_vision
    reason: str        # why this model was selected
    fallback: Optional[str] = None  # if primary unavailable


# Tier definitions from GEMMA-210 benchmarks
DRONE_MODELS = [
    "phi4-mini:latest",   # 3.8s, accurate, fastest correct
    "gemma4:e2b",         # 9.6s with thinking, accurate
    "gemma3:1b",          # 1.6s but lower accuracy
    "tinyllama:latest",   # 637MB, ultra-light
    "llama3.2:1b",        # 1.3GB, decent accuracy
]

PLANE_MODELS = [
    "gemma4:e4b",         # 26.3s, best quality, 2x faster than qwen3.5
    "qwen3.5:latest",     # 53.9s, clean JSON but slower
    "qwen3:8b",           # good for code
    "qwen2.5:7b",         # balanced
    "deepseek-r1:8b",     # strong reasoning
]

PLANE_VISION_MODELS = [
    "gemma4:e4b",         # vision + text, 37.8s, detailed analysis
    "qwen2.5vl:3b",      # 8.3s, fast vision, basic quality
    "gemma4:26b",         # deep analysis if memory allows (18GB)
]


# Task-type to tier mapping
_TASK_TIER_MAP: Dict[str, str] = {
    # Drone tasks (sub-second, classification)
    "classify": "drone",
    "intent": "drone",
    "validate_json": "drone",
    "relevance": "drone",
    "token_extract": "drone",
    "error_category": "drone",
    # Plane tasks (Sherpa/Scout main ops)
    "enrich": "plane",
    "code_review": "plane",
    "allowed_paths": "plane",
    "completion_contract": "plane",
    "recon_summary": "plane",
    "task_enrichment": "plane",
    # Vision tasks (screenshots, UI analysis)
    "screenshot": "plane_vision",
    "ui_analysis": "plane_vision",
    "code_ocr": "plane_vision",
    "visual_qa": "plane_vision",
    "media_debug": "plane_vision",
}

# Urgency overrides: high urgency → prefer speed over quality
_URGENCY_SPEED_PREFERENCE: Dict[str, int] = {
    "high": 0,    # pick fastest (index 0 in sorted-by-speed list)
    "medium": 1,  # pick second
    "low": -1,    # pick last (best quality, slowest)
}


def _get_available_ollama_models() -> List[str]:
    """Check which models are actually pulled in Ollama."""
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        if resp.status_code == 200:
            return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        pass
    return []


def route_model(
    task_type: str,
    urgency: str = "medium",
    require_vision: bool = False,
    available_models: Optional[List[str]] = None,
) -> ModelRoute:
    """Route a task to the optimal model based on type and urgency.

    Args:
        task_type: One of the known task types (classify, enrich, screenshot, etc.)
        urgency: low (quality), medium (balanced), high (speed)
        require_vision: Force vision-capable model regardless of task_type
        available_models: Override Ollama model list (for testing)

    Returns:
        ModelRoute with selected model, tier, and reasoning
    """
    if available_models is None:
        available_models = _get_available_ollama_models()

    # Determine tier
    if require_vision:
        tier = "plane_vision"
    else:
        tier = _TASK_TIER_MAP.get(task_type, "plane")

    # Get candidate list for tier
    candidates = {
        "drone": DRONE_MODELS,
        "plane": PLANE_MODELS,
        "plane_vision": PLANE_VISION_MODELS,
    }.get(tier, PLANE_MODELS)

    # Filter to available models
    available_candidates = [m for m in candidates if m in available_models]

    if not available_candidates:
        # Fallback: try any available model from any tier
        all_known = DRONE_MODELS + PLANE_MODELS + PLANE_VISION_MODELS
        available_candidates = [m for m in all_known if m in available_models]
        if not available_candidates:
            # Last resort: return first candidate (user needs to pull it)
            selected = candidates[0]
            return ModelRoute(
                model_id=selected,
                tier=tier,
                reason=f"no models available locally; pull with: ollama pull {selected}",
                fallback=candidates[1] if len(candidates) > 1 else None,
            )

    # Select by urgency
    idx = _URGENCY_SPEED_PREFERENCE.get(urgency, 1)
    if idx == -1:
        idx = len(available_candidates) - 1
    idx = min(idx, len(available_candidates) - 1)
    selected = available_candidates[idx]

    fallback = None
    if len(available_candidates) > 1:
        fallback = available_candidates[1] if idx == 0 else available_candidates[0]

    return ModelRoute(
        model_id=selected,
        tier=tier,
        reason=f"{task_type}@{urgency} → {tier} tier, {len(available_candidates)} available",
        fallback=fallback,
    )


def extract_json(response: str) -> Optional[Dict[str, Any]]:
    """GEMMA-211.JSON_STRIP: Extract JSON from markdown-wrapped LLM responses.

    Gemma 4 models wrap JSON in ```json ... ``` blocks. This helper
    strips the wrapper and parses the JSON.

    Args:
        response: Raw LLM response text

    Returns:
        Parsed dict, or None if parsing fails
    """
    import json

    text = response.strip()

    # Fast path: already valid JSON
    if text.startswith("{") or text.startswith("["):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Strip markdown code block wrapper
    if text.startswith("```"):
        lines = text.split("\n")
        json_lines = []
        in_block = False
        for line in lines:
            if line.startswith("```"):
                in_block = not in_block
                continue
            if in_block:
                json_lines.append(line)
        text = "\n".join(json_lines).strip()

    # Try parsing stripped content
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse JSON from response ({len(response)} chars)")
        return None


# Gemma 4 entries for LOCALGUYS_CATALOG extension
GEMMA4_MODELS = {
    "gemma4:e2b": {
        "tier": "drone",
        "params": "5.1B (2.3B effective)",
        "size_gb": 7.2,
        "context": 128_000,
        "vision": True,
        "audio": True,
        "license": "Apache-2.0",
        "role_fit": ["scout", "classifier", "router"],
        "fc_reliability": 0.80,
        "notes": "Any-to-any. 9.6s with thinking on classification.",
    },
    "gemma4:e4b": {
        "tier": "plane_vision",
        "params": "8.0B (4.5B effective)",
        "size_gb": 9.6,
        "context": 128_000,
        "vision": True,
        "audio": True,
        "license": "Apache-2.0",
        "role_fit": ["sherpa", "code_review", "vision_qa", "enrichment"],
        "fc_reliability": 0.82,
        "notes": "Best balance: 2x faster than qwen3.5, higher quality. Primary Sherpa candidate.",
    },
    "gemma4:26b": {
        "tier": "plane_vision",
        "params": "26.5B (3.8B active MoE)",
        "size_gb": 18.0,
        "context": 256_000,
        "vision": True,
        "audio": False,
        "license": "Apache-2.0",
        "role_fit": ["architect", "deep_analysis"],
        "fc_reliability": 0.85,
        "notes": "MoE, deep analysis. Tight on 24GB M4 — limit context to 32-64K.",
    },
}
