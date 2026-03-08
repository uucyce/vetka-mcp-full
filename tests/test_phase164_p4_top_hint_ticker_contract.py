from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_top_hint_ticker_markers_and_speed_constant():
    text = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "MARKER_164.P4.TOP_HINT_TICKER_2WPS.V1" in text
    assert "MARKER_164.P4.TOP_HINT_TICKER_STOPS_SPEAKING_AT_END.V1" in text
    assert "const MYCO_TOP_HINT_WORDS_PER_SECOND = 2;" in text
    assert "const MYCO_TOP_HINT_TICK_MS = Math.round(1000 / MYCO_TOP_HINT_WORDS_PER_SECOND);" in text
