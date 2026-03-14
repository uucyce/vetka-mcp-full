from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_coder_is_not_hardcoded_running_in_inline_workflow():
    code = (ROOT / "client/src/components/mcc/MyceliumCommandCenter.tsx").read_text(encoding="utf-8")
    assert "Coder (Build)', status: 'running'" not in code
    assert "role === 'coder' ? 'running' : 'pending'" not in code
