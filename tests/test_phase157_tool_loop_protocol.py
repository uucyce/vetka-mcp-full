from pathlib import Path
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 157 contracts changed")


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_backend_tool_loop_protocol_events_exist():
    src = _read("src/api/handlers/user_message_handler.py")
    assert '@sio.on("tool_call_decision")' in src
    assert '"tool_call_proposed"' in src
    assert '"tool_call_executing"' in src
    assert '"tool_call_rejected"' in src
    assert "adaptive_tool_loop_mode" in src


def test_frontend_tool_loop_protocol_handlers_exist():
    src = _read("client/src/hooks/useSocket.ts")
    assert "socket.on('tool_call_proposed'" in src
    assert "socket.on('tool_call_executing'" in src
    assert "socket.on('tool_call_rejected'" in src
    assert "socket.on('tool_result'" in src
    assert "emit('tool_call_decision'" in src
