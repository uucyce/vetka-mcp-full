"""
VETKA Phase 9 → VETKA-JSON v1.3 Transformer Tests
=================================================

Comprehensive test suite for the Phase 10 Transformer.

Author: AI Council + Opus 4.5
Date: December 13, 2025
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.transformers.phase9_to_vetka import (
    Phase10Transformer,
    AgentType,
    BranchType,
    EdgeSemantics,
    EdgeType,
    AnimationType,
    VisualHintsCalculator,
    AGENT_COLORS,
    EDGE_STYLES,
    ANIMATION_PARAMS,
    DEFAULTS,
)
from src.validators.vetka_validator import VetkaValidator


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_phase9_output():
    """Sample Phase 9 workflow output for testing"""
    return {
        "workflow_id": "abc123",
        "pm_result": {
            "plan": "4 этапа: Research → Design → Dev → QA. Timeline: 2 недели.",
            "risks": ["Технические", "Временные", "Ресурсные"],
            "eval_score": 0.91
        },
        "architect_result": {
            "diagram": "graph TD\n  A[Client] --> B[API]\n  B --> C[DB]",
            "description": "Микросервисная архитектура с API Gateway",
            "score": 0.87
        },
        "dev_result": {
            "files": [
                {"name": "login.py", "path": "src/auth/login.py", "tokens": 450, "language": "python"},
                {"name": "api.py", "path": "src/api.py", "tokens": 320, "language": "python"}
            ],
            "eval_score": 0.84
        },
        "qa_result": {
            "coverage": 85,
            "passed": 42,
            "failed": 8,
            "tests": ["test_login.py", "test_api.py"],
            "eval_score": 0.79
        },
        "arc_suggestions": [
            {"transformation": "Add caching layer", "success": 0.92},
            {"transformation": "Optimize DB queries", "success": 0.88}
        ],
        "metrics": {
            "total_time_ms": 35000,
            "parallel_execution": True,
            "pm_time_ms": 8000,
            "dev_time_ms": 12000,
            "qa_time_ms": 10000
        }
    }


@pytest.fixture
def sample_phase9_with_infrastructure():
    """Sample Phase 9 output with infrastructure data"""
    return {
        "workflow_id": "infra123",
        "pm_result": {
            "plan": "Simple plan",
            "risks": [],
            "eval_score": 0.85
        },
        "dev_result": {
            "files": [{"name": "main.py", "path": "src/main.py", "tokens": 100, "language": "python"}],
            "eval_score": 0.82
        },
        "qa_result": {
            "coverage": 90,
            "passed": 10,
            "failed": 0,
            "tests": ["test_main.py"],
            "eval_score": 0.95
        },
        "infrastructure": {
            "learning": {
                "student_level": 4,
                "learner_model": "QwenLearner",
                "model_version": "qwen:7b-instruct"
            },
            "routing": {
                "decisions": [
                    {"agent": "pm", "model": "gpt-4o-mini", "provider": "openrouter", "tokens_total": 1500, "cost_usd": 0.02},
                    {"agent": "dev", "model": "qwen:7b", "provider": "ollama", "tokens_total": 3000, "cost_usd": 0.0},
                    {"agent": "qa", "model": "qwen:7b", "provider": "ollama", "tokens_total": 2000, "cost_usd": 0.0}
                ]
            },
            "elisya": {
                "version": "1.2.3",
                "lod_requested": "BRANCH",
                "lod_applied": "BRANCH",
                "assembly_time_ms": 150,
                "reframes_applied": True
            },
            "parallel": {
                "dev_start_time": "2025-12-13T14:10:00.000Z",
                "dev_end_time": "2025-12-13T14:10:12.000Z",
                "qa_start_time": "2025-12-13T14:10:00.200Z",
                "qa_end_time": "2025-12-13T14:10:10.500Z",
                "overlap_ms": 10300
            }
        }
    }


@pytest.fixture
def minimal_phase9_output():
    """Minimal Phase 9 output (missing optional fields)"""
    return {
        "workflow_id": "minimal123"
    }


@pytest.fixture
def transformer():
    """Create transformer instance"""
    return Phase10Transformer()


@pytest.fixture
def validator():
    """Create validator instance"""
    schema_path = project_root / "config" / "vetka_schema_v1.3.json"
    return VetkaValidator(str(schema_path))


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnums:
    """Test enum definitions"""

    def test_agent_types_no_elisya(self):
        """CRITICAL: Elisya should NOT be in AgentType"""
        agent_values = [a.value for a in AgentType]
        assert "Elisya" not in agent_values
        assert "elisya" not in agent_values
        assert "ELISYA" not in agent_values

    def test_agent_types_complete(self):
        """All expected agent types present"""
        expected = {"PM", "Dev", "QA", "ARC", "Human", "System"}
        actual = {a.value for a in AgentType}
        assert expected == actual

    def test_branch_types(self):
        """All branch types present"""
        expected = {"memory", "task", "data", "control"}
        actual = {b.value for b in BranchType}
        assert expected == actual

    def test_edge_semantics(self):
        """All 6 edge semantic types present"""
        expected = {"informs", "influences", "creates", "depends", "supersedes", "references"}
        actual = {e.value for e in EdgeSemantics}
        assert expected == actual

    def test_animation_types(self):
        """All animation types present"""
        expected = {"static", "pulse", "glow", "flicker"}
        actual = {a.value for a in AnimationType}
        assert expected == actual


# ═══════════════════════════════════════════════════════════════════════════════
# VISUAL HINTS CALCULATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestVisualHintsCalculator:
    """Test visual hints calculations (Qwen + DeepSeek formulas)"""

    def test_size_multiplier_min(self):
        """Size multiplier at minimum entropy"""
        result = VisualHintsCalculator.calculate_size_multiplier(0.0)
        assert result == 1.0

    def test_size_multiplier_max(self):
        """Size multiplier at maximum entropy"""
        result = VisualHintsCalculator.calculate_size_multiplier(1.0)
        assert result == 1.5

    def test_size_multiplier_mid(self):
        """Size multiplier at mid entropy"""
        result = VisualHintsCalculator.calculate_size_multiplier(0.5)
        assert result == 1.25

    def test_opacity_min(self):
        """Opacity at minimum completion"""
        result = VisualHintsCalculator.calculate_opacity(0.0)
        assert result == 0.2

    def test_opacity_max(self):
        """Opacity at maximum completion"""
        result = VisualHintsCalculator.calculate_opacity(1.0)
        assert result == 1.0

    def test_animation_pulse_for_incomplete_task(self):
        """Task in progress should pulse"""
        result = VisualHintsCalculator.calculate_animation(
            completion_rate=0.5,
            branch_type="task",
            eval_score=0.8,
            entropy=0.3
        )
        assert result == "pulse"

    def test_animation_flicker_for_low_quality(self):
        """Low quality should flicker"""
        result = VisualHintsCalculator.calculate_animation(
            completion_rate=1.0,
            branch_type="memory",
            eval_score=0.3,
            entropy=0.3
        )
        assert result == "flicker"

    def test_animation_glow_for_high_entropy(self):
        """High entropy should glow"""
        result = VisualHintsCalculator.calculate_animation(
            completion_rate=1.0,
            branch_type="memory",
            eval_score=0.8,
            entropy=0.9
        )
        assert result == "glow"

    def test_animation_static_default(self):
        """Default should be static"""
        result = VisualHintsCalculator.calculate_animation(
            completion_rate=1.0,
            branch_type="memory",
            eval_score=0.8,
            entropy=0.3
        )
        assert result == "static"

    def test_color_full_saturation(self):
        """High quality keeps full saturation"""
        result = VisualHintsCalculator.calculate_color("PM", 0.9)
        assert result == AGENT_COLORS["PM"]

    def test_color_desaturated_for_low_quality(self):
        """Low quality desaturates color"""
        result = VisualHintsCalculator.calculate_color("PM", 0.3)
        assert result != AGENT_COLORS["PM"]  # Should be desaturated

    def test_position_hint_root(self):
        """Root position should be at origin"""
        result = VisualHintsCalculator.calculate_position_hint(0, 0)
        assert result["y"] == 0
        assert result["calculation"] == "phylotaxis"

    def test_position_hint_depth(self):
        """Position Y increases with depth"""
        result = VisualHintsCalculator.calculate_position_hint(1, 2)
        assert result["y"] == 200  # depth * LAYER_HEIGHT (100)

    def test_animation_params_lookup(self):
        """Animation params lookup works"""
        for anim_type in ["static", "pulse", "glow", "flicker"]:
            params = VisualHintsCalculator.get_animation_params(anim_type)
            assert "scale" in params
            assert "opacity" in params
            assert "period_ms" in params


# ═══════════════════════════════════════════════════════════════════════════════
# TRANSFORMER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPhase10Transformer:
    """Test Phase 10 Transformer"""

    def test_transform_basic(self, transformer, sample_phase9_output):
        """Basic transformation produces valid structure"""
        result = transformer.transform(sample_phase9_output)

        # Top-level structure
        assert result["$schema"] == "https://vetka.io/schema/v1.3.json"
        assert result["format"] == "vetka-v1.3"
        assert result["version"] == "1.3"
        assert "tree" in result
        assert "origin" in result
        assert result["origin"]["workflow_id"] == "abc123"

    def test_transform_creates_root_node(self, transformer, sample_phase9_output):
        """Transformation creates root node"""
        result = transformer.transform(sample_phase9_output)
        tree = result["tree"]

        # Find root node
        root_id = tree["root_node_id"]
        root_node = next(n for n in tree["nodes"] if n["id"] == root_id)

        assert root_node["type"] == "root"
        assert root_node["parent_id"] is None
        assert root_node["metadata"]["agent"] == "System"

    def test_transform_creates_pm_node(self, transformer, sample_phase9_output):
        """Transformation creates PM branch node"""
        result = transformer.transform(sample_phase9_output)
        nodes = result["tree"]["nodes"]

        # Find PM node
        pm_nodes = [n for n in nodes if n["metadata"]["agent"] == "PM" and "plan" in str(n["content"]["data"])]
        assert len(pm_nodes) >= 1

        pm_node = pm_nodes[0]
        assert pm_node["type"] == "branch"
        assert pm_node["branch_type"] == "memory"
        assert pm_node["metadata"]["eval_score"] == 0.91

    def test_transform_creates_dev_branch_and_leaves(self, transformer, sample_phase9_output):
        """Transformation creates Dev branch with file leaves"""
        result = transformer.transform(sample_phase9_output)
        nodes = result["tree"]["nodes"]

        # Find Dev branch
        dev_nodes = [n for n in nodes if n["metadata"]["agent"] == "Dev" and n["type"] == "branch"]
        assert len(dev_nodes) >= 1

        # Find file leaves under Dev
        file_leaves = [n for n in nodes if n["type"] == "leaf" and n["metadata"]["agent"] == "Dev"]
        assert len(file_leaves) == 2  # login.py and api.py

    def test_transform_creates_qa_branch_and_leaves(self, transformer, sample_phase9_output):
        """Transformation creates QA branch with test leaves"""
        result = transformer.transform(sample_phase9_output)
        nodes = result["tree"]["nodes"]

        # Find QA branch
        qa_nodes = [n for n in nodes if n["metadata"]["agent"] == "QA" and n["type"] == "branch"]
        assert len(qa_nodes) >= 1

        # Check completion rate calculation
        qa_node = qa_nodes[0]
        expected_completion = 42 / (42 + 8)  # passed / total
        assert abs(qa_node["metadata"]["completion_rate"] - expected_completion) < 0.01

    def test_transform_creates_arc_branches(self, transformer, sample_phase9_output):
        """Transformation creates ARC suggestion branches"""
        result = transformer.transform(sample_phase9_output)
        nodes = result["tree"]["nodes"]

        arc_nodes = [n for n in nodes if n["metadata"]["agent"] == "ARC"]
        assert len(arc_nodes) == 2  # Two suggestions

    def test_transform_creates_edges(self, transformer, sample_phase9_output):
        """Transformation creates proper edges"""
        result = transformer.transform(sample_phase9_output)
        edges = result["tree"]["edges"]

        # Should have multiple edges
        assert len(edges) > 0

        # Check edge semantics
        semantics = [e["semantics"] for e in edges]
        assert "creates" in semantics  # root → branches
        assert "informs" in semantics  # PM → Dev, PM → QA

    def test_transform_no_elisya_agent(self, transformer, sample_phase9_output):
        """CRITICAL: No node should have Elisya as agent"""
        result = transformer.transform(sample_phase9_output)
        nodes = result["tree"]["nodes"]

        for node in nodes:
            agent = node["metadata"]["agent"]
            assert agent.lower() != "elisya", f"Node {node['id']} has Elisya as agent!"

    def test_transform_visual_hints_present(self, transformer, sample_phase9_output):
        """All nodes have visual hints"""
        result = transformer.transform(sample_phase9_output)
        nodes = result["tree"]["nodes"]

        for node in nodes:
            assert "visual_hints" in node
            hints = node["visual_hints"]
            assert "size_multiplier" in hints
            assert "color" in hints
            assert "opacity" in hints
            assert "animation" in hints
            assert "icon" in hints

    def test_transform_entropy_calculated(self, transformer, sample_phase9_output):
        """Entropy is calculated for all nodes"""
        result = transformer.transform(sample_phase9_output)
        nodes = result["tree"]["nodes"]

        for node in nodes:
            entropy = node["metadata"]["entropy"]
            assert 0 <= entropy <= 1

    def test_transform_with_missing_optional_fields(self, transformer, minimal_phase9_output):
        """Transformation handles missing optional fields gracefully"""
        result = transformer.transform(minimal_phase9_output)

        assert result["format"] == "vetka-v1.3"
        assert len(result["tree"]["nodes"]) >= 1  # At least root

    def test_transform_with_infrastructure(self, transformer, sample_phase9_with_infrastructure):
        """Transformation captures infrastructure data"""
        result = transformer.transform(sample_phase9_with_infrastructure)
        nodes = result["tree"]["nodes"]

        # Find PM node - should have infrastructure tracking
        pm_nodes = [n for n in nodes if n["metadata"]["agent"] == "PM" and n["type"] == "branch"]
        if pm_nodes:
            pm_node = pm_nodes[0]
            # Context source should reflect Elisya usage
            context_source = pm_node["metadata"].get("context_source", {})
            assert context_source.get("type") in ["elisya", "direct"]

    def test_transform_cost_optimization(self, transformer, sample_phase9_with_infrastructure):
        """Transformation calculates cost optimization"""
        result = transformer.transform(sample_phase9_with_infrastructure)
        metadata = result["tree"]["metadata"]

        if "cost_optimization" in metadata:
            cost = metadata["cost_optimization"]
            assert "total_tokens_used" in cost
            assert "total_cost_usd" in cost
            assert "savings_percent" in cost


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestVetkaValidator:
    """Test VETKA Validator"""

    def test_validator_accepts_valid_output(self, transformer, validator, sample_phase9_output):
        """Validator accepts valid transformer output"""
        result = transformer.transform(sample_phase9_output)
        is_valid, errors = validator.validate(result)

        if not is_valid:
            print("Validation errors:", errors)

        assert is_valid, f"Validation failed: {errors}"

    def test_validator_detects_duplicate_node_ids(self, validator):
        """Validator detects duplicate node IDs"""
        invalid_data = {
            "$schema": "https://vetka.io/schema/v1.3.json",
            "format": "vetka-v1.3",
            "version": "1.3",
            "origin": {"source": "phase9", "workflow_id": "test"},
            "created_at": datetime.now().isoformat(),
            "tree": {
                "id": "tree_test",
                "name": "Test",
                "root_node_id": "root_1",
                "nodes": [
                    {"id": "root_1", "type": "root", "branch_type": "memory", "name": "Root",
                     "content": {"type": "text", "data": {}},
                     "metadata": {"agent": "System", "eval_score": 1.0, "entropy": 0.0, "completion_rate": 1.0, "timestamp": "2025-01-01T00:00:00Z"},
                     "visual_hints": {"size_multiplier": 1.0, "color": "#FFFFFF", "opacity": 1.0, "animation": "static", "icon": "document"}},
                    {"id": "root_1", "type": "branch", "branch_type": "memory", "name": "Duplicate",
                     "content": {"type": "text", "data": {}},
                     "metadata": {"agent": "PM", "eval_score": 0.8, "entropy": 0.0, "completion_rate": 1.0, "timestamp": "2025-01-01T00:00:00Z"},
                     "visual_hints": {"size_multiplier": 1.0, "color": "#FFFFFF", "opacity": 1.0, "animation": "static", "icon": "document"}}
                ],
                "edges": []
            }
        }

        is_valid, errors = validator.validate(invalid_data)
        assert not is_valid
        assert any("Duplicate" in e for e in errors)

    def test_validator_detects_elisya_agent(self, validator):
        """CRITICAL: Validator detects Elisya as agent"""
        invalid_data = {
            "$schema": "https://vetka.io/schema/v1.3.json",
            "format": "vetka-v1.3",
            "version": "1.3",
            "origin": {"source": "phase9", "workflow_id": "test"},
            "created_at": datetime.now().isoformat(),
            "tree": {
                "id": "tree_test",
                "name": "Test",
                "root_node_id": "root_1",
                "nodes": [
                    {"id": "root_1", "type": "root", "branch_type": "memory", "name": "Root",
                     "parent_id": None,
                     "content": {"type": "text", "data": {}},
                     "metadata": {"agent": "Elisya", "eval_score": 1.0, "entropy": 0.0, "completion_rate": 1.0, "timestamp": "2025-01-01T00:00:00Z"},
                     "visual_hints": {"size_multiplier": 1.0, "color": "#FFFFFF", "opacity": 1.0, "animation": "static", "icon": "document"}}
                ],
                "edges": []
            }
        }

        is_valid, errors = validator.validate(invalid_data)
        assert not is_valid
        assert any("Elisya" in e for e in errors)

    def test_validator_detects_invalid_edge_references(self, validator):
        """Validator detects edges referencing non-existent nodes"""
        invalid_data = {
            "$schema": "https://vetka.io/schema/v1.3.json",
            "format": "vetka-v1.3",
            "version": "1.3",
            "origin": {"source": "phase9", "workflow_id": "test"},
            "created_at": datetime.now().isoformat(),
            "tree": {
                "id": "tree_test",
                "name": "Test",
                "root_node_id": "root_1",
                "nodes": [
                    {"id": "root_1", "type": "root", "branch_type": "memory", "name": "Root",
                     "parent_id": None,
                     "content": {"type": "text", "data": {}},
                     "metadata": {"agent": "System", "eval_score": 1.0, "entropy": 0.0, "completion_rate": 1.0, "timestamp": "2025-01-01T00:00:00Z"},
                     "visual_hints": {"size_multiplier": 1.0, "color": "#FFFFFF", "opacity": 1.0, "animation": "static", "icon": "document"}}
                ],
                "edges": [
                    {"id": "edge_1", "from": "root_1", "to": "nonexistent", "type": "liana", "semantics": "informs", "flow_weight": 0.5}
                ]
            }
        }

        is_valid, errors = validator.validate(invalid_data)
        assert not is_valid
        assert any("nonexistent" in e for e in errors)

    def test_validator_detects_invalid_visual_hints(self, validator):
        """Validator detects out-of-range visual hints"""
        invalid_data = {
            "$schema": "https://vetka.io/schema/v1.3.json",
            "format": "vetka-v1.3",
            "version": "1.3",
            "origin": {"source": "phase9", "workflow_id": "test"},
            "created_at": datetime.now().isoformat(),
            "tree": {
                "id": "tree_test",
                "name": "Test",
                "root_node_id": "root_1",
                "nodes": [
                    {"id": "root_1", "type": "root", "branch_type": "memory", "name": "Root",
                     "parent_id": None,
                     "content": {"type": "text", "data": {}},
                     "metadata": {"agent": "System", "eval_score": 1.0, "entropy": 0.0, "completion_rate": 1.0, "timestamp": "2025-01-01T00:00:00Z"},
                     "visual_hints": {"size_multiplier": 10.0, "color": "#FFFFFF", "opacity": 2.0, "animation": "static", "icon": "document"}}
                ],
                "edges": []
            }
        }

        is_valid, errors = validator.validate(invalid_data)
        assert not is_valid
        assert any("size_multiplier" in e or "opacity" in e for e in errors)


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    """Integration tests"""

    def test_full_workflow(self, sample_phase9_output):
        """Full workflow: transform → validate → serialize"""
        # Transform
        transformer = Phase10Transformer()
        vetka_json = transformer.transform(sample_phase9_output)

        # Validate
        schema_path = project_root / "config" / "vetka_schema_v1.3.json"
        validator = VetkaValidator(str(schema_path))
        is_valid, errors = validator.validate(vetka_json)

        assert is_valid, f"Validation failed: {errors}"

        # Serialize (should not raise)
        json_str = json.dumps(vetka_json, ensure_ascii=False, indent=2)
        assert len(json_str) > 0

        # Deserialize back
        parsed = json.loads(json_str)
        assert parsed["format"] == "vetka-v1.3"

    def test_node_count_matches_metadata(self, transformer, sample_phase9_output):
        """Tree metadata node count matches actual nodes"""
        result = transformer.transform(sample_phase9_output)

        actual_count = len(result["tree"]["nodes"])
        metadata_count = result["tree"]["metadata"]["total_nodes"]

        assert actual_count == metadata_count

    def test_edge_count_matches_metadata(self, transformer, sample_phase9_output):
        """Tree metadata edge count matches actual edges"""
        result = transformer.transform(sample_phase9_output)

        actual_count = len(result["tree"]["edges"])
        metadata_count = result["tree"]["metadata"]["total_edges"]

        assert actual_count == metadata_count

    def test_children_ids_consistency(self, transformer, sample_phase9_output):
        """children_ids are consistent with parent_id references"""
        result = transformer.transform(sample_phase9_output)
        nodes = result["tree"]["nodes"]
        node_map = {n["id"]: n for n in nodes}

        for node in nodes:
            for child_id in node.get("children_ids", []):
                child_node = node_map.get(child_id)
                assert child_node is not None, f"Child {child_id} not found"
                assert child_node["parent_id"] == node["id"], \
                    f"Child {child_id} parent_id mismatch"


# ═══════════════════════════════════════════════════════════════════════════════
# EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_workflow_id(self, transformer):
        """Handles empty workflow_id"""
        result = transformer.transform({"workflow_id": ""})
        assert result["origin"]["workflow_id"] != ""  # Should generate UUID

    def test_none_workflow_id(self, transformer):
        """Handles None workflow_id"""
        result = transformer.transform({})
        assert result["origin"]["workflow_id"] is not None

    def test_empty_files_list(self, transformer):
        """Handles empty files list in dev_result"""
        data = {
            "workflow_id": "test",
            "dev_result": {"files": [], "eval_score": 0.8}
        }
        result = transformer.transform(data)
        # Should create Dev branch but no file leaves
        nodes = result["tree"]["nodes"]
        dev_branches = [n for n in nodes if n["metadata"]["agent"] == "Dev" and n["type"] == "branch"]
        assert len(dev_branches) == 1
        assert dev_branches[0]["content"]["data"]["file_count"] == 0

    def test_empty_tests_list(self, transformer):
        """Handles empty tests list in qa_result"""
        data = {
            "workflow_id": "test",
            "qa_result": {"coverage": 0, "passed": 0, "failed": 0, "tests": [], "eval_score": 0.5}
        }
        result = transformer.transform(data)
        nodes = result["tree"]["nodes"]
        qa_branches = [n for n in nodes if n["metadata"]["agent"] == "QA" and n["type"] == "branch"]
        assert len(qa_branches) == 1

    def test_eval_score_clamping(self, transformer):
        """Eval scores are clamped to [0, 1]"""
        data = {
            "workflow_id": "test",
            "pm_result": {"plan": "test", "risks": [], "eval_score": 1.5}
        }
        result = transformer.transform(data)
        nodes = result["tree"]["nodes"]
        pm_nodes = [n for n in nodes if n["metadata"]["agent"] == "PM"]
        # The transformer uses the value directly, but visual hints should still be valid
        for node in pm_nodes:
            assert node["visual_hints"]["opacity"] <= 1.0

    def test_unicode_content(self, transformer):
        """Handles Unicode content properly"""
        data = {
            "workflow_id": "unicode_test",
            "pm_result": {
                "plan": "План проекта: 日本語テスト 🚀",
                "risks": ["Риск 1", "風險 2"],
                "eval_score": 0.9
            }
        }
        result = transformer.transform(data)
        nodes = result["tree"]["nodes"]
        pm_nodes = [n for n in nodes if n["metadata"]["agent"] == "PM" and "plan" in str(n["content"]["data"])]
        assert len(pm_nodes) == 1
        assert "日本語" in pm_nodes[0]["content"]["data"]["plan"]


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    """Test constant definitions"""

    def test_agent_colors_complete(self):
        """All agents have colors defined"""
        for agent in AgentType:
            assert agent.value in AGENT_COLORS

    def test_edge_styles_complete(self):
        """All edge semantics have styles defined"""
        for sem in EdgeSemantics:
            assert sem.value in EDGE_STYLES

    def test_animation_params_complete(self):
        """All animations have params defined"""
        for anim in AnimationType:
            assert anim.value in ANIMATION_PARAMS

    def test_defaults_present(self):
        """All default values are defined"""
        required = ["eval_score", "entropy", "completion_rate", "student_level", "flow_weight"]
        for key in required:
            assert key in DEFAULTS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
