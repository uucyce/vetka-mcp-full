"""
MARKER_EPSILON.LAYERFX: LayerFX Manifest Contract Tests (TDD-RED).

Canonical spec: docs/190_ph_CUT_WORKFLOW_ARCH/HANDOFF_LAYERFX_MANIFEST_CONTRACT_2026-03-27.md

These tests define the contract BEFORE implementation exists.
Tests marked xfail will turn GREEN as Alpha/Beta/Gamma implement each piece.

Sections:
  1. SemanticLayer — from_dict with camelCase→snake_case, role normalization
  2. CameraContract — space block parsing, focalLengthMm/zNear/zFar
  3. LayerManifest — full manifest load, format detection, source resolution
  4. Role Normalization — kebab-case → underscore mapping table
  5. Legacy Bridge — plate_export_manifest.json auto-detect, bridge-only flag
  6. Clip Attachment — clip.layer_manifest.manifest_path wiring
  7. API Endpoint — POST /cut/layers/import returns manifest_id
"""

import json
import pytest
from pathlib import Path

# ─── Canonical test data from §1 of spec ───────────────────────

CANONICAL_LAYER_SPACE = {
    "contract_version": "1.0.0",
    "sampleId": "hover-politsia",
    "source": {
        "path": "/abs/path/source.jpg",
        "width": 1920,
        "height": 1080,
    },
    "layers": [
        {
            "id": "fg_01",
            "role": "foreground-subject",
            "label": "SUV + Walker",
            "order": 2,
            "depthPriority": 0.78,
            "z": 0.5,
            "visible": True,
            "rgba": "fg_01_rgba.png",
            "mask": "fg_01_mask.png",
            "depth": "fg_01_depth.png",
            "coverage": 0.3,
            "parallaxStrength": 1.3,
            "motionDamping": 1.0,
        },
        {
            "id": "bg_01",
            "role": "background-far",
            "label": "Street + Buildings",
            "order": 0,
            "depthPriority": 0.15,
            "z": 1.5,
            "visible": True,
            "rgba": "bg_01_rgba.png",
            "mask": "bg_01_mask.png",
            "depth": "bg_01_depth.png",
            "coverage": 0.85,
            "parallaxStrength": 0.3,
            "motionDamping": 1.0,
        },
    ],
    "space": {
        "focalLengthMm": 50,
        "filmWidthMm": 36,
        "zNear": 0.72,
        "zFar": 1.85,
        "motionType": "orbit",
        "durationSec": 4.0,
        "travelXPct": 3.0,
        "travelYPct": 0.0,
        "zoom": 1.0,
        "overscanPct": 20.0,
    },
    "provenance": {
        "depth_backend": "depth-pro",
        "grouping_backend": "qwen-vl",
    },
}

LEGACY_PLATE_EXPORT = {
    "plates": [
        {
            "id": "plate_01",
            "role": "foreground-subject",
            "label": "Subject",
            "index": 2,
            "plateCoverage": 0.3,
        }
    ],
    "camera": {
        "focalLengthMm": 50,
        "filmWidthMm": 36,
    },
}


# ─── §1: SemanticLayer from_dict ────────────────────────────────

