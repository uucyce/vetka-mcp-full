#!/usr/bin/env python3
"""
Phase 155C probe:
Manual JEPA architect bootstrap diagnostics for first-turn policy.
"""

import argparse
import asyncio
import json
import os
import sys
from typing import Any, Dict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe architect JEPA bootstrap trace")
    parser.add_argument("--scope", default="", help="Override scope path (default: current cwd)")
    parser.add_argument("--message", default="plan architecture", help="Architect user message")
    parser.add_argument("--model", default="moonshotai/kimi-k2.5", help="Model id")
    parser.add_argument("--not-first-turn", action="store_true", help="Simulate non-first turn")
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> Dict[str, Any]:
    from src.api.routes.architect_chat_routes import (
        ArchitectChatRequest,
        ChatContext,
        _build_architect_jepa_bootstrap,
    )

    history = []
    if args.not_first_turn:
        history = [{"role": "user", "content": "previous turn"}]

    workflow_ctx = {}
    if args.scope:
        workflow_ctx["scope_path"] = os.path.abspath(args.scope)

    req = ArchitectChatRequest(
        message=args.message,
        context=ChatContext(chatHistory=history, workflowContext=workflow_ctx or None),
    )
    jepa_context, trace = await _build_architect_jepa_bootstrap(req, model_name=args.model)
    return {
        "has_jepa_context": bool((jepa_context or "").strip()),
        "jepa_context_preview": (jepa_context or "")[:300],
        "trace": trace,
    }


def main() -> int:
    args = _parse_args()
    result = asyncio.run(_run(args))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
