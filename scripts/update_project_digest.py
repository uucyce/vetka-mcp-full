#!/usr/bin/env python3
"""
Auto-update project_digest.json with live system status.

This script updates the project digest with real-time data from:
- Qdrant collections (vetka_elisya, VetkaTree)
- MCP server status
- Git branch/commit info

Usage:
    python scripts/update_project_digest.py
    python scripts/update_project_digest.py --phase 102 --name "New Phase Name"

Can be run:
- Manually after significant changes
- As part of CI/CD pipeline
- Via cron job for periodic updates
"""

import os
import sys
import json
import re
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DIGEST_PATH = PROJECT_ROOT / "data" / "project_digest.json"


def get_qdrant_stats() -> dict:
    """Get collection stats from Qdrant."""
    stats = {
        "vetka_elisya": {"points": 0, "vectors": "unknown", "hnsw_status": "unknown"},
        "vetka_tree": {"points": 0, "vectors": "unknown", "hierarchy": "unknown"}
    }

    try:
        import requests
    except ModuleNotFoundError:
        return stats

    try:
        # Check vetka_elisya
        resp = requests.get("http://127.0.0.1:6333/collections/vetka_elisya", timeout=5)
        if resp.ok:
            data = resp.json().get("result", {})
            stats["vetka_elisya"]["points"] = data.get("points_count", 0)
            vectors = data.get("vectors_count", 0)
            stats["vetka_elisya"]["vectors"] = "indexed" if vectors > 0 else "none"
            hnsw = data.get("config", {}).get("hnsw_config", {})
            stats["vetka_elisya"]["hnsw_status"] = "active" if hnsw else "inactive"

        # Check VetkaTree
        resp = requests.get("http://127.0.0.1:6333/collections/VetkaTree", timeout=5)
        if resp.ok:
            data = resp.json().get("result", {})
            stats["vetka_tree"]["points"] = data.get("points_count", 0)
            vectors = data.get("vectors_count", 0)
            stats["vetka_tree"]["vectors"] = "indexed" if vectors > 0 else "none"
            stats["vetka_tree"]["hierarchy"] = "enabled" if data.get("points_count", 0) > 0 else "disabled"

    except Exception as e:
        print(f"  Warning: Could not get Qdrant stats: {e}")

    return stats


def get_mcp_status() -> dict:
    """Get MCP server status."""
    status = {
        "status": "unknown",
        "port": 5001,
        "tools_count": 0
    }

    try:
        import requests
    except ModuleNotFoundError:
        status["status"] = "degraded"
        status["error"] = "python dependency 'requests' is missing"
        return status

    try:
        resp = requests.get("http://127.0.0.1:5001/api/health", timeout=5)
        if resp.ok:
            status["status"] = "running"
            data = resp.json()
            status["tools_count"] = data.get("tools_count", 15)
        else:
            status["status"] = "error"
    except requests.exceptions.ConnectionError:
        status["status"] = "offline"
    except Exception as e:
        status["status"] = f"error: {str(e)[:50]}"

    return status


def get_git_info() -> dict:
    """Get current git branch and commit info."""
    info = {
        "branch": "unknown",
        "commit": "unknown",
        "dirty": False
    }

    try:
        # Get current branch
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            info["branch"] = result.stdout.strip()

        # Get latest commit
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            info["commit"] = result.stdout.strip()

        # Check if dirty
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            info["dirty"] = len(result.stdout.strip()) > 0

    except Exception as e:
        print(f"  Warning: Could not get git info: {e}")

    return info


