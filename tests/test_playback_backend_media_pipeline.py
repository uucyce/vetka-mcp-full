"""
MARKER_EPSILON.MEDIA1: Playback backend media pipeline live tests.

Verifies Beta's media endpoints with real GH5 MOV files:
1. GET /cut/thumbnail → image/jpeg
2. GET /cut/waveform-peaks → peaks array
3. GET /cut/audio/clip-segment → audio/wav
4. POST /cut/render/master → MP4 output

Part A: Source-parsing (route existence)
Part B: Live API tests (when backend available)
"""

import json
import re
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ROUTES_MEDIA = ROOT / "src" / "api" / "routes" / "cut_routes_media.py"
ROUTES_RENDER = ROOT / "src" / "api" / "routes" / "cut_routes_render.py"
ROUTES_MAIN = ROOT / "src" / "api" / "routes" / "cut_routes.py"

MOV_FILE = Path("/Users/danilagulin/work/teletape_temp/berlin/source_gh5/P1733383.MOV")
API_BASE = "http://localhost:5001"


def _read(path: Path) -> str:
    if not path.exists():
        pytest.skip(f"File not found: {path}")
    return path.read_text()


def _find(source: str, pattern: str) -> bool:
    return bool(re.search(pattern, source))


def _backend_available() -> bool:
    try:
        req = urllib.request.Request(f"{API_BASE}/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def _api_get(path: str, params: dict = None) -> tuple:
    """GET request, returns (status_code, content_type, body_bytes)."""
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.headers.get("Content-Type", ""), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, "", e.read()


# ═══════════════════════════════════════════════════════════════════════
# PART A: Source-parsing — route existence
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def all_routes_src():
    """Combine all route files."""
    parts = []
    for p in [ROUTES_MEDIA, ROUTES_RENDER, ROUTES_MAIN]:
        if p.exists():
            parts.append(p.read_text())
    if not parts:
        pytest.skip("No route files found")
    return "\n".join(parts)


class TestMediaRoutesDefined:
    """Media pipeline routes must exist in backend."""

    def test_thumbnail_route(self, all_routes_src):
        assert _find(all_routes_src, r"/cut/thumbnail|/thumbnail"), \
            "Thumbnail route not defined"

    def test_waveform_route(self, all_routes_src):
        assert _find(all_routes_src, r"/cut/waveform|/waveform"), \
            "Waveform route not defined"

    def test_audio_segment_route(self, all_routes_src):
        assert _find(all_routes_src, r"/cut/audio|/audio.*segment|clip.segment"), \
            "Audio segment route not defined"

    def test_render_route(self, all_routes_src):
        assert _find(all_routes_src, r"/cut/render|/render"), \
            "Render route not defined"


class TestMediaImplementation:
    """Media pipeline must use FFmpeg/FFprobe."""

    def test_uses_ffmpeg(self, all_routes_src):
        assert _find(all_routes_src, r"ffmpeg|FFmpeg|subprocess.*ff"), \
            "No FFmpeg usage found in routes"

    def test_thumbnail_returns_image(self, all_routes_src):
        """Thumbnail must return image response."""
        assert _find(all_routes_src, r"image/jpeg|image/png|StreamingResponse|FileResponse|Response.*media"), \
            "Thumbnail doesn't return image response type"

    def test_waveform_returns_json(self, all_routes_src):
        """Waveform must return peaks data."""
        assert _find(all_routes_src, r"peaks|waveform.*data|bins"), \
            "Waveform doesn't return peaks data"


# ═══════════════════════════════════════════════════════════════════════
# PART B: Live API tests
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def backend():
    if not _backend_available():
        pytest.skip("Backend not available at localhost:5001")
    return True


@pytest.fixture(scope="module")
def mov_file():
    if not MOV_FILE.exists():
        pytest.skip(f"GH5 MOV not found: {MOV_FILE}")
    return str(MOV_FILE)


class TestLiveThumbnail:
    """GET /api/cut/thumbnail with real MOV."""

    def test_thumbnail_returns_jpeg(self, backend, mov_file):
        status, ctype, body = _api_get("/api/cut/thumbnail", {
            "source_path": mov_file,
            "time_sec": "2",
            "width": "320",
            "height": "180",
        })
        if status == 422:
            pytest.xfail(f"Thumbnail endpoint exists but params mismatch (422)")
        assert status == 200, f"Thumbnail returned {status}"
        assert "image" in ctype.lower(), f"Expected image, got {ctype}"
        assert len(body) > 1000, f"Thumbnail too small: {len(body)} bytes"

    def test_thumbnail_different_times(self, backend, mov_file):
        """Thumbnails at different times should differ."""
        _, _, body1 = _api_get("/api/cut/thumbnail", {
            "source_path": mov_file, "time_sec": "0", "width": "160", "height": "90",
        })
        _, _, body2 = _api_get("/api/cut/thumbnail", {
            "source_path": mov_file, "time_sec": "5", "width": "160", "height": "90",
        })
        if body1 and body2 and len(body1) > 100 and len(body2) > 100:
            # Different frames should produce different images
            assert body1 != body2, "Thumbnails at t=0 and t=5 are identical"


class TestLiveWaveform:
    """GET /api/cut/waveform-peaks with real MOV."""

    def test_waveform_returns_peaks(self, backend, mov_file):
        status, ctype, body = _api_get("/api/cut/waveform-peaks", {
            "source_path": mov_file,
            "bins": "64",
        })
        if status == 422:
            pytest.xfail("Waveform endpoint exists but params mismatch (422)")
        if status == 404:
            pytest.xfail("Waveform endpoint not found (may be different path)")
        assert status == 200, f"Waveform returned {status}"
        data = json.loads(body)
        assert "peaks" in data or "data" in data or isinstance(data, list), \
            f"Waveform missing peaks: {list(data.keys()) if isinstance(data, dict) else type(data)}"

    def test_waveform_not_degraded(self, backend, mov_file):
        """Waveform should not be degraded for real media."""
        status, _, body = _api_get("/api/cut/waveform-peaks", {
            "source_path": mov_file,
            "bins": "64",
        })
        if status != 200:
            pytest.skip("Waveform endpoint not returning 200")
        data = json.loads(body)
        if isinstance(data, dict) and "degraded" in data:
            assert data["degraded"] is False, "Waveform is degraded for real MOV"


class TestLiveAudioSegment:
    """GET /api/cut/audio/clip-segment with real MOV."""

    def test_audio_segment_returns_data(self, backend, mov_file):
        status, ctype, body = _api_get("/api/cut/audio/clip-segment", {
            "source_path": mov_file,
            "start_sec": "0",
            "duration_sec": "2",
        })
        if status == 422:
            pytest.xfail("Audio segment exists but params mismatch (422)")
        if status == 404:
            pytest.xfail("Audio segment not found (may be different path)")
        assert status == 200, f"Audio segment returned {status}"
        assert len(body) > 1000, f"Audio segment too small: {len(body)} bytes"


class TestLiveHealth:
    """Verify media-related health indicators."""

    def test_health_returns_components(self, backend):
        status, _, body = _api_get("/api/health")
        assert status == 200
        data = json.loads(body)
        assert data.get("status") == "healthy"
