from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")
PROBE_SCRIPT = ROOT / "scripts/media_dom_playback_probe.sh"


def _require_bin(name: str) -> None:
    if shutil.which(name) is None:
        pytest.skip(f"{name} is required for DOM playback probe")


def test_phase159_dom_playback_probe_advances_current_time(tmp_path: Path):
    if os.getenv("VETKA_E2E_BROWSER", "0") not in {"1", "true", "TRUE"}:
        pytest.skip("Set VETKA_E2E_BROWSER=1 to run real-browser DOM playback probe")

    _require_bin("ffmpeg")
    _require_bin("npx")
    _require_bin("python3")

    # Tiny deterministic video fixture for probe (no project media dependency).
    probe_video = tmp_path / "probe.mp4"
    ffmpeg_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=640x360:rate=24",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-t",
        "2",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        str(probe_video),
    ]
    subprocess.run(ffmpeg_cmd, check=True, cwd=ROOT)

    result = subprocess.run(
        [str(PROBE_SCRIPT), str(probe_video)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "PASS: DOM playback probe" in result.stdout
    assert "PLAYBACK_CURRENT_TIME=" in result.stdout
