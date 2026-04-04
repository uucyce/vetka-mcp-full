#!/usr/bin/env python3
"""
VETKA Event Bus — UDS Daemon

Standalone asyncio process that provides real-time event fan-out
to connected MCP server processes. Zero intervals, zero polling.

Architecture:
    EventBus emit() → UDSPublisher → THIS DAEMON → MCP servers (per-agent)

Two types of connections:
    1. Publisher (TaskBoard process) — sends events TO daemon
    2. Agent (MCP server process) — receives events FROM daemon

Wire protocol: 4-byte big-endian length prefix + JSON payload.
    Publisher sends: {"event_id": ..., "event_type": ..., "payload": ...}
    Agent receives: same frames, fan-out from publisher
    Registration: first frame from connection is {"type": "publisher"|"agent", "role": "Alpha", ...}

Usage:
    python3 scripts/uds_daemon.py                    # foreground
    python3 scripts/uds_daemon.py --daemon            # background (nohup)
    python3 scripts/uds_daemon.py --status            # check if running
    python3 scripts/uds_daemon.py --stop              # stop daemon

MARKER_201.UDS_DAEMON
@phase: 201
"""

import argparse
import asyncio
import json
import logging
import os
import signal
import struct
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

SOCKET_PATH = "/tmp/vetka-events.uds"
PID_FILE = "/tmp/vetka-events-daemon.pid"
LOG_FORMAT = "%(asctime)s [UDS] %(levelname)s %(message)s"

logger = logging.getLogger("vetka.uds_daemon")


