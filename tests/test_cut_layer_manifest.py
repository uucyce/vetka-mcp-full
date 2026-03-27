"""
MARKER_LAYERFX — Tests for CUT layer manifest ingestion.

Tests: SemanticLayer, LayerManifest, CameraContract, manifest ingestion
(layer_space + plate_export formats), LayerManifestMeta, auto-detection.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.services.cut_layer_manifest import (
    LAYER_ROLES,
    CameraContract,
    LayerManifest,
    LayerManifestMeta,
    SemanticLayer,
    ingest_layer_space,
    ingest_manifest,
    ingest_plate_export,
)


# ── SemanticLayer ──


class TestSemanticLayer:
    def test_from_dict_basic(self) -> None:
        layer = SemanticLayer.from_dict({
            "id": "fg_01", "role": "foreground_subject",
            "label": "Person", "z": 0.5, "visible": True,
        })
        assert layer.layer_id == "fg_01"
        assert layer.role == "foreground_subject"
        assert layer.z == 0.5

    def test_from_dict_playground_format(self) -> None:
        """Handles parallax playground field names (camelCase)."""
        layer = SemanticLayer.from_dict({
            "id": "plate_01", "role": "mid_environment",
            "depthPriority": 3, "parallaxStrength": 1.2,
            "plateCoverage": 0.45,
        })
        assert layer.order == 3
        assert layer.parallax_strength == 1.2
        assert layer.coverage == 0.45

    def test_to_dict_roundtrip(self) -> None:
        layer = SemanticLayer(layer_id="fg", role="foreground_subject", z=0.3)
        d = layer.to_dict()
        assert d["layer_id"] == "fg"
        assert d["role"] == "foreground_subject"

    def test_has_rgba_false_by_default(self) -> None:
        layer = SemanticLayer()
        assert layer.has_rgba is False
        assert layer.has_mask is False

    def test_has_rgba_true_with_file(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".png") as f:
            layer = SemanticLayer(rgba_path=f.name)
            assert layer.has_rgba is True


# ── CameraContract ──


class TestCameraContract:
    def test_default_values(self) -> None:
        cam = CameraContract()
        assert cam.focal_length_mm == 50.0
        assert cam.z_near == 0.72
        assert cam.motion_type == "orbit"

    def test_from_dict_camelcase(self) -> None:
        cam = CameraContract.from_dict({
            "focalLengthMm": 85.0, "zNear": 0.5, "zFar": 2.0,
            "motionType": "dolly_zoom_in", "durationSec": 6.0,
        })
        assert cam.focal_length_mm == 85.0
        assert cam.z_near == 0.5
        assert cam.motion_type == "dolly_zoom_in"
        assert cam.duration_sec == 6.0

    def test_from_dict_snakecase(self) -> None:
        cam = CameraContract.from_dict({
            "focal_length_mm": 35.0, "z_near": 0.3,
        })
        assert cam.focal_length_mm == 35.0

    def test_to_dict(self) -> None:
        cam = CameraContract(focal_length_mm=85.0)
        d = cam.to_dict()
        assert d["focal_length_mm"] == 85.0


# ── LayerManifest ──


class TestLayerManifest:
    def test_layer_count(self) -> None:
        m = LayerManifest(layers=[
            SemanticLayer(layer_id="a"), SemanticLayer(layer_id="b"),
        ])
        assert m.layer_count == 2

    def test_visible_layers(self) -> None:
        m = LayerManifest(layers=[
            SemanticLayer(layer_id="a", visible=True),
            SemanticLayer(layer_id="b", visible=False),
            SemanticLayer(layer_id="c", visible=True),
        ])
        assert len(m.visible_layers) == 2

    def test_get_layer_by_role(self) -> None:
        m = LayerManifest(layers=[
            SemanticLayer(layer_id="bg", role="background"),
            SemanticLayer(layer_id="fg", role="foreground_subject"),
        ])
        fg = m.get_layer_by_role("foreground_subject")
        assert fg is not None
        assert fg.layer_id == "fg"
        assert m.get_layer_by_role("special_clean") is None

    def test_has_foreground_background(self) -> None:
        m = LayerManifest(layers=[
            SemanticLayer(role="foreground_subject"),
            SemanticLayer(role="background"),
        ])
        assert m.has_foreground is True
        assert m.has_background is True

    def test_has_background_via_rgba_path(self) -> None:
        m = LayerManifest(background_rgba_path="/bg.png")
        assert m.has_background is True

    def test_to_dict(self) -> None:
        m = LayerManifest(
            sample_id="test",
            layers=[SemanticLayer(layer_id="a", role="foreground_subject")],
            camera=CameraContract(focal_length_mm=85.0),
        )
        d = m.to_dict()
        assert d["sample_id"] == "test"
        assert len(d["layers"]) == 1
        assert d["camera"]["focal_length_mm"] == 85.0


# ── LAYER_ROLES ──


class TestLayerRoles:
    def test_canonical_roles_present(self) -> None:
        assert "foreground_subject" in LAYER_ROLES
        assert "secondary_subject" in LAYER_ROLES
        assert "mid_environment" in LAYER_ROLES
        assert "background" in LAYER_ROLES
        assert "special_clean" in LAYER_ROLES


# ── Ingestion: layer_space format ──


class TestIngestLayerSpace:
    def _write_manifest(self, tmpdir: str) -> str:
        data = {
            "contract_version": "1.0",
            "sampleId": "test_scene",
            "source": {"path": "/src.jpg", "width": 1920, "height": 1080},
            "layers": [
                {"id": "fg_01", "role": "foreground_subject", "label": "Person",
                 "z": 0.5, "visible": True, "rgba": "fg_rgba.png", "mask": "fg_mask.png"},
                {"id": "bg_01", "role": "background", "label": "City",
                 "z": 1.5, "visible": True, "rgba": "bg_rgba.png"},
            ],
            "space": {"focalLengthMm": 85.0, "zNear": 0.4, "zFar": 2.0},
            "provenance": {"depth_backend": "depth-pro"},
        }
        path = Path(tmpdir) / "layer_space.json"
        path.write_text(json.dumps(data))
        return str(path)

    def test_ingests_basic_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_manifest(tmpdir)
            m = ingest_layer_space(path)
            assert m.sample_id == "test_scene"
            assert m.layer_count == 2
            assert m.format == "layer_space"
            assert m.source_width == 1920

    def test_resolves_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_manifest(tmpdir)
            m = ingest_layer_space(path)
            fg = m.get_layer_by_role("foreground_subject")
            assert fg is not None
            assert Path(fg.rgba_path).is_absolute()
            assert "fg_rgba.png" in fg.rgba_path

    def test_reads_camera(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_manifest(tmpdir)
            m = ingest_layer_space(path)
            assert m.camera.focal_length_mm == 85.0
            assert m.camera.z_near == 0.4

    def test_reads_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_manifest(tmpdir)
            m = ingest_layer_space(path)
            assert m.provenance["depth_backend"] == "depth-pro"


# ── Ingestion: plate_export format ──


class TestIngestPlateExport:
    def _write_manifest(self, tmpdir: str) -> str:
        data = {
            "exportedPlates": [
                {"id": "plate_00", "role": "foreground_subject", "visible": True,
                 "order": 2, "z": 0.5, "files": {"rgba": "plate_00_rgba.png"},
                 "parallaxStrength": 1.3, "plateCoverage": 0.3},
                {"id": "plate_01", "role": "background", "visible": True,
                 "order": 0, "z": 1.8, "files": {"rgba": "plate_01_rgba.png"}},
            ],
        }
        path = Path(tmpdir) / "plate_export_manifest.json"
        path.write_text(json.dumps(data))
        return str(path)

    def test_ingests_plate_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_manifest(tmpdir)
            m = ingest_plate_export(path)
            assert m.layer_count == 2
            assert m.format == "plate_export"

    def test_maps_plate_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_manifest(tmpdir)
            m = ingest_plate_export(path)
            fg = m.get_layer_by_role("foreground_subject")
            assert fg is not None
            assert fg.parallax_strength == 1.3
            assert fg.coverage == 0.3


# ── Auto-detection ──


class TestIngestManifest:
    def test_auto_detects_layer_space(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {
                "contract_version": "1.0", "sampleId": "s1",
                "source": {"width": 100, "height": 100},
                "layers": [{"id": "l1", "role": "background"}],
            }
            path = Path(tmpdir) / "manifest.json"
            path.write_text(json.dumps(data))
            m = ingest_manifest(str(path))
            assert m.format == "layer_space"

    def test_auto_detects_plate_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"exportedPlates": [{"id": "p1", "visible": True, "files": {}}]}
            path = Path(tmpdir) / "manifest.json"
            path.write_text(json.dumps(data))
            m = ingest_manifest(str(path))
            assert m.format == "plate_export"

    def test_unknown_format_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "weird.json"
            path.write_text('{"foo": "bar"}')
            with pytest.raises(ValueError, match="Unknown manifest format"):
                ingest_manifest(str(path))

    def test_missing_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            ingest_manifest("/nonexistent/manifest.json")


# ── LayerManifestMeta ──


class TestLayerManifestMeta:
    def test_from_manifest(self) -> None:
        m = LayerManifest(
            sample_id="scene1", format="layer_space",
            layers=[
                SemanticLayer(role="foreground_subject"),
                SemanticLayer(role="background"),
            ],
        )
        meta = LayerManifestMeta.from_manifest(m, "/path/manifest.json")
        assert meta.manifest_path == "/path/manifest.json"
        assert meta.layer_count == 2
        assert meta.has_foreground is True
        assert meta.has_background is True

    def test_to_dict_roundtrip(self) -> None:
        meta = LayerManifestMeta(
            manifest_path="/m.json", format="plate_export",
            layer_count=3, has_foreground=True,
        )
        d = meta.to_dict()
        meta2 = LayerManifestMeta.from_dict(d)
        assert meta2.manifest_path == meta.manifest_path
        assert meta2.layer_count == 3
