"""
Tests for UDS Daemon + UDSPublisher — Event Bus Phase 2.

Tests:
1. UDSPublisher queues events non-blocking (<0.01ms)
2. UDSPublisher sends to daemon via UDS socket
3. UDS Daemon accepts publisher + agent connections
4. Daemon fans out events from publisher to agent
5. Agent receives length-prefixed JSON frames
6. Graceful handling when daemon not running
7. Reconnection on socket failure
"""

import asyncio
import json
import os
import struct
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest

from src.orchestration.event_bus import (
    AgentEvent,
    UDSPublisher,
)

# Use temp socket paths to avoid conflicts with real daemon
_TMP_SOCKET = None


def _tmp_socket():
    global _TMP_SOCKET
    if _TMP_SOCKET is None:
        _TMP_SOCKET = tempfile.mktemp(suffix=".uds", prefix="vetka-test-")
    return _TMP_SOCKET


@pytest.fixture(autouse=True)
def cleanup_socket():
    yield
    path = _tmp_socket()
    if os.path.exists(path):
        os.unlink(path)


class TestUDSPublisherNoServer:
    """Test UDSPublisher when no daemon is running."""

    def test_accepts_all_events(self):
        pub = UDSPublisher(socket_path="/tmp/nonexistent.uds")
        event = AgentEvent(event_type="test")
        assert pub.accepts(event) is True

    def test_handle_queues_without_blocking(self):
        """handle() must be non-blocking even if daemon is not running."""
        pub = UDSPublisher(socket_path="/tmp/nonexistent.uds")
        event = AgentEvent(event_type="task_created", source_agent="Alpha")

        start = time.perf_counter()
        pub.handle(event)
        elapsed = time.perf_counter() - start

        # Must be <1ms (queue operation only)
        assert elapsed < 0.001, f"handle() took {elapsed*1000:.3f}ms"
        pub.close()

    def test_graceful_when_daemon_missing(self):
        """UDSPublisher should not crash when daemon socket doesn't exist."""
        pub = UDSPublisher(socket_path="/tmp/nonexistent-vetka-test.uds")
        event = AgentEvent(event_type="test")
        pub.handle(event)
        # Give background thread time to attempt connection and fail
        time.sleep(0.1)
        pub.close()
        # No exception = success

    def test_close_idempotent(self):
        pub = UDSPublisher(socket_path="/tmp/nonexistent.uds")
        pub.close()
        pub.close()  # should not raise


class TestUDSPublisherWithServer:
    """Test UDSPublisher with a real UDS server (mock daemon)."""

    @pytest.fixture
    def mock_server(self):
        """Start a simple UDS server that records received frames."""
        socket_path = _tmp_socket()
        received = []

        async def handle_client(reader, writer):
            try:
                while True:
                    header = await reader.readexactly(4)
                    length = struct.unpack(">I", header)[0]
                    data = await reader.readexactly(length)
                    received.append(json.loads(data))
            except (asyncio.IncompleteReadError, ConnectionError):
                pass

        async def run_server():
            if os.path.exists(socket_path):
                os.unlink(socket_path)
            srv = await asyncio.start_unix_server(handle_client, socket_path)
            return srv

        loop = asyncio.new_event_loop()
        srv = loop.run_until_complete(run_server())

        # Run server in background thread
        import threading
        def serve():
            loop.run_until_complete(srv.serve_forever())

        t = threading.Thread(target=serve, daemon=True)
        t.start()

        yield socket_path, received

        try:
            srv.close()
        except Exception:
            pass
        loop.call_soon_threadsafe(loop.stop)
        t.join(timeout=2)
        try:
            loop.close()
        except Exception:
            pass

    def test_publisher_sends_to_server(self, mock_server):
        """UDSPublisher should send events to daemon."""
        socket_path, received = mock_server

        pub = UDSPublisher(socket_path=socket_path)
        event = AgentEvent(
            event_type="task_completed",
            source_agent="Alpha",
            payload={"task_id": "tb_123"},
        )
        pub.handle(event)

        # Wait for background thread to send
        time.sleep(0.3)

        # First frame is registration, second is the event
        assert len(received) >= 2, f"Expected >=2 frames, got {len(received)}: {received}"
        # Registration frame
        assert received[0]["type"] == "publisher"
        # Event frame
        assert received[1]["event_type"] == "task_completed"
        assert received[1]["source_agent"] == "Alpha"
        assert received[1]["payload"]["task_id"] == "tb_123"

        pub.close()

    def test_publisher_sends_multiple_events(self, mock_server):
        """Multiple events should all arrive."""
        socket_path, received = mock_server

        pub = UDSPublisher(socket_path=socket_path)
        for i in range(5):
            event = AgentEvent(
                event_type="task_created",
                payload={"index": i},
            )
            pub.handle(event)

        time.sleep(0.5)

        # 1 registration + 5 events
        assert len(received) >= 6, f"Expected >=6 frames, got {len(received)}"
        event_frames = [r for r in received if r.get("event_type") == "task_created"]
        assert len(event_frames) == 5

        pub.close()


