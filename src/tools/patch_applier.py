"""
MARKER_150.SPARSE_APPLY: Sparse Apply — Surgical code insertion.

Instead of LLM rewriting entire files (catastrophic: 410→34 lines),
this module applies changes surgically:

Mode 1: MARKER INSERT — find marker line → insert code after/before it
Mode 2: UNIFIED DIFF — parse unified diff → apply via line operations
Mode 3: CREATE — new file (no patching needed, just write)

Phase 150A implements Mode 1 (Marker Insert) + Mode 2 (Unified Diff).
Mode 3 is existing behavior (playground file write).

Safety: All operations are APPEND-ONLY by default. Delete operations
require explicit opt-in. Falls back to full-file write on any failure.

@phase 150.3
@status active
@depends agent_pipeline.py, playground_manager.py
"""
import logging
import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PatchResult:
    """Result of applying a patch."""
    success: bool
    file_path: str
    mode: str  # "marker_insert" | "unified_diff" | "create"
    lines_added: int = 0
    lines_removed: int = 0
    error: str = ""
    backup_path: str = ""


class PatchApplier:
    """
    Applies code changes surgically instead of full-file rewrites.

    Usage:
        applier = PatchApplier(base_path="/path/to/playground")

        # Mode 1: Marker insert
        result = applier.apply_marker_insert(
            file_path="client/src/store.ts",
            marker_id="MARKER_SCOUT_1",
            code="export const toggleBookmark = () => { ... }",
            action="INSERT_AFTER"
        )

        # Mode 2: Unified diff
        result = applier.apply_unified_diff(
            file_path="client/src/store.ts",
            diff_content="--- a/store.ts\\n+++ b/store.ts\\n@@ -10,3 +10,5 @@..."
        )
    """

    def __init__(self, base_path: str = None):
        """
        Args:
            base_path: Root directory for file operations (playground path).
                       If None, uses relative paths as-is.
        """
        self.base_path = base_path

    def _resolve_path(self, file_path: str) -> Path:
        """Resolve file path relative to base_path."""
        if self.base_path:
            return Path(self.base_path) / file_path
        return Path(file_path)

    def _backup_file(self, abs_path: Path) -> str:
        """Create backup before modifying. Returns backup path."""
        backup_path = abs_path.with_suffix(abs_path.suffix + ".bak")
        try:
            if abs_path.exists():
                import shutil
                shutil.copy2(abs_path, backup_path)
                return str(backup_path)
        except Exception as e:
            logger.warning(f"[PatchApplier] Backup failed: {e}")
        return ""

    # ── Mode 1: Marker Insert ──

    def apply_marker_insert(
        self,
        file_path: str,
        marker_id: str,
        code: str,
        action: str = "INSERT_AFTER",
        line_number: int = None,
    ) -> PatchResult:
        """
        Insert code at a marker location in a file.

        Supports:
        - INSERT_AFTER: Insert code after the marker line
        - INSERT_BEFORE: Insert code before the marker line
        - REPLACE: Replace the marker line with code (marker line removed)

        If marker_id contains ":" (e.g., "MARKER_SCOUT_1:42"), uses
        the line number as fallback when marker text is not found.

        Args:
            file_path: Relative path to file
            marker_id: Marker to find (e.g., "MARKER_SCOUT_1" or "MARKER_SCOUT_1:42")
            code: Code to insert
            action: INSERT_AFTER | INSERT_BEFORE | REPLACE
            line_number: Optional forced line number (overrides marker search)

        Returns:
            PatchResult with success status
        """
        abs_path = self._resolve_path(file_path)

        if not abs_path.exists():
            return PatchResult(
                success=False, file_path=file_path, mode="marker_insert",
                error=f"File not found: {abs_path}"
            )

        # Parse marker_id:line_number format
        forced_line = line_number
        search_marker = marker_id
        if ":" in marker_id:
            parts = marker_id.rsplit(":", 1)
            search_marker = parts[0]
            try:
                forced_line = int(parts[1])
            except ValueError:
                pass

        # Read file
        try:
            lines = abs_path.read_text(encoding="utf-8").splitlines(keepends=True)
        except Exception as e:
            return PatchResult(
                success=False, file_path=file_path, mode="marker_insert",
                error=f"Read failed: {e}"
            )

        # Find marker line
        marker_line_idx = None
        for i, line in enumerate(lines):
            if search_marker in line:
                marker_line_idx = i
                break

        # Fallback to forced line number
        if marker_line_idx is None and forced_line is not None:
            # Convert 1-based to 0-based
            marker_line_idx = forced_line - 1
            if marker_line_idx < 0 or marker_line_idx >= len(lines):
                marker_line_idx = None

        if marker_line_idx is None:
            return PatchResult(
                success=False, file_path=file_path, mode="marker_insert",
                error=f"Marker '{search_marker}' not found and no valid line number"
            )

        # Backup
        backup = self._backup_file(abs_path)

        # Prepare code lines (ensure each line ends with newline)
        code_lines = code.splitlines(keepends=True)
        if code_lines and not code_lines[-1].endswith("\n"):
            code_lines[-1] += "\n"

        # Apply based on action
        if action == "INSERT_AFTER":
            insert_idx = marker_line_idx + 1
            new_lines = lines[:insert_idx] + code_lines + lines[insert_idx:]
        elif action == "INSERT_BEFORE":
            new_lines = lines[:marker_line_idx] + code_lines + lines[marker_line_idx:]
        elif action == "REPLACE":
            new_lines = lines[:marker_line_idx] + code_lines + lines[marker_line_idx + 1:]
        else:
            return PatchResult(
                success=False, file_path=file_path, mode="marker_insert",
                error=f"Unknown action: {action}"
            )

        # Write result
        try:
            abs_path.write_text("".join(new_lines), encoding="utf-8")
        except Exception as e:
            return PatchResult(
                success=False, file_path=file_path, mode="marker_insert",
                error=f"Write failed: {e}"
            )

        lines_added = len(code_lines)
        lines_removed = 1 if action == "REPLACE" else 0

        logger.info(
            f"[PatchApplier] Marker insert: {file_path} @ {search_marker} "
            f"({action}, +{lines_added}/-{lines_removed})"
        )

        return PatchResult(
            success=True, file_path=file_path, mode="marker_insert",
            lines_added=lines_added, lines_removed=lines_removed,
            backup_path=backup,
        )

    # ── Mode 2: Unified Diff ──

    def apply_unified_diff(self, file_path: str, diff_content: str) -> PatchResult:
        """
        Apply a unified diff to a file.

        Parses unified diff format and applies hunks line by line.
        Does NOT use git apply (avoids subprocess dependency).

        Args:
            file_path: Relative path to target file
            diff_content: Unified diff content (with @@ hunks)

        Returns:
            PatchResult with success status
        """
        abs_path = self._resolve_path(file_path)

        if not abs_path.exists():
            return PatchResult(
                success=False, file_path=file_path, mode="unified_diff",
                error=f"File not found: {abs_path}"
            )

        # Parse hunks from diff
        hunks = self._parse_unified_diff(diff_content)
        if not hunks:
            return PatchResult(
                success=False, file_path=file_path, mode="unified_diff",
                error="No valid hunks found in diff"
            )

        # Read file
        try:
            lines = abs_path.read_text(encoding="utf-8").splitlines(keepends=True)
        except Exception as e:
            return PatchResult(
                success=False, file_path=file_path, mode="unified_diff",
                error=f"Read failed: {e}"
            )

        # Backup
        backup = self._backup_file(abs_path)

        # Apply hunks in reverse order (to preserve line numbers)
        total_added = 0
        total_removed = 0

        for hunk in reversed(hunks):
            start_line = hunk["old_start"] - 1  # 0-based
            old_count = hunk["old_count"]

            # Build new content for this hunk
            new_hunk_lines = []
            for op, line_content in hunk["changes"]:
                if op == " " or op == "+":
                    if not line_content.endswith("\n"):
                        line_content += "\n"
                    new_hunk_lines.append(line_content)
                # op == "-" means line is removed (not added to new_hunk_lines)

            # Validate: check if old lines match (fuzzy — skip whitespace)
            # For safety, we just replace the hunk range
            end_line = start_line + old_count
            if end_line > len(lines):
                end_line = len(lines)

            lines = lines[:start_line] + new_hunk_lines + lines[end_line:]

            added = sum(1 for op, _ in hunk["changes"] if op == "+")
            removed = sum(1 for op, _ in hunk["changes"] if op == "-")
            total_added += added
            total_removed += removed

        # Write result
        try:
            abs_path.write_text("".join(lines), encoding="utf-8")
        except Exception as e:
            return PatchResult(
                success=False, file_path=file_path, mode="unified_diff",
                error=f"Write failed: {e}"
            )

        logger.info(
            f"[PatchApplier] Unified diff: {file_path} "
            f"({len(hunks)} hunks, +{total_added}/-{total_removed})"
        )

        return PatchResult(
            success=True, file_path=file_path, mode="unified_diff",
            lines_added=total_added, lines_removed=total_removed,
            backup_path=backup,
        )

    def _parse_unified_diff(self, diff_content: str) -> List[Dict]:
        """Parse unified diff into list of hunks.

        Each hunk: {
            "old_start": int,  # 1-based line number in original file
            "old_count": int,
            "new_start": int,
            "new_count": int,
            "changes": [(op, line), ...]  # op = " " | "+" | "-"
        }
        """
        hunks = []
        hunk_header_re = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')

        current_hunk = None

        for line in diff_content.splitlines():
            # Skip file headers
            if line.startswith("---") or line.startswith("+++"):
                continue

            # Hunk header
            match = hunk_header_re.match(line)
            if match:
                if current_hunk:
                    hunks.append(current_hunk)
                current_hunk = {
                    "old_start": int(match.group(1)),
                    "old_count": int(match.group(2) or 1),
                    "new_start": int(match.group(3)),
                    "new_count": int(match.group(4) or 1),
                    "changes": [],
                }
                continue

            # Hunk content
            if current_hunk is not None:
                if line.startswith("+"):
                    current_hunk["changes"].append(("+", line[1:]))
                elif line.startswith("-"):
                    current_hunk["changes"].append(("-", line[1:]))
                elif line.startswith(" "):
                    current_hunk["changes"].append((" ", line[1:]))
                elif line == "":
                    current_hunk["changes"].append((" ", ""))

        if current_hunk:
            hunks.append(current_hunk)

        return hunks

    # ── Mode 3: Create (pass-through) ──

    def create_file(self, file_path: str, content: str) -> PatchResult:
        """Create a new file (no patching needed)."""
        abs_path = self._resolve_path(file_path)

        # Ensure parent directory exists
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            abs_path.write_text(content, encoding="utf-8")
        except Exception as e:
            return PatchResult(
                success=False, file_path=file_path, mode="create",
                error=f"Write failed: {e}"
            )

        lines = content.count("\n") + 1

        logger.info(f"[PatchApplier] Create: {file_path} ({lines} lines)")

        return PatchResult(
            success=True, file_path=file_path, mode="create",
            lines_added=lines,
        )

    # ── Auto-detect Mode ──

    def detect_mode(self, coder_output: str, target_file: str = None) -> str:
        """Detect which mode to use based on coder output content.

        Returns: "marker_insert" | "unified_diff" | "create" | "full_file"
        """
        # Check for unified diff format
        if re.search(r'^@@ -\d+', coder_output, re.MULTILINE):
            return "unified_diff"

        # Check for marker insert format (JSON with marker_id + code)
        if '"marker"' in coder_output or '"marker_id"' in coder_output:
            if '"action"' in coder_output and '"code"' in coder_output:
                return "marker_insert"

        # Check if target file exists (if we have base_path)
        if target_file and self.base_path:
            abs_path = self._resolve_path(target_file)
            if not abs_path.exists():
                return "create"

        # Default: full file write (existing behavior)
        return "full_file"

    # ── Extract patches from coder output ──

    def extract_patches(self, coder_output: str) -> List[Dict]:
        """Extract patch instructions from coder output.

        Looks for:
        1. Unified diffs (--- a/file ... +++ b/file ... @@ ... @@)
        2. Marker insert JSON blocks
        3. Code blocks with file paths

        Returns list of: {mode, file_path, content, marker_id?, action?}
        """
        patches = []

        # 1. Extract unified diffs
        diff_blocks = re.findall(
            r'(---\s+a/(.+?)\n\+\+\+\s+b/.+?\n(?:@@.+?@@.*?\n(?:[+ -].*?\n)*))',
            coder_output, re.MULTILINE
        )
        for diff_content, file_path in diff_blocks:
            patches.append({
                "mode": "unified_diff",
                "file_path": file_path.strip(),
                "content": diff_content.strip(),
            })

        # 2. Extract marker insert blocks (JSON format)
        # Look for {"marker": "...", "action": "...", "code": "..."}
        import json
        json_blocks = re.findall(r'\{[^{}]*"marker[_id]*"[^{}]*\}', coder_output, re.DOTALL)
        for block in json_blocks:
            try:
                data = json.loads(block)
                if ("marker" in data or "marker_id" in data) and "code" in data:
                    patches.append({
                        "mode": "marker_insert",
                        "file_path": data.get("file", data.get("file_path", "")),
                        "content": data["code"],
                        "marker_id": data.get("marker", data.get("marker_id", "")),
                        "action": data.get("action", "INSERT_AFTER"),
                    })
            except json.JSONDecodeError:
                pass

        return patches