# MARKER_119.6: Auto-sync phase, headline, achievements from git log
def auto_sync_from_git(digest: dict) -> dict:
    """Auto-sync phase, headline, and achievements from last git commit.

    Called during pre-commit hook to keep digest in sync with git history.
    Extracts phase number from commit message, updates current_phase,
    generates headline, adds achievement, and cleans completed pending_items.
    """
    try:
        # Get last commit message
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H %s"],
            cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return digest

        parts = result.stdout.strip().split(" ", 1)
        if len(parts) < 2:
            return digest
        commit_hash, message = parts[0][:8], parts[1]

        # Extract phase from commit message — supports multiple formats:
        # "Phase 119.5: ..."  →  (119, "5")
        # "Phase 144 COMPLETE: ..."  →  (144, "0")
        # "MARKER_144.7: ..."  →  (144, "7")
        phase_match = re.search(r'Phase\s+(\d+)\.(\d+)', message, re.IGNORECASE)
        if not phase_match:
            # Try "Phase X COMPLETE" or "Phase X:" without subphase
            phase_match = re.search(r'Phase\s+(\d+)\b', message, re.IGNORECASE)
        if not phase_match:
            # Try "MARKER_X.Y" format (e.g., "MARKER_144.7:")
            phase_match = re.search(r'MARKER[_\s]+(\d+)\.(\d+)', message, re.IGNORECASE)
        if not phase_match:
            return digest

        phase_num = int(phase_match.group(1))
        try:
            subphase = phase_match.group(2) or "0"
        except IndexError:
            subphase = "0"

        # Update current_phase
        digest.setdefault("current_phase", {})
        digest["current_phase"]["number"] = phase_num
        digest["current_phase"]["subphase"] = subphase

        # Detect status from message content
        if "complete" in message.lower():
            digest["current_phase"]["status"] = "COMPLETED"
        else:
            digest["current_phase"]["status"] = "IN_PROGRESS"

        # Extract title — supports Phase, MARKER_, and COMPLETE variants
        title_match = re.search(
            r'(?:Phase|MARKER[_\s])\s*\d+[\.\d]*\s*(?:COMPLETE)?[:\s\u2014\u2014—-]+(.+?)(?:\n|$)',
            message, re.IGNORECASE
        )
        if title_match:
            digest["current_phase"]["name"] = title_match.group(1).strip()[:80]

        # Auto-generate headline
        name = digest["current_phase"].get("name", "")
        digest.setdefault("summary", {})
        digest["summary"]["headline"] = f"Phase {phase_num}.{subphase} DONE! {name}"

        # Add achievement if not already present (breaking news pattern)
        achievement = f"[{commit_hash}] Phase {phase_num}.{subphase}: {message[:60]}"
        achievements = digest.get("summary", {}).get("key_achievements", [])
        if not any(commit_hash in a for a in achievements):
            achievements.insert(0, achievement)
            digest["summary"]["key_achievements"] = achievements[:10]

        # Clean completed items from pending_items
        pending = digest.get("summary", {}).get("pending_items", [])
        cleaned = []
        for item in pending:
            item_match = re.search(r'Phase\s+(\d+)\.(\d+)', item)
            if item_match:
                item_phase = int(item_match.group(1))
                item_sub = int(item_match.group(2))
                if item_phase < phase_num or (item_phase == phase_num and item_sub <= int(subphase)):
                    continue  # Skip — this phase is done
            cleaned.append(item)
        digest["summary"]["pending_items"] = cleaned

        print(f"  Auto-sync: Phase {phase_num}.{subphase} from git ({commit_hash})")

    except Exception as e:
        print(f"  Warning: auto_sync_from_git failed: {e}")

    return digest
# MARKER_119.6_END


def load_digest() -> dict:
    """Load existing digest or return default structure."""
    if DIGEST_PATH.exists():
        try:
            with open(DIGEST_PATH, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("  Warning: Invalid JSON in digest, using defaults")

    return {
        "version": "1.0.0",
        "last_updated": None,
        "auto_updated": False,
        "current_phase": {
            "number": 101,
            "subphase": "2",
            "name": "Unknown",
            "status": "UNKNOWN"
        },
        "summary": {
            "headline": "",
            "key_achievements": [],
            "pending_items": []
        },
        "system_status": {},
        "recent_fixes": [],
        "architecture": {},
        "documentation": {},
        "agent_instructions": {},
        "agent_notes": [],  # MARKER_109_12: Phase 109.12 - Agent research notes
        "quick_commands": {}
    }


def save_digest(digest: dict):
    """Save digest to file."""
    DIGEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DIGEST_PATH, 'w') as f:
        json.dump(digest, f, indent=2)
    print(f"  Saved: {DIGEST_PATH}")


