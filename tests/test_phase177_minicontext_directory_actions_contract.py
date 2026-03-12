from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MINI_CONTEXT = ROOT / 'client/src/components/mcc/MiniContext.tsx'


def test_minicontext_directory_tree_exposes_file_actions():
    text = MINI_CONTEXT.read_text()
    assert 'function DirectoryTreeView' in text
    assert 'onPreviewFile' in text
    assert 'onOpenFile' in text
    assert 'onFocusFile' in text
    assert '>\n              preview\n' in text
    assert '>\n              open\n' in text
    assert '>\n              full\n' in text
    assert '>\n              focus\n' in text
    assert "snippet: 'code scope jump'" in text
    assert 'onJump={handleFocusLinkedPath}' in text or 'jump to' in text
