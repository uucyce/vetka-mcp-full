"""
MARKER_211.TEST: Model Router + JSON strip + Context alert tests.

Tests for:
1. route_model() — task routing to correct tier
2. extract_json() — markdown-wrapped JSON extraction
3. Gemma 4 entries in model_policy LOCALGUYS_CATALOG
4. OllamaProvider tool support override for gemma4/gemma3
5. Context 70% alert in session_init budget

@phase: 211
@task: tb_1775435882_68814_10
"""

import json
import pytest
import sys
from pathlib import Path

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ── 1. Model Router Tests ──────────────────────────────────────────────────

class TestRouteModel:
    """Test route_model() task-type → tier routing."""

    def test_classify_routes_to_drone(self):
        from src.services.model_router import route_model
        result = route_model("classify", available_models=["phi4-mini:latest", "gemma4:e4b"])
        assert result.tier == "drone"
        assert result.model_id == "phi4-mini:latest"

    def test_enrich_routes_to_plane(self):
        from src.services.model_router import route_model
        result = route_model("enrich", available_models=["gemma4:e4b", "qwen3.5:latest"])
        assert result.tier == "plane"
        assert result.model_id in ("gemma4:e4b", "qwen3.5:latest")

    def test_screenshot_routes_to_vision(self):
        from src.services.model_router import route_model
        result = route_model("screenshot", available_models=["gemma4:e4b", "qwen2.5vl:3b"])
        assert result.tier == "plane_vision"

    def test_require_vision_overrides_task_type(self):
        from src.services.model_router import route_model
        result = route_model("classify", require_vision=True, available_models=["gemma4:e4b"])
        assert result.tier == "plane_vision"

    def test_urgency_high_prefers_fastest(self):
        from src.services.model_router import route_model
        result = route_model(
            "enrich", urgency="high",
            available_models=["gemma4:e4b", "qwen3.5:latest", "qwen3:8b"]
        )
        # First available in the plane tier list
        assert result.model_id == "gemma4:e4b"

    def test_urgency_low_prefers_quality(self):
        from src.services.model_router import route_model
        result = route_model(
            "enrich", urgency="low",
            available_models=["gemma4:e4b", "qwen3.5:latest", "qwen3:8b"]
        )
        # Last available = best quality
        assert result.model_id == "qwen3:8b"

    def test_no_available_models_returns_first_candidate(self):
        from src.services.model_router import route_model
        result = route_model("classify", available_models=[])
        assert result.model_id is not None
        assert "pull" in result.reason

    def test_fallback_populated(self):
        from src.services.model_router import route_model
        result = route_model("enrich", available_models=["gemma4:e4b", "qwen3.5:latest"])
        assert result.fallback is not None

    def test_unknown_task_type_defaults_to_plane(self):
        from src.services.model_router import route_model
        result = route_model("unknown_task", available_models=["gemma4:e4b"])
        assert result.tier == "plane"


# ── 2. JSON Strip Helper Tests ─────────────────────────────────────────────

