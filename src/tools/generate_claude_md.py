"""
MARKER_ZETA.D3: CLAUDE.md Generator — auto-generate per-worktree agent instructions.

Reads:
  - agent_registry.yaml (D1) — role definitions
  - data/experience_reports/*.json (D2) — latest experience reports
  - docs/.../feedback/EXPERIENCE_*.md — markdown experience reports (fallback)
  - Task board state (optional, via MCP)

Writes:
  - .claude/worktrees/<worktree>/CLAUDE.md for each role

Usage:
    # Dry-run (print to stdout, no file writes)
    python -m src.tools.generate_claude_md --dry-run

    # Generate for specific role
    python -m src.tools.generate_claude_md --role Alpha --dry-run

    # Generate all and write to disk
    python -m src.tools.generate_claude_md --all

    # As a module import
    from src.tools.generate_claude_md import generate_claude_md
    content = generate_claude_md("Alpha")
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import jinja2

from src.services.agent_registry import AgentRegistry, AgentRole

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_TEMPLATE_PATH = _PROJECT_ROOT / "data" / "templates" / "claude_md_template.j2"
_REGISTRY_PATH = _PROJECT_ROOT / "data" / "templates" / "agent_registry.yaml"
_EXPERIENCE_REPORTS_DIR = _PROJECT_ROOT / "data" / "experience_reports"
_FEEDBACK_DOCS_DIR = _PROJECT_ROOT / "docs" / "190_ph_CUT_WORKFLOW_ARCH" / "feedback"
_WORKTREES_DIR = _PROJECT_ROOT / ".claude" / "worktrees"


def _load_template(template_path: Optional[Path] = None) -> jinja2.Template:
    """Load Jinja2 template from disk."""
    path = template_path or _TEMPLATE_PATH
    with open(path, "r", encoding="utf-8") as f:
        return jinja2.Template(f.read(), undefined=jinja2.StrictUndefined)


def _extract_predecessor_advice_from_json(callsign: str) -> list[str]:
    """Extract lessons_learned + recommendations from JSON experience reports (D2)."""
    advice = []
    if not _EXPERIENCE_REPORTS_DIR.exists():
        return advice

    # Find all reports for this callsign, sorted newest first
    reports = []
    for path in _EXPERIENCE_REPORTS_DIR.glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("agent_callsign", "").lower() == callsign.lower():
                reports.append((path.stat().st_mtime, data))
        except Exception:
            continue

    reports.sort(key=lambda x: x[0], reverse=True)

    # Take up to 3 latest reports
    for _, data in reports[:3]:
        for lesson in data.get("lessons_learned", []):
            if lesson not in advice:
                advice.append(lesson)
        for rec in data.get("recommendations", []):
            if rec not in advice:
                advice.append(rec)

    return advice


def _extract_predecessor_advice_from_md(callsign: str) -> list[str]:
    """Extract advice from markdown EXPERIENCE_*.md files (fallback)."""
    advice = []
    if not _FEEDBACK_DOCS_DIR.exists():
        return advice

    # Find matching experience report files
    pattern = f"EXPERIENCE_{callsign.upper()}_*.md"
    files = sorted(
        _FEEDBACK_DOCS_DIR.glob(pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not files:
        return advice

    # Parse latest file — extract bullet points from "Predecessor Advice" or "Recommendations" sections
    latest = files[0]
    try:
        content = latest.read_text(encoding="utf-8")
        # Look for sections with bullet points
        in_advice_section = False
        for line in content.splitlines():
            header_lower = line.strip().lower()
            if any(
                kw in header_lower
                for kw in ["recommendation", "predecessor", "successor", "what worked", "lesson"]
            ):
                in_advice_section = True
                continue
            if line.startswith("##") or line.startswith("# "):
                in_advice_section = False
                continue
            if in_advice_section and line.strip().startswith("- "):
                bullet = line.strip()[2:].strip()
                if bullet and bullet not in advice:
                    advice.append(bullet)
    except Exception:
        logger.debug("Could not parse %s", latest.name)

    return advice


def _get_predecessor_advice(callsign: str) -> list[str]:
    """Get combined predecessor advice from JSON reports (primary) and MD files (fallback)."""
    advice = _extract_predecessor_advice_from_json(callsign)
    if not advice:
        advice = _extract_predecessor_advice_from_md(callsign)
    return advice


def _find_latest_feedback_doc() -> Optional[str]:
    """Find the latest FEEDBACK_WAVE*_ALL_AGENTS_*.md file."""
    if not _FEEDBACK_DOCS_DIR.exists():
        return None
    files = sorted(
        _FEEDBACK_DOCS_DIR.glob("FEEDBACK_WAVE*_ALL_*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if files:
        return str(files[0].relative_to(_PROJECT_ROOT))
    return None


def generate_claude_md(
    callsign: str,
    registry: Optional[AgentRegistry] = None,
    template: Optional[jinja2.Template] = None,
    pending_tasks: Optional[list[dict]] = None,
) -> Optional[str]:
    """Generate CLAUDE.md content for a given callsign.

    Args:
        callsign: Agent callsign (Alpha, Beta, Gamma, Delta, Commander)
        registry: AgentRegistry instance (loaded from agent_registry.yaml if None)
        template: Jinja2 template (loaded from claude_md_template.j2 if None)
        pending_tasks: Optional list of pending tasks for this role

    Returns:
        Generated CLAUDE.md content string, or None if callsign not found.
    """
    if registry is None:
        registry = AgentRegistry(_REGISTRY_PATH)
    if template is None:
        template = _load_template()

    role = registry.get_by_callsign(callsign)
    if role is None:
        logger.warning("Unknown callsign: %s", callsign)
        return None

    advice = _get_predecessor_advice(callsign)
    feedback_doc = _find_latest_feedback_doc()

    context = {
        "role": role,
        "predecessor_advice": advice,
        "pending_tasks": pending_tasks or [],
        "feedback_doc": feedback_doc,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }

    return template.render(**context)


def write_claude_md(
    callsign: str,
    output_dir: Optional[Path] = None,
    **kwargs,
) -> Optional[Path]:
    """Generate and write CLAUDE.md to disk.

    Args:
        callsign: Agent callsign
        output_dir: Override output directory (default: .claude/worktrees/<worktree>/)
        **kwargs: Forwarded to generate_claude_md()

    Returns:
        Path to written file, or None if generation failed.
    """
    registry = kwargs.pop("registry", None) or AgentRegistry(_REGISTRY_PATH)
    role = registry.get_by_callsign(callsign)
    if role is None:
        return None

    content = generate_claude_md(callsign, registry=registry, **kwargs)
    if content is None:
        return None

    if output_dir is None:
        output_dir = _WORKTREES_DIR / role.worktree

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "CLAUDE.md"
    output_path.write_text(content, encoding="utf-8")
    logger.info("[generate_claude_md] Wrote %s (%d bytes)", output_path, len(content))
    return output_path


def generate_all(dry_run: bool = False, output_base: Optional[Path] = None) -> dict[str, str]:
    """Generate CLAUDE.md for all roles.

    Args:
        dry_run: If True, don't write files
        output_base: Override base directory for worktree CLAUDE.md files

    Returns:
        Dict of callsign -> generated content
    """
    registry = AgentRegistry(_REGISTRY_PATH)
    template = _load_template()
    results = {}

    for role in registry.roles:
        content = generate_claude_md(role.callsign, registry=registry, template=template)
        if content is None:
            continue
        results[role.callsign] = content

        if not dry_run:
            out_dir = (output_base or _WORKTREES_DIR) / role.worktree
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "CLAUDE.md").write_text(content, encoding="utf-8")
            logger.info("[generate_claude_md] Wrote %s/CLAUDE.md", out_dir)

    return results


# ── CLI ─────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Generate per-worktree CLAUDE.md files")
    parser.add_argument("--role", type=str, help="Generate for specific callsign (Alpha, Beta, etc.)")
    parser.add_argument("--all", action="store_true", help="Generate for all roles")
    parser.add_argument("--dry-run", action="store_true", help="Print to stdout, don't write files")
    parser.add_argument("--output-dir", type=str, help="Override output directory")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.role and not args.all:
        parser.print_help()
        sys.exit(1)

    output_base = Path(args.output_dir) if args.output_dir else None

    if args.all:
        results = generate_all(dry_run=args.dry_run, output_base=output_base)
        for callsign, content in results.items():
            if args.dry_run:
                print(f"\n{'='*60}")
                print(f"  {callsign}")
                print(f"{'='*60}\n")
                print(content)
            else:
                print(f"Generated: {callsign}")
        print(f"\nTotal: {len(results)} files {'(dry-run)' if args.dry_run else 'written'}")
    else:
        content = generate_claude_md(args.role)
        if content is None:
            print(f"Error: Unknown callsign '{args.role}'", file=sys.stderr)
            sys.exit(1)
        if args.dry_run:
            print(content)
        else:
            path = write_claude_md(args.role, output_dir=output_base)
            print(f"Written: {path}")


if __name__ == "__main__":
    main()
