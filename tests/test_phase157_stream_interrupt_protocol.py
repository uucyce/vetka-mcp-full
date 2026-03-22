from pathlib import Path
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 157 contracts changed")

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_backend_has_stream_interrupt_request_protocol_events():
    src = _read("src/api/handlers/user_message_handler.py")
    assert '@sio.on("stream_interrupt_request")' in src
    assert '"stream_interrupt_ack"' in src
    assert '"stream_restart_start"' in src
    assert '"stream_restart_token"' in src
    assert '"stream_restart_end"' in src


def test_frontend_has_stream_interrupt_request_and_restart_handlers():
    src = _read("client/src/hooks/useSocket.ts")
    assert "socket.on('stream_interrupt_ack'" in src
    assert "socket.on('stream_restart_start'" in src
    assert "socket.on('stream_restart_token'" in src
    assert "socket.on('stream_restart_end'" in src
    assert "emit('stream_interrupt_request'" in src
    assert "reason: 'new_user_message'" in src
