"""
E2E test: Commander notify → UDS daemon → autospawn → agent alive in tmux

Phase 205 synapse test — proves Commander can wake offline agents without human relay.
Requires: UDS daemon running (scripts/uds_daemon.py --daemon)

MARKER_205.E2E_TEST
"""

import json
import os
import socket
import struct
import subprocess
import time
import unittest


UDS_SOCKET = "/tmp/vetka-events.uds"
TEST_ROLE = "Eta"  # Has worktree=harness-eta in agent_registry.yaml
TEST_SESSION = f"vetka-{TEST_ROLE}"


class TestAgentAutospawnE2E(unittest.TestCase):
    """Full cycle: notify → daemon → tmux spawn → claude running."""

    @classmethod
    def setUpClass(cls):
        """Ensure daemon is running and no stale test sessions exist."""
        # Kill stale test session if present
        subprocess.run(["tmux", "kill-session", "-t", TEST_SESSION],
                       capture_output=True)
        # Verify daemon is running
        result = subprocess.run(
            ["python3", "scripts/uds_daemon.py", "--status"],
            capture_output=True, text=True,
        )
        if "not running" in result.stdout:
            subprocess.run(
                ["python3", "scripts/uds_daemon.py", "--daemon"],
                capture_output=True,
            )
            time.sleep(2)

    @classmethod
    def tearDownClass(cls):
        """Clean up spawned test session."""
        subprocess.run(["tmux", "kill-session", "-t", TEST_SESSION],
                       capture_output=True)

    def test_01_daemon_running(self):
        """UDS daemon must be running with valid socket."""
        self.assertTrue(os.path.exists(UDS_SOCKET), "UDS socket missing")
        result = subprocess.run(
            ["python3", "scripts/uds_daemon.py", "--status"],
            capture_output=True, text=True,
        )
        self.assertIn("running", result.stdout)

    def test_02_notify_triggers_autospawn(self):
        """Send notify event → daemon spawns offline agent in tmux."""
        # Ensure agent is NOT running
        result = subprocess.run(
            ["tmux", "has-session", "-t", TEST_SESSION],
            capture_output=True,
        )
        if result.returncode == 0:
            self.skipTest(f"{TEST_SESSION} already running")

        # Connect as publisher and send notify
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(UDS_SOCKET)

        # Register
        reg = json.dumps({"type": "publisher", "pid": os.getpid()}).encode()
        sock.sendall(struct.pack(">I", len(reg)) + reg)

        # Send notify for offline agent
        event = {
            "event_id": f"e2e_test_{int(time.time())}",
            "event_type": "notify",
            "source_agent": "test",
            "source_tool": "test",
            "timestamp": time.time(),
            "payload": {
                "action": "notify",
                "target_role": TEST_ROLE,
                "source_role": "Zeta",
                "message": "E2E autospawn test",
            },
            "tags": [],
        }
        data = json.dumps(event).encode()
        sock.sendall(struct.pack(">I", len(data)) + data)
        sock.close()

        # Wait for spawn (tmux + claude boot takes ~2-5s)
        for _ in range(10):
            time.sleep(1)
            result = subprocess.run(
                ["tmux", "has-session", "-t", TEST_SESSION],
                capture_output=True,
            )
            if result.returncode == 0:
                break

        # Verify tmux session was created
        result = subprocess.run(
            ["tmux", "has-session", "-t", TEST_SESSION],
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0,
                         f"tmux session {TEST_SESSION} was not created by autospawn")

    def test_03_spawned_agent_is_claude(self):
        """Spawned tmux session contains Claude Code process."""
        result = subprocess.run(
            ["tmux", "has-session", "-t", TEST_SESSION],
            capture_output=True,
        )
        if result.returncode != 0:
            self.skipTest("No tmux session to verify")

        # Capture pane output
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", TEST_SESSION, "-p"],
            capture_output=True, text=True,
        )
        # Claude Code shows this banner on start
        self.assertIn("Claude", result.stdout,
                       "Claude Code not detected in tmux session output")

    def test_04_daemon_graceful_shutdown(self):
        """Daemon handles SIGTERM without RuntimeError."""
        # Start a fresh daemon
        subprocess.run(["python3", "scripts/uds_daemon.py", "--stop"],
                       capture_output=True)
        time.sleep(1)

        log_path = "/tmp/vetka-uds-daemon-test.log"
        # Remove old log
        try:
            os.unlink(log_path)
        except FileNotFoundError:
            pass

        subprocess.run(
            ["python3", "scripts/uds_daemon.py", "--daemon"],
            capture_output=True,
        )
        time.sleep(2)

        subprocess.run(
            ["python3", "scripts/uds_daemon.py", "--stop"],
            capture_output=True,
        )
        time.sleep(1)

        # Check log for RuntimeError
        if os.path.exists(log_path):
            with open(log_path) as f:
                log_content = f.read()
            self.assertNotIn("RuntimeError", log_content,
                             "Daemon crashed on shutdown with RuntimeError")

    def test_05_duplicate_spawn_guard(self):
        """spawn_agent.sh does not create duplicate sessions."""
        # Start session if not exists
        project_root = os.path.expanduser(
            "~/Documents/VETKA_Project/vetka_live_03"
        )
        spawn = os.path.join(project_root, ".claude/worktrees/harness/scripts/spawn_agent.sh")

        result1 = subprocess.run(
            [spawn, TEST_ROLE, "harness-eta"],
            capture_output=True, text=True,
        )

        # Second call should be idempotent
        result2 = subprocess.run(
            [spawn, TEST_ROLE, "harness-eta"],
            capture_output=True, text=True,
        )
        self.assertIn("already running", result2.stdout)


if __name__ == "__main__":
    unittest.main()
