from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_video_player_has_core_controls_and_no_autoplay():
    src = _read("client/src/components/artifact/viewers/VideoArtifactPlayer.tsx")
    assert "autoPlay={false}" in src
    assert "preload=\"metadata\"" in src
    assert "type=\"range\"" in src
    assert "setVolume(" in src
    assert "setPlaybackRate(" in src
    assert "requestFullscreen" in src
    assert "title=\"Play\"" in src
    assert "onError={handlePlaybackError}" in src
    assert "isMuted ? (" in src
    assert "viewBox=\"0 0 24 24\"" in src
    assert "requestFullscreen" in src
    assert "webkitEnterFullscreen" in src


def test_phase159_video_player_has_quality_menu_and_speed_menu():
    src = _read("client/src/components/artifact/viewers/VideoArtifactPlayer.tsx")
    assert "const [selectedQualityScale, setSelectedQualityScale] = useState<\"full\" | \"half\" | \"quarter\" | \"eighth\" | \"sixteenth\">(" in src
    assert "qualityScaleSources?" in src
    assert "label: \"1/2\"" in src
    assert "label: \"1/4\"" in src
    assert "label: \"1/8\"" in src
    assert "label: \"1/16\"" in src
    assert "const speedOptions = [0.5, 1, 1.25, 1.5, 2, 4];" in src
    assert "setSelectedQualityScale(" in src
    assert "const resolvedQualityScaleSources = useMemo(() => {" in src
    assert "const effectiveSrc = resolvedQualityScaleSources[selectedQualityScale] || resolvedQualityScaleSources.full;" in src
    assert "key={effectiveSrc}" in src
    assert "<source src={effectiveSrc} type={mimeType} />" in src


def test_phase159_video_player_resets_on_source_switch():
    src = _read("client/src/components/artifact/viewers/VideoArtifactPlayer.tsx")
    assert "video.pause();" in src
    assert "video.currentTime = 0;" in src
    assert "video.load();" in src
