"""Performance baseline tests for CUT NLE.
Source-parsing tier: verify performance guards exist in code.
Live API tier: measure actual response times when backend available.

Task: tb_1774312433_65
"""
import os
import re
import json
import time
import pytest
from pathlib import Path

# Resolve project root (worktree-safe)
_THIS = Path(__file__).resolve()
_ROOT = _THIS
while _ROOT.name != 'vetka_live_03' and _ROOT != _ROOT.parent:
    _ROOT = _ROOT.parent
    if (_ROOT / '.claude').exists():
        break

CLIENT_SRC = _ROOT / 'client' / 'src'
SERVER_SRC = _ROOT / 'src'

BENCHMARKS_DIR = _ROOT / 'data' / 'benchmarks'


def _read(path):
    """Read file content, return empty string if not found."""
    try:
        return Path(path).read_text(encoding='utf-8', errors='replace')
    except (FileNotFoundError, IsADirectoryError):
        return ''


class TestPerfGuardsExist:
    """Verify performance guard patterns exist in source code."""

    def test_video_preview_raf_loop(self):
        """VideoPreview must use requestAnimationFrame for playback sync."""
        src = _read(CLIENT_SRC / 'components' / 'cut' / 'VideoPreview.tsx')
        assert 'requestAnimationFrame' in src, \
            "VideoPreview.tsx missing rAF loop — playback sync will jank"

    def test_audio_meter_raf_loop(self):
        """AudioLevelMeter must use rAF for visualization."""
        src = _read(CLIENT_SRC / 'components' / 'cut' / 'AudioLevelMeter.tsx')
        assert 'requestAnimationFrame' in src, \
            "AudioLevelMeter.tsx missing rAF loop"

    def test_shuttle_performance_now(self):
        """Shuttle playback must use performance.now() for timing."""
        src = _read(CLIENT_SRC / 'components' / 'cut' / 'CutEditorLayoutV2.tsx')
        assert 'performance.now()' in src, \
            "CutEditorLayoutV2.tsx missing performance.now() for shuttle timing"

    def test_media_throttle_guard(self):
        """Media timeupdate must be throttled (not every frame)."""
        # Check for throttle constant in any relevant file
        found = False
        for f in (CLIENT_SRC / 'components' / 'cut').glob('*.tsx'):
            content = _read(f)
            if re.search(r'THROTTLE.*(?:MS|ms|INTERVAL)', content):
                found = True
                break
            if re.search(r'throttle.*\d{2,}', content):
                found = True
                break
        assert found, "No media throttle guard found in CUT components"

    def test_cancel_raf_on_unmount(self):
        """VideoPreview must cancel rAF on cleanup to prevent memory leaks."""
        src = _read(CLIENT_SRC / 'components' / 'cut' / 'VideoPreview.tsx')
        assert 'cancelAnimationFrame' in src, \
            "VideoPreview.tsx missing cancelAnimationFrame — memory leak risk"

    def test_no_sync_blocking_in_render_path(self):
        """Render endpoint must use async/background workers, not sync blocking."""
        routes_render = None
        for name in ['cut_routes_render.py', 'cut_routes.py']:
            p = SERVER_SRC / 'api' / 'routes' / name
            if p.exists():
                routes_render = _read(p)
                break
        if routes_render is None:
            pytest.skip("Render routes not found")
        # Should have async def or background task pattern
        assert 'async def' in routes_render or 'BackgroundTask' in routes_render or 'asyncio' in routes_render, \
            "Render route appears to be synchronous — will block server"

    def test_vite_build_no_giant_chunks(self):
        """Vite config should not suppress chunk size warnings excessively."""
        vite_cfg = _read(CLIENT_SRC.parent / 'vite.config.ts')
        if not vite_cfg:
            pytest.skip("vite.config.ts not found")
        # If chunkSizeWarningLimit is set, it should be <= 1000KB
        match = re.search(r'chunkSizeWarningLimit\s*:\s*(\d+)', vite_cfg)
        if match:
            limit = int(match.group(1))
            assert limit <= 1000, f"Chunk size warning limit too high: {limit}KB"

    def test_timeline_no_inline_style_in_render(self):
        """TimelineTrackView should not use inline style objects in render (causes re-renders)."""
        src = _read(CLIENT_SRC / 'components' / 'cut' / 'TimelineTrackView.tsx')
        if not src:
            pytest.skip("TimelineTrackView.tsx not found")
        # Count style={{ occurrences — too many inline styles hurt perf
        inline_count = len(re.findall(r'style=\{\{', src))
        # Baseline 2026-03-26: 73 inline styles. Target: reduce over time.
        assert inline_count < 100, \
            f"TimelineTrackView has {inline_count} inline style objects (baseline: 73, target: <100)"

    def test_store_no_full_state_subscription(self):
        """CUT components should use selectors, not subscribe to full store state."""
        cut_dir = CLIENT_SRC / 'components' / 'cut'
        if not cut_dir.exists():
            pytest.skip("CUT components dir not found")
        # Check for useCutEditorStore() without selector — causes re-render on any change
        violations = []
        for f in cut_dir.glob('*.tsx'):
            content = _read(f)
            # Bare useCutEditorStore() without selector arg
            bare = re.findall(r'useCutEditorStore\(\s*\)', content)
            if bare:
                violations.append(f"{f.name}: {len(bare)} bare store subscription(s)")
        assert not violations, \
            f"Components subscribing to full store (perf risk):\n" + "\n".join(violations)

    def test_zustand_selector_pattern(self):
        """CUT components should use arrow fn selectors with zustand store."""
        src = _read(CLIENT_SRC / 'components' / 'cut' / 'TimelineTrackView.tsx')
        if not src:
            pytest.skip("TimelineTrackView.tsx not found")
        # Should have useCutEditorStore((s) => ...) pattern
        selectors = re.findall(r'useCutEditorStore\(\s*\(', src)
        assert len(selectors) > 0, \
            "TimelineTrackView should use zustand selectors for perf"

    def test_websocket_reconnect_guard(self):
        """WebSocket hook should have reconnection logic."""
        hooks_dir = CLIENT_SRC / 'hooks'
        if not hooks_dir.exists():
            pytest.skip("hooks dir not found")
        found = False
        for f in hooks_dir.glob('*.ts'):
            content = _read(f)
            if 'WebSocket' in content and ('reconnect' in content.lower() or 'retry' in content.lower()):
                found = True
                break
        # Also check useSocket
        for f in hooks_dir.glob('*.tsx'):
            content = _read(f)
            if 'WebSocket' in content and ('reconnect' in content.lower() or 'retry' in content.lower()):
                found = True
                break
        assert found, "No WebSocket reconnection guard found in hooks"


