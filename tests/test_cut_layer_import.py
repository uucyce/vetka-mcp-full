"""
MARKER_LAYERFX — Tests for POST /cut/layers/import endpoint contract.

Tests: manifest validation, clip metadata storage, Alpha-compatible data
ingestion, role normalization through the full pipeline, error handling.

Uses mock CutProjectStore (no real project needed).
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.services.cut_layer_manifest import (
    LayerManifest,
    LayerManifestMeta,
    SemanticLayer,
    ingest_manifest,
)


# ── Alpha-compatible data ingestion ──


class TestAlphaCompatibleIngest:
    """Verify real Alpha plate_export_manifest format is ingested without data loss."""

    ALPHA_MANIFEST = {
        "contract_version": "1.0.0",
        "sampleId": "hover-politsia",
        "files": {
            "plateLayout": "plate_layout.json",
            "globalDepth": "global_depth_bw.png",
            "backgroundRgba": "background_rgba.png",
        },
        "exportedPlates": [
            {
                "index": 1, "id": "plate_01", "label": "vehicle",
                "role": "foreground-subject", "visible": True,
                "coverage": 0.2153, "z": 26, "depthPriority": 0.86,
                "cleanVariant": "no-vehicle",
                "files": {"rgba": "plate_01_rgba.png", "mask": "plate_01_mask.png",
                          "depth": "plate_01_depth.png"},
            },
            {
                "index": 2, "id": "plate_02", "label": "walker",
                "role": "secondary-subject", "visible": True,
                "coverage": 0.0354, "z": 14, "depthPriority": 0.58,
                "cleanVariant": "no-people",
                "files": {"rgba": "plate_02_rgba.png", "mask": "plate_02_mask.png"},
            },
            {
                "index": 3, "id": "plate_03", "label": "street steam",
                "role": "environment-mid", "visible": True,
                "coverage": 0.0159, "z": -8, "depthPriority": 0.36,
                "cleanVariant": None,
                "files": {"rgba": "plate_03_rgba.png"},
            },
            {
                "index": 4, "id": "plate_04", "label": "background city",
                "role": "background-far", "visible": True,
                "coverage": 0, "z": -30, "depthPriority": 0.14,
                "files": {},
            },
            {
                "index": 5, "id": "plate_05", "label": "no vehicle",
                "role": "special-clean", "visible": False,
                "coverage": 0, "z": -34, "depthPriority": 0.08,
                "cleanVariant": "no-vehicle",
                "files": {"clean": "plate_05_clean.png"},
            },
        ],
    }

    def _write_alpha_manifest(self, tmpdir: str) -> str:
        path = Path(tmpdir) / "plate_export_manifest.json"
        path.write_text(json.dumps(self.ALPHA_MANIFEST))
        return str(path)

    def test_all_roles_normalize(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_alpha_manifest(tmpdir)
            m = ingest_manifest(path)
            roles = [l.role for l in m.layers]
            assert "foreground_subject" in roles
            assert "secondary_subject" in roles
            assert "mid_environment" in roles
            assert "background" in roles
            assert "special_clean" in roles
            # NO kebab roles should survive
            for r in roles:
                assert "-" not in r, f"Kebab role leaked: {r}"

    def test_coverage_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_alpha_manifest(tmpdir)
            m = ingest_manifest(path)
            fg = m.get_layer_by_role("foreground_subject")
            assert fg is not None
            assert fg.coverage == 0.2153  # exact Alpha value

    def test_depth_priority_preserved_as_float(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_alpha_manifest(tmpdir)
            m = ingest_manifest(path)
            fg = m.get_layer_by_role("foreground_subject")
            assert fg.depth_priority == 0.86
            assert fg.order == 1  # from "index"

    def test_clean_variant_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_alpha_manifest(tmpdir)
            m = ingest_manifest(path)
            fg = m.get_layer_by_role("foreground_subject")
            assert fg.clean_variant == "no-vehicle"

    def test_clean_files_path_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_alpha_manifest(tmpdir)
            m = ingest_manifest(path)
            clean_layer = [l for l in m.layers if l.role == "special_clean"][0]
            assert "plate_05_clean.png" in clean_layer.clean_path
            assert Path(clean_layer.clean_path).is_absolute()

    def test_z_values_preserved_as_is(self) -> None:
        """Alpha z values are raw integers, not 0-1 normalized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_alpha_manifest(tmpdir)
            m = ingest_manifest(path)
            fg = m.get_layer_by_role("foreground_subject")
            assert fg.z == 26.0  # raw integer from Alpha

    def test_has_foreground_and_background(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_alpha_manifest(tmpdir)
            m = ingest_manifest(path)
            assert m.has_foreground is True
            assert m.has_background is True

    def test_layer_count_includes_clean_plates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_alpha_manifest(tmpdir)
            m = ingest_manifest(path)
            assert m.layer_count == 5
            assert len(m.visible_layers) == 4  # plate_05 is invisible

    def test_sample_id_from_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_alpha_manifest(tmpdir)
            m = ingest_manifest(path)
            assert m.sample_id == "hover-politsia"

    def test_manifest_meta_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_alpha_manifest(tmpdir)
            m = ingest_manifest(path)
            meta = LayerManifestMeta.from_manifest(m, path)
            assert meta.layer_count == 5
            assert meta.has_foreground is True
            assert meta.has_background is True
            assert meta.sample_id == "hover-politsia"


# ── Endpoint contract (no real server, test data flow) ──


class TestLayerImportContract:
    """Verify the endpoint request/response contract matches canonical spec."""

    def test_meta_stored_on_clip(self) -> None:
        """Simulate what the endpoint does: ingest → meta → clip dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {
                "contract_version": "1.0.0", "sampleId": "test",
                "source": {"width": 1920, "height": 1080},
                "layers": [
                    {"id": "fg", "role": "foreground-subject", "z": 0.5,
                     "rgba": "fg.png", "coverage": 0.4},
                ],
            }
            path = Path(tmpdir) / "layer_space.json"
            path.write_text(json.dumps(data))

            manifest = ingest_manifest(str(path))
            meta = LayerManifestMeta.from_manifest(manifest, str(path))

            # Simulate clip dict
            clip = {"clip_id": "c1", "source_path": "/vid.mp4"}
            clip["layer_manifest"] = meta.to_dict()

            # Verify what Gamma would read
            assert clip["layer_manifest"]["manifest_path"] == str(path)
            assert clip["layer_manifest"]["layer_count"] == 1
            assert clip["layer_manifest"]["has_foreground"] is True

    def test_error_on_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad.json"
            path.write_text("not json")
            with pytest.raises(json.JSONDecodeError):
                ingest_manifest(str(path))

    def test_error_on_unknown_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mystery.json"
            path.write_text('{"unknown": true}')
            with pytest.raises(ValueError):
                ingest_manifest(str(path))