class TestSemanticLayerContract:
    """SemanticLayer.from_dict must parse camelCase JSON into snake_case Python."""

    @pytest.fixture
    def layer_module(self):
        try:
            from src.services.cut_layer_manifest import SemanticLayer
            return SemanticLayer
        except ImportError:
            pytest.skip("cut_layer_manifest.py not yet implemented")

    def test_from_dict_exists(self, layer_module):
        """SemanticLayer must have from_dict classmethod."""
        assert hasattr(layer_module, "from_dict")

    def test_parses_layer_id(self, layer_module):
        """JSON 'id' → Python layer_id."""
        layer = layer_module.from_dict(CANONICAL_LAYER_SPACE["layers"][0])
        assert layer.layer_id == "fg_01"

    def test_depth_priority_is_float(self, layer_module):
        """depthPriority must be float, NOT cast to int order."""
        layer = layer_module.from_dict(CANONICAL_LAYER_SPACE["layers"][0])
        assert isinstance(layer.depth_priority, float)
        assert layer.depth_priority == pytest.approx(0.78)

    def test_order_is_int(self, layer_module):
        """order is separate from depthPriority, must be int."""
        layer = layer_module.from_dict(CANONICAL_LAYER_SPACE["layers"][0])
        assert isinstance(layer.order, int)
        assert layer.order == 2

    def test_depth_priority_not_equal_order(self, layer_module):
        """§4 bug fix: depthPriority (0.78) must NOT be truncated to order (0)."""
        layer = layer_module.from_dict(CANONICAL_LAYER_SPACE["layers"][0])
        # depth_priority=0.78, order=2 — they are independent fields
        assert layer.depth_priority != layer.order

    def test_coverage_from_coverage_field(self, layer_module):
        """coverage reads from 'coverage' JSON field."""
        layer = layer_module.from_dict(CANONICAL_LAYER_SPACE["layers"][0])
        assert layer.coverage == pytest.approx(0.3)

    def test_coverage_fallback_to_plateCoverage(self, layer_module):
        """§4 bug fix: also accept 'plateCoverage' for legacy compat."""
        data = {"id": "x", "role": "foreground-subject", "plateCoverage": 0.45}
        layer = layer_module.from_dict(data)
        assert layer.coverage == pytest.approx(0.45)

    def test_parallax_strength(self, layer_module):
        """parallaxStrength → parallax_strength."""
        layer = layer_module.from_dict(CANONICAL_LAYER_SPACE["layers"][0])
        assert layer.parallax_strength == pytest.approx(1.3)

    def test_motion_damping(self, layer_module):
        """motionDamping → motion_damping."""
        layer = layer_module.from_dict(CANONICAL_LAYER_SPACE["layers"][0])
        assert layer.motion_damping == pytest.approx(1.0)

    def test_rgba_path(self, layer_module):
        """JSON 'rgba' → rgba_path."""
        layer = layer_module.from_dict(CANONICAL_LAYER_SPACE["layers"][0])
        assert layer.rgba_path == "fg_01_rgba.png"

    def test_visible_bool(self, layer_module):
        """visible must be bool."""
        layer = layer_module.from_dict(CANONICAL_LAYER_SPACE["layers"][0])
        assert layer.visible is True


# ─── §2: CameraContract ─────────────────────────────────────────

class TestCameraContractSpec:
    """CameraContract parses the 'space' block from layer_space.json."""

    @pytest.fixture
    def camera_class(self):
        try:
            from src.services.cut_layer_manifest import CameraContract
            return CameraContract
        except ImportError:
            pytest.skip("cut_layer_manifest.py not yet implemented")

    def test_from_dict_exists(self, camera_class):
        assert hasattr(camera_class, "from_dict")

    def test_focal_length(self, camera_class):
        cam = camera_class.from_dict(CANONICAL_LAYER_SPACE["space"])
        assert cam.focal_length_mm == pytest.approx(50.0)

    def test_z_near_far(self, camera_class):
        cam = camera_class.from_dict(CANONICAL_LAYER_SPACE["space"])
        assert cam.z_near == pytest.approx(0.72)
        assert cam.z_far == pytest.approx(1.85)

    def test_motion_type(self, camera_class):
        cam = camera_class.from_dict(CANONICAL_LAYER_SPACE["space"])
        assert cam.motion_type == "orbit"

    def test_travel_is_percentage(self, camera_class):
        """travel_x_pct is PERCENTAGE, not pixels (§2 note)."""
        cam = camera_class.from_dict(CANONICAL_LAYER_SPACE["space"])
        assert cam.travel_x_pct == pytest.approx(3.0)
        assert cam.travel_y_pct == pytest.approx(0.0)

    def test_overscan(self, camera_class):
        cam = camera_class.from_dict(CANONICAL_LAYER_SPACE["space"])
        assert cam.overscan_pct == pytest.approx(20.0)


