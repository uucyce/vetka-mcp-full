#!/usr/bin/env python3
"""
Call vetka_session_init through VETKA MCP Socket.IO namespace (/mcp).

This script is intended for lightweight session bootstrap on terminal/desktop startup.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from typing import Any

try:
    import socketio
except Exception as exc:  # pragma: no cover
    print(json.dumps({"ok": False, "error": f"socketio import failed: {exc}"}))
    sys.exit(2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="VETKA MCP session bootstrap")
    parser.add_argument("--base-url", default="http://127.0.0.1:5001")
    parser.add_argument("--user-id", default="danila")
    parser.add_argument("--compress", default="true")
    parser.add_argument("--include-pinned", default="true")
    parser.add_argument("--include-viewport", default="true")
    parser.add_argument("--max-context-tokens", type=int, default=4000)
    parser.add_argument("--session-id", default="")
    parser.add_argument("--timeout", type=float, default=8.0)
    return parser.parse_args()


def as_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def main() -> int:
    args = parse_args()
    namespace = "/mcp"
    request_id = f"autoinit-{uuid.uuid4().hex[:10]}"
    done: dict[str, Any] = {"ok": False}
    joined_session_id = args.session_id or f"auto-{int(time.time())}"

    sio = socketio.Client(reconnection=False, logger=False, engineio_logger=False)

    @sio.on("mcp_status", namespace=namespace)
    def on_status(payload: dict[str, Any]) -> None:
        status = payload.get("status")
        if status in {"joined", "rejoined"}:
            nonlocal joined_session_id
            joined_session_id = str(payload.get("session_id") or joined_session_id)
            sio.emit(
                "mcp_tool_call",
                {
                    "request_id": request_id,
                    "tool": "vetka_session_init",
                    "arguments": {
                        "user_id": args.user_id,
                        "compress": as_bool(args.compress),
                        "include_pinned": as_bool(args.include_pinned),
                        "include_viewport": as_bool(args.include_viewport),
                        "max_context_tokens": args.max_context_tokens,
                    },
                },
                namespace=namespace,
            )

    @sio.on("mcp_result", namespace=namespace)
    def on_result(payload: dict[str, Any]) -> None:
        if payload.get("request_id") != request_id:
            return
        done["ok"] = True
        done["session_id"] = payload.get("session_id") or joined_session_id
        done["result"] = payload.get("result")
        sio.disconnect()

    @sio.on("mcp_error", namespace=namespace)
    def on_error(payload: dict[str, Any]) -> None:
        if payload.get("request_id") not in {None, request_id}:
            return
        done["ok"] = False
        done["error"] = payload.get("error") or "unknown mcp_error"
        sio.disconnect()

    try:
        sio.connect(args.base_url, namespaces=[namespace], wait_timeout=args.timeout)
        sio.emit("mcp_join", {"session_id": joined_session_id, "reconnect": False}, namespace=namespace)
        sio.sleep(args.timeout)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    finally:
        try:
            sio.disconnect()
        except Exception:
            pass

    if not done.get("ok"):
        print(json.dumps({"ok": False, "error": done.get("error", "timeout"), "session_id": joined_session_id}))
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "session_id": done.get("session_id", joined_session_id),
                "source": "mcp_socket",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

