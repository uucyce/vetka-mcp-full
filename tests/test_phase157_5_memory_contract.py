import types
import sys


def test_jarvis_trace_buffer_getter():
    from src.api.handlers import jarvis_handler as jh

    jh._append_jarvis_trace({"ts": 1, "sid": "x", "user_id": "u"})
    items = jh.get_jarvis_turn_traces(limit=1)
    assert isinstance(items, list)
    assert len(items) == 1
    assert items[0].get("sid") == "x"


def test_get_jarvis_context_includes_memory_contract(monkeypatch):
    from src.voice import jarvis_llm as jl

    class Entry:
        def __init__(self, source, content):
            self.source = source
            self.content = content

    class FakeSTM:
        def get_context(self, max_items=5):
            return [Entry("user", "Привет"), Entry("agent", "Здравствуйте")]

    class FakeEngram:
        def get_preference(self, user_id, category, key):
            mapping = {
                ("communication_style", "formality"): 0.5,
                ("communication_style", "preferred_language"): "ru",
                ("communication_style", "prefers_russian"): True,
                ("communication_style", "last_assistant_language"): "ru",
                ("communication_style", "user_name"): "Danila",
            }
            return mapping.get((category, key))

    fake_stm_mod = types.SimpleNamespace(get_stm_buffer=lambda: FakeSTM())
    fake_engram_mod = types.SimpleNamespace(get_engram_user_memory=lambda: FakeEngram())
    fake_elision_mod = types.SimpleNamespace(compress_context=lambda payload, level=2: str(payload))
    monkeypatch.setitem(sys.modules, "src.memory.stm_buffer", fake_stm_mod)
    monkeypatch.setitem(sys.modules, "src.memory.engram_user_memory", fake_engram_mod)
    monkeypatch.setitem(sys.modules, "src.memory.elision", fake_elision_mod)

    ctx = jl.asyncio.run(jl.get_jarvis_context("u1", "привет"))
    assert "session_summary" in ctx
    assert ctx.get("preferred_language") == "ru"
    assert ctx.get("last_assistant_language") == "ru"
    assert ctx.get("prefers_russian") is True
    assert ctx.get("user_name") == "Danila"


def test_extract_client_context_compacts_payload():
    from src.api.handlers import jarvis_handler as jh

    viewport_nodes = [
        {
            "id": f"n{i}",
            "name": f"node-{i}",
            "path": f"/tmp/{i}",
            "type": "file",
            "lod_level": i % 10,
            "distance_to_camera": float(i),
            "is_center": False,
            "is_pinned": False,
            "position": {"x": i, "y": i, "z": i},
        }
        for i in range(80)
    ]
    payload = {
        "viewport_context": {
            "zoom_level": 4,
            "total_visible": 80,
            "total_pinned": 12,
            "camera_position": {"x": 1, "y": 2, "z": 3},
            "camera_target": {"x": 4, "y": 5, "z": 6},
            "viewport_nodes": viewport_nodes,
            "pinned_nodes": viewport_nodes[:20],
        },
        "open_chat_context": {
            "chat_id": "c1",
            "messages": [{"role": "user", "content": "x" * 1000, "timestamp": i} for i in range(20)],
        },
    }

    ctx = jh._extract_client_context(payload)
    vc = ctx["viewport_context"]
    assert len(vc["viewport_nodes"]) <= jh.JARVIS_CONTEXT_MAX_VIEWPORT
    assert len(vc["pinned_nodes"]) <= jh.JARVIS_CONTEXT_MAX_PINNED
    assert len(ctx["open_chat_context"]["messages"]) <= jh.JARVIS_CONTEXT_MAX_CHAT_MESSAGES
    assert len(ctx["open_chat_context"]["messages"][0]["content"]) <= 220


def test_get_jarvis_context_state_key_retrieval(monkeypatch):
    from src.voice import jarvis_llm as jl

    class FakeSTM:
        def get_context(self, max_items=5):
            return []

    class FakeEngram:
        def get_preference(self, user_id, category, key):
            return None

    def fake_retrieve_myco_hidden_context(*, query, focus, top_k=3, min_score=0.22):
        assert "workflow" in query
        assert "expanded" in query
        assert "agent" in query
        return {
            "query": query,
            "items": [
                {"source_path": "docs/guide.md", "snippet": "Use Context panel and run tasks", "score": 0.88}
            ],
            "marker": "test",
        }

    fake_stm_mod = types.SimpleNamespace(get_stm_buffer=lambda: FakeSTM())
    fake_engram_mod = types.SimpleNamespace(get_engram_user_memory=lambda: FakeEngram())
    fake_myco_bridge = types.SimpleNamespace(retrieve_myco_hidden_context=fake_retrieve_myco_hidden_context)

    monkeypatch.setitem(sys.modules, "src.memory.stm_buffer", fake_stm_mod)
    monkeypatch.setitem(sys.modules, "src.memory.engram_user_memory", fake_engram_mod)
    monkeypatch.setitem(sys.modules, "src.services.myco_memory_bridge", fake_myco_bridge)

    extra = {
        "nav_level": "workflow",
        "task_drill_state": "expanded",
        "node_kind": "agent",
        "role": "architect",
        "active_task_id": "tb_1",
    }

    ctx = jl.asyncio.run(jl.get_jarvis_context("u1", "what next", extra_context=extra, session_id="s1"))
    assert "hidden_retrieval" in ctx
    assert isinstance(ctx["hidden_retrieval"].get("items"), list)
    assert len(ctx["hidden_retrieval"]["items"]) == 1
    assert ctx.get("state_key_query")
