from __future__ import annotations

from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def test_detached_media_debug_api_is_installed_in_standalone_route():
    standalone_tsx = (ROOT / "client/src/ArtifactMediaStandalone.tsx").read_text(encoding="utf-8")
    assert "installDetachedMediaDebug" in standalone_tsx
    assert "return installDetachedMediaDebug({" in standalone_tsx


def test_video_player_marks_wrapper_for_geometry_probe():
    player_tsx = (ROOT / "client/src/components/artifact/viewers/VideoArtifactPlayer.tsx").read_text(encoding="utf-8")
    assert 'data-vetka-media-wrapper="1"' in player_tsx


def test_detached_media_debug_helper_exposes_snapshot_and_assertion():
    helper_ts = (ROOT / "client/src/utils/detachedMediaDebug.ts").read_text(encoding="utf-8")
    assert "window.__VETKA_MEDIA_DEBUG__ = api" in helper_ts
    assert "window.debugMedia = api" in helper_ts
    assert "assertNoSideLetterbox" in helper_ts
    assert "MARKER_159.R15.DETACHED_MEDIA_DEBUG_SNAPSHOT" in helper_ts


def test_detached_media_geometry_probe_script_targets_debug_media_api():
    probe_sh = (ROOT / "scripts/detached_media_geometry_probe.sh").read_text(encoding="utf-8")
    assert "window.debugMedia.snapshot()" in probe_sh
    assert "window.debugMedia.assertNoSideLetterbox" in probe_sh
    assert "PASS: detached media geometry probe" in probe_sh
