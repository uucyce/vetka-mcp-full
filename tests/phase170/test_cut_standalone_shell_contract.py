from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_cut_standalone_shell_route_registered():
    main_tsx = _read("client/src/main.tsx")

    assert "import CutStandalone from './CutStandalone';" in main_tsx
    assert "pathname === '/cut'" in main_tsx
    assert "return <CutStandalone />;" in main_tsx


def test_cut_standalone_shell_binds_to_cut_mcp_contracts():
    shell = _read("client/src/CutStandalone.tsx")

    assert "import { NOLAN_PALETTE } from './utils/dagLayout';" in shell
    assert "Open CUT Project" in shell
    assert "Start Scene Assembly" in shell
    assert "Build Waveforms" in shell
    assert "Normalize Transcripts" in shell
    assert "Build Thumbnails" in shell
    assert "Favorite Moment" in shell
    assert "Comment Marker" in shell
    assert "Cognitive Markers" in shell
    assert "time_markers_ready:" in shell
    assert "Worker Queue" in shell
    assert "Storyboard Strip" in shell
    assert "active_jobs:" in shell
    assert "recent_jobs:" in shell
    assert "Cancel Job" in shell
    assert "/cut/bootstrap" in shell
    assert "/cut/project-state" in shell
    assert "/cut/job/" in shell
    assert "/cancel" in shell
    assert "/cut/scene-assembly-async" in shell
    assert "/cut/worker/waveform-build-async" in shell
    assert "/cut/worker/transcript-normalize-async" in shell
    assert "/cut/worker/thumbnail-build-async" in shell
    assert "/cut/time-markers/apply" in shell
    assert "/cut/timeline/apply" in shell
    assert "/cut/scene-graph/apply" in shell
    assert "#2563eb" not in shell