def git_commit_digest(message: str = None) -> bool:
    """
    Commit project_digest.json to git with auto-generated message.

    Returns True if commit was successful.
    """
    try:
        # Stage the digest file
        result = subprocess.run(
            ["git", "add", "data/project_digest.json"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            print(f"  Warning: git add failed: {result.stderr}")
            return False

        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print("  No changes to commit")
            return True

        # Generate commit message
        if not message:
            digest = load_digest()
            phase = digest.get("current_phase", {})
            phase_str = f"Phase {phase.get('number', '?')}.{phase.get('subphase', '?')}"
            status = phase.get('status', 'UPDATE')
            message = f"[Digest] {phase_str} - {status}"

        # Commit
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print(f"  Git commit: {message}")
            return True
        else:
            print(f"  Warning: git commit failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"  Warning: git commit error: {e}")
        return False


def git_push(remote: str = "origin", branch: str = None) -> bool:
    """
    Push commits to remote.

    Returns True if push was successful.
    """
    try:
        # Get current branch if not specified
        if not branch:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=5
            )
            branch = result.stdout.strip() if result.returncode == 0 else "main"

        # Push
        result = subprocess.run(
            ["git", "push", remote, branch],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            print(f"  Git push: {remote}/{branch}")
            return True
        else:
            # SSH passphrase might be needed
            print(f"  Warning: git push may need manual intervention")
            print(f"  Run: git push {remote} {branch}")
            return False

    except Exception as e:
        print(f"  Warning: git push error: {e}")
        return False


def update_digest(
    phase_number: int = None,
    phase_subphase: str = None,
    phase_name: str = None,
    phase_status: str = None,
    headline: str = None,
    add_achievement: str = None,
    add_pending: str = None,
    add_fix: dict = None,
    add_agent_note: dict = None  # MARKER_109_12: {"agent": "...", "note": "...", "phase": "...", "status": "..."}
):
    """Update digest with new information."""
    print("=" * 60)
    print("Project Digest Auto-Update")
    print("=" * 60)

    digest = load_digest()

    # MARKER_119.6: Auto-sync from git before manual overrides
    digest = auto_sync_from_git(digest)

    # Update timestamp
    digest["last_updated"] = datetime.now(timezone.utc).isoformat()
    digest["auto_updated"] = True

    # Update phase if provided (manual overrides auto-sync)
    if phase_number is not None:
        digest["current_phase"]["number"] = phase_number
        print(f"  Phase number: {phase_number}")
    if phase_subphase is not None:
        digest["current_phase"]["subphase"] = phase_subphase
        print(f"  Subphase: {phase_subphase}")
    if phase_name is not None:
        digest["current_phase"]["name"] = phase_name
        print(f"  Phase name: {phase_name}")
    if phase_status is not None:
        digest["current_phase"]["status"] = phase_status
        print(f"  Phase status: {phase_status}")

    # Update summary
    if headline:
        digest["summary"]["headline"] = headline
        print(f"  Headline: {headline}")
    if add_achievement:
        if add_achievement not in digest["summary"]["key_achievements"]:
            digest["summary"]["key_achievements"].append(add_achievement)
            print(f"  Added achievement: {add_achievement}")
    if add_pending:
        if add_pending not in digest["summary"]["pending_items"]:
            digest["summary"]["pending_items"].append(add_pending)
            print(f"  Added pending: {add_pending}")

    # Add fix if provided
    if add_fix:
        # Check if fix ID already exists
        existing_ids = [f.get("id") for f in digest.get("recent_fixes", [])]
        if add_fix.get("id") not in existing_ids:
            digest.setdefault("recent_fixes", []).insert(0, add_fix)
            print(f"  Added fix: {add_fix.get('id')}")

    # MARKER_109_12: Add agent note if provided
    if add_agent_note:
        note_entry = {
            "agent": add_agent_note.get("agent", "Unknown"),
            "note": add_agent_note.get("note", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": add_agent_note.get("phase", ""),
            "status": add_agent_note.get("status", "completed")
        }
        digest.setdefault("agent_notes", []).insert(0, note_entry)
        # Keep only last 10 notes
        digest["agent_notes"] = digest["agent_notes"][:10]
        print(f"  Added agent note from: {note_entry['agent']}")

    # Auto-update system status
    print("\nUpdating system status...")
    qdrant_stats = get_qdrant_stats()
    digest["system_status"]["vetka_elisya"] = qdrant_stats["vetka_elisya"]
    digest["system_status"]["vetka_tree"] = qdrant_stats["vetka_tree"]
    print(f"  vetka_elisya: {qdrant_stats['vetka_elisya']['points']} points")
    print(f"  VetkaTree: {qdrant_stats['vetka_tree']['points']} points")

    mcp_status = get_mcp_status()
    digest["system_status"]["mcp_server"] = mcp_status
    print(f"  MCP server: {mcp_status['status']}")

    # Add git info
    git_info = get_git_info()
    digest["git"] = git_info
    print(f"  Git: {git_info['branch']}@{git_info['commit']}" +
          (" (dirty)" if git_info['dirty'] else ""))

    save_digest(digest)

    print("\n" + "=" * 60)
    print("Update Complete!")
    print("=" * 60)

    return digest


def main():
    parser = argparse.ArgumentParser(description="Update project digest")
    parser.add_argument("--phase", type=int, help="Phase number")
    parser.add_argument("--subphase", type=str, help="Subphase (e.g., '2', '3a')")
    parser.add_argument("--name", type=str, help="Phase name")
    parser.add_argument("--status", type=str, choices=["PLANNING", "IN_PROGRESS", "COMPLETED", "BLOCKED"],
                        help="Phase status")
    parser.add_argument("--headline", type=str, help="Summary headline")
    parser.add_argument("--achievement", type=str, help="Add achievement")
    parser.add_argument("--pending", type=str, help="Add pending item")
    parser.add_argument("--fix-id", type=str, help="Fix ID (e.g., FIX_102.1)")
    parser.add_argument("--fix-file", type=str, help="File path for fix")
    parser.add_argument("--fix-line", type=int, help="Line number for fix")
    parser.add_argument("--fix-desc", type=str, help="Fix description")

    # MARKER_109_12: Agent notes
    parser.add_argument("--agent-note", type=str, help="Agent note text")
    parser.add_argument("--agent-name", type=str, help="Agent name (e.g., 'Haiku Scout', 'Grok')")
    parser.add_argument("--agent-phase", type=str, help="Phase for agent note")
    parser.add_argument("--agent-status", type=str, help="Agent status (completed/in_progress/blocked)")

    # Git options
    parser.add_argument("--commit", action="store_true", help="Commit digest to git after update")
    parser.add_argument("--push", action="store_true", help="Push to remote after commit (implies --commit)")
    parser.add_argument("--message", "-m", type=str, help="Custom commit message")

    args = parser.parse_args()

    # Build fix dict if provided
    add_fix = None
    if args.fix_id:
        add_fix = {
            "id": args.fix_id,
            "file": args.fix_file or "unknown",
            "line": args.fix_line or 0,
            "description": args.fix_desc or ""
        }

    # Build agent note dict if provided
    add_agent_note = None
    if args.agent_note:
        add_agent_note = {
            "agent": args.agent_name or "Unknown",
            "note": args.agent_note,
            "phase": args.agent_phase or "",
            "status": args.agent_status or "completed"
        }

    update_digest(
        phase_number=args.phase,
        phase_subphase=args.subphase,
        phase_name=args.name,
        phase_status=args.status,
        headline=args.headline,
        add_achievement=args.achievement,
        add_pending=args.pending,
        add_fix=add_fix,
        add_agent_note=add_agent_note
    )

    # Git operations
    if args.push or args.commit:
        print("\nGit operations...")
        if git_commit_digest(args.message):
            if args.push:
                git_push()


if __name__ == "__main__":
    main()