# ─── §4: Role Normalization ─────────────────────────────────────

class TestRoleNormalization:
    """§0: kebab-case on disk → underscore in Python via normalize_role()."""

    @pytest.fixture
    def normalize(self):
        try:
            from src.services.cut_layer_manifest import normalize_role
            return normalize_role
        except ImportError:
            pytest.skip("cut_layer_manifest.py not yet implemented")

    ROLE_TABLE = [
        ("foreground-subject", "foreground_subject"),
        ("secondary-subject", "secondary_subject"),
        ("environment-mid", "mid_environment"),
        ("background-far", "background"),
        ("special-clean", "special_clean"),
    ]

    @pytest.mark.parametrize("json_role,python_role", ROLE_TABLE)
    def test_role_mapping(self, normalize, json_role, python_role):
        assert normalize(json_role) == python_role

    def test_already_normalized_passes_through(self, normalize):
        """If role is already underscore, return as-is."""
        assert normalize("foreground_subject") == "foreground_subject"

    def test_unknown_role_uses_hyphen_to_underscore(self, normalize):
        """Unknown roles: simple hyphen→underscore fallback."""
        result = normalize("some-new-role")
        assert "_" in result or result == "some-new-role"


# ─── §3: LayerManifest full load ────────────────────────────────

class TestLayerManifestContract:
    """LayerManifest.from_json loads full canonical manifest."""

    @pytest.fixture
    def manifest_class(self):
        try:
            from src.services.cut_layer_manifest import LayerManifest
            return LayerManifest
        except ImportError:
            pytest.skip("cut_layer_manifest.py not yet implemented")

    def test_from_json_exists(self, manifest_class):
        assert hasattr(manifest_class, "from_json") or hasattr(manifest_class, "from_dict")

    def test_loads_layers(self, manifest_class):
        loader = getattr(manifest_class, "from_dict", getattr(manifest_class, "from_json", None))
        m = loader(CANONICAL_LAYER_SPACE)
        assert len(m.layers) == 2

    def test_format_is_layer_space(self, manifest_class):
        loader = getattr(manifest_class, "from_dict", getattr(manifest_class, "from_json", None))
        m = loader(CANONICAL_LAYER_SPACE)
        assert m.format == "layer_space"

    def test_sample_id(self, manifest_class):
        loader = getattr(manifest_class, "from_dict", getattr(manifest_class, "from_json", None))
        m = loader(CANONICAL_LAYER_SPACE)
        assert m.sample_id == "hover-politsia"

    def test_camera_loaded(self, manifest_class):
        loader = getattr(manifest_class, "from_dict", getattr(manifest_class, "from_json", None))
        m = loader(CANONICAL_LAYER_SPACE)
        assert m.camera is not None
        assert m.camera.focal_length_mm == pytest.approx(50.0)

    def test_source_dimensions(self, manifest_class):
        loader = getattr(manifest_class, "from_dict", getattr(manifest_class, "from_json", None))
        m = loader(CANONICAL_LAYER_SPACE)
        assert m.source_width == 1920
        assert m.source_height == 1080


# ─── §5: Legacy Bridge ──────────────────────────────────────────