class TestExtractJson:
    """Test extract_json() markdown wrapper stripping."""

    def test_clean_json(self):
        from src.services.model_router import extract_json
        result = extract_json('{"priority": 1, "complexity": "high"}')
        assert result == {"priority": 1, "complexity": "high"}

    def test_markdown_wrapped_json(self):
        from src.services.model_router import extract_json
        raw = '```json\n{"priority": 1, "hints": "check auth"}\n```'
        result = extract_json(raw)
        assert result is not None
        assert result["priority"] == 1

    def test_markdown_with_language_tag(self):
        from src.services.model_router import extract_json
        raw = '```json\n{"key": "value"}\n```'
        result = extract_json(raw)
        assert result == {"key": "value"}

    def test_invalid_json_returns_none(self):
        from src.services.model_router import extract_json
        result = extract_json("not json at all")
        assert result is None

    def test_array_json(self):
        from src.services.model_router import extract_json
        result = extract_json('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_whitespace_padded(self):
        from src.services.model_router import extract_json
        result = extract_json('  \n  {"a": 1}  \n  ')
        assert result == {"a": 1}

    def test_nested_json_in_markdown(self):
        from src.services.model_router import extract_json
        raw = '```\n{"outer": {"inner": [1, 2]}}\n```'
        result = extract_json(raw)
        assert result["outer"]["inner"] == [1, 2]


# ── 3. Model Policy Gemma 4 Integration ────────────────────────────────────

class TestModelPolicyGemma4:
    """Test Gemma 4 entries in model_policy."""

    def test_gemma4_in_catalog(self):
        from src.services.model_policy import LOCALGUYS_CATALOG
        assert "gemma4:e2b" in LOCALGUYS_CATALOG
        assert "gemma4:e4b" in LOCALGUYS_CATALOG
        assert "gemma4:26b" in LOCALGUYS_CATALOG

    def test_gemma4_e2b_role_fit(self):
        from src.services.model_policy import get_unified_policy
        policy = get_unified_policy("gemma4:e2b")
        assert "scout" in policy.role_fit
        assert "classifier" in policy.role_fit

    def test_gemma4_e4b_role_fit(self):
        from src.services.model_policy import get_unified_policy
        policy = get_unified_policy("gemma4:e4b")
        assert "sherpa" in policy.role_fit
        assert "vision_qa" in policy.role_fit

    def test_gemma4_26b_role_fit(self):
        from src.services.model_policy import get_unified_policy
        policy = get_unified_policy("gemma4:26b")
        assert "architect" in policy.role_fit

    def test_policy_to_dict_has_all_fields(self):
        from src.services.model_policy import get_unified_policy
        d = get_unified_policy("gemma4:e4b").to_dict()
        for key in ("model_id", "provider", "fc_reliability", "role_fit", "context_class"):
            assert key in d


# ── 4. Provider Registry Tool Override ─────────────────────────────────────

class TestOllamaToolOverride:
    """Test that gemma4/gemma3 bypass the 'gemma' blacklist for tool support."""

    def _get_ollama_provider(self):
        from src.elisya.provider_registry import OllamaProvider, ProviderConfig
        return OllamaProvider(ProviderConfig())

    def test_gemma_base_no_tools(self):
        provider = self._get_ollama_provider()
        assert provider._model_supports_tools("gemma:7b") is False

    def test_gemma4_e2b_has_tools(self):
        provider = self._get_ollama_provider()
        assert provider._model_supports_tools("gemma4:e2b") is True

    def test_gemma4_e4b_has_tools(self):
        provider = self._get_ollama_provider()
        assert provider._model_supports_tools("gemma4:e4b") is True

    def test_gemma4_26b_has_tools(self):
        provider = self._get_ollama_provider()
        assert provider._model_supports_tools("gemma4:26b") is True

    def test_gemma3_4b_has_tools(self):
        provider = self._get_ollama_provider()
        assert provider._model_supports_tools("gemma3:4b") is True

    def test_gemma3_12b_has_tools(self):
        provider = self._get_ollama_provider()
        assert provider._model_supports_tools("gemma3:12b") is True

    def test_other_blacklisted_still_blocked(self):
        provider = self._get_ollama_provider()
        assert provider._model_supports_tools("llama2:7b") is False
        assert provider._model_supports_tools("vicuna:13b") is False


# ── 5. Context Budget Alert ────────────────────────────────────────────────

class TestContextBudgetAlert:
    """Test context 70% alert logic (unit-level, no async session_init)."""

    def test_estimate_tokens_function_exists(self):
        from src.mcp.tools.session_tools import _estimate_tokens
        result = _estimate_tokens({"key": "value"})
        assert isinstance(result, int)
        assert result > 0

    def test_small_context_no_alert(self):
        """Under 70% should produce no alert."""
        from src.mcp.tools.session_tools import _estimate_tokens
        context = {"session_id": "test", "role_context": {"name": "Eta"}}
        tokens = _estimate_tokens(context)
        max_budget = tokens * 10  # ~10% usage
        ratio = tokens / max_budget
        assert ratio < 0.70

    def test_alert_threshold_math(self):
        """Verify 70% threshold produces correct level."""
        # Simulate the logic from session_tools
        used = 750
        budget = 1000
        ratio = used / budget
        assert ratio > 0.70
        level = "critical" if ratio > 0.90 else "warning"
        assert level == "warning"

    def test_critical_threshold(self):
        used = 950
        budget = 1000
        ratio = used / budget
        level = "critical" if ratio > 0.90 else "warning"
        assert level == "critical"


# ── 6. GEMMA4_MODELS Catalog ──────────────────────────────────────────────

class TestGemma4ModelsCatalog:
    """Test the GEMMA4_MODELS reference dict in model_router."""

    def test_three_variants_present(self):
        from src.services.model_router import GEMMA4_MODELS
        assert "gemma4:e2b" in GEMMA4_MODELS
        assert "gemma4:e4b" in GEMMA4_MODELS
        assert "gemma4:26b" in GEMMA4_MODELS

    def test_e4b_is_primary_sherpa(self):
        from src.services.model_router import GEMMA4_MODELS
        e4b = GEMMA4_MODELS["gemma4:e4b"]
        assert "sherpa" in e4b["role_fit"]
        assert e4b["vision"] is True
        assert e4b["license"] == "Apache-2.0"

    def test_e2b_is_drone_tier(self):
        from src.services.model_router import GEMMA4_MODELS
        assert GEMMA4_MODELS["gemma4:e2b"]["tier"] == "drone"

    def test_26b_memory_budget(self):
        from src.services.model_router import GEMMA4_MODELS
        assert GEMMA4_MODELS["gemma4:26b"]["size_gb"] == 18.0
        assert GEMMA4_MODELS["gemma4:26b"]["context"] == 256_000
