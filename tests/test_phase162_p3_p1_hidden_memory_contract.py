from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_myco_memory_bridge_markers_present():
    code = _read("src/services/myco_memory_bridge.py")
    assert "MARKER_162.P3.MYCO.HIDDEN_TRIPLE_MEMORY_INDEX.V1" in code
    assert "MARKER_162.P3.MYCO.README_SCAN_PIPELINE.V1" in code
    assert "MARKER_162.P3.MYCO.ENGRAM_USER_TASK_MEMORY.V1" in code
    assert "MARKER_162.P3.MYCO.JEPA_GEMMA_LOCAL_FASTPATH.V1" in code
    assert "MARKER_162.P3.MYCO.NO_UI_MEMORY_SURFACE.V1" in code
    assert "def reindex_hidden_instruction_memory" in code
    assert "def build_myco_memory_payload" in code


def test_mcc_routes_expose_myco_hidden_context_endpoints():
    code = _read("src/api/routes/mcc_routes.py")
    assert '@router.post("/myco/hidden-index/reindex")' in code
    assert '@router.post("/myco/context")' in code
    assert "MARKER_162.P3.MYCO.HIDDEN_TRIPLE_MEMORY_INDEX.V1" in code
    assert "MARKER_162.P3.MYCO.ENGRAM_USER_TASK_MEMORY.V1" in code


def test_chat_quick_route_contract_for_myco_fastpath():
    code = _read("src/api/routes/chat_routes.py")
    assert '@router.post("/chat/quick")' in code
    assert "MARKER_162.P3.MYCO.JEPA_GEMMA_LOCAL_FASTPATH.V1" in code
    assert "build_myco_memory_payload" in code
    assert "_build_myco_quick_reply" in code


def test_minichat_routes_helper_mode_to_quick_backend():
    code = _read("client/src/components/mcc/MiniChat.tsx")
    assert "role: helperMode !== 'off' ? 'helper_myco' : 'architect'" in code
    assert "helper_mode: helperMode" in code