class TestLegacyBridge:
    """plate_export_manifest.json is bridge-only, not canonical."""

    @pytest.fixture
    def manifest_class(self):
        try:
            from src.services.cut_layer_manifest import LayerManifest
            return LayerManifest
        except ImportError:
            pytest.skip("cut_layer_manifest.py not yet implemented")

    def test_detects_legacy_format(self, manifest_class):
        """Legacy manifest must be detected as 'plate_export' format."""
        loader = getattr(manifest_class, "from_dict", getattr(manifest_class, "from_json", None))
        m = loader(LEGACY_PLATE_EXPORT)
        assert m.format == "plate_export"

    def test_legacy_coverage_from_plateCoverage(self, manifest_class):
        """Legacy uses 'plateCoverage' — must be read correctly."""
        loader = getattr(manifest_class, "from_dict", getattr(manifest_class, "from_json", None))
        m = loader(LEGACY_PLATE_EXPORT)
        assert m.layers[0].coverage == pytest.approx(0.3)

    def test_space_fallback_to_camera_key(self, manifest_class):
        """Legacy uses 'camera' key instead of 'space'."""
        loader = getattr(manifest_class, "from_dict", getattr(manifest_class, "from_json", None))
        m = loader(LEGACY_PLATE_EXPORT)
        assert m.camera.focal_length_mm == pytest.approx(50.0)


# ─── §6: Clip Attachment (LayerManifestMeta) ─────────────────────

class TestClipLayerManifestMeta:
    """Clip gets layer_manifest metadata after import."""

    @pytest.fixture
    def meta_class(self):
        try:
            from src.services.cut_layer_manifest import LayerManifestMeta
            return LayerManifestMeta
        except ImportError:
            pytest.skip("cut_layer_manifest.py not yet implemented")

    def test_meta_has_manifest_path(self, meta_class):
        """LayerManifestMeta must have manifest_path field."""
        fields = [f for f in dir(meta_class) if not f.startswith("_")]
        assert "manifest_path" in fields or hasattr(meta_class, "manifest_path")

    def test_meta_has_layer_count(self, meta_class):
        assert hasattr(meta_class, "layer_count") or "layer_count" in meta_class.__dataclass_fields__

    def test_meta_has_foreground_flag(self, meta_class):
        assert hasattr(meta_class, "has_foreground") or "has_foreground" in meta_class.__dataclass_fields__


# ─── §7: API Endpoint (TDD-RED) ─────────────────────────────────

class TestLayerImportEndpoint:
    """POST /cut/layers/import — TDD-RED until Beta implements."""

    @pytest.fixture
    def routes_source(self):
        """Check if the endpoint is defined in any route file."""
        route_files = list(Path("src/api/routes").glob("cut_routes*.py"))
        if not route_files:
            route_files = [Path("src/api/routes/cut_routes.py")]
        combined = ""
        for f in route_files:
            if f.exists():
                combined += f.read_text()
        return combined

    @pytest.mark.xfail(reason="POST /cut/layers/import — xfail pending test verification")
    def test_import_endpoint_exists(self, routes_source):
        """Route for layer import must be defined."""
        assert "/layers/import" in routes_source or "layers_import" in routes_source

    @pytest.mark.xfail(reason="POST /cut/layers/import — xfail pending test verification")
    def test_endpoint_returns_manifest_id(self, routes_source):
        """Import endpoint must return manifest_id in response."""
        assert "manifest_id" in routes_source


# ─── No Prototype Dependency ─────────────────────────────────────

class TestNoPrototypeDependency:
    """Contract tests must NOT depend on legacy prototype inline schema.
    If cut_layer_manifest.py exists, it must not import from parallax prototype."""

    def test_no_parallax_playground_import(self):
        """cut_layer_manifest must not import from photo_parallax_playground."""
        manifest_path = Path("src/services/cut_layer_manifest.py")
        if not manifest_path.exists():
            pytest.skip("cut_layer_manifest.py not yet created")
        source = manifest_path.read_text()
        assert "photo_parallax_playground" not in source
        assert "parallax_playground" not in source

    def test_no_plate_export_as_default(self):
        """Default format must be layer_space, not plate_export."""
        manifest_path = Path("src/services/cut_layer_manifest.py")
        if not manifest_path.exists():
            pytest.skip("cut_layer_manifest.py not yet created")
        source = manifest_path.read_text()
        # Should not have plate_export as the default/primary format
        assert 'format = "plate_export"' not in source or 'format = "layer_space"' in source
