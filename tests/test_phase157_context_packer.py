from src.orchestration.context_packer import ContextPacker


def test_context_packer_modality_detection():
    packer = ContextPacker()
    pinned = [
        {"path": "/repo/a.py"},
        {"path": "/repo/b.md"},
        {"path": "/repo/audio.wav"},
        {"path": "/repo/video.mp4"},
    ]
    assert packer._detect_modalities(pinned) >= 3


def test_context_packer_trigger_policy_docs():
    packer = ContextPacker()
    triggered = packer._should_trigger_jepa(
        overflow_risk=False,
        docs_count=packer.docs_threshold + 1,
        entropy=0.1,
        modality_mix=1,
    )
    assert triggered is True


def test_context_packer_trigger_policy_overflow():
    packer = ContextPacker()
    triggered = packer._should_trigger_jepa(
        overflow_risk=True,
        docs_count=1,
        entropy=0.1,
        modality_mix=1,
    )
    assert triggered is True


def test_context_packer_pack_uses_jepa_when_triggered(monkeypatch):
    import asyncio
    import types

    monkeypatch.setenv("VETKA_CONTEXT_PACKER_ENABLED", "true")
    monkeypatch.setenv("VETKA_CONTEXT_PACKER_JEPA_ENABLE", "true")
    monkeypatch.setenv("VETKA_CONTEXT_PACKER_DOCS_THRESHOLD", "1")
    monkeypatch.setenv("VETKA_CONTEXT_PACKER_HYSTERESIS_ON", "1")

    fake_message_utils = types.ModuleType("src.api.handlers.message_utils")
    fake_message_utils.build_pinned_context = lambda *args, **kwargs: "PINNED"
    fake_message_utils.build_viewport_summary = lambda *_args, **_kwargs: "VIEWPORT"
    fake_message_utils.build_json_context = lambda *_args, **_kwargs: '{"ok": true}'
    monkeypatch.setitem(__import__("sys").modules, "src.api.handlers.message_utils", fake_message_utils)

    fake_adapter = types.ModuleType("src.services.mcc_jepa_adapter")

    class _Result:
        provider_mode = "live-jepa"
        detail = "ok"
        vectors = [[1.0, 0.0], [0.8, 0.2], [0.7, 0.3]]

    fake_adapter.embed_texts_for_overlay = lambda **_kwargs: _Result()
    monkeypatch.setitem(__import__("sys").modules, "src.services.mcc_jepa_adapter", fake_adapter)

    packer = ContextPacker()
    result = asyncio.run(
        packer.pack(
            user_query="query",
            pinned_files=[{"path": "/repo/a.py"}, {"path": "/repo/b.md"}],
            viewport_context={"zoom": 4},
            session_id="s1",
            model_name="grok-4",
        )
    )

    assert result.trace["jepa_trigger"] is True
    assert result.trace["jepa_mode"] is True
    assert result.trace["packing_path"] == "hybrid-jepa"
    assert "JEPA SEMANTIC CORE" in result.jepa_context
    assert "semantic_focus:" in result.jepa_context
    assert "representative_items:" in result.jepa_context


def test_context_packer_pack_graceful_if_jepa_fails(monkeypatch):
    import asyncio
    import types

    monkeypatch.setenv("VETKA_CONTEXT_PACKER_ENABLED", "true")
    monkeypatch.setenv("VETKA_CONTEXT_PACKER_JEPA_ENABLE", "true")
    monkeypatch.setenv("VETKA_CONTEXT_PACKER_DOCS_THRESHOLD", "1")
    monkeypatch.setenv("VETKA_CONTEXT_PACKER_HYSTERESIS_ON", "1")

    fake_message_utils = types.ModuleType("src.api.handlers.message_utils")
    fake_message_utils.build_pinned_context = lambda *args, **kwargs: "PINNED"
    fake_message_utils.build_viewport_summary = lambda *_args, **_kwargs: "VIEWPORT"
    fake_message_utils.build_json_context = lambda *_args, **_kwargs: '{"ok": true}'
    monkeypatch.setitem(__import__("sys").modules, "src.api.handlers.message_utils", fake_message_utils)

    fake_adapter = types.ModuleType("src.services.mcc_jepa_adapter")

    def _boom(**_kwargs):
        raise RuntimeError("adapter down")

    fake_adapter.embed_texts_for_overlay = _boom
    monkeypatch.setitem(__import__("sys").modules, "src.services.mcc_jepa_adapter", fake_adapter)

    packer = ContextPacker()
    result = asyncio.run(
        packer.pack(
            user_query="query",
            pinned_files=[{"path": "/repo/a.py"}, {"path": "/repo/b.md"}],
            viewport_context={"zoom": 4},
            session_id="s1",
            model_name="grok-4",
        )
    )

    assert result.trace["jepa_trigger"] is True
    assert result.trace["jepa_mode"] is False
    assert result.trace["packing_path"] == "algorithmic"
    assert result.trace["jepa_error"] == "RuntimeError"
    assert result.jepa_context == ""


