from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCC = ROOT / "client/src/components/mcc/MyceliumCommandCenter.tsx"
MINI = ROOT / "client/src/components/mcc/MiniContext.tsx"


def test_mcc_code_viewer_supports_fullscreen_mode():
    text = MCC.read_text()
    assert "const [artifactViewerMode, setArtifactViewerMode] = useState<'pane' | 'fullscreen'>('pane');" in text
    assert "artifactViewerMode === 'fullscreen' ? '96%' : '80%'" in text
    assert "artifactViewerMode === 'fullscreen' ? 'pane' : 'fullscreen'" in text
    assert "const handleOpenFileInPane = useCallback((path: string, mode: 'pane' | 'fullscreen' = 'pane') => {" in text


def test_minicontext_breadcrumbs_are_clickable():
    text = MINI.read_text()
    assert 'function CodeBreadcrumbs' in text
    assert 'onJump?: (path: string) => void' in text
    assert "const partialPath = parts.slice(0, idx + 1).join('/');" in text
    assert 'title={`switch context to ${partialPath}`}' in text
