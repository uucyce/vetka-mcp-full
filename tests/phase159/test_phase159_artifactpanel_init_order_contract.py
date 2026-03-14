from pathlib import Path


def test_phase159_artifactpanel_israwcontent_declared_before_isfilemode():
    panel = Path('client/src/components/artifact/ArtifactPanel.tsx').read_text(encoding='utf-8')
    is_raw_idx = panel.find('const isRawContentMode = !!rawContent;')
    is_file_idx = panel.find('const isFileMode = !isRawContentMode && Boolean(detachedCurrentPath);')
    assert is_raw_idx != -1, 'isRawContentMode declaration must exist'
    assert is_file_idx != -1, 'isFileMode declaration must exist'
    assert is_raw_idx < is_file_idx, 'isRawContentMode must be declared before isFileMode (avoid TDZ runtime crash)'
