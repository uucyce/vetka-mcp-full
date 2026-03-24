# MARKER_QA.PYRAMID_T2: Tier 2 — vite build smoke test
# Catches missing exports, import errors that tsc misses (esbuild vs tsc)
# Target: <10s, catches EFFECT_APPLY_MAP class of bugs before merge
#
# Three-tier test pyramid (Delta-3 idea):
#   Tier 1 (0.1s): Static file/export checks — test_monochrome_static, test_cut_new_components
#   Tier 2 (3-10s): vite build — THIS FILE
#   Tier 3 (8s): Playwright navigate + root check — test_monochrome_enforcement.spec.cjs
import subprocess
import shutil
import os
import pytest

CLIENT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "client",
)

HAS_NODE = shutil.which("node") is not None
HAS_VITE = os.path.exists(os.path.join(CLIENT_DIR, "node_modules", ".bin", "vite"))


@pytest.mark.skipif(not HAS_NODE, reason="node not installed")
@pytest.mark.skipif(not HAS_VITE, reason="vite not installed (run npm install in client/)")
class TestViteBuildSmoke:
    """Tier 2: vite build catches missing exports and import resolution errors."""

    def test_vite_build_succeeds(self):
        """Run `vite build` and assert exit code 0.

        This catches:
        - Missing exports (EFFECT_APPLY_MAP class)
        - Broken imports after route/module refactors
        - esbuild-specific errors tsc doesn't flag

        Known failures should be tracked as tasks, not xfail'd.
        """
        result = subprocess.run(
            ["node_modules/.bin/vite", "build", "--mode", "production"],
            cwd=CLIENT_DIR,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            # Extract the key error line for clear failure message
            stderr = result.stderr or result.stdout
            error_lines = [
                line for line in stderr.splitlines()
                if "is not exported" in line
                or "Could not resolve" in line
                or "error" in line.lower()
            ]
            error_summary = "\n".join(error_lines[:5]) if error_lines else stderr[-500:]
            pytest.fail(
                f"vite build failed (exit {result.returncode}).\n"
                f"This means broken imports/exports exist in CUT client.\n"
                f"Errors:\n{error_summary}"
            )

    def test_vite_build_no_missing_exports(self):
        """Specifically check for 'is not exported by' errors — the #1 build blocker."""
        result = subprocess.run(
            ["node_modules/.bin/vite", "build", "--mode", "production"],
            cwd=CLIENT_DIR,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = (result.stderr or "") + (result.stdout or "")
        missing_exports = [
            line.strip()
            for line in output.splitlines()
            if "is not exported by" in line
        ]
        if missing_exports:
            pytest.fail(
                f"Missing exports detected ({len(missing_exports)}):\n"
                + "\n".join(missing_exports)
                + "\nEach needs an `export` added in the source file."
            )
