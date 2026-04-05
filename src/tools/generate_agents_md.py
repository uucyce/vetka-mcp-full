#!/usr/bin/env python3
"""
MARKER_201.AGENTS_MD_GEN: Generate per-worktree AGENTS.md from agent_registry.yaml.

Usage:
    python -m src.tools.generate_agents_md --all          # all roles
    python -m src.tools.generate_agents_md --role Lambda   # single role
    python -m src.tools.generate_agents_md --role Lambda --dry-run  # preview

Pattern: same as generate_claude_md.py
- Root AGENTS.md = shared instructions (committed)
- .claude/worktrees/*/AGENTS.md = per-role instructions (gitignored, auto-generated)
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.agent_registry import AgentRegistry

_REGISTRY_PATH = (
    Path(__file__).parent.parent.parent / "data" / "templates" / "agent_registry.yaml"
)
_WORKTREES_DIR = Path(__file__).parent.parent.parent / ".claude" / "worktrees"

TEMPLATE = """\
# {callsign} — {role_title}

**Role:** {role_title} | **Domain:** {domain} | **Branch:** `{branch}`

## Init
```
1. mcp__vetka__vetka_session_init role={callsign}
   → returns: role_context (callsign={callsign}, domain={domain}, pipeline_stage={pipeline_stage})
2. mcp__vetka__vetka_task_board action=list filter_status={filter_status}
3. Claim → Work → mcp__vetka__vetka_task_board action=complete task_id=<id> branch={branch}
```

`action=complete` = auto-stage + commit + close. NEVER raw git commit.

## Signal Setup (PRETOOL_HOOK)
Run before starting: `export VETKA_AGENT_ROLE={callsign}`
Check inbox: `mcp__vetka__vetka_task_board action=notifications role={callsign}`
Send message: `mcp__vetka__vetka_task_board action=notify source_role={callsign} target_role=Commander message="..."` to signal Commander

{memory_section}

## YOUR ROLE
You are **{callsign}** — {role_title}.

{owned_paths_section}
{blocked_paths_section}

## RULES
- Modify ONLY files in your allowed_paths
- NEVER touch blocked_paths
- Commit via `mcp__vetka__vetka_git_commit` with `[task:tb_xxxx]`
- NEVER set `done_worktree` yourself — QA agent does that after verification
"""

TEMPLATE_VIBE = """\
# {callsign} — {role_title}

**Role:** {role_title} | **Domain:** {domain} | **Branch:** `{branch}`

## Init

**MCP required.** Vibe must have vetka MCP loaded from `~/.vibe/config.toml`.
If `vetka_session_init` shows as "Unknown tool" — MCP not connected. Restart Vibe after verifying the config.

```
1. vetka_session_init role={callsign}
   → returns: role_context (callsign={callsign}, domain={domain}, pipeline_stage={pipeline_stage})
2. vetka_task_board action=list filter_status={filter_status}
3. Claim → Work → vetka_task_board action=complete task_id=<id> branch={branch}
```

`action=complete` = auto-stage + commit + close. NEVER raw git commit.

### If MCP unavailable (fallback — read-only init)
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python -c "
import asyncio, sys
sys.path.insert(0, '.')
from src.mcp.tools.session_tools import vetka_session_init
result = asyncio.run(vetka_session_init(user_id='danila', role='{callsign}', compress=True))
import json; print(json.dumps(result, indent=2, default=str))
"
```
After Python init — use bash tools only (git, find, cat). vetka_git_commit and vetka_task_board require MCP.

## Error Handling
STOP immediately if you see:
- "Unknown tool" → MCP not connected, restart Vibe
- "Permission denied" → file outside owned_paths, do NOT modify
- Any crash → notify Commander before retrying

## Signal Setup (PRETOOL_HOOK)
Launch via: `source launch_vibe.sh` (sets VETKA_AGENT_ROLE={callsign} + PRETOOL_HOOK=check_opencode_signals.sh)
The `check_opencode_signals.sh` script runs before each tool call — reads signal files from `~/.vetka/signals/`.
Check inbox: `vetka_task_board action=notifications role={callsign}`
Send message: `vetka_task_board action=notify source_role={callsign} target_role=Commander message="..."` to signal Commander

{memory_section}

## YOUR ROLE
You are **{callsign}** — {role_title}.

{owned_paths_section}
{blocked_paths_section}

## RULES
- Modify ONLY files in your allowed_paths
- NEVER touch blocked_paths
- Commit via `vetka_git_commit` with `[task:tb_xxxx]`
- NEVER set `done_worktree` yourself — QA agent does that after verification
"""


def generate_agents_md(callsign: str, dry_run: bool = False) -> str:
    registry = AgentRegistry(_REGISTRY_PATH)
    role = registry.get_by_callsign(callsign)
    if not role:
        print(f"Error: Unknown callsign '{callsign}'", file=sys.stderr)
        sys.exit(1)

    callsign = role.callsign
    domain = role.domain
    branch = role.branch
    role_title = role.role_title or f"{callsign} Agent"
    pipeline_stage = role.pipeline_stage or "coder"
    tool_type = role.tool_type or "claude_code"
    owned_paths = role.owned_paths or []
    blocked_paths = role.blocked_paths or []

    filter_status = "need_qa" if pipeline_stage == "verifier" else "pending"

    owned_section = ""
    if owned_paths:
        paths_str = "\n".join(f"- {p}" for p in owned_paths[:8])
        owned_section = f"## ALLOWED PATHS\n{paths_str}"

    blocked_section = ""
    if blocked_paths:
        paths_str = "\n".join(f"- {p}" for p in blocked_paths[:8])
        blocked_section = f"## BLOCKED PATHS\n{paths_str}"

    memory_path = getattr(role, "memory_path", "") or ""
    memory_section = ""
    if memory_path:
        memory_section = (
            f"## Role Memory\n"
            f"Your persistent memory: `{memory_path}`\n"
            f"Read at session start. Write lessons/decisions there so next session picks them up."
        )

    template = TEMPLATE_VIBE if tool_type == "vibe" else TEMPLATE
    content = template.format(
        callsign=callsign,
        role_title=role_title,
        domain=domain,
        branch=branch,
        pipeline_stage=pipeline_stage,
        filter_status=filter_status,
        owned_paths_section=owned_section,
        blocked_paths_section=blocked_section,
        memory_section=memory_section,
    )

    # Write to worktree
    worktree_dir = _WORKTREES_DIR / (role.worktree or callsign.lower())
    agents_md_path = worktree_dir / "AGENTS.md"

    if dry_run:
        print(f"[dry-run] Would write {agents_md_path}")
        print(content)
        return content

    worktree_dir.mkdir(parents=True, exist_ok=True)
    agents_md_path.write_text(content)
    print(f"[generate_agents_md] Wrote {agents_md_path} ({len(content)} bytes)")
    return content


def main():
    parser = argparse.ArgumentParser(description="Generate per-worktree AGENTS.md")
    parser.add_argument("--role", help="Generate for specific role")
    parser.add_argument("--all", action="store_true", help="Generate for all roles")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    registry = AgentRegistry(_REGISTRY_PATH)

    if args.role:
        generate_agents_md(args.role, dry_run=args.dry_run)
    elif args.all:
        for role in registry.roles:
            if role.worktree:
                generate_agents_md(role.callsign, dry_run=args.dry_run)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
