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
2. mcp__vetka__vetka_task_board action=notifications role={callsign}
   → READ Commander orders BEFORE doing anything else
3. mcp__vetka__vetka_task_board action=ack_notifications role={callsign}
4. mcp__vetka__vetka_task_board action=list filter_status={filter_status}
5. Claim → Work → action=complete task_id=<id> branch={branch}
```

**MANDATORY: Steps 2-3 (notifications) MUST NOT be skipped.** Agents that skip notifications miss Commander orders and work on wrong/stale tasks. This was the root cause of the wake bug.

`action=complete` = auto-stage + commit + close. NEVER use vetka_git_commit manually.

## YOUR ROLE
You are **{callsign}** — {role_title}.
{memory_section}
{owned_paths_section}
{blocked_paths_section}

## RULES
- Modify ONLY files in your allowed_paths
- NEVER touch blocked_paths
- NEVER commit to main
- Use `mcp__vetka__vetka_task_board action=notify source_role={callsign} target_role=Commander message="..."` to signal Commander
"""

TEMPLATE_VIBE = """\
# {callsign} — {role_title}

**Role:** {role_title} | **Domain:** {domain} | **Branch:** `{branch}`

## Init (Vibe CLI)

**MCP required.** Vibe must have vetka MCP loaded from `~/.vibe/config.toml`.
If `vetka_session_init` shows as "Unknown tool" — MCP not connected. Restart Vibe after verifying the config.
**DO NOT** use `mcp__vetka__` prefix — Vibe exposes tools without namespace prefix.

```
1. vetka_session_init role={callsign}
   → returns: role_context (callsign={callsign}, domain={domain}, pipeline_stage={pipeline_stage})
2. vetka_task_board action=notifications role={callsign}
   → READ Commander orders BEFORE doing anything else
3. vetka_task_board action=ack_notifications role={callsign}
4. vetka_task_board action=list filter_status={filter_status}
5. Claim → Work → vetka_task_board action=complete task_id=<id> branch={branch}
```

**MANDATORY: Steps 2-3 (notifications) MUST NOT be skipped.** Agents that skip notifications miss Commander orders and work on wrong/stale tasks. This was the root cause of the wake bug.

`action=complete` = auto-commit + close. NEVER use vetka_git_commit manually.

## Error Handling
If any MCP tool returns an error:
- **STOP immediately** — DO NOT retry the same call
- Report the error text
- Ask what to do next

## Signal Setup (run once before launching Vibe)
```bash
export VETKA_AGENT_ROLE={callsign}
export PRETOOL_HOOK="bash scripts/check_opencode_signals.sh"
```
Or use the pre-configured `launch_vibe.sh` in this worktree.

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
After Python init — use bash tools only. vetka_git_commit and vetka_task_board require MCP.

## YOUR ROLE
You are **{callsign}** — {role_title}.
{memory_section}
{owned_paths_section}
{blocked_paths_section}

## RULES
- Modify ONLY files in your allowed_paths
- NEVER touch blocked_paths
- NEVER commit to main
- Use `vetka_task_board action=notify source_role={callsign} target_role=Commander message="..."` to signal Commander
"""


TEMPLATE_CODEX = """\
# {callsign} — {role_title}

**Role:** {role_title} | **Domain:** {domain} | **Branch:** `{branch}`

## Init (Codex CLI)

```
1. mcp__vetka__vetka_session_init role={callsign}
   → returns: role_context (callsign={callsign}, domain={domain}, pipeline_stage={pipeline_stage})
2. mcp__vetka__vetka_task_board action=notifications role={callsign}
   → READ Commander orders BEFORE doing anything else
3. mcp__vetka__vetka_task_board action=ack_notifications role={callsign}
4. mcp__vetka__vetka_task_board action=list filter_status={filter_status}
5. Claim → Work → action=complete task_id=<id> branch={branch}
```

**MANDATORY: Steps 2-3 (notifications) MUST NOT be skipped.**

`action=complete` = auto-stage + commit + close. NEVER use vetka_git_commit manually.

## YOUR ROLE
You are **{callsign}** — {role_title}.
{memory_section}
{owned_paths_section}
{blocked_paths_section}

## RULES
- Modify ONLY files in your allowed_paths
- NEVER touch blocked_paths
- NEVER commit to main
- Use `mcp__vetka__vetka_task_board action=notify source_role={callsign} target_role=Commander message="..."` to signal Commander
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

    memory_path = getattr(role, "memory_path", "") or ""
    memory_section = ""
    if memory_path:
        memory_section = f"\n## Role Memory\nYour persistent memory: `{memory_path}`\nRead on init, update after key decisions. Stores: lessons, patterns, anti-patterns.\n"

    owned_section = ""
    if owned_paths:
        paths_str = "\n".join(f"- {p}" for p in owned_paths[:8])
        owned_section = f"## ALLOWED PATHS\n{paths_str}"

    blocked_section = ""
    if blocked_paths:
        paths_str = "\n".join(f"- {p}" for p in blocked_paths[:8])
        blocked_section = f"## BLOCKED PATHS\n{paths_str}"

    if tool_type == "vibe":
        template = TEMPLATE_VIBE
    elif tool_type == "codex":
        template = TEMPLATE_CODEX
    else:
        template = TEMPLATE
    content = template.format(
        callsign=callsign,
        role_title=role_title,
        domain=domain,
        branch=branch,
        pipeline_stage=pipeline_stage,
        filter_status=filter_status,
        memory_section=memory_section,
        owned_paths_section=owned_section,
        blocked_paths_section=blocked_section,
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
