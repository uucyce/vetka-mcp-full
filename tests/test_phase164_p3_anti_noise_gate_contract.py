from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding='utf-8')


def test_anti_noise_gate_doc_has_marker_and_policy():
    text = _read('docs/164_MYCO_ARH_MCC/PHASE_164_P3_ANTI_NOISE_GATE_2026-03-08.md')
    assert 'MARKER_164.P3.ANTI_NOISE_SILENCE_DEDUPE_GATE.V1' in text
    assert 'helperMode=off' in text
    assert 'No duplicate helper message' in text


def test_mini_chat_contains_existing_off_mode_guards():
    code = _read('client/src/components/mcc/MiniChat.tsx')
    assert 'MARKER_162.P4.P1.MYCO.OFF_MODE_NO_HELPER_ECHO.V1' in code
    assert 'messages.filter((m) => m.role !== \'helper_myco\')' in code
