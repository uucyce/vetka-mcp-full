from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_r3_media_state_sync_contract_present():
    player = _read("client/src/components/artifact/viewers/VideoArtifactPlayer.tsx")
    panel = _read("client/src/components/artifact/ArtifactPanel.tsx")

    assert 'const MEDIA_SESSION_CHANNEL = "vetka-media-session-v1"' in player
    assert 'action: "sync_playback_state"' in player
    assert 'schema_version: "artifact_media_session_state_v1"' in player
    assert "new BroadcastChannel(MEDIA_SESSION_CHANNEL)" in player
    assert "channel.onmessage" in player
    assert "applyRemoteSessionState" in player

    # Media identity must be stable path (not scaled source URL).
    assert "mediaPath={fileData.path}" in panel

