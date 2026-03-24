"""
Beta B61–B66 Verification Suite
================================
Static analysis tests — no live server required.
All tests complete in <1 second via imports and file reads.

Coverage:
  B61 — CutBootstrapRequest.timeline_id default field
  B62 — /api/cut/stream endpoint with Range/206 support
  B63 — .cutignore pruning via os.walk in bootstrap
  B64 — auto-scan trigger in _execute_cut_bootstrap (XFAIL: lost in B65 extraction)
  B65 — cut_routes_bootstrap.py extraction + cut_routes.py re-export
  B66 — dead code cleanup: no _OLD_REMOVED / _DEPRECATED / commented-out defs
"""

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Project root on sys.path so src.* imports resolve without a running server
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BOOTSTRAP_PY = PROJECT_ROOT / "src" / "api" / "routes" / "cut_routes_bootstrap.py"
MEDIA_PY     = PROJECT_ROOT / "src" / "api" / "routes" / "cut_routes_media.py"
CUT_ROUTES_PY = PROJECT_ROOT / "src" / "api" / "routes" / "cut_routes.py"


# ---------------------------------------------------------------------------
# B61 — timeline_id field on CutBootstrapRequest
# ---------------------------------------------------------------------------

class TestB61TimelineIdField:
    """B61: CutBootstrapRequest must carry a timeline_id field defaulting to 'main'."""

    def test_cutbootstraprequest_importable(self):
        """CutBootstrapRequest is importable from cut_routes_bootstrap."""
        from src.api.routes.cut_routes_bootstrap import CutBootstrapRequest  # noqa: F401
        assert CutBootstrapRequest is not None

    def test_timeline_id_field_exists(self):
        """CutBootstrapRequest has a 'timeline_id' field."""
        from src.api.routes.cut_routes_bootstrap import CutBootstrapRequest
        assert "timeline_id" in CutBootstrapRequest.model_fields, (
            "Expected 'timeline_id' in CutBootstrapRequest.model_fields"
        )

    def test_timeline_id_default_is_main(self):
        """timeline_id defaults to 'main' when not explicitly supplied."""
        from src.api.routes.cut_routes_bootstrap import CutBootstrapRequest
        # Supply the two required fields; leave timeline_id unset to exercise the default.
        instance = CutBootstrapRequest(source_path="/tmp/test", sandbox_root="/tmp/sandbox")
        assert instance.timeline_id == "main", (
            f"Expected timeline_id default 'main', got {instance.timeline_id!r}"
        )


# ---------------------------------------------------------------------------
# B62 — /api/cut/stream endpoint
# ---------------------------------------------------------------------------

class TestB62StreamEndpoint:
    """B62: cut_routes_media.py must implement an HTTP Range-aware /stream endpoint."""

    @pytest.fixture(scope="class")
    def media_text(self):
        return MEDIA_PY.read_text(encoding="utf-8")

    def test_stream_route_decorator_present(self, media_text):
        """Route decorator for '/stream' is present in cut_routes_media.py."""
        assert '"/stream"' in media_text or "'/stream'" in media_text, (
            "Expected route decorator with '/stream' in cut_routes_media.py"
        )

    def test_range_header_regex_present(self, media_text):
        """A Range-header parsing regex (bytes= pattern) is defined."""
        # The file defines _RANGE_RE = _re.compile(r"bytes=(\d+)-(\d*)")
        assert "bytes=" in media_text, (
            "Expected 'bytes=' regex pattern for Range header parsing in cut_routes_media.py"
        )
        # More specific: the compiled regex variable
        assert "_RANGE_RE" in media_text, (
            "Expected '_RANGE_RE' compiled regex in cut_routes_media.py"
        )

    def test_206_status_code_present(self, media_text):
        """HTTP 206 Partial Content status code is referenced."""
        assert "206" in media_text, (
            "Expected HTTP 206 status code in cut_routes_media.py"
        )

    def test_content_range_header_present(self, media_text):
        """Content-Range response header is set in the stream handler."""
        assert "Content-Range" in media_text, (
            "Expected 'Content-Range' header string in cut_routes_media.py"
        )


# ---------------------------------------------------------------------------
# B63 — .cutignore support with os.walk pruning
# ---------------------------------------------------------------------------

class TestB63Cutignore:
    """B63: Bootstrap must load .cutignore and prune os.walk accordingly."""

    @pytest.fixture(scope="class")
    def bootstrap_text(self):
        return BOOTSTRAP_PY.read_text(encoding="utf-8")

    def test_cutignore_variable_present(self, bootstrap_text):
        """'_cutignore' variable or logic is referenced in cut_routes_bootstrap.py."""
        assert "_cutignore" in bootstrap_text, (
            "Expected '_cutignore' reference in cut_routes_bootstrap.py"
        )

    def test_os_walk_pruning_present(self, bootstrap_text):
        """os.walk is used for directory traversal in cut_routes_bootstrap.py."""
        assert "os.walk" in bootstrap_text, (
            "Expected 'os.walk' in cut_routes_bootstrap.py for directory pruning"
        )

    def test_default_excludes_pycache(self, bootstrap_text):
        """Default exclude list contains __pycache__."""
        assert "__pycache__" in bootstrap_text, (
            "Expected '__pycache__' in default cutignore excludes"
        )

    def test_default_excludes_ds_store(self, bootstrap_text):
        """.DS_Store is in the default exclude list."""
        assert ".DS_Store" in bootstrap_text, (
            "Expected '.DS_Store' in default cutignore excludes"
        )

    def test_default_excludes_node_modules(self, bootstrap_text):
        """node_modules is in the default exclude list."""
        assert "node_modules" in bootstrap_text, (
            "Expected 'node_modules' in default cutignore excludes"
        )

    def test_default_excludes_git(self, bootstrap_text):
        """.git is in the default exclude list."""
        assert ".git" in bootstrap_text, (
            "Expected '.git' in default cutignore excludes"
        )


