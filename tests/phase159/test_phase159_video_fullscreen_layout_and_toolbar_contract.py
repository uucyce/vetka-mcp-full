from pathlib import Path

ROOT = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase159_c2_video_fullscreen_hides_artifact_toolbar_and_removes_detached_width_cap():
    panel = _read('client/src/components/artifact/ArtifactPanel.tsx')

    assert "const [isMediaFullscreen, setIsMediaFullscreen] = useState<boolean>(false);" in panel
    assert "padding: windowMode === 'detached' ? 0 : 16" in panel
    assert "maxWidth: windowMode === 'detached' ? 'none' : 1280" in panel
    assert 'onFullscreenChange={setIsMediaFullscreen}' in panel
    assert "!(isMediaArtifact && windowMode === 'detached' && isMediaFullscreen)" in panel
    assert "alignItems: windowMode === 'detached' ? 'stretch' : 'center'" in panel
    assert "justifyContent: windowMode === 'detached' ? 'flex-start' : 'center'" in panel
