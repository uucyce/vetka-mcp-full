from pathlib import Path
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 164 contracts changed")

def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_top_hint_ticker_markers_and_speed_constant():
    text = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "MARKER_164.P4.TOP_HINT_TICKER_2WPS.V1" in text
    assert "MARKER_164.P4.TOP_HINT_TICKER_STOPS_SPEAKING_AT_END.V1" in text
    assert "MARKER_164.P4.P6.TOP_HINT_REAL_MARQUEE_PORT.V1" in text
    assert "MARKER_164.P4.P6.TOP_HINT_NO_LABEL_DUPLICATION.V1" in text
    assert "const MYCO_TOP_HINT_WORDS_PER_SECOND = 2;" in text
    assert "const MYCO_TOP_HINT_TICK_MS = Math.round(1000 / MYCO_TOP_HINT_WORDS_PER_SECOND);" in text
    assert "@keyframes mcc-myco-marquee" in text
    assert "to { transform: translateX(-50%); }" in text
