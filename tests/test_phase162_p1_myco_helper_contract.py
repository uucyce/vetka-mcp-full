from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_store_has_myco_mode_contract():
    code = _read("client/src/store/useMCCStore.ts")
    assert "export type MycoHelperMode = 'off' | 'passive' | 'active'" in code
    assert "helperMode: MycoHelperMode" in code
    assert "setHelperMode: (mode: MycoHelperMode) => void" in code
    assert "MYCO_HELPER_MODE_STORAGE_KEY" in code


def test_minichat_has_myco_role_injection_contract():
    code = _read("client/src/components/mcc/MiniChat.tsx")
    assert "helper_myco" in code
    assert "isMycoTrigger" in code
    assert "myco:off" in code
    assert "buildMycoReply" in code
