"""
Contract tests for the shared Playwright global setup infrastructure.

Verifies:
1. globalSetup.ts exists and contains required symbols
2. globalTeardown.ts exists and contains required symbols
3. playwright.config.ts references both globalSetup and globalTeardown
4. No individual spec files spawn their own Vite server via spawn/exec
   (documents current state — does NOT fail if specs still have their own server)
"""
import os
import re
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_DIR = os.path.join(BASE_DIR, "client")
E2E_DIR = os.path.join(CLIENT_DIR, "e2e")
PLAYWRIGHT_CONFIG = os.path.join(CLIENT_DIR, "playwright.config.ts")
GLOBAL_SETUP = os.path.join(E2E_DIR, "globalSetup.ts")
GLOBAL_TEARDOWN = os.path.join(E2E_DIR, "globalTeardown.ts")


# ---------------------------------------------------------------------------
# 1. File existence
# ---------------------------------------------------------------------------

def test_global_setup_file_exists():
    """globalSetup.ts must exist in client/e2e/."""
    assert os.path.isfile(GLOBAL_SETUP), (
        f"globalSetup.ts not found at {GLOBAL_SETUP}"
    )


def test_global_teardown_file_exists():
    """globalTeardown.ts must exist in client/e2e/."""
    assert os.path.isfile(GLOBAL_TEARDOWN), (
        f"globalTeardown.ts not found at {GLOBAL_TEARDOWN}"
    )


# ---------------------------------------------------------------------------
# 2. globalSetup.ts content
# ---------------------------------------------------------------------------

def test_global_setup_exports_default():
    """globalSetup.ts must export a default function."""
    content = open(GLOBAL_SETUP).read()
    assert "export default globalSetup" in content or "export default async" in content, (
        "globalSetup.ts must export a default function"
    )


def test_global_setup_starts_vite():
    """globalSetup.ts must spawn a Vite process."""
    content = open(GLOBAL_SETUP).read()
    assert "spawn" in content, "globalSetup.ts must use spawn() to start Vite"
    assert "vite" in content.lower() or "npm" in content, (
        "globalSetup.ts must reference vite or npm run dev"
    )


def test_global_setup_waits_for_server():
    """globalSetup.ts must wait for the server to be ready (HTTP polling)."""
    content = open(GLOBAL_SETUP).read()
    assert "waitForHttpOk" in content or "waitUntilReady" in content or "http.get" in content, (
        "globalSetup.ts must poll/wait for server readiness"
    )


def test_global_setup_stores_pid():
    """globalSetup.ts must store the PID so globalTeardown can kill the process."""
    content = open(GLOBAL_SETUP).read()
    assert "VETKA_VITE_PID" in content or "VITE_PID" in content, (
        "globalSetup.ts must store PID in an env variable for teardown"
    )


def test_global_setup_uses_env_port():
    """globalSetup.ts must use VETKA_GLOBAL_PORT env variable for the port."""
    content = open(GLOBAL_SETUP).read()
    assert "VETKA_GLOBAL_PORT" in content, (
        "globalSetup.ts must honour VETKA_GLOBAL_PORT environment variable"
    )


# ---------------------------------------------------------------------------
# 3. globalTeardown.ts content
# ---------------------------------------------------------------------------

def test_global_teardown_exports_default():
    """globalTeardown.ts must export a default function."""
    content = open(GLOBAL_TEARDOWN).read()
    assert "export default globalTeardown" in content or "export default async" in content, (
        "globalTeardown.ts must export a default function"
    )


def test_global_teardown_kills_process():
    """globalTeardown.ts must kill the Vite process."""
    content = open(GLOBAL_TEARDOWN).read()
    assert "process.kill" in content or "SIGTERM" in content, (
        "globalTeardown.ts must kill the Vite process"
    )


