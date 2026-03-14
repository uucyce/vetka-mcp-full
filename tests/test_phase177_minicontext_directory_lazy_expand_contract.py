from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MINI_CONTEXT = ROOT / 'client/src/components/mcc/MiniContext.tsx'


def test_minicontext_directory_tree_is_lazy_expand():
    text = MINI_CONTEXT.read_text()
    assert '/api/mcc/directory-tree?path=${encodeURIComponent(resolvedPath)}&depth=1' in text
    assert 'const shouldAutoExpand = isDirectory && depth < autoExpandDepth;' in text
    assert 'const [expanded, setExpanded] = useState(shouldAutoExpand);' in text
    assert 'const [loadingChildren, setLoadingChildren] = useState(false);' in text
    assert 'const [loadedOnce, setLoadedOnce]' in text
    assert 'const handleToggle = useCallback(() => {' in text
    assert "expanded ? '▾' : '▸'" in text
    assert 'loading...' in text


def test_minicontext_directory_tree_has_generation_controls():
    text = MINI_CONTEXT.read_text()
    assert 'function descendantLabel(generations: number): string {' in text
    assert "if (generations === 2) return 'grandchildren';" in text
    assert "if (generations === 3) return 'great-grandchildren';" in text
    assert 'const [directoryGenerations, setDirectoryGenerations] = useState(1);' in text
    assert 'showing: {descendantLabel(directoryGenerations)}' in text
    assert '+1 deeper' in text
