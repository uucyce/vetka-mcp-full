from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_r2_detached_window_reuses_artifact_panel_with_actions():
    standalone = _read("client/src/ArtifactMediaStandalone.tsx")
    panel = _read("client/src/components/artifact/ArtifactPanel.tsx")
    app_tsx = _read("client/src/App.tsx")

    assert "<ArtifactPanel" in standalone
    assert "windowMode=\"detached\"" in standalone
    assert "onClose={() => { void handleClose(); }}" in standalone

    # Action parity gate: detached mode still uses same toolbar actions.
    assert "onDownload={() => { void handleDownload(); }}" in panel
    assert "onOpenInFinder={handleOpenInFinder}" in panel
    assert "onPin={handlePinToChat}" in panel
    assert "onClose={windowMode === 'detached' ? () => { void handleCloseDetachedWindow(); } : onClose}" in panel
    assert "writeDetachedArtifactPinRequest({" in panel
    assert "readDetachedArtifactChatState()" in panel
    assert "DETACHED_ARTIFACT_CHAT_STATE_KEY" in panel
    assert "writeDetachedArtifactChatState(nextState);" in app_tsx
    assert "event.key !== DETACHED_ARTIFACT_PIN_REQUEST_KEY" in app_tsx
