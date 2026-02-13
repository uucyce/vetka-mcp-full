"""
MARKER_141.PIPELINE_CONFIG: Pipeline Configuration API.

Read/write model_presets.json and pipeline_prompts.json.
Used by MCC DetailPanel to edit agent roles and prompts.

@phase 141
@status active
"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict

router = APIRouter(prefix="/api/pipeline", tags=["pipeline-config"])

# MARKER_141.PATHS: Data file locations
_DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "templates"
_PRESETS_FILE = _DATA_DIR / "model_presets.json"
_PROMPTS_FILE = _DATA_DIR / "pipeline_prompts.json"


def _load_json(path: Path) -> dict:
    """Load JSON file with error handling."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: dict) -> None:
    """Save JSON file with pretty formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


# ============================================================
# PRESETS API
# ============================================================


@router.get("/presets")
async def get_presets():
    """
    Get all model presets with their role→model mappings.

    Returns preset names, descriptions, roles, and default/tier info.
    """
    try:
        data = _load_json(_PRESETS_FILE)
        presets = data.get("presets", {})
        return {
            "success": True,
            "presets": presets,
            "default_preset": data.get("default_preset", "dragon_silver"),
            "tier_map": data.get("_tier_map", {}),
            "stm_window_map": data.get("_stm_window_map", {}),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/presets/{preset_name}")
async def get_preset(preset_name: str):
    """Get a single preset by name."""
    data = _load_json(_PRESETS_FILE)
    presets = data.get("presets", {})
    if preset_name not in presets:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_name}' not found")
    return {
        "success": True,
        "preset_name": preset_name,
        "preset": presets[preset_name],
    }


class UpdateRoleModel(BaseModel):
    """Update a single role's model in a preset."""
    preset_name: str
    role: str  # architect, researcher, coder, verifier, scout
    model: str  # e.g. "qwen/qwen3-coder"


@router.post("/presets/update-role")
async def update_preset_role(req: UpdateRoleModel):
    """
    Update a single role's model within a preset.

    This is the primary endpoint for the DAG DetailPanel
    when user clicks an agent node and changes its model.
    """
    data = _load_json(_PRESETS_FILE)
    presets = data.get("presets", {})

    if req.preset_name not in presets:
        raise HTTPException(status_code=404, detail=f"Preset '{req.preset_name}' not found")

    preset = presets[req.preset_name]
    roles = preset.get("roles", preset)

    valid_roles = {"architect", "researcher", "coder", "verifier", "scout"}
    if req.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role: {req.role}. Must be one of {valid_roles}")

    old_model = roles.get(req.role, "")
    roles[req.role] = req.model

    # Ensure roles dict is properly nested
    if "roles" in preset:
        preset["roles"] = roles
    else:
        presets[req.preset_name] = {**preset, **roles}

    _save_json(_PRESETS_FILE, data)

    return {
        "success": True,
        "preset_name": req.preset_name,
        "role": req.role,
        "old_model": old_model,
        "new_model": req.model,
    }


class SetDefaultPreset(BaseModel):
    """Set the default preset."""
    preset_name: str


@router.post("/presets/default")
async def set_default_preset(req: SetDefaultPreset):
    """Set which preset is used by default."""
    data = _load_json(_PRESETS_FILE)
    presets = data.get("presets", {})

    if req.preset_name not in presets:
        raise HTTPException(status_code=404, detail=f"Preset '{req.preset_name}' not found")

    data["default_preset"] = req.preset_name
    _save_json(_PRESETS_FILE, data)

    return {"success": True, "default_preset": req.preset_name}


# ============================================================
# PROMPTS API
# ============================================================


@router.get("/prompts")
async def get_prompts():
    """
    Get all pipeline role prompts.

    Returns system prompts, temperatures, and model info for each role.
    """
    try:
        data = _load_json(_PROMPTS_FILE)
        # Separate config from role prompts
        config = data.pop("_config", {})
        roles = {}
        for role_name, role_data in data.items():
            roles[role_name] = {
                "system": role_data.get("system", ""),
                "temperature": role_data.get("temperature", 0.3),
                "model": role_data.get("model", ""),
                "model_fallback": role_data.get("model_fallback", ""),
            }
        return {
            "success": True,
            "config": config,
            "prompts": roles,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/prompts/{role}")
async def get_prompt(role: str):
    """Get prompt config for a specific role."""
    data = _load_json(_PROMPTS_FILE)
    if role not in data or role.startswith("_"):
        raise HTTPException(status_code=404, detail=f"Role '{role}' not found")
    return {
        "success": True,
        "role": role,
        "prompt": data[role],
    }


class UpdatePrompt(BaseModel):
    """Update a role's system prompt."""
    role: str
    system: Optional[str] = None
    temperature: Optional[float] = None


@router.post("/prompts/update")
async def update_prompt(req: UpdatePrompt):
    """
    Update a role's system prompt and/or temperature.

    Used by DetailPanel prompt editor.
    """
    data = _load_json(_PROMPTS_FILE)

    if req.role not in data or req.role.startswith("_"):
        raise HTTPException(status_code=404, detail=f"Role '{req.role}' not found")

    updated = {}
    if req.system is not None:
        data[req.role]["system"] = req.system
        updated["system"] = True
    if req.temperature is not None:
        data[req.role]["temperature"] = req.temperature
        updated["temperature"] = req.temperature

    _save_json(_PROMPTS_FILE, data)

    return {
        "success": True,
        "role": req.role,
        "updated": updated,
    }