def test_global_teardown_reads_pid():
    """globalTeardown.ts must read the PID from env."""
    content = open(GLOBAL_TEARDOWN).read()
    assert "VETKA_VITE_PID" in content or "VITE_PID" in content, (
        "globalTeardown.ts must read the PID env variable set by globalSetup"
    )


# ---------------------------------------------------------------------------
# 4. playwright.config.ts references
# ---------------------------------------------------------------------------

def test_playwright_config_references_global_setup():
    """playwright.config.ts must reference globalSetup."""
    content = open(PLAYWRIGHT_CONFIG).read()
    assert "globalSetup" in content, (
        "playwright.config.ts must set globalSetup property"
    )
    assert "globalSetup.ts" in content or "globalSetup'" in content or 'globalSetup"' in content or "./e2e/globalSetup" in content, (
        "playwright.config.ts must point to the globalSetup file"
    )


def test_playwright_config_references_global_teardown():
    """playwright.config.ts must reference globalTeardown."""
    content = open(PLAYWRIGHT_CONFIG).read()
    assert "globalTeardown" in content, (
        "playwright.config.ts must set globalTeardown property"
    )
    assert "globalTeardown.ts" in content or "globalTeardown'" in content or 'globalTeardown"' in content or "./e2e/globalTeardown" in content, (
        "playwright.config.ts must point to the globalTeardown file"
    )


def test_playwright_config_no_web_server():
    """playwright.config.ts must NOT use webServer (specs self-manage servers)."""
    content = open(PLAYWRIGHT_CONFIG).read()
    # webServer would conflict with per-spec server management
    # Allow the key to appear in comments but not as a live config key
    non_comment_lines = [
        line for line in content.splitlines()
        if not line.strip().startswith("//") and not line.strip().startswith("*")
    ]
    non_comment_content = "\n".join(non_comment_lines)
    assert "webServer:" not in non_comment_content, (
        "playwright.config.ts must not configure webServer — specs manage their own servers"
    )


# ---------------------------------------------------------------------------
# 5. Spec audit: document which specs still spawn their own server
# ---------------------------------------------------------------------------

def _find_spec_files():
    specs = []
    for fname in os.listdir(E2E_DIR):
        if fname.endswith(".spec.cjs") or fname.endswith(".spec.ts") or fname.endswith(".spec.js"):
            specs.append(os.path.join(E2E_DIR, fname))
    return sorted(specs)


def _spec_spawns_own_server(filepath: str) -> bool:
    content = open(filepath).read()
    # Pattern: spawn(...npm run dev...) or spawn(...vite...)
    spawn_npm = bool(re.search(r"spawn\s*\(", content) and re.search(r"npm.*run.*dev|vite", content))
    return spawn_npm


def test_audit_specs_with_own_server_is_documented():
    """
    AUDIT (non-blocking): documents which specs still spawn their own Vite server.

    This test always passes — it prints the audit results so developers know
    which specs can be migrated to use VETKA_GLOBAL_PORT.
    """
    spec_files = _find_spec_files()
    assert len(spec_files) > 0, f"No spec files found in {E2E_DIR}"

    self_spawning = []
    opted_in = []

    for spec in spec_files:
        content = open(spec).read()
        if _spec_spawns_own_server(spec):
            self_spawning.append(os.path.basename(spec))
        elif "VETKA_GLOBAL_PORT" in content or "VETKA_GLOBAL_ORIGIN" in content:
            opted_in.append(os.path.basename(spec))

    total = len(spec_files)
    print(f"\n[Global Setup Audit] {total} spec files total")
    print(f"  Opted-in to global server: {len(opted_in)}")
    print(f"  Still self-spawning Vite:  {len(self_spawning)}")
    if opted_in:
        print("  Opted-in specs:")
        for s in opted_in:
            print(f"    + {s}")
    if self_spawning:
        print("  Self-spawning specs (candidates for migration):")
        for s in self_spawning:
            print(f"    - {s}")

    # Non-blocking: just verify we got results (audit ran successfully)
    assert total > 0
