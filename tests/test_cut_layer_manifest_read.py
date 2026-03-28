"""
MARKER_LAYERFX_READ — Tests for GET /cut/layers/manifest endpoint contract.

Tests the full chain: manifest_path → ingest_manifest → canonical dict response.
Covers success, missing file, bad format, Alpha-compatible data.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.services.cut_layer_manifest import ingest_manifest


class TestManifestReadHappyPath:
    """Verify manifest read returns canonical shape for Gamma."""

    def _write_canonical(self, tmpdir: str) -> str:
        data = {
            "contract_version": "1.0.0",
            "sampleId": "test-scene",
            "source": {"path": "/src.jpg", "width": 1920, "height": 1080},
            "layers": [
                {"id": "fg", "role": "foreground-subject", "label": "Person",
                 "z": 0.5, "visible": True, "rgba": "fg.png",
                 "coverage": 0.3, "parallaxStrength": 1.2},
                {"id": "bg", "role": "background-far", "label": "Sky",
                 "z": 1.8, "visible": True, "rgba": "bg.png"},
            ],
            "space": {
                "focalLengthMm": 85, "zNear": 0.4, "zFar": 2.0,
                "motionType": "orbit", "durationSec": 5.0,
                "travelXPct": 4.0, "zoom": 1.1,
            },
        }
        path = Path(tmpdir) / "layer_space.json"
        path.write_text(json.dumps(data))
        return str(path)

    def test_returns_manifest_dict(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_canonical(tmpdir)
            manifest = ingest_manifest(path)
            d = manifest.to_dict()
            assert d["sample_id"] == "test-scene"
            assert len(d["layers"]) == 2

    def test_layers_have_normalized_roles(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_canonical(tmpdir)
            manifest = ingest_manifest(path)
            d = manifest.to_dict()
            roles = [l["role"] for l in d["layers"]]
            assert "foreground_subject" in roles  # normalized from kebab
            assert "background" in roles          # background-far → background

    def test_camera_in_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_canonical(tmpdir)
            manifest = ingest_manifest(path)
            d = manifest.to_dict()
            cam = d["camera"]
            assert cam["focal_length_mm"] == 85.0
            assert cam["z_near"] == 0.4
            assert cam["motion_type"] == "orbit"

    def test_layers_have_rgba_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_canonical(tmpdir)
            manifest = ingest_manifest(path)
            d = manifest.to_dict()
            fg = d["layers"][0]
            assert "fg.png" in fg["rgba_path"]
            assert Path(fg["rgba_path"]).is_absolute()

    def test_coverage_and_parallax_strength(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_canonical(tmpdir)
            manifest = ingest_manifest(path)
            d = manifest.to_dict()
            fg = d["layers"][0]
            assert fg["coverage"] == 0.3
            assert fg["parallax_strength"] == 1.2


class TestManifestReadAlphaCompat:
    """Verify Alpha plate_export format works through the same read path."""

    def _write_alpha(self, tmpdir: str) -> str:
        data = {
            "contract_version": "1.0.0",
            "sampleId": "hover-politsia",
            "exportedPlates": [
                {"index": 1, "id": "plate_01", "role": "foreground-subject",
                 "visible": True, "coverage": 0.21, "z": 26,
                 "depthPriority": 0.86, "cleanVariant": "no-vehicle",
                 "files": {"rgba": "p01.png", "mask": "p01_m.png"}},
                {"index": 2, "id": "plate_02", "role": "environment-mid",
                 "visible": True, "coverage": 0.02, "z": -8,
                 "files": {"rgba": "p02.png"}},
            ],
        }
        path = Path(tmpdir) / "plate_export_manifest.json"
        path.write_text(json.dumps(data))
        return str(path)

    def test_alpha_format_returns_canonical_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_alpha(tmpdir)
            manifest = ingest_manifest(path)
            d = manifest.to_dict()
            assert d["format"] == "plate_export"
            assert d["sample_id"] == "hover-politsia"
            assert len(d["layers"]) == 2

    def test_alpha_roles_normalized_in_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_alpha(tmpdir)
            manifest = ingest_manifest(path)
            d = manifest.to_dict()
            roles = [l["role"] for l in d["layers"]]
            assert "foreground_subject" in roles
            assert "mid_environment" in roles
            assert all("-" not in r for r in roles)

    def test_alpha_depth_priority_in_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_alpha(tmpdir)
            manifest = ingest_manifest(path)
            d = manifest.to_dict()
            fg = [l for l in d["layers"] if l["role"] == "foreground_subject"][0]
            assert fg["depth_priority"] == 0.86
            assert fg["order"] == 1
            assert fg["clean_variant"] == "no-vehicle"


class TestManifestReadFailures:
    def test_missing_file(self) -> None:
        with pytest.raises(FileNotFoundError):
            ingest_manifest("/nonexistent/layer_space.json")

    def test_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad.json"
            path.write_text("{broken json")
            with pytest.raises(json.JSONDecodeError):
                ingest_manifest(str(path))

    def test_unknown_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mystery.json"
            path.write_text('{"nothing": "useful"}')
            with pytest.raises(ValueError, match="Unknown manifest format"):
                ingest_manifest(str(path))
