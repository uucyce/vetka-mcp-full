from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_myco_topbar_button_and_mode_toggle_contract():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "MARKER_162.P2.MYCO.TOPROW_BUTTON.V1" in code
    assert "activateMycoInChat" in code
    assert "windowId: 'chat'" in code
    assert "mcc-myco-activate" in code
    assert "MYCO" in code


def test_myco_reply_animation_event_contract():
    mcc_code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    mini_code = _read("client/src/components/mcc/MiniChat.tsx")
    assert "MARKER_162.P2.MYCO.AVATAR_RESPONSE_ANIM.V1" in mcc_code
    assert "mcc-myco-reply" in mcc_code
    assert "emitMycoReplyEvent" in mini_code
    assert "mcc-myco-reply" in mini_code


def test_mycelium_window_title_contract():
    conf = _read("client/src-tauri/tauri.conf.json")
    main_rs = _read("client/src-tauri/src/main.rs")
    assert '"label": "mycelium"' in conf
    assert '"title": "MYCELIUM"' in conf
    assert '.title("MYCELIUM")' in main_rs
