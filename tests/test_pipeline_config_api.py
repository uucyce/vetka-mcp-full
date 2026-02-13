# MARKER_141.TESTS: Tests for pipeline config API (presets + prompts)
"""Tests for /api/pipeline/* endpoints (model presets + role prompts)."""

import json
import shutil
from pathlib import Path

import pytest

from src.api.routes.pipeline_config_routes import (
    _load_json,
    _save_json,
    _DATA_DIR,
    _PRESETS_FILE,
    _PROMPTS_FILE,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def tmp_presets(tmp_path, monkeypatch):
    """Create a temporary presets file and monkeypatch the path."""
    presets_data = {
        "_meta": {"version": "test"},
        "default_preset": "dragon_silver",
        "_tier_map": {"low": "dragon_bronze", "medium": "dragon_silver", "high": "dragon_gold"},
        "_stm_window_map": {"low": 3, "medium": 5, "high": 8},
        "presets": {
            "dragon_bronze": {
                "description": "Bronze test",
                "provider": "polza",
                "roles": {
                    "architect": "qwen/qwen3-30b-a3b",
                    "researcher": "x-ai/grok-4.1-fast",
                    "coder": "qwen/qwen3-coder-flash",
                    "verifier": "xiaomi/mimo-v2-flash",
                    "scout": "xiaomi/mimo-v2-flash",
                },
            },
            "dragon_silver": {
                "description": "Silver test",
                "provider": "polza",
                "roles": {
                    "architect": "moonshotai/kimi-k2.5",
                    "researcher": "x-ai/grok-4.1-fast",
                    "coder": "qwen/qwen3-coder",
                    "verifier": "z-ai/glm-4.7-flash",
                    "scout": "z-ai/glm-4.7-flash",
                },
            },
        },
    }
    presets_file = tmp_path / "model_presets.json"
    with open(presets_file, "w") as f:
        json.dump(presets_data, f)

    import src.api.routes.pipeline_config_routes as mod
    monkeypatch.setattr(mod, "_PRESETS_FILE", presets_file)
    return presets_file


@pytest.fixture
def tmp_prompts(tmp_path, monkeypatch):
    """Create a temporary prompts file and monkeypatch the path."""
    prompts_data = {
        "_config": {"default_router": "openrouter", "comment": "Test prompts"},
        "architect": {
            "system": "You are a task architect. Output ONLY valid JSON.",
            "temperature": 0.1,
            "model": "anthropic/claude-sonnet-4",
            "model_fallback": "meta-llama/llama-3.1-8b-instruct:free",
        },
        "coder": {
            "system": "You are a coder in an autonomous pipeline.",
            "temperature": 0.4,
            "model": "anthropic/claude-sonnet-4",
            "model_fallback": "meta-llama/llama-3.1-8b-instruct:free",
        },
        "verifier": {
            "system": "You verify code output.",
            "temperature": 0.1,
            "model": "anthropic/claude-sonnet-4",
            "model_fallback": "meta-llama/llama-3.1-8b-instruct:free",
        },
    }
    prompts_file = tmp_path / "pipeline_prompts.json"
    with open(prompts_file, "w") as f:
        json.dump(prompts_data, f)

    import src.api.routes.pipeline_config_routes as mod
    monkeypatch.setattr(mod, "_PROMPTS_FILE", prompts_file)
    return prompts_file


# ============================================================
# JSON Helpers
# ============================================================


class TestJsonHelpers:
    def test_load_json_existing_file(self, tmp_path):
        p = tmp_path / "test.json"
        p.write_text('{"key": "value"}')
        assert _load_json(p) == {"key": "value"}

    def test_load_json_missing_file(self, tmp_path):
        p = tmp_path / "nonexistent.json"
        assert _load_json(p) == {}

    def test_save_json_creates_file(self, tmp_path):
        p = tmp_path / "out.json"
        _save_json(p, {"hello": "world"})
        assert p.exists()
        data = json.loads(p.read_text())
        assert data == {"hello": "world"}

    def test_save_json_creates_dirs(self, tmp_path):
        p = tmp_path / "sub" / "dir" / "file.json"
        _save_json(p, {"nested": True})
        assert p.exists()


# ============================================================
# Presets API (unit-level via direct function calls)
# ============================================================


class TestPresetsAPI:
    @pytest.mark.asyncio
    async def test_get_presets(self, tmp_presets):
        from src.api.routes.pipeline_config_routes import get_presets
        result = await get_presets()
        assert result["success"] is True
        assert "dragon_bronze" in result["presets"]
        assert "dragon_silver" in result["presets"]
        assert result["default_preset"] == "dragon_silver"

    @pytest.mark.asyncio
    async def test_get_single_preset(self, tmp_presets):
        from src.api.routes.pipeline_config_routes import get_preset
        result = await get_preset("dragon_bronze")
        assert result["success"] is True
        assert result["preset"]["roles"]["coder"] == "qwen/qwen3-coder-flash"

    @pytest.mark.asyncio
    async def test_get_nonexistent_preset(self, tmp_presets):
        from src.api.routes.pipeline_config_routes import get_preset
        with pytest.raises(Exception):  # HTTPException
            await get_preset("nonexistent")

    @pytest.mark.asyncio
    async def test_update_role_model(self, tmp_presets):
        from src.api.routes.pipeline_config_routes import update_preset_role, UpdateRoleModel

        req = UpdateRoleModel(
            preset_name="dragon_silver",
            role="coder",
            model="deepseek/deepseek-v3.2",
        )
        result = await update_preset_role(req)
        assert result["success"] is True
        assert result["old_model"] == "qwen/qwen3-coder"
        assert result["new_model"] == "deepseek/deepseek-v3.2"

        # Verify persistence
        data = json.loads(tmp_presets.read_text())
        assert data["presets"]["dragon_silver"]["roles"]["coder"] == "deepseek/deepseek-v3.2"

    @pytest.mark.asyncio
    async def test_update_role_invalid_role(self, tmp_presets):
        from src.api.routes.pipeline_config_routes import update_preset_role, UpdateRoleModel

        req = UpdateRoleModel(
            preset_name="dragon_silver",
            role="invalid_role",
            model="test",
        )
        with pytest.raises(Exception):  # HTTPException
            await update_preset_role(req)

    @pytest.mark.asyncio
    async def test_set_default_preset(self, tmp_presets):
        from src.api.routes.pipeline_config_routes import set_default_preset, SetDefaultPreset

        req = SetDefaultPreset(preset_name="dragon_bronze")
        result = await set_default_preset(req)
        assert result["success"] is True
        assert result["default_preset"] == "dragon_bronze"

        data = json.loads(tmp_presets.read_text())
        assert data["default_preset"] == "dragon_bronze"

    @pytest.mark.asyncio
    async def test_set_default_preset_nonexistent(self, tmp_presets):
        from src.api.routes.pipeline_config_routes import set_default_preset, SetDefaultPreset

        req = SetDefaultPreset(preset_name="nonexistent_preset")
        with pytest.raises(Exception):  # HTTPException
            await set_default_preset(req)


# ============================================================
# Prompts API
# ============================================================


class TestPromptsAPI:
    @pytest.mark.asyncio
    async def test_get_prompts(self, tmp_prompts):
        from src.api.routes.pipeline_config_routes import get_prompts
        result = await get_prompts()
        assert result["success"] is True
        assert "architect" in result["prompts"]
        assert "coder" in result["prompts"]
        assert "verifier" in result["prompts"]
        assert result["prompts"]["architect"]["temperature"] == 0.1

    @pytest.mark.asyncio
    async def test_get_single_prompt(self, tmp_prompts):
        from src.api.routes.pipeline_config_routes import get_prompt
        result = await get_prompt("coder")
        assert result["success"] is True
        assert "pipeline" in result["prompt"]["system"]

    @pytest.mark.asyncio
    async def test_get_prompt_nonexistent(self, tmp_prompts):
        from src.api.routes.pipeline_config_routes import get_prompt
        with pytest.raises(Exception):  # HTTPException
            await get_prompt("nonexistent_role")

    @pytest.mark.asyncio
    async def test_get_prompt_config_excluded(self, tmp_prompts):
        """_config key should not be treated as a role."""
        from src.api.routes.pipeline_config_routes import get_prompt
        with pytest.raises(Exception):
            await get_prompt("_config")

    @pytest.mark.asyncio
    async def test_update_prompt_system(self, tmp_prompts):
        from src.api.routes.pipeline_config_routes import update_prompt, UpdatePrompt

        req = UpdatePrompt(role="architect", system="New system prompt.")
        result = await update_prompt(req)
        assert result["success"] is True
        assert result["updated"]["system"] is True

        data = json.loads(tmp_prompts.read_text())
        assert data["architect"]["system"] == "New system prompt."

    @pytest.mark.asyncio
    async def test_update_prompt_temperature(self, tmp_prompts):
        from src.api.routes.pipeline_config_routes import update_prompt, UpdatePrompt

        req = UpdatePrompt(role="coder", temperature=0.7)
        result = await update_prompt(req)
        assert result["success"] is True
        assert result["updated"]["temperature"] == 0.7

        data = json.loads(tmp_prompts.read_text())
        assert data["coder"]["temperature"] == 0.7

    @pytest.mark.asyncio
    async def test_update_prompt_both(self, tmp_prompts):
        from src.api.routes.pipeline_config_routes import update_prompt, UpdatePrompt

        req = UpdatePrompt(role="verifier", system="Updated verifier.", temperature=0.2)
        result = await update_prompt(req)
        assert result["success"] is True
        assert "system" in result["updated"]
        assert "temperature" in result["updated"]

    @pytest.mark.asyncio
    async def test_update_prompt_nonexistent_role(self, tmp_prompts):
        from src.api.routes.pipeline_config_routes import update_prompt, UpdatePrompt

        req = UpdatePrompt(role="nonexistent", system="test")
        with pytest.raises(Exception):
            await update_prompt(req)


# ============================================================
# Data integrity tests
# ============================================================


class TestDataIntegrity:
    def test_real_presets_file_parseable(self):
        """Ensure the actual presets file can be loaded."""
        if _PRESETS_FILE.exists():
            data = _load_json(_PRESETS_FILE)
            assert "presets" in data
            assert "default_preset" in data

    def test_real_prompts_file_parseable(self):
        """Ensure the actual prompts file can be loaded."""
        if _PROMPTS_FILE.exists():
            data = _load_json(_PROMPTS_FILE)
            assert "architect" in data
            assert "coder" in data

    def test_all_presets_have_five_roles(self):
        """Every preset should have all 5 roles defined."""
        if not _PRESETS_FILE.exists():
            pytest.skip("presets file not found")
        data = _load_json(_PRESETS_FILE)
        required_roles = {"architect", "researcher", "coder", "verifier", "scout"}
        for name, preset in data.get("presets", {}).items():
            roles = preset.get("roles", preset)
            for role in required_roles:
                assert role in roles, f"Preset '{name}' missing role '{role}'"
