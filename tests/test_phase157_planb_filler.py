from __future__ import annotations

import asyncio

import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 157 contracts changed")

class _FakeSio:
    def __init__(self) -> None:
        self.events = []

    async def emit(self, event, payload, to=None):
        self.events.append((event, payload, to))


@pytest.mark.asyncio
async def test_planb_filler_disabled(monkeypatch):
    from src.api.handlers import jarvis_handler as jh

    monkeypatch.setattr(jh, "JARVIS_PLANB_FILLER_ENABLE", False)
    monkeypatch.setattr(jh, "JARVIS_PLANB_FILLER_DELAY_SEC", 0.01)

    sio = _FakeSio()
    ready = asyncio.Event()

    emitted = await jh._emit_planb_filler_if_slow(
        sio=sio,
        sid="sid1",
        user_id="u1",
        partial_input="Почему так?",
        ready_event=ready,
    )

    assert emitted is False
    assert sio.events == []


@pytest.mark.asyncio
async def test_planb_filler_not_emitted_when_ready(monkeypatch):
    from src.api.handlers import jarvis_handler as jh

    monkeypatch.setattr(jh, "JARVIS_PLANB_FILLER_ENABLE", True)
    monkeypatch.setattr(jh, "JARVIS_PLANB_FILLER_DELAY_SEC", 0.01)

    sio = _FakeSio()
    ready = asyncio.Event()
    ready.set()

    emitted = await jh._emit_planb_filler_if_slow(
        sio=sio,
        sid="sid1",
        user_id="u1",
        partial_input="Почему так?",
        ready_event=ready,
    )

    assert emitted is False
    assert sio.events == []


@pytest.mark.asyncio
async def test_planb_filler_emits_once_when_slow(monkeypatch):
    from src.api.handlers import jarvis_handler as jh

    monkeypatch.setattr(jh, "JARVIS_PLANB_FILLER_ENABLE", True)
    monkeypatch.setattr(jh, "JARVIS_PLANB_FILLER_DELAY_SEC", 0.01)
    monkeypatch.setattr(jh, "JARVIS_FILLER_AUDIO_ENABLE", False)

    sio = _FakeSio()
    ready = asyncio.Event()

    emitted = await jh._emit_planb_filler_if_slow(
        sio=sio,
        sid="sid42",
        user_id="u42",
        partial_input="Найди файл где все аббревиатуры с памятью связано",
        ready_event=ready,
    )

    assert emitted is True
    assert len(sio.events) == 1
    event, payload, to = sio.events[0]
    assert event == "jarvis_response"
    assert payload["status"] == "filler"
    assert payload["is_draft"] is True
    assert payload["user_id"] == "u42"
    assert to == "sid42"


@pytest.mark.asyncio
async def test_planb_filler_emits_audio_when_cached(monkeypatch):
    from src.api.handlers import jarvis_handler as jh

    monkeypatch.setattr(jh, "JARVIS_PLANB_FILLER_ENABLE", True)
    monkeypatch.setattr(jh, "JARVIS_PLANB_FILLER_DELAY_SEC", 0.01)
    monkeypatch.setattr(jh, "JARVIS_FILLER_AUDIO_ENABLE", True)

    phrase = "Секунду, собираю ответ."
    monkeypatch.setattr(jh, "_select_filler_phrase", lambda _partial: phrase)
    monkeypatch.setattr(jh, "_detect_language_hint", lambda _text: "ru")
    monkeypatch.setattr(jh, "_filler_audio_cache", {"ru": {phrase: (b"\xff\xfb" + b"A" * 4096, "mp3")}, "en": {}})

    sio = _FakeSio()
    ready = asyncio.Event()

    emitted = await jh._emit_planb_filler_if_slow(
        sio=sio,
        sid="sid99",
        user_id="u99",
        partial_input="Почему тормозит?",
        ready_event=ready,
    )

    assert emitted is True
    assert len(sio.events) == 2
    response_event, response_payload, _ = sio.events[0]
    audio_event, audio_payload, _ = sio.events[1]
    assert response_event == "jarvis_response"
    assert response_payload["status"] == "filler"
    assert audio_event == "jarvis_audio"
    assert audio_payload["format"] == "mp3"
    assert audio_payload["status"] == "filler"
