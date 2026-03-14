from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / 'client/src/main.tsx'


def test_main_router_normalizes_trailing_slash_for_mycelium_route():
    text = MAIN.read_text()
    assert "const pathname = window.location.pathname.replace(/\\/+$/, '') || '/';" in text
    assert "if (pathname === '/mycelium') {" in text
    assert "return <MyceliumStandalone />;" in text