class UDSDaemon:
    """Single daemon process. N agent connections. 0 CPU when idle."""

    def __init__(self, socket_path: str = SOCKET_PATH):
        self.socket_path = socket_path
        # role → (reader, writer) for agent MCP servers
        self.agents: dict[str, asyncio.StreamWriter] = {}
        # publisher connections (TaskBoard processes)
        self.publishers: list[asyncio.StreamReader] = []
        self._stats = {
            "events_received": 0,
            "events_fanout": 0,
            "autospawns": 0,
            "agents_connected": 0,
            "agents_disconnected": 0,
            "publishers_connected": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        # Load role→worktree mapping from agent_registry.yaml
        self._role_worktree = self._load_registry()

    @staticmethod
    def _load_registry() -> dict[str, str]:
        """Load role→worktree mapping from agent_registry.yaml."""
        registry_path = Path(__file__).resolve().parent.parent / "data" / "templates" / "agent_registry.yaml"
        if not registry_path.exists():
            logger.warning("agent_registry.yaml not found at %s", registry_path)
            return {}
        try:
            with open(registry_path) as f:
                data = yaml.safe_load(f)
            mapping = {}
            for role in data.get("roles", []):
                callsign = role.get("callsign")
                worktree = role.get("worktree")
                if callsign and worktree:
                    mapping[callsign] = worktree
            logger.info("Registry loaded: %d roles with worktrees", len(mapping))
            return mapping
        except Exception as exc:
            logger.warning("Failed to load agent_registry.yaml: %s", exc)
            return {}

    def _maybe_autospawn(self, raw_data: bytes):
        """If event targets an offline agent, spawn it via tmux."""
        try:
            event = json.loads(raw_data)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return

        # Only autospawn on notify events
        payload = event.get("payload", {})
        if event.get("event_type") != "notify" and payload.get("action") != "notify":
            return

        target_role = payload.get("target_role") or event.get("target_role")
        if not target_role:
            return

        # Skip if agent is connected to daemon (online via UDS)
        if target_role in self.agents:
            return

        # Check tmux session
        session_name = f"vetka-{target_role}"
        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True,
        )
        if result.returncode == 0:
            # tmux session exists — agent is running but not UDS-connected
            return

        # Agent offline — spawn
        worktree = self._role_worktree.get(target_role)
        if not worktree:
            logger.warning("[AUTOSPAWN] No worktree for role %s, skipping", target_role)
            return

        spawn_script = Path(__file__).resolve().parent / "spawn_agent.sh"
        if not spawn_script.exists():
            logger.warning("[AUTOSPAWN] spawn_agent.sh not found at %s", spawn_script)
            return

        logger.info("[AUTOSPAWN] %s offline → spawning in worktree %s", target_role, worktree)
        subprocess.Popen(
            [str(spawn_script), target_role, worktree],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._stats["autospawns"] += 1

    async def run(self):
        """Start the daemon. Blocks forever (or until signal)."""
        # Clean up stale socket
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

        server = await asyncio.start_unix_server(
            self._handle_connection, self.socket_path
        )
        # Make socket world-readable so all processes can connect
        os.chmod(self.socket_path, 0o777)

        # Write PID file
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))

        logger.info(
            "UDS Daemon started on %s (PID %d)", self.socket_path, os.getpid()
        )

        # Handle shutdown signals
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self._shutdown(server)))

        async with server:
            await server.serve_forever()

    async def _shutdown(self, server):
        """Graceful shutdown."""
        logger.info("Shutting down UDS Daemon...")
        server.close()
        await server.wait_closed()
        # Close all agent connections
        for role, writer in self.agents.items():
            try:
                writer.close()
            except Exception:
                pass
        self.agents.clear()
        # Cleanup
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        if os.path.exists(PID_FILE):
            os.unlink(PID_FILE)
        logger.info("UDS Daemon stopped. Stats: %s", json.dumps(self._stats))
        # Stop event loop
        asyncio.get_running_loop().stop()

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle a new connection. First frame determines type (publisher or agent)."""
        try:
            # Read registration frame
            header = await asyncio.wait_for(reader.readexactly(4), timeout=5.0)
            length = struct.unpack(">I", header)[0]
            if length > 65536:
                writer.close()
                return
            data = await asyncio.wait_for(reader.readexactly(length), timeout=5.0)
            reg = json.loads(data)

            conn_type = reg.get("type", "unknown")

            if conn_type == "publisher":
                await self._handle_publisher(reader, writer, reg)
            elif conn_type == "agent":
                await self._handle_agent(reader, writer, reg)
            else:
                logger.warning("Unknown connection type: %s", conn_type)
                writer.close()
        except (asyncio.TimeoutError, asyncio.IncompleteReadError, ConnectionError):
            try:
                writer.close()
            except Exception:
                pass
        except Exception as exc:
            logger.warning("Connection handler error: %s", exc)
            try:
                writer.close()
            except Exception:
                pass

    async def _handle_publisher(self, reader: asyncio.StreamReader,
                                 writer: asyncio.StreamWriter, reg: dict):
        """Publisher (TaskBoard) sends events. Daemon fans out to agents."""
        pid = reg.get("pid", "?")
        self._stats["publishers_connected"] += 1
        logger.info("Publisher connected (PID %s)", pid)

        try:
            while True:
                # Read length-prefixed frame — blocks until data arrives (0 CPU)
                header = await reader.readexactly(4)
                length = struct.unpack(">I", header)[0]
                if length > 1048576:  # 1MB sanity limit
                    logger.warning("Publisher sent oversized frame (%d bytes), dropping", length)
                    await reader.readexactly(length)  # drain
                    continue
                data = await reader.readexactly(length)

                self._stats["events_received"] += 1

                # Auto-spawn offline agents on notify events
                self._maybe_autospawn(data)

                # Fan-out to all connected agents
                await self._fanout(data)

        except (asyncio.IncompleteReadError, ConnectionError):
            logger.info("Publisher disconnected (PID %s)", pid)
        except Exception as exc:
            logger.warning("Publisher error (PID %s): %s", pid, exc)

    async def _handle_agent(self, reader: asyncio.StreamReader,
                             writer: asyncio.StreamWriter, reg: dict):
        """Agent MCP server connects, registers role, stays connected."""
        role = reg.get("role", "unknown")
        self._stats["agents_connected"] += 1

        # If role already connected, close old connection
        if role in self.agents:
            try:
                self.agents[role].close()
            except Exception:
                pass
            logger.info("Agent %s reconnected (replaced old connection)", role)
        else:
            logger.info("Agent %s connected", role)

        self.agents[role] = writer

        try:
            # Stay connected — detect disconnect via read
            while True:
                data = await reader.read(1)
                if not data:
                    break
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            self.agents.pop(role, None)
            self._stats["agents_disconnected"] += 1
            logger.info("Agent %s disconnected", role)

    async def _fanout(self, raw_data: bytes):
        """Send raw frame to all connected agents."""
        if not self.agents:
            return

        frame = struct.pack(">I", len(raw_data)) + raw_data
        dead = []
        for role, writer in self.agents.items():
            try:
                writer.write(frame)
                await writer.drain()
                self._stats["events_fanout"] += 1
            except Exception:
                dead.append(role)
        for r in dead:
            self.agents.pop(r, None)
            logger.info("Agent %s dropped (write failed)", r)


def check_status():
    """Check if daemon is running."""
    if not os.path.exists(PID_FILE):
        print("UDS Daemon: not running (no PID file)")
        return False
    with open(PID_FILE) as f:
        pid = int(f.read().strip())
    try:
        os.kill(pid, 0)  # check if process exists
        print(f"UDS Daemon: running (PID {pid}, socket {SOCKET_PATH})")
        return True
    except OSError:
        print(f"UDS Daemon: stale PID file (PID {pid} not running)")
        os.unlink(PID_FILE)
        return False


def stop_daemon():
    """Send SIGTERM to running daemon."""
    if not os.path.exists(PID_FILE):
        print("UDS Daemon: not running")
        return
    with open(PID_FILE) as f:
        pid = int(f.read().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"UDS Daemon: sent SIGTERM to PID {pid}")
    except OSError as e:
        print(f"UDS Daemon: could not stop PID {pid}: {e}")
        if os.path.exists(PID_FILE):
            os.unlink(PID_FILE)


def main():
    parser = argparse.ArgumentParser(description="VETKA Event Bus UDS Daemon")
    parser.add_argument("--daemon", action="store_true", help="Run in background")
    parser.add_argument("--status", action="store_true", help="Check if running")
    parser.add_argument("--stop", action="store_true", help="Stop running daemon")
    parser.add_argument("--socket", default=SOCKET_PATH, help="Socket path")
    args = parser.parse_args()

    if args.status:
        check_status()
        return
    if args.stop:
        stop_daemon()
        return

    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    if args.daemon:
        # Fork to background
        pid = os.fork()
        if pid > 0:
            print(f"UDS Daemon started in background (PID {pid})")
            return
        # Child — detach
        os.setsid()
        # Redirect stdout/stderr to log
        log_path = Path("/tmp/vetka-uds-daemon.log")
        sys.stdout = open(log_path, "a")
        sys.stderr = sys.stdout

    daemon = UDSDaemon(socket_path=args.socket)
    asyncio.run(daemon.run())


if __name__ == "__main__":
    main()
