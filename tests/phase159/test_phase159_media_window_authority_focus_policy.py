from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_r3_focus_authority_policy_enforced():
    player = _read("client/src/components/artifact/viewers/VideoArtifactPlayer.tsx")

    assert "MARKER_159.WINFS.R3_AUTHORITY" in player
    assert "const localHasFocus = document.hasFocus();" in player
    assert "const remoteHasFocus = Boolean(envelope.trace?.has_focus);" in player
    assert "if (!localHasFocus && remoteHasFocus) return true;" in player
    assert "if (localHasFocus && !remoteHasFocus) return false;" in player
    assert "return remoteTs > lastAppliedRemoteTsRef.current;" in player