# ---------------------------------------------------------------------------
# B64 — auto-scan trigger inside _execute_cut_bootstrap  (XFAIL)
# ---------------------------------------------------------------------------

class TestB64AutoScanTrigger:
    """
    B64: _execute_cut_bootstrap should launch a background scan job via threading.Thread.

    XFAIL: The auto-scan wiring was lost when _execute_cut_bootstrap was extracted
    to cut_routes_bootstrap.py during B65.  A dedicated fix task
    tb_1774324565_1 has been created to restore this behaviour.
    """

    @pytest.mark.xfail(
        reason="B64 auto-scan lost during B65 extraction — task tb_1774324565_1",
        strict=False,
    )
    def test_execute_bootstrap_launches_scan_thread(self):
        """
        _execute_cut_bootstrap references _run_cut_scan_matrix_job or
        threading.Thread to launch a background scan after bootstrapping.
        """
        bootstrap_text = BOOTSTRAP_PY.read_text(encoding="utf-8")

        # Locate the body of _execute_cut_bootstrap
        func_marker = "_execute_cut_bootstrap"
        assert func_marker in bootstrap_text, (
            f"Function '{func_marker}' not found in cut_routes_bootstrap.py"
        )

        func_start = bootstrap_text.index(f"def {func_marker}")
        # Grab a generous slice after the function definition
        func_body = bootstrap_text[func_start: func_start + 4000]

        has_scan_job   = "_run_cut_scan_matrix_job" in func_body
        has_thread     = "threading.Thread" in func_body

        assert has_scan_job or has_thread, (
            "_execute_cut_bootstrap must reference _run_cut_scan_matrix_job "
            "or threading.Thread to auto-launch a scan (B64 feature)"
        )


# ---------------------------------------------------------------------------
# B65 — bootstrap extraction
# ---------------------------------------------------------------------------

class TestB65BootstrapExtraction:
    """B65: Core bootstrap logic must live in cut_routes_bootstrap.py and be re-exported by cut_routes.py."""

    def test_cut_routes_bootstrap_file_exists(self):
        """cut_routes_bootstrap.py file exists on disk."""
        assert BOOTSTRAP_PY.exists(), (
            f"Expected file not found: {BOOTSTRAP_PY}"
        )

    def test_cutbootstraprequest_importable_from_bootstrap(self):
        """CutBootstrapRequest is importable from cut_routes_bootstrap."""
        from src.api.routes.cut_routes_bootstrap import CutBootstrapRequest
        assert CutBootstrapRequest is not None

    def test_execute_cut_bootstrap_importable(self):
        """_execute_cut_bootstrap is importable from cut_routes_bootstrap."""
        from src.api.routes.cut_routes_bootstrap import _execute_cut_bootstrap
        assert callable(_execute_cut_bootstrap)

    def test_run_cut_bootstrap_job_importable(self):
        """_run_cut_bootstrap_job is importable from cut_routes_bootstrap."""
        from src.api.routes.cut_routes_bootstrap import _run_cut_bootstrap_job
        assert callable(_run_cut_bootstrap_job)

    def test_cut_routes_imports_from_bootstrap(self):
        """cut_routes.py imports bootstrap symbols from cut_routes_bootstrap."""
        cut_routes_text = CUT_ROUTES_PY.read_text(encoding="utf-8")
        assert "cut_routes_bootstrap" in cut_routes_text, (
            "Expected 'cut_routes_bootstrap' import statement in cut_routes.py"
        )


# ---------------------------------------------------------------------------
# B66 — dead code cleanup
# ---------------------------------------------------------------------------

class TestB66DeadCodeCleanup:
    """B66: cut_routes.py must have no legacy dead-code markers or commented-out function defs."""

    @pytest.fixture(scope="class")
    def cut_routes_text(self):
        return CUT_ROUTES_PY.read_text(encoding="utf-8")

    def test_no_old_removed_marker(self, cut_routes_text):
        """No '_OLD_REMOVED' markers remain in cut_routes.py."""
        assert "_OLD_REMOVED" not in cut_routes_text, (
            "Found '_OLD_REMOVED' dead-code marker in cut_routes.py"
        )

    def test_no_deprecated_marker(self, cut_routes_text):
        """No '_DEPRECATED' markers remain in cut_routes.py."""
        assert "_DEPRECATED" not in cut_routes_text, (
            "Found '_DEPRECATED' dead-code marker in cut_routes.py"
        )

    def test_no_removed_comment_marker(self, cut_routes_text):
        """No '# REMOVED' inline comments remain in cut_routes.py."""
        assert "# REMOVED" not in cut_routes_text, (
            "Found '# REMOVED' comment marker in cut_routes.py"
        )

    def test_no_commented_out_def(self, cut_routes_text):
        """No commented-out function definitions ('# def ...') remain in cut_routes.py."""
        lines = cut_routes_text.splitlines()
        offending = [
            (i + 1, line.strip())
            for i, line in enumerate(lines)
            if line.strip().startswith("# def ") or line.strip().startswith("# async def ")
        ]
        assert len(offending) == 0, (
            f"Found {len(offending)} commented-out function definition(s) in cut_routes.py:\n"
            + "\n".join(f"  line {ln}: {txt}" for ln, txt in offending)
        )