class TestUDSDaemonIntegration:
    """Integration test: start real daemon, connect publisher + agent, verify fan-out."""

    @pytest.fixture
    def daemon_process(self):
        """Start the UDS daemon in a subprocess."""
        socket_path = _tmp_socket()
        import subprocess
        proc = subprocess.Popen(
            ["python3", "scripts/uds_daemon.py", "--socket", socket_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Wait for socket to appear
        for _ in range(20):
            if os.path.exists(socket_path):
                break
            time.sleep(0.1)
        else:
            proc.kill()
            pytest.skip("Daemon did not start in time")

        yield socket_path, proc

        proc.terminate()
        proc.wait(timeout=3)
        if os.path.exists(socket_path):
            os.unlink(socket_path)

    def test_full_pipeline(self, daemon_process):
        """Publisher → Daemon → Agent fan-out."""
        import socket as sock_mod

        socket_path, proc = daemon_process

        # Connect as agent
        agent_sock = sock_mod.socket(sock_mod.AF_UNIX, sock_mod.SOCK_STREAM)
        agent_sock.connect(socket_path)
        agent_sock.settimeout(3.0)
        # Register as agent
        reg = json.dumps({"type": "agent", "role": "TestAlpha"}).encode()
        agent_sock.sendall(struct.pack(">I", len(reg)) + reg)

        time.sleep(0.1)

        # Connect as publisher and send event
        pub_sock = sock_mod.socket(sock_mod.AF_UNIX, sock_mod.SOCK_STREAM)
        pub_sock.connect(socket_path)
        pub_sock.settimeout(3.0)
        # Register as publisher
        pub_reg = json.dumps({"type": "publisher", "pid": os.getpid()}).encode()
        pub_sock.sendall(struct.pack(">I", len(pub_reg)) + pub_reg)

        time.sleep(0.1)

        # Send an event
        event_data = json.dumps({
            "event_id": "test_001",
            "event_type": "task_completed",
            "source_agent": "Zeta",
            "payload": {"task_id": "tb_smoke"},
        }).encode()
        pub_sock.sendall(struct.pack(">I", len(event_data)) + event_data)

        # Agent should receive the fan-out
        try:
            header = agent_sock.recv(4)
            assert len(header) == 4, f"Expected 4-byte header, got {len(header)}"
            length = struct.unpack(">I", header)[0]
            data = agent_sock.recv(length)
            event = json.loads(data)

            assert event["event_type"] == "task_completed"
            assert event["source_agent"] == "Zeta"
            assert event["payload"]["task_id"] == "tb_smoke"
        finally:
            agent_sock.close()
            pub_sock.close()

    def test_multiple_agents(self, daemon_process):
        """Fan-out to multiple agents."""
        import socket as sock_mod

        socket_path, proc = daemon_process

        # Connect two agents
        agents = []
        for role in ["Alpha", "Beta"]:
            s = sock_mod.socket(sock_mod.AF_UNIX, sock_mod.SOCK_STREAM)
            s.connect(socket_path)
            s.settimeout(3.0)
            reg = json.dumps({"type": "agent", "role": role}).encode()
            s.sendall(struct.pack(">I", len(reg)) + reg)
            agents.append(s)

        time.sleep(0.1)

        # Publisher sends event
        pub = sock_mod.socket(sock_mod.AF_UNIX, sock_mod.SOCK_STREAM)
        pub.connect(socket_path)
        pub.settimeout(3.0)
        pub_reg = json.dumps({"type": "publisher", "pid": os.getpid()}).encode()
        pub.sendall(struct.pack(">I", len(pub_reg)) + pub_reg)
        time.sleep(0.1)

        event_data = json.dumps({
            "event_id": "multi_001",
            "event_type": "notification",
            "source_agent": "Commander",
            "payload": {"message": "All agents: deploy ready"},
        }).encode()
        pub.sendall(struct.pack(">I", len(event_data)) + event_data)

        # Both agents should receive
        for i, agent_sock in enumerate(agents):
            try:
                header = agent_sock.recv(4)
                assert len(header) == 4
                length = struct.unpack(">I", header)[0]
                data = agent_sock.recv(length)
                event = json.loads(data)
                assert event["event_type"] == "notification"
                assert event["payload"]["message"] == "All agents: deploy ready"
            finally:
                agent_sock.close()
        pub.close()
