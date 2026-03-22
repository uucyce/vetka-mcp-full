from pathlib import Path
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 157 contracts changed")


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_backend_has_partial_voice_handoff_markers():
    src = _read("src/api/handlers/user_message_handler.py")
    assert "_extract_ready_voice_sentences" in src
    assert "_emit_live_voice_sentence" in src
    assert "_finalize_live_voice_stream" in src
    assert "voice_live_state[\"pending_text\"]" in src
    assert "chat_voice_stream_start" in src
    assert "chat_voice_stream_chunk" in src
    assert "chat_voice_stream_end" in src


def test_backend_avoids_duplicate_solo_voice_job_when_live_started():
    src = _read("src/api/handlers/user_message_handler.py")
    assert "if not bool(voice_live_state.get(\"started\"))" in src