def test_context_packer_pack_legacy_mode_when_disabled(monkeypatch):
    import asyncio
    import types

    monkeypatch.setenv("VETKA_CONTEXT_PACKER_ENABLED", "false")

    fake_message_utils = types.ModuleType("src.api.handlers.message_utils")
    fake_message_utils.build_pinned_context = lambda *args, **kwargs: "PINNED-LEGACY"
    fake_message_utils.build_viewport_summary = lambda *_args, **_kwargs: "VIEWPORT-LEGACY"
    fake_message_utils.build_json_context = lambda *_args, **_kwargs: '{"legacy": true}'
    monkeypatch.setitem(__import__("sys").modules, "src.api.handlers.message_utils", fake_message_utils)

    packer = ContextPacker()
    result = asyncio.run(
        packer.pack(
            user_query="query",
            pinned_files=[{"path": "/repo/a.py"}],
            viewport_context={"zoom": 1},
            session_id="s1",
            model_name="grok-4",
        )
    )

    assert result.trace["packing_path"] == "legacy"
    assert result.trace["packer_enabled"] is False
    assert result.pinned_context == "PINNED-LEGACY"
    assert result.viewport_summary == "VIEWPORT-LEGACY"
    assert result.jepa_context == ""


def test_context_packer_hysteresis_stabilizes_trigger(monkeypatch):
    monkeypatch.setenv("VETKA_CONTEXT_PACKER_HYSTERESIS_ON", "3")
    monkeypatch.setenv("VETKA_CONTEXT_PACKER_HYSTERESIS_OFF", "2")

    packer = ContextPacker()

    active, t1 = packer._apply_hysteresis(session_id="s1", trigger_raw=True)
    assert active is False
    assert t1["hysteresis_on_streak"] == 1

    active, t2 = packer._apply_hysteresis(session_id="s1", trigger_raw=True)
    assert active is False
    assert t2["hysteresis_on_streak"] == 2

    active, t3 = packer._apply_hysteresis(session_id="s1", trigger_raw=True)
    assert active is True
    assert t3["hysteresis_active"] is True

    active, t4 = packer._apply_hysteresis(session_id="s1", trigger_raw=False)
    assert active is True
    assert t4["hysteresis_off_streak"] == 1

    active, t5 = packer._apply_hysteresis(session_id="s1", trigger_raw=False)
    assert active is False
    assert t5["hysteresis_active"] is False


def test_context_packer_recent_stats_collects_latency(monkeypatch):
    import asyncio
    import types

    monkeypatch.setenv("VETKA_CONTEXT_PACKER_ENABLED", "true")
    monkeypatch.setenv("VETKA_CONTEXT_PACKER_JEPA_ENABLE", "true")
    monkeypatch.setenv("VETKA_CONTEXT_PACKER_DOCS_THRESHOLD", "1")
    monkeypatch.setenv("VETKA_CONTEXT_PACKER_HYSTERESIS_ON", "1")

    fake_message_utils = types.ModuleType("src.api.handlers.message_utils")
    fake_message_utils.build_pinned_context = lambda *args, **kwargs: "PINNED"
    fake_message_utils.build_viewport_summary = lambda *_args, **_kwargs: "VIEWPORT"
    fake_message_utils.build_json_context = lambda *_args, **_kwargs: '{"ok": true}'
    monkeypatch.setitem(__import__("sys").modules, "src.api.handlers.message_utils", fake_message_utils)

    fake_adapter = types.ModuleType("src.services.mcc_jepa_adapter")

    class _Result:
        provider_mode = "live-jepa"
        detail = "ok"
        vectors = [[1.0, 0.0], [0.8, 0.2], [0.7, 0.3]]

    fake_adapter.embed_texts_for_overlay = lambda **_kwargs: _Result()
    monkeypatch.setitem(__import__("sys").modules, "src.services.mcc_jepa_adapter", fake_adapter)

    packer = ContextPacker()
    for _ in range(3):
        asyncio.run(
            packer.pack(
                user_query="query",
                pinned_files=[{"path": "/repo/a.py"}, {"path": "/repo/b.md"}],
                viewport_context={"zoom": 4},
                session_id="s-stats",
                model_name="grok-4",
            )
        )

    stats = packer.get_recent_stats(limit=10)
    assert stats["count"] >= 3
    assert "pack_latency_ms_p50" in stats
    assert "jepa_mode_ratio" in stats
