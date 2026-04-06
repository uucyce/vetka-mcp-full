# === PHASE 203: PULSAR SCOUT SERVICE ===
"""
VETKA Phase 203 — Scout: The PULSAR Telescope

MARKER_203.SCOUT

Local, synchronous, deterministic code analysis.
Finds exact code locations for tasks via ripgrep + ast.parse.
Injects scout_context into tasks so Sherpa gets real code, not guesses.

Flow:
    task (title, description, allowed_paths, domain)
    → extract keywords → ripgrep with line numbers
    → expand to symbol boundaries (ast.parse for Python)
    → score by relevance → top markers → scout_context

@status: active
@phase: 203
@depends: subprocess (ripgrep), ast
@used_by: src/orchestration/task_board.py
"""

import ast
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("VETKA_SCOUT")


# ============================================================================
# PROJECT ROOT
# ============================================================================

def _resolve_project_root() -> Path:
    """Find the main repo root, even when called from a worktree."""
    env_root = os.environ.get("VETKA_MAIN_REPO")
    if env_root and Path(env_root).is_dir():
        return Path(env_root)
    return Path(__file__).resolve().parent.parent.parent


PROJECT_ROOT = _resolve_project_root()

# MARKER_203.SCOUT.RG: ripgrep binary path
_RG_BIN = os.environ.get("VETKA_RG_BIN", "rg")

# Max markers to return per analysis
MAX_MARKERS = 8
# Max snippet lines
SNIPPET_LINES = 10
# ripgrep timeout in seconds
RG_TIMEOUT = 5


# ============================================================================
# DOMAIN -> SEARCH DIRECTORIES MAPPING
# ============================================================================

# MARKER_203.SCOUT.DOMAINS: Derived from agent_registry.yaml
DOMAIN_PATHS: Dict[str, List[str]] = {
    "engine": [
        "client/src/store/",
        "client/src/hooks/",
        "client/src/components/cut/TimelineTrackView.tsx",
        "client/src/components/cut/CutEditorLayoutV2.tsx",
        "client/src-tauri/",
    ],
    "media": [
        "src/services/cut_codec_probe.py",
        "src/services/cut_render_engine.py",
        "src/services/cut_effects_engine.py",
        "src/services/cut_color_pipeline.py",
        "src/services/cut_lut_manager.py",
        "client/src/components/cut/panels/",
    ],
    "ux": [
        "client/src/components/cut/MenuBar.tsx",
        "client/src/components/cut/DockviewLayout.tsx",
        "client/src/components/cut/VideoPreview.tsx",
        "client/src/components/cut/panels/",
    ],
    "qa": [
        "e2e/",
        "tests/",
    ],
    "harness": [
        "src/mcp/tools/",
        "src/orchestration/",
        "src/services/",
    ],
    "architect": [
        "docs/",
    ],
}


# ============================================================================
# STOP WORDS
# ============================================================================

_STOP_WORDS = frozenset({
    "the", "a", "an", "in", "on", "at", "to", "for", "of", "is", "it",
    "and", "or", "not", "with", "from", "by", "as", "be", "was", "are",
    "this", "that", "all", "add", "fix", "update", "implement", "create",
    "new", "use", "make", "set", "get", "task", "file", "code", "should",
    "when", "after", "before", "into", "also", "must", "can", "will",
})


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ScoutMarker:
    """A code location found by Scout for a task.

    MARKER_203.SCOUT.MARKER
    """
    file: str           # Relative path: "src/orchestration/task_board.py"
    start_line: int     # First line of enclosing symbol
    end_line: int       # Last line of enclosing symbol
    symbol: str         # "class TaskBoard.update_status"
    snippet: str        # First N lines of the region
    relevance: float    # 0.0-1.0 (term overlap score)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "symbol": self.symbol,
            "snippet": self.snippet,
            "relevance": round(self.relevance, 3),
        }


# ============================================================================
# SCOUT CLASS
# ============================================================================

