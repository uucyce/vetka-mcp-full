from pathlib import Path

from src.api.routes.chat_routes import _build_myco_quick_reply


ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_myco_memory_bridge_has_orchestration_snapshot_contract():
    code = _read("src/services/myco_memory_bridge.py")
    assert "MARKER_162.P3.P2.MYCO.ORCHESTRATION_SNAPSHOT.V1" in code
    assert "def _digest_snapshot" in code
    assert "MARKER_162.P3.P3.MYCO.MULTITASK_CFG_SNAPSHOT.V1" in code
    assert '"multitask": multitask' in code
    assert '"digest": digest_snapshot' in code
    assert "myco_last_phase" in code


def test_chat_quick_wires_p3_p2_runtime_persistence_contract():
    code = _read("src/api/routes/chat_routes.py")
    assert "MARKER_162.P3.P2.MYCO.ORCHESTRATION_SNAPSHOT.V1" in code
    assert "persist_myco_runtime_facts" in code
    assert '"orchestration": payload.get("orchestration")' in code


def test_myco_quick_reply_includes_multitask_and_digest_context():
    payload = {
        "user_name": "Danila",
        "user_id": "danila",
        "active_project_id": "vetka_live_03",
        "recent_tasks_by_project": {
            "vetka_live_03": [{"title": "Wire MYCO orchestration", "status": "running"}],
        },
        "hidden_index": {"source_count": 12},
        "fastpath": {"mode": "local_jepa_gemma_first"},
        "orchestration": {
            "multitask": {"active": 2, "queued": 5, "done": 11, "max_concurrent": 4, "auto_dispatch": True, "phase": "121"},
            "digest": {"phase": "162", "summary": "myco helper stabilization"},
        },
    }
    reply = _build_myco_quick_reply("/myco", payload, {"label": "tests/mcc"})
    assert "multitask: active 2" in reply
    assert "cap 4" in reply
    assert "auto_dispatch on" in reply
    assert "digest phase: 162" in reply
    assert "hidden memory sources: 12" in reply


def test_rag_split_docs_exist_with_markers():
    core = _read("docs/162_ph_MCC_MYCO_HELPER/MYCO_RAG_CORE_V1.md")
    roles = _read("docs/162_ph_MCC_MYCO_HELPER/MYCO_RAG_AGENT_ROLES_V1.md")
    playbook = _read("docs/162_ph_MCC_MYCO_HELPER/MYCO_RAG_USER_PLAYBOOK_V1.md")
    assert "MARKER_162.P3.P3.MYCO.RAG_CORE_SPLIT.V1" in core
    assert "MARKER_162.P3.P3.MYCO.RAG_AGENT_ROLES_SPLIT.V1" in roles
    assert "MARKER_162.P3.P3.MYCO.RAG_USER_PLAYBOOK_SPLIT.V1" in playbook
