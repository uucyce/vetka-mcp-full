from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_marker_and_status_propagation_present() -> None:
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "MARKER_164.P5.P2.MYCO.TASK_STATUS_PROPAGATION_FROM_ACTIVE_TASK.V1" in code
    assert "const status = String(selectedTask.status || '').toLowerCase().trim();" in code
    assert "status," in code


def test_done_failed_tails_are_actionable() -> None:
    mcc = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    chat = _read("client/src/components/mcc/MiniChat.tsx")
    assert "pick next queued/pending task in Tasks" in mcc
    assert "inspect failure in Context -> retry with corrected model/prompt" in mcc
    assert "pick next queued/pending task in Tasks" in chat
