from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_media_artifact_uses_raw_stream_not_base64():
    src = _read("client/src/components/artifact/ArtifactPanel.tsx")
    assert "const fileUrl = `/api/files/raw?path=${encodeURIComponent(path)}`;" in src
    assert "const previewPlaybackSrc = mediaPreview?.playback?.source_url;" in src
    assert "const mediaSrc = streamMedia ? fileUrl : (isBase64 ? `data:${mimeType};base64,${content}` : fileUrl);" in src
    assert "const videoQualitySources: Partial<Record<'Auto' | 'Original' | 'Preview', string>> = {" in src
    assert "const videoQualityScaleSources: Partial<Record<'full' | 'half' | 'quarter' | 'eighth' | 'sixteenth', string>> = {" in src
    assert "qualitySources={videoQualitySources}" in src
    assert "qualityScaleSources={videoQualityScaleSources}" in src


def test_phase159_media_toolbar_hides_text_edit_actions():
    src = _read("client/src/components/artifact/ArtifactPanel.tsx")
    assert "onEdit={isMediaArtifact ? undefined : () => setIsEditing(!isEditing)}" in src
    assert "onSave={isMediaArtifact ? undefined : saveFile}" in src
    assert "onSaveAs={isMediaArtifact ? undefined : () => { void handleSaveAs(); }}" in src
    assert "onCopy={isMediaArtifact ? undefined : handleCopy}" in src
    assert "onInfo={isMediaArtifact ? () => setMediaInfoOpen((v) => !v) : undefined}" in src
