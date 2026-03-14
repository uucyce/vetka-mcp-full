from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_myco_p4_p1_proactive_markers_present():
    code = _read("client/src/components/mcc/MiniChat.tsx")
    assert "MARKER_162.P4.P1.MYCO.CONTEXT_PROACTIVE_CHAT_COMPACT.V1" in code
    assert "MARKER_162.P4.P1.MYCO.CONTEXT_PROACTIVE_CHAT_EXPANDED.V1" in code
    assert "MARKER_162.P4.P1.MYCO.COMPACT_NO_STALE_SETMESSAGES.V1" in code
    assert "MARKER_162.P4.P1.MYCO.OFF_MODE_NO_HELPER_ECHO.V1" in code
    assert "MARKER_162.P4.P1.MYCO.NO_FILE_LABEL_NOISE_IN_CHAT.V1" in code


def test_chat_compact_has_no_expanded_state_write_regression():
    code = _read("client/src/components/mcc/MiniChat.tsx")
    compact_block = code.split("function ChatExpanded", 1)[0]
    assert "setMessages(" not in compact_block
    assert "setLastAnswer(" in compact_block


def test_proactive_context_key_dedupe_contract():
    code = _read("client/src/components/mcc/MiniChat.tsx")
    assert "buildMycoContextKey" in code
    assert "proactiveContextKeyRef" in code
    assert "emitMycoReplyEvent()" in code


def test_helper_messages_hidden_when_mode_off_contract():
    code = _read("client/src/components/mcc/MiniChat.tsx")
    assert "lastAnswerSource" in code
    assert "helperMode === 'off' && lastAnswerSource === 'helper'" in code
    assert "messages.filter((m) => m.role !== 'helper_myco')" in code


def test_no_helper_off_echo_message_in_architect_mode_contract():
    code = _read("client/src/components/mcc/MiniChat.tsx")
    assert "MYCO helper is off. Toggle helper icon." not in code
    assert "Helper is off. Toggle helper icon to passive/active." not in code
