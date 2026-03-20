"""Contract tests for video_inspection_pack.py.

Run: python -m pytest tests/test_video_inspection_pack.py -v
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "scripts" / "video_inspection_pack.py"
# Use the depth-venv python which has Pillow
VENV_PY = (Path(__file__).parent.parent /
           "photo_parallax_playground" / ".depth-venv" / "bin" / "python3")
PYTHON = str(VENV_PY) if VENV_PY.exists() else sys.executable

# Real test video from parallax output
TEST_VIDEO = (Path(__file__).parent.parent /
              "photo_parallax_playground" / "output" /
              "render_preview_multiplate_qwen_gated_camera_bridge" /
              "hover-politsia" / "preview_multiplate.mp4")


def _have_test_video():
    return TEST_VIDEO.exists()


def _run_inspection(outdir: str, *extra_args) -> subprocess.CompletedProcess:
    cmd = [PYTHON, str(SCRIPT),
           "--input", str(TEST_VIDEO),
           "--outdir", outdir,
           *extra_args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120)


# ---- Layer 1 contract tests ----

@pytest.mark.skipif(not _have_test_video(), reason="test video not found")
class TestLayer1:

    def test_produces_contact_sheet(self, tmp_path):
        r = _run_inspection(str(tmp_path), "--frames", "4", "--width", "480")
        assert r.returncode == 0, r.stderr
        assert (tmp_path / "contact_sheet.jpg").exists()

    def test_produces_motion_diff(self, tmp_path):
        r = _run_inspection(str(tmp_path), "--frames", "4", "--width", "480")
        assert r.returncode == 0, r.stderr
        assert (tmp_path / "motion_diff.jpg").exists()

    def test_produces_inspection_json(self, tmp_path):
        r = _run_inspection(str(tmp_path), "--frames", "4", "--width", "480")
        assert r.returncode == 0, r.stderr
        jpath = tmp_path / "inspection.json"
        assert jpath.exists()
        data = json.loads(jpath.read_text())
        assert data["version"] == "1.1"
        assert data["input"]["fps"] > 0
        assert data["input"]["frame_count"] > 0
        assert len(data["timestamps_sampled"]) > 0

    def test_json_has_analysis(self, tmp_path):
        r = _run_inspection(str(tmp_path), "--frames", "4", "--width", "480")
        assert r.returncode == 0, r.stderr
        data = json.loads((tmp_path / "inspection.json").read_text())
        assert "analysis" in data
        assert "rgb_motion" in data["analysis"]
        assert "spatial_concentration" in data["analysis"]["rgb_motion"]

    def test_json_has_file_sizes(self, tmp_path):
        r = _run_inspection(str(tmp_path), "--frames", "4", "--width", "480")
        assert r.returncode == 0, r.stderr
        data = json.loads((tmp_path / "inspection.json").read_text())
        assert "file_sizes_kb" in data
        assert data["file_sizes_kb"]["_total_kb"] > 0

    def test_timestamps_match_frame_count(self, tmp_path):
        r = _run_inspection(str(tmp_path), "--frames", "6", "--width", "480")
        assert r.returncode == 0, r.stderr
        data = json.loads((tmp_path / "inspection.json").read_text())
        assert len(data["timestamps_sampled"]) <= 6

    def test_weight_under_budget_layer1(self, tmp_path):
        """Layer 1 only should be well under 800KB at width=640."""
        r = _run_inspection(str(tmp_path), "--frames", "8", "--width", "640")
        assert r.returncode == 0, r.stderr
        data = json.loads((tmp_path / "inspection.json").read_text())
        total_kb = data["file_sizes_kb"]["_total_kb"]
        assert total_kb < 800, f"Layer 1 pack too heavy: {total_kb}KB"


# ---- Edge cases ----

@pytest.mark.skipif(not _have_test_video(), reason="test video not found")
class TestEdgeCases:

    def test_single_frame_requested(self, tmp_path):
        """--frames 1 should still produce contact sheet (no diff)."""
        r = _run_inspection(str(tmp_path), "--frames", "1", "--width", "320")
        assert r.returncode == 0, r.stderr
        assert (tmp_path / "contact_sheet.jpg").exists()
        data = json.loads((tmp_path / "inspection.json").read_text())
        assert data["outputs"]["motion_diff"] is None or \
               not (tmp_path / "motion_diff.jpg").exists()

    def test_columns_exceeds_frames(self, tmp_path):
        """--columns 10 with --frames 3 should not crash."""
        r = _run_inspection(str(tmp_path), "--frames", "3", "--columns", "10",
                            "--width", "320")
        assert r.returncode == 0, r.stderr

    def test_missing_input_returns_error(self, tmp_path):
        cmd = [PYTHON, str(SCRIPT),
               "--input", "/nonexistent/video.mp4",
               "--outdir", str(tmp_path)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        assert r.returncode != 0


# ---- Depth contract tests ----

@pytest.mark.skipif(not _have_test_video(), reason="test video not found")
@pytest.mark.skipif(not VENV_PY.exists(), reason=".depth-venv not found")
class TestDepth:

    @pytest.mark.slow
    def test_depth_produces_all_artifacts(self, tmp_path):
        r = _run_inspection(str(tmp_path), "--depth",
                            "--frames", "4", "--width", "480",
                            "--sample-rate", "25")
        assert r.returncode == 0, r.stderr
        assert (tmp_path / "depth_contact_sheet.jpg").exists()
        assert (tmp_path / "depth_diff.png").exists()
        assert (tmp_path / "motion_energy.png").exists()

    @pytest.mark.slow
    def test_depth_json_has_stats(self, tmp_path):
        r = _run_inspection(str(tmp_path), "--depth",
                            "--frames", "4", "--width", "480",
                            "--sample-rate", "25")
        assert r.returncode == 0, r.stderr
        data = json.loads((tmp_path / "inspection.json").read_text())
        assert "depth_stats" in data
        assert data["depth_stats"]["frames_processed"] > 0
        assert "depth_timestamps_sampled" in data
        assert "depth_quality" in data.get("analysis", {})

    @pytest.mark.slow
    def test_sample_rate_changes_frame_count(self, tmp_path):
        """--sample-rate 25 should extract fewer depth frames than --sample-rate 5."""
        r = _run_inspection(str(tmp_path), "--depth",
                            "--frames", "4", "--width", "320",
                            "--sample-rate", "25")
        assert r.returncode == 0, r.stderr
        data = json.loads((tmp_path / "inspection.json").read_text())
        n_depth_25 = data["depth_stats"]["frames_processed"]

        tmp2 = tmp_path / "sr5"
        tmp2.mkdir()
        r2 = _run_inspection(str(tmp2), "--depth",
                             "--frames", "4", "--width", "320",
                             "--sample-rate", "5")
        assert r2.returncode == 0, r2.stderr
        data2 = json.loads((tmp2 / "inspection.json").read_text())
        n_depth_5 = data2["depth_stats"]["frames_processed"]

        assert n_depth_5 > n_depth_25, \
            f"sample-rate 5 ({n_depth_5}) should > sample-rate 25 ({n_depth_25})"
