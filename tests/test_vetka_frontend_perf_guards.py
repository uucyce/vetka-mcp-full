from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_filecard_preview_restored_to_lod_or_hover():
    src = _read("client/src/components/canvas/FileCard.tsx")
    assert "const HOVER_PREVIEW_ENABLED = true;" in src
    assert "(lodLevel >= 5 || isHoveredDebounced)" in src
    assert "setTimeout(() => setIsHoveredDebounced(true), 300)" in src


def test_tree_edges_no_empty_first_frame_fallback():
    src = _read("client/src/components/canvas/TreeEdges.tsx")
    assert "const [visibleEdgeIds, setVisibleEdgeIds] = useState<Set<string>>(() => new Set());" in src
    assert "if (visibleEdgeIds.size === 0) return edges; // Initial render: show all" in src
    assert "const FAR_VIEW_EDGE_BUDGET" not in src


def test_mcc_diagnostics_build_design_is_manual_triggered():
    src = _read("client/src/hooks/useMCCDiagnostics.ts")
    assert "const MIN_BUILD_FETCH_INTERVAL_MS = 15000;" in src
    assert "void doFetch('manual', forceRuntime, true);" in src
    assert "void doFetch('pipeline-activity', false, false);" in src


def test_socket_progressive_voice_handlers_not_duplicated():
    src = _read("client/src/hooks/useSocket.ts")
    assert src.count("socket.on('chat_voice_stream_start'") == 1
    assert src.count("socket.on('chat_voice_stream_chunk'") == 1
    assert src.count("socket.on('chat_voice_stream_end'") == 1