class TestViteBuildPerformance:
    """Measure and record vite build time."""

    @pytest.mark.slow
    def test_vite_build_time(self):
        """tsc --noEmit should complete in under 30 seconds.

        Records timing even if TS errors exist (separate concern from perf).
        """
        import subprocess
        client_dir = CLIENT_SRC.parent
        if not (client_dir / 'node_modules').exists():
            pytest.skip("node_modules not installed")

        start = time.time()
        result = subprocess.run(
            ['npx', 'tsc', '--noEmit'],
            cwd=str(client_dir),
            capture_output=True, text=True, timeout=60
        )
        tsc_time = time.time() - start

        # Count TS errors
        error_count = result.stdout.count(': error TS')

        # Record benchmark regardless of pass/fail
        BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)
        benchmark = {
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'metric': 'tsc_noEmit_seconds',
            'value': round(tsc_time, 2),
            'exit_code': result.returncode,
            'ts_error_count': error_count,
            'branch': 'claude/cut-qa-2',
        }
        bench_file = BENCHMARKS_DIR / 'build_perf.jsonl'
        with open(bench_file, 'a') as f:
            f.write(json.dumps(benchmark) + '\n')

        # Performance assertion — even with TS errors, timing should be fast
        assert tsc_time < 30, f"tsc --noEmit took {tsc_time:.1f}s (target: <30s)"
        # TS errors are a separate concern; xfail if present
        if result.returncode != 0:
            pytest.xfail(f"tsc has {error_count} type errors (perf OK: {tsc_time:.1f}s)")


