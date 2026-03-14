"""
MARKER_177.3: Transport Capability Broker.

Discovers available transports at session start and builds a capability manifest.
Agents use this to know which tools/transports are alive and which fallbacks exist.

Transport check order per capability:
  task_board: MCP_MYCELIUM → REST → FILE
  pipeline:   MCP_MYCELIUM only (no safe fallback)
  search:     MCP_VETKA (always available in-process)
  git:        MCP_VETKA (always available in-process)

@status: active
@phase: 177.3
"""
import socket
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
from urllib.request import urlopen
from urllib.error import URLError

logger = logging.getLogger("vetka.capability_broker")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class TransportKind(str, Enum):
    MCP_MYCELIUM = "mcp_mycelium"
    MCP_VETKA = "mcp_vetka"
    REST = "rest"
    FILE = "file"


class TransportStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass
class TransportEntry:
    kind: TransportKind
    status: TransportStatus
    endpoint: str
    capabilities: List[str]
    note: str = ""


@dataclass
class CapabilityManifest:
    transports: List[TransportEntry] = field(default_factory=list)
    recommended: Dict[str, str] = field(default_factory=dict)
    generated_at: float = 0.0


def _check_mycelium(timeout_s: float = 0.5) -> TransportStatus:
    """Check if MYCELIUM WebSocket server is reachable on port 8082."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout_s)
        result = sock.connect_ex(("127.0.0.1", 8082))
        sock.close()
        return TransportStatus.AVAILABLE if result == 0 else TransportStatus.UNAVAILABLE
    except Exception:
        return TransportStatus.UNAVAILABLE


def _check_rest(timeout_s: float = 0.5) -> TransportStatus:
    """Check if VETKA REST API is reachable on port 5001.

    MARKER_177.7: Use socket check instead of HTTP request.
    HTTP calls can deadlock when MCP bridge runs inside the same process as FastAPI,
    or timeout too aggressively on cold starts. Socket connect is non-blocking and safe.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout_s)
        result = sock.connect_ex(("127.0.0.1", 5001))
        sock.close()
        return TransportStatus.AVAILABLE if result == 0 else TransportStatus.UNAVAILABLE
    except Exception:
        return TransportStatus.UNAVAILABLE


def _check_file() -> TransportStatus:
    """Check if task_board.json exists and is readable."""
    tb_path = PROJECT_ROOT / "data" / "task_board.json"
    try:
        if tb_path.exists() and tb_path.stat().st_size > 0:
            return TransportStatus.AVAILABLE
    except Exception:
        pass
    return TransportStatus.UNAVAILABLE


def build_capability_manifest(timeout_s: float = 0.5) -> CapabilityManifest:
    """MARKER_177.3: Build capability manifest by checking all transports in parallel.

    Returns a manifest with transport availability and recommended transport per capability.
    Never throws — returns UNKNOWN status on errors.
    Total wall time ≤ timeout_s (checks run in parallel).
    """
    manifest = CapabilityManifest(generated_at=time.time())

    # Run transport checks in parallel
    results = {
        TransportKind.MCP_MYCELIUM: TransportStatus.UNKNOWN,
        TransportKind.REST: TransportStatus.UNKNOWN,
        TransportKind.FILE: TransportStatus.UNKNOWN,
    }

    try:
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(_check_mycelium, timeout_s): TransportKind.MCP_MYCELIUM,
                executor.submit(_check_rest, timeout_s): TransportKind.REST,
                executor.submit(_check_file): TransportKind.FILE,
            }
            for future in as_completed(futures, timeout=timeout_s + 0.2):
                kind = futures[future]
                try:
                    results[kind] = future.result()
                except Exception:
                    results[kind] = TransportStatus.UNAVAILABLE
    except Exception as e:
        logger.warning(f"Capability broker parallel check failed: {e}")

    # Build transport entries
    manifest.transports = [
        TransportEntry(
            kind=TransportKind.MCP_MYCELIUM,
            status=results[TransportKind.MCP_MYCELIUM],
            endpoint="ws://127.0.0.1:8082",
            capabilities=["task_board", "pipeline", "heartbeat", "track_done", "call_model"],
        ),
        TransportEntry(
            kind=TransportKind.MCP_VETKA,
            status=TransportStatus.AVAILABLE,  # Always available (in-process)
            endpoint="in-process",
            capabilities=["search", "git", "session", "camera", "edit_file"],
        ),
        TransportEntry(
            kind=TransportKind.REST,
            status=results[TransportKind.REST],
            endpoint="http://127.0.0.1:5001/api",
            capabilities=["task_board", "analytics", "mcc", "chat", "health"],
        ),
        TransportEntry(
            kind=TransportKind.FILE,
            status=results[TransportKind.FILE],
            endpoint=str(PROJECT_ROOT / "data"),
            capabilities=["task_board", "digest", "config"],
        ),
    ]

    # Build recommended transport per capability
    mycelium_up = results[TransportKind.MCP_MYCELIUM] == TransportStatus.AVAILABLE
    rest_up = results[TransportKind.REST] == TransportStatus.AVAILABLE
    file_up = results[TransportKind.FILE] == TransportStatus.AVAILABLE

    # task_board: MCP_MYCELIUM → REST → FILE
    if mycelium_up:
        manifest.recommended["task_board"] = TransportKind.MCP_MYCELIUM
    elif rest_up:
        manifest.recommended["task_board"] = TransportKind.REST
    elif file_up:
        manifest.recommended["task_board"] = TransportKind.FILE
    else:
        manifest.recommended["task_board"] = "unavailable"

    # pipeline: MYCELIUM only (no safe fallback — pipeline dispatch needs async)
    manifest.recommended["pipeline"] = (
        TransportKind.MCP_MYCELIUM if mycelium_up else "unavailable"
    )

    # search/git/session: always MCP_VETKA (in-process)
    manifest.recommended["search"] = TransportKind.MCP_VETKA
    manifest.recommended["git"] = TransportKind.MCP_VETKA
    manifest.recommended["session"] = TransportKind.MCP_VETKA

    logger.info(
        f"MARKER_177.3: Capability manifest built — "
        f"mycelium={results[TransportKind.MCP_MYCELIUM]}, "
        f"rest={results[TransportKind.REST]}, "
        f"file={results[TransportKind.FILE]}"
    )

    return manifest


def manifest_to_dict(manifest: CapabilityManifest) -> dict:
    """Serialize manifest to JSON-compatible dict for session_init response."""
    return {
        "transports": [
            {
                "kind": t.kind.value,
                "status": t.status.value,
                "endpoint": t.endpoint,
                "capabilities": t.capabilities,
                "note": t.note,
            }
            for t in manifest.transports
        ],
        "recommended": {
            k: (v.value if isinstance(v, TransportKind) else v)
            for k, v in manifest.recommended.items()
        },
        "generated_at": manifest.generated_at,
    }
