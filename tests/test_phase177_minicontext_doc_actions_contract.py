from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MINI_CONTEXT = ROOT / 'client/src/components/mcc/MiniContext.tsx'


def test_minicontext_exposes_richer_doc_actions():
    text = MINI_CONTEXT.read_text()
    assert 'function LinkedDocActions' in text
    assert 'focus in DAG' in text
    assert 'preview' in text
    assert 'copy path' in text
    assert 'open in pane' in text
    assert 'open fullscreen' in text
    assert 'navigator.clipboard?.writeText' in text
    assert 'onPreview={setSelectedDocPath}' in text
    assert 'onOpenFile={onOpenFile}' in text
    assert 'previewing: {selectedDocPath}' in text