class TestLiveAPIPerformance:
    """Live API performance tests — only run when backend is available."""

    @pytest.fixture(autouse=True)
    def check_backend(self):
        """Skip all tests if backend is not running."""
        import urllib.request
        try:
            urllib.request.urlopen('http://127.0.0.1:5001/api/health', timeout=2)
        except Exception:
            pytest.skip("Backend not running on port 5001")

    def _timed_request(self, url, method='GET', data=None, timeout=10):
        """Make a timed HTTP request, return (response_time_ms, status_code, body)."""
        import urllib.request
        start = time.time()
        req = urllib.request.Request(url, method=method)
        if data:
            req.data = json.dumps(data).encode()
            req.add_header('Content-Type', 'application/json')
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode()
                elapsed_ms = (time.time() - start) * 1000
                return elapsed_ms, resp.status, body
        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            return elapsed_ms, 0, str(e)

    def _record(self, metric, value_ms, target_ms=None):
        """Record a benchmark measurement."""
        BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'metric': metric,
            'value_ms': round(value_ms, 1),
            'target_ms': target_ms,
            'passed': value_ms <= target_ms if target_ms else None,
            'branch': 'claude/cut-qa-2',
        }
        with open(BENCHMARKS_DIR / 'api_perf.jsonl', 'a') as f:
            f.write(json.dumps(entry) + '\n')

    def test_health_endpoint_latency(self):
        """Health check should respond in < 100ms."""
        ms, status, _ = self._timed_request('http://127.0.0.1:5001/api/health')
        self._record('health_latency_ms', ms, 100)
        assert status == 200
        assert ms < 100, f"Health endpoint took {ms:.0f}ms (target: <100ms)"

    def test_project_state_latency(self):
        """Project state load should respond in < 500ms."""
        ms, status, _ = self._timed_request('http://127.0.0.1:5001/api/cut/project-state')
        self._record('project_state_latency_ms', ms, 500)
        # 404 is OK if no project is loaded
        assert status in (200, 404, 422)
        if status == 200:
            assert ms < 500, f"Project state took {ms:.0f}ms (target: <500ms)"

    def test_thumbnail_latency(self):
        """Thumbnail generation should respond in < 2000ms."""
        ms, status, _ = self._timed_request('http://127.0.0.1:5001/api/cut/thumbnail?t=0')
        self._record('thumbnail_latency_ms', ms, 2000)
        # May fail if no media loaded — that's OK for baseline
        if status == 200:
            assert ms < 2000, f"Thumbnail took {ms:.0f}ms (target: <2000ms)"

    def test_timeline_list_latency(self):
        """Timeline list should respond in < 200ms."""
        ms, status, _ = self._timed_request('http://127.0.0.1:5001/api/cut/timeline/list')
        self._record('timeline_list_latency_ms', ms, 200)
        assert status in (200, 404)
        if status == 200:
            assert ms < 200, f"Timeline list took {ms:.0f}ms (target: <200ms)"

    def test_undo_stack_latency(self):
        """Undo stack query should respond in < 100ms."""
        ms, status, _ = self._timed_request('http://127.0.0.1:5001/api/cut/undo-stack')
        self._record('undo_stack_latency_ms', ms, 100)
        if status == 200:
            assert ms < 100, f"Undo stack took {ms:.0f}ms (target: <100ms)"

    def test_render_presets_latency(self):
        """Render presets list should respond in < 200ms."""
        ms, status, _ = self._timed_request('http://127.0.0.1:5001/api/cut/render/presets')
        self._record('render_presets_latency_ms', ms, 200)
        if status == 200:
            assert ms < 200, f"Render presets took {ms:.0f}ms (target: <200ms)"


class TestPytestSuitePerformance:
    """Meta-test: measure pytest suite execution characteristics."""

    def test_total_test_count_tracked(self):
        """Record current test count as baseline metric."""
        import sys
        import subprocess
        # Use --collect-only to count tests without running them
        # Exclude this file to avoid recursive pytest invocation issues
        result = subprocess.run(
            [sys.executable, '-m', 'pytest',
             'tests/', '--collect-only', '-q', '--tb=no',
             '--ignore=tests/test_performance_baseline.py'],
            cwd=str(_ROOT),
            capture_output=True, text=True, timeout=120
        )
        # Parse "X tests collected" or "X items" or "X test"
        match = re.search(r'(\d+)\s+(?:tests?|items?)', result.stdout)
        count = int(match.group(1)) if match else 0

        BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'metric': 'total_test_count',
            'value': count,
            'branch': 'claude/cut-qa-2',
        }
        with open(BENCHMARKS_DIR / 'suite_metrics.jsonl', 'a') as f:
            f.write(json.dumps(entry) + '\n')

        # Baseline: worktree has ~7000 tests, main has more.
        # Alert if it drops below a reasonable minimum.
        assert count > 100, f"Test count suspiciously low: {count} (expected >100)"
