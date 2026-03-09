from pathlib import Path

from src.api.routes.chat_routes import _build_myco_quick_reply
from src.services.myco_memory_bridge import expand_myco_query_aliases, retrieve_myco_hidden_context


ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_p3_p4_markers_present_in_runtime_paths():
    bridge = _read("src/services/myco_memory_bridge.py")
    chat = _read("src/api/routes/chat_routes.py")
    assert "MARKER_162.P3.P4.MYCO.RETRIEVAL_BRIDGE.V1" in bridge
    assert "MARKER_162.P3.P4.MYCO.GLOSSARY_ALIAS_EXPANSION.V1" in bridge
    assert "MARKER_162.P3.P4.MYCO.RETRIEVAL_QUALITY_GATE.V1" in bridge
    assert "retrieve_myco_hidden_context" in chat


def test_alias_expansion_uses_glossary_terms():
    pack = expand_myco_query_aliases("ENGRAM DAG quality")
    assert pack["query"] == "ENGRAM DAG quality"
    assert isinstance(pack["expanded_queries"], list)
    assert len(pack["expanded_queries"]) >= 1
    # Canonical glossary has ENGRAM and DAG keys.
    lower_aliases = [x.lower() for x in pack.get("aliases_used") or []]
    assert any(k in lower_aliases for k in ("engram", "dag"))


def test_retrieval_bridge_returns_structured_fallback_or_hits():
    out = retrieve_myco_hidden_context(query="ENGRAM JEPA DAG", focus={"label": "tests/mcc"}, top_k=2)
    assert "marker" in out and "RETRIEVAL_BRIDGE" in out["marker"]
    assert out.get("method") in {"qdrant_semantic", "lexical_fallback", "none"}
    assert isinstance(out.get("items"), list)
    for item in out.get("items"):
        assert "source_path" in item
        assert "score" in item
        assert "snippet" in item


def test_quick_reply_includes_hidden_refs_when_retrieval_exists():
    payload = {
        "user_name": "Danila",
        "user_id": "danila",
        "active_project_id": "vetka_live_03",
        "recent_tasks_by_project": {},
        "hidden_index": {"source_count": 9},
        "fastpath": {"mode": "local_jepa_gemma_first"},
        "orchestration": {
            "multitask": {"active": 1, "queued": 2, "done": 3, "max_concurrent": 4, "auto_dispatch": True, "phase": "121"},
            "digest": {"phase": "162", "summary": "ok"},
        },
    }
    retrieval = {
        "items": [
            {"source_path": "docs/162_ph_MCC_MYCO_HELPER/MYCO_RAG_CORE_V1.md", "score": 0.72, "snippet": "MYCO core contract"},
        ]
    }
    reply = _build_myco_quick_reply("/myco", payload, {"label": "tests/mcc"}, retrieval)
    assert "hidden refs:" in reply
    assert "MYCO_RAG_CORE_V1.md" in reply