class Scout:
    """PULSAR Scout — local code analysis for task context enrichment.

    MARKER_203.SCOUT.MAIN

    Analyzes task metadata (title, description, allowed_paths, domain)
    and finds specific code locations via ripgrep + ast.parse.
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.root = project_root or PROJECT_ROOT

    def analyze(self, task: Dict[str, Any]) -> List[ScoutMarker]:
        """Analyze a task and return relevant code markers.

        Args:
            task: Task dict with title, description, allowed_paths, domain, etc.

        Returns:
            List of ScoutMarker sorted by relevance (max MAX_MARKERS).
            Empty list if no relevant code found.
            Never raises — returns [] on any error.
        """
        try:
            return self._analyze_inner(task)
        except Exception as exc:
            logger.warning("[Scout] analyze failed (safe): %s", exc)
            return []

    def _analyze_inner(self, task: Dict[str, Any]) -> List[ScoutMarker]:
        # Step 1: Extract keywords
        keywords = self._extract_keywords(task)
        if not keywords:
            logger.debug("[Scout] No keywords extracted from task %s", task.get("id", "?"))
            return []

        # Step 2: Resolve search scope
        search_dirs = self._resolve_scope(task)

        # Step 3: ripgrep for keyword matches with line numbers
        raw_matches = self._ripgrep_search(keywords, search_dirs)
        if not raw_matches:
            logger.debug("[Scout] No ripgrep matches for task %s", task.get("id", "?"))
            return []

        # Step 4: Expand to symbol boundaries
        markers = self._expand_to_symbols(raw_matches, keywords)

        # Step 5: Deduplicate overlapping markers
        markers = self._deduplicate(markers)

        # Step 6: Sort by relevance, take top N
        markers.sort(key=lambda m: m.relevance, reverse=True)
        return markers[:MAX_MARKERS]

    # ── Step 1: Keyword Extraction ─────────────────────────────────────

    @staticmethod
    def _extract_keywords(task: Dict[str, Any]) -> List[str]:
        """Extract technical keywords from task title + description."""
        text = f"{task.get('title', '')} {task.get('description', '')}"
        # Split on non-alphanumeric (keep underscores for identifiers)
        tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', text.lower())
        # Filter stop words and short tokens
        keywords = []
        seen = set()
        for t in tokens:
            if t in _STOP_WORDS or len(t) < 3:
                continue
            if t not in seen:
                seen.add(t)
                keywords.append(t)
        return keywords[:20]  # Cap at 20 keywords

    # ── Step 2: Scope Resolution ───────────────────────────────────────

    def _resolve_scope(self, task: Dict[str, Any]) -> List[str]:
        """Resolve search directories from allowed_paths + domain."""
        dirs = []

        # From allowed_paths
        for p in (task.get("allowed_paths") or []):
            p = str(p).strip()
            if p:
                full = self.root / p
                if full.exists():
                    dirs.append(p)
                elif full.parent.exists():
                    # Path might be a file that doesn't exist yet — use parent
                    dirs.append(str(Path(p).parent))

        # From domain
        domain = str(task.get("domain") or "").lower()
        if domain in DOMAIN_PATHS:
            for dp in DOMAIN_PATHS[domain]:
                full = self.root / dp
                if full.exists():
                    dirs.append(dp)

        # Deduplicate
        seen = set()
        unique = []
        for d in dirs:
            if d not in seen:
                seen.add(d)
                unique.append(d)

        # Fallback: search common code dirs
        if not unique:
            for fallback in ["src/", "client/src/"]:
                if (self.root / fallback).is_dir():
                    unique.append(fallback)

        return unique

    # ── Step 3: ripgrep Search ─────────────────────────────────────────

    def _ripgrep_search(
        self, keywords: List[str], search_dirs: List[str]
    ) -> List[Dict[str, Any]]:
        """Run ripgrep to find keyword matches with line numbers.

        Returns list of {file, line, content, keyword} dicts.
        """
        matches = []
        # Build pattern: join keywords with OR
        # Use top 8 most specific keywords to keep search fast
        search_keywords = keywords[:8]
        pattern = "|".join(re.escape(kw) for kw in search_keywords)

        abs_dirs = []
        for d in search_dirs:
            full = self.root / d
            if full.exists():
                abs_dirs.append(str(full))

        if not abs_dirs:
            return []

        try:
            cmd = [
                _RG_BIN, "--no-heading", "-n", "-i",
                "--type", "py", "--type", "ts",
                "--max-count", "50",  # Max matches per file
                pattern,
            ] + abs_dirs

            result = subprocess.run(
                cmd,
                capture_output=True, text=True,
                timeout=RG_TIMEOUT,
                cwd=str(self.root),
            )
            # rg returns 1 if no matches (not an error)
            if result.returncode > 1:
                logger.debug("[Scout] rg returned %d: %s", result.returncode, result.stderr[:200])
                return []

            for line in result.stdout.splitlines():
                # Format: /abs/path/file.py:42:content
                parts = line.split(":", 2)
                if len(parts) < 3:
                    continue
                filepath = parts[0]
                try:
                    lineno = int(parts[1])
                except ValueError:
                    continue
                content = parts[2]

                # Convert to relative path
                try:
                    rel = str(Path(filepath).relative_to(self.root))
                except ValueError:
                    rel = filepath

                # Track which keywords matched
                matched_kws = [kw for kw in search_keywords if kw.lower() in content.lower()]
                matches.append({
                    "file": rel,
                    "line": lineno,
                    "content": content.strip(),
                    "keywords": matched_kws,
                })

        except subprocess.TimeoutExpired:
            logger.warning("[Scout] ripgrep timed out after %ds", RG_TIMEOUT)
        except FileNotFoundError:
            logger.warning("[Scout] ripgrep not found at %s", _RG_BIN)
        except Exception as exc:
            logger.warning("[Scout] ripgrep error: %s", exc)

        return matches

    # ── Step 4: Symbol Expansion ───────────────────────────────────────

    def _expand_to_symbols(
        self, matches: List[Dict[str, Any]], keywords: List[str]
    ) -> List[ScoutMarker]:
        """Expand line matches to enclosing symbol boundaries."""
        markers = []
        keyword_set = set(kw.lower() for kw in keywords)

        # Group matches by file
        by_file: Dict[str, List[Dict]] = {}
        for m in matches:
            by_file.setdefault(m["file"], []).append(m)

        for filepath, file_matches in by_file.items():
            full_path = self.root / filepath

            if filepath.endswith(".py"):
                file_markers = self._expand_python(full_path, file_matches, keyword_set)
            else:
                # For non-Python files: use simple line-range expansion
                file_markers = self._expand_simple(full_path, file_matches, keyword_set)

            markers.extend(file_markers)

        return markers

    def _expand_python(
        self, filepath: Path, matches: List[Dict], keyword_set: set
    ) -> List[ScoutMarker]:
        """Use ast.parse to find enclosing functions/classes for Python files."""
        markers = []
        try:
            source = filepath.read_text(encoding="utf-8", errors="replace")
            lines = source.splitlines()
            tree = ast.parse(source, filename=str(filepath))
        except (SyntaxError, UnicodeDecodeError, OSError) as exc:
            logger.debug("[Scout] Cannot parse %s: %s", filepath, exc)
            return self._expand_simple(filepath, matches, keyword_set)

        # Build symbol map: line -> (symbol_name, start_line, end_line)
        symbols = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = getattr(node, 'name', '?')
                start = node.lineno
                end = getattr(node, 'end_lineno', start + 10) or start + 10
                # Try to get parent class name
                parent_name = ""
                for parent in ast.walk(tree):
                    if isinstance(parent, ast.ClassDef):
                        for child in ast.iter_child_nodes(parent):
                            if child is node:
                                parent_name = parent.name + "."
                                break
                symbol_name = f"{parent_name}{name}"
                symbols.append((start, end, symbol_name))

        # For each match, find enclosing symbol
        rel_path = str(filepath.relative_to(self.root))
        seen_symbols = set()

        for match in matches:
            line = match["line"]
            best_symbol = None
            best_start = 1
            best_end = min(len(lines), line + SNIPPET_LINES)

            for s_start, s_end, s_name in symbols:
                if s_start <= line <= s_end:
                    # Pick the tightest enclosing symbol
                    if best_symbol is None or (s_end - s_start) < (best_end - best_start):
                        best_symbol = s_name
                        best_start = s_start
                        best_end = s_end

            if best_symbol is None:
                best_symbol = f"<module>:{line}"
                best_start = max(1, line - 2)
                best_end = min(len(lines), line + SNIPPET_LINES)

            # Deduplicate by symbol within same file
            dedup_key = (rel_path, best_symbol)
            if dedup_key in seen_symbols:
                continue
            seen_symbols.add(dedup_key)

            # Build snippet
            snippet_lines = lines[best_start - 1:best_start - 1 + SNIPPET_LINES]
            snippet = "\n".join(snippet_lines)

            # Score relevance
            symbol_text = f"{best_symbol} {snippet}".lower()
            matched_count = sum(1 for kw in keyword_set if kw in symbol_text)
            relevance = min(1.0, matched_count / max(len(keyword_set), 1))

            markers.append(ScoutMarker(
                file=rel_path,
                start_line=best_start,
                end_line=best_end,
                symbol=best_symbol,
                snippet=snippet,
                relevance=relevance,
            ))

        return markers

    def _expand_simple(
        self, filepath: Path, matches: List[Dict], keyword_set: set
    ) -> List[ScoutMarker]:
        """Simple line-range expansion for non-Python files."""
        markers = []
        try:
            lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return []

        rel_path = str(filepath.relative_to(self.root))
        seen_ranges = set()

        for match in matches:
            line = match["line"]
            start = max(1, line - 3)
            end = min(len(lines), line + SNIPPET_LINES)

            # Deduplicate overlapping ranges
            range_key = (rel_path, start // 20)  # Group by ~20-line blocks
            if range_key in seen_ranges:
                continue
            seen_ranges.add(range_key)

            snippet_lines = lines[start - 1:start - 1 + SNIPPET_LINES]
            snippet = "\n".join(snippet_lines)

            symbol_text = f"{match['content']} {snippet}".lower()
            matched_count = sum(1 for kw in keyword_set if kw in symbol_text)
            relevance = min(1.0, matched_count / max(len(keyword_set), 1))

            markers.append(ScoutMarker(
                file=rel_path,
                start_line=start,
                end_line=end,
                symbol=f"line:{line}",
                snippet=snippet,
                relevance=relevance,
            ))

        return markers

    # ── Step 5: Deduplication ──────────────────────────────────────────

    @staticmethod
    def _deduplicate(markers: List[ScoutMarker]) -> List[ScoutMarker]:
        """Remove overlapping markers, keeping the one with higher relevance."""
        if not markers:
            return []

        # Sort by file, then start_line
        markers.sort(key=lambda m: (m.file, m.start_line))
        result = [markers[0]]

        for m in markers[1:]:
            prev = result[-1]
            if m.file == prev.file and m.start_line <= prev.end_line:
                # Overlap: keep higher relevance
                if m.relevance > prev.relevance:
                    result[-1] = m
            else:
                result.append(m)

        return result


# ============================================================================
# SINGLETON
# ============================================================================

_scout_instance: Optional[Scout] = None


def get_scout(project_root: Optional[Path] = None) -> Scout:
    """Get or create the Scout singleton."""
    global _scout_instance
    if _scout_instance is None:
        _scout_instance = Scout(project_root=project_root)
    return _scout_instance


def reset_scout() -> None:
    """Reset the Scout singleton (for testing)."""
    global _scout_instance
    _scout_instance = None
