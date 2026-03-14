"""
Phase 156 S6 tests:
- TTS autostart python resolver
- Group role-based voice lock
- Voice mode policy behavior in group chat
"""

from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path
from types import SimpleNamespace
import importlib


def test_resolve_tts_python_prefers_supported_candidate(monkeypatch):
    from src.voice import tts_server_manager as mgr

    env_python = Path("/tmp/fake-env-python")
    fallback_python = Path("/tmp/fake-fallback-python")
    monkeypatch.setattr(mgr, "_python_candidates", lambda: [env_python, fallback_python])
    monkeypatch.setattr(
        mgr,
        "_python_supports_mlx_audio",
        lambda p: p == env_python,
    )

    resolved = mgr._resolve_tts_python()
    assert resolved == env_python


def test_resolve_tts_python_returns_none_when_not_available(monkeypatch):
    from src.voice import tts_server_manager as mgr

    monkeypatch.setattr(mgr, "_python_candidates", lambda: [Path("/tmp/nope")])
    monkeypatch.setattr(mgr, "_python_supports_mlx_audio", lambda _p: False)

    assert mgr._resolve_tts_python() is None


def test_start_tts_server_uses_resolved_python(monkeypatch):
    from src.voice import tts_server_manager as mgr

    fake_python = Path("/usr/bin/python3")
    monkeypatch.setattr(mgr, "_resolve_tts_python", lambda: fake_python)
    monkeypatch.setattr(mgr, "is_tts_running", lambda: False)
    monkeypatch.setattr(mgr, "_wait_for_ready", lambda _timeout: True)

    captured = {}

    class DummyProcess:
        pid = 4242

        def terminate(self):
            return None

        def wait(self, timeout=None):  # noqa: ARG002
            return 0

        def kill(self):
            return None

    def fake_popen(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return DummyProcess()

    monkeypatch.setattr(mgr.subprocess, "Popen", fake_popen)

    proc = mgr.start_tts_server(wait_ready=False)
    assert proc is not None
    assert captured["args"][0] == str(fake_python)
    assert captured["args"][1].endswith("scripts/voice_tts_server.py")
    mgr._tts_process = None


def test_group_role_voice_lock_stable(tmp_path, monkeypatch):
    from src.voice import voice_assignment_registry as regmod

    role_map_path = tmp_path / "agent_role_voice_map.json"
    role_map_path.write_text(
        json.dumps({"roles": {"pm": "ryan", "dev": "eric"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(regmod, "_DEFAULT_ROLE_MAP_PATH", role_map_path)

    registry = regmod.VoiceAssignmentRegistry(path=tmp_path / "assignments.json")

    first = asyncio.run(
        registry.get_or_assign_group_role(
            group_id="g1",
            role="PM",
            provider="xai",
            model_id="grok-4",
            tts_provider="qwen3",
        )
    )
    second = asyncio.run(
        registry.get_or_assign_group_role(
            group_id="g1",
            role="pm",
            provider="openai",
            model_id="gpt-4o",
            tts_provider="qwen3",
        )
    )

    assert first["voice_id"] == "ryan"
    assert second["voice_id"] == "ryan"
    assert first["model_identity_key"] == "group:g1:role:pm"
    assert second["model_identity_key"] == "group:g1:role:pm"


def test_group_voice_reply_mode_auto_resets_on_text_input():
    from src.api.handlers.group_message_handler import _resolve_voice_reply_policy

    group = SimpleNamespace(shared_context={})

    mode1, should_emit1 = _resolve_voice_reply_policy(
        group,
        {"voice_reply_mode": "voice_auto", "voice_input": True},
    )
    assert mode1 == "voice_auto"
    assert should_emit1 is True

    mode2, should_emit2 = _resolve_voice_reply_policy(
        group,
        {"voice_reply_mode": "voice_auto", "voice_input": False},
    )
    assert mode2 == "voice_auto"
    assert should_emit2 is False


def test_registry_migrates_legacy_voice_ids_on_load(tmp_path):
    from src.voice import voice_assignment_registry as regmod

    state_path = tmp_path / "assignments.json"
    state_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "updated_at": "2026-02-26T00:00:00+00:00",
                "assignments": {
                    "group:g1:role:jarvis": {
                        "model_identity_key": "group:g1:role:jarvis",
                        "provider": "openai",
                        "model_id": "gpt-4o",
                        "voice_id": "verse",
                        "tts_provider": "qwen3",
                        "persona_tag": "calm",
                        "created_at": "2026-02-26T00:00:00+00:00",
                        "updated_at": "2026-02-26T00:00:00+00:00",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    registry = regmod.VoiceAssignmentRegistry(path=state_path)
    record = asyncio.run(
        registry.get_or_assign_group_role(
            group_id="g1",
            role="jarvis",
            provider="openai",
            model_id="gpt-4o",
            tts_provider="qwen3",
        )
    )

    assert record["voice_id"] == "dylan"


def test_model_voice_registry_tracks_usage_fields(tmp_path):
    from src.voice import voice_assignment_registry as regmod

    registry = regmod.VoiceAssignmentRegistry(path=tmp_path / "assignments.json")
    first = asyncio.run(
        registry.get_or_assign(
            provider="openrouter",
            model_id="upstage/solar-pro-3:free",
            tts_provider="qwen3",
        )
    )
    second = asyncio.run(
        registry.get_or_assign(
            provider="openrouter",
            model_id="upstage/solar-pro-3:free",
            tts_provider="qwen3",
        )
    )

    assert first["model_identity_key"] == "openrouter:upstage/solar-pro-3:free"
    assert first["status"] == "active"
    assert first["usage_count"] == 1
    assert second["usage_count"] == 2
    assert second["assigned_at"]
    assert second["last_used_at"]


def test_registry_state_has_last_free_voice_marker(tmp_path):
    from src.voice import voice_assignment_registry as regmod

    state_path = tmp_path / "assignments.json"
    registry = regmod.VoiceAssignmentRegistry(path=state_path)
    asyncio.run(
        registry.get_or_assign(
            provider="xai",
            model_id="grok-4-fast",
            tts_provider="qwen3",
        )
    )

    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert "last_free_voice_id" in payload


def test_resolve_jarvis_text_model_prefers_favorites_over_default():
    from src.voice.jarvis_llm import resolve_jarvis_text_model

    model_id, route, reason = resolve_jarvis_text_model(
        default_model="qwen2.5:3b",
        favorites=["x-ai/grok-4.1-fast"],
        registry=None,
    )

    assert model_id == "x-ai/grok-4.1-fast"
    assert route == "provider_registry"
    assert reason == "favorite"


def test_resolve_jarvis_text_model_falls_back_to_free_cloud():
    from src.voice.jarvis_llm import resolve_jarvis_text_model

    class _Type:
        def __init__(self, value):
            self.value = value

    class _Model:
        def __init__(self, mid, mtype, rating):
            self.id = mid
            self.type = _Type(mtype)
            self.rating = rating

    class DummyRegistry:
        def get_all(self):
            return []

        def get_free(self):
            return [
                _Model("qwen2.5:3b", "local", 0.9),
                _Model("deepseek/deepseek-r1:free", "cloud_free", 0.8),
                _Model("meta-llama/llama-3.1-405b-instruct:free", "cloud_free", 0.88),
            ]

        def get_local(self):
            return [_Model("qwen2.5:3b", "local", 0.9)]

    model_id, route, reason = resolve_jarvis_text_model(
        default_model="qwen2.5:3b",
        favorites=[],
        registry=DummyRegistry(),
    )

    assert model_id == "meta-llama/llama-3.1-405b-instruct:free"
    assert route == "provider_registry"
    assert reason == "free_cloud"


def test_get_jarvis_context_merges_client_context():
    jarvis_llm = importlib.import_module("src.voice.jarvis_llm")

    context = asyncio.run(
        jarvis_llm.get_jarvis_context(
            user_id="default_user",
            transcript="check active chat context",
            extra_context={
                "viewport_context": {"zoom_level": 3},
                "pinned_files": [{"path": "/tmp/a.py"}],
                "open_chat_context": {"chat_id": "chat-1", "messages": [{"role": "user", "content": "hello"}]},
                "llm_model": "x-ai/grok-4.1-fast",
            },
        )
    )

    assert context["viewport_context"]["zoom_level"] == 3
    assert context["pinned_files"][0]["path"] == "/tmp/a.py"
    assert context["open_chat_context"]["chat_id"] == "chat-1"
    assert context["llm_model"] == "x-ai/grok-4.1-fast"


def test_voice_audio_timeout_propagates_request_id(monkeypatch):
    mod = importlib.import_module("src.api.handlers.voice_socket_handler")

    class DummySio:
        def __init__(self):
            self.handlers = {}
            self.emitted = []

        def on(self, event):
            def decorator(fn):
                self.handlers[event] = fn
                return fn
            return decorator

        async def emit(self, event, data, to=None):
            self.emitted.append((event, data, to))

    class DummyRouter:
        def __init__(self, *args, **kwargs):
            pass

        async def handle_stream_start(self, sid):  # noqa: ARG002
            return None

        async def handle_pcm_frame(self, sid, pcm):  # noqa: ARG002
            return None

        async def handle_utterance_end(self, sid):  # noqa: ARG002
            return None

        async def handle_stream_end(self, sid):  # noqa: ARG002
            return None

        async def handle_interrupt(self, sid):  # noqa: ARG002
            return None

        async def handle_config(self, sid, data):  # noqa: ARG002
            return None

    async def fake_stt(_audio, _provider):
        await asyncio.sleep(0)
        return "ok"

    captured = {}

    async def fake_wait_for(coro, timeout):
        captured["timeout"] = timeout
        coro.close()
        raise asyncio.TimeoutError

    monkeypatch.setattr(mod, "VoiceRouter", DummyRouter)
    monkeypatch.setattr(mod, "set_voice_router", lambda _router: None)
    monkeypatch.setattr(
        mod,
        "get_voice_service",
        lambda: SimpleNamespace(speech_to_text=fake_stt),
    )
    monkeypatch.setattr(mod.asyncio, "wait_for", fake_wait_for)

    sio = DummySio()
    mod.register_voice_socket_handlers(sio)
    handler = sio.handlers["voice_audio"]

    payload = {
        "audio": base64.b64encode(b"dummy").decode("ascii"),
        "provider": "whisper",
        "request_id": "req-42",
        "timeout_ms": 1,
    }
    asyncio.run(handler("sid-1", payload))

    assert captured["timeout"] == 5.0
    event, data, to = sio.emitted[-1]
    assert event == "voice_error"
    assert to == "sid-1"
    assert data["request_id"] == "req-42"
    assert "timeout (5000ms)" in data["error"]


def test_voice_audio_no_audio_keeps_request_id(monkeypatch):
    mod = importlib.import_module("src.api.handlers.voice_socket_handler")

    class DummySio:
        def __init__(self):
            self.handlers = {}
            self.emitted = []

        def on(self, event):
            def decorator(fn):
                self.handlers[event] = fn
                return fn
            return decorator

        async def emit(self, event, data, to=None):
            self.emitted.append((event, data, to))

    class DummyRouter:
        def __init__(self, *args, **kwargs):
            pass

        async def handle_stream_start(self, sid):  # noqa: ARG002
            return None

        async def handle_pcm_frame(self, sid, pcm):  # noqa: ARG002
            return None

        async def handle_utterance_end(self, sid):  # noqa: ARG002
            return None

        async def handle_stream_end(self, sid):  # noqa: ARG002
            return None

        async def handle_interrupt(self, sid):  # noqa: ARG002
            return None

        async def handle_config(self, sid, data):  # noqa: ARG002
            return None

    monkeypatch.setattr(mod, "VoiceRouter", DummyRouter)
    monkeypatch.setattr(mod, "set_voice_router", lambda _router: None)
    monkeypatch.setattr(
        mod,
        "get_voice_service",
        lambda: SimpleNamespace(speech_to_text=lambda *_a, **_k: "unused"),
    )

    sio = DummySio()
    mod.register_voice_socket_handlers(sio)
    handler = sio.handlers["voice_audio"]
    asyncio.run(handler("sid-2", {"request_id": "r-no-audio"}))

    event, data, to = sio.emitted[-1]
    assert event == "voice_error"
    assert to == "sid-2"
    assert data["request_id"] == "r-no-audio"


def test_qwen_tts_synthesize_route_success(monkeypatch):
    routes = importlib.import_module("src.api.routes.voice_storage_routes")

    monkeypatch.setattr("src.voice.tts_server_manager.is_tts_running", lambda: True)
    monkeypatch.setattr("src.voice.tts_server_manager.start_tts_server", lambda **_k: None)
    monkeypatch.setattr(
        routes,
        "store_voice_audio_bytes",
        lambda *_a, **_k: {
            "storage_id": "s1",
            "url": "/api/voice/storage/s1",
            "duration_ms": 1234,
        },
    )

    class DummyResponse:
        def __init__(self, status_code=200, payload=None):
            self.status_code = status_code
            self._payload = payload or {}
            self.content = b"x"

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError("http error")

        def json(self):
            return self._payload

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, timeout=None):  # noqa: ARG002
            return DummyResponse(status_code=200, payload={"ok": True})

        async def post(self, url, json=None, timeout=None):  # noqa: ARG002
            return DummyResponse(
                status_code=200,
                payload={"audio": base64.b64encode(b"wav-bytes").decode("ascii")},
            )

    monkeypatch.setattr(routes.httpx, "AsyncClient", lambda *a, **k: DummyClient())

    req = routes.TTSSynthesizeRequest(text="hello world", speaker="dylan", language="en")
    result = asyncio.run(routes.synthesize_qwen_tts(req))
    assert result["ok"] is True
    assert result["speaker"] == "dylan"
    assert result["storage_id"] == "s1"
    assert result["url"] == "/api/voice/storage/s1"


def test_qwen_tts_synthesize_route_unavailable(monkeypatch):
    routes = importlib.import_module("src.api.routes.voice_storage_routes")

    monkeypatch.setattr("src.voice.tts_server_manager.is_tts_running", lambda: True)
    monkeypatch.setattr("src.voice.tts_server_manager.start_tts_server", lambda **_k: None)

    class DummyResponse:
        def __init__(self, status_code=503, payload=None):
            self.status_code = status_code
            self._payload = payload or {}
            self.content = b"x"

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, timeout=None):  # noqa: ARG002
            return DummyResponse(status_code=503)

    monkeypatch.setattr(routes.httpx, "AsyncClient", lambda *a, **k: DummyClient())

    req = routes.TTSSynthesizeRequest(text="hello")
    try:
        asyncio.run(routes.synthesize_qwen_tts(req))
        raise AssertionError("Expected HTTPException")
    except Exception as exc:
        from fastapi import HTTPException

        assert isinstance(exc, HTTPException)
        assert exc.status_code == 503


def test_qwen_tts_synthesize_route_normalizes_legacy_speaker(monkeypatch):
    routes = importlib.import_module("src.api.routes.voice_storage_routes")

    monkeypatch.setattr("src.voice.tts_server_manager.is_tts_running", lambda: True)
    monkeypatch.setattr("src.voice.tts_server_manager.start_tts_server", lambda **_k: None)
    monkeypatch.setattr(
        routes,
        "store_voice_audio_bytes",
        lambda *_a, **_k: {"storage_id": "s2", "url": "/api/voice/storage/s2", "duration_ms": 1000},
    )

    captured = {}

    class DummyResponse:
        def __init__(self):
            self.status_code = 200
            self.content = b"x"

        def json(self):
            return {"audio": base64.b64encode(b"wav-bytes").decode("ascii")}

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, timeout=None):  # noqa: ARG002
            return type("Health", (), {"status_code": 200})()

        async def post(self, url, json=None, timeout=None):  # noqa: ARG002
            captured["speaker"] = json.get("speaker")
            return DummyResponse()

    monkeypatch.setattr(routes.httpx, "AsyncClient", lambda *a, **k: DummyClient())
    result = asyncio.run(
        routes.synthesize_qwen_tts(
            routes.TTSSynthesizeRequest(text="hello", speaker="verse", language="en")
        )
    )
    assert captured["speaker"] == "dylan"
    assert result["speaker"] == "dylan"


def test_normalize_qwen_audio_payload_wraps_raw_pcm():
    routes = importlib.import_module("src.api.routes.voice_storage_routes")
    raw_pcm = b"\x00\x00\x10\x00\xf0\xff" * 1000
    out, content_type, ext = routes.normalize_qwen_audio_payload(raw_pcm)
    assert content_type == "audio/wav"
    assert ext == "wav"
    assert out[:4] == b"RIFF"


def test_qwen_tts_synthesize_route_converts_raw_pcm_to_wav(monkeypatch):
    routes = importlib.import_module("src.api.routes.voice_storage_routes")

    monkeypatch.setattr("src.voice.tts_server_manager.is_tts_running", lambda: True)
    monkeypatch.setattr("src.voice.tts_server_manager.start_tts_server", lambda **_k: None)

    captured = {}

    def _store(payload, **kwargs):
        captured["payload"] = payload
        captured["kwargs"] = kwargs
        return {"storage_id": "s3", "url": "/api/voice/storage/s3", "duration_ms": 123}

    monkeypatch.setattr(routes, "store_voice_audio_bytes", _store)

    class DummyResponse:
        def __init__(self, status_code=200, payload=None):
            self.status_code = status_code
            self._payload = payload or {}
            self.content = b"x"
            self.text = ""

        def json(self):
            return self._payload

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, timeout=None):  # noqa: ARG002
            return DummyResponse(status_code=200, payload={"ok": True})

        async def post(self, url, json=None, timeout=None):  # noqa: ARG002
            raw_pcm = b"\x00\x00\x10\x00\xf0\xff" * 1000
            return DummyResponse(
                status_code=200,
                payload={"audio": base64.b64encode(raw_pcm).decode("ascii")},
            )

    monkeypatch.setattr(routes.httpx, "AsyncClient", lambda *a, **k: DummyClient())

    result = asyncio.run(routes.synthesize_qwen_tts(routes.TTSSynthesizeRequest(text="pcm test")))
    assert result["ok"] is True
    assert result["format"] == "wav"
    assert captured["payload"][:4] == b"RIFF"
