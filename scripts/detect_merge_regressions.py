#!/usr/bin/env python3
"""
detect_merge_regressions.py — Post-merge regression detector.

Scans git diff after a merge for two classes of regression:

  1. EXPORTS: export declarations removed by the merge that are still imported
               elsewhere (broken import → runtime crash or build failure)
  2. MARKERS: conflict markers (<<<<<<< / ======= / >>>>>>>) shipped in any
               changed file (the fa6245ca1 incident class)

Usage:
  python scripts/detect_merge_regressions.py [merge_commit] [options]

  merge_commit        SHA of merge commit (default: HEAD if it is a merge,
                      else walks back to find the last merge commit)
  --create-tasks      POST a DELTA-BUG task for each regression found
  --api-url URL       Task board REST base URL (default: http://localhost:5001)
  --json              Machine-readable JSON output
  --root PATH         Repo root (default: git rev-parse --show-toplevel)
  --ext .ts .tsx .py  File extensions to scan (default: .ts .tsx .js .jsx .py)

Exit codes:
  0  No regressions
  1  Regressions found
  2  Usage / git error
"""

import argparse
import json
import re
import subprocess
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def git(*args: str, cwd: str | None = None) -> str:
    try:
        return subprocess.check_output(
            ["git"] + list(args), text=True,
            stderr=subprocess.DEVNULL, cwd=cwd,
        ).strip()
    except subprocess.CalledProcessError:
        return ""


def repo_root(hint: str | None) -> str:
    if hint:
        return hint
    r = git("rev-parse", "--show-toplevel")
    if not r:
        print("ERROR: not inside a git repo", file=sys.stderr)
        sys.exit(2)
    return r


def find_merge_commit(ref: str | None, root: str) -> str:
    if ref:
        return ref
    # Is HEAD itself a merge commit?
    head = git("rev-parse", "HEAD", cwd=root)
    parents_line = git("cat-file", "-p", head, cwd=root)
    parent_count = sum(1 for l in parents_line.splitlines() if l.startswith("parent "))
    if parent_count >= 2:
        return head
    # Walk back to find last merge
    log = git("log", "--merges", "--format=%H", "-1", cwd=root)
    if not log:
        print("ERROR: no merge commit found", file=sys.stderr)
        sys.exit(2)
    return log


def merge_parents(commit: str, root: str) -> tuple[str, str]:
    raw = git("cat-file", "-p", commit, cwd=root)
    parents = [l.split()[1] for l in raw.splitlines() if l.startswith("parent ")]
    if len(parents) < 2:
        print(f"ERROR: {commit[:12]} is not a merge commit", file=sys.stderr)
        sys.exit(2)
    return parents[0], parents[1]


def diff_text(base: str, head: str, root: str) -> str:
    return git("diff", base, head, "--unified=0", cwd=root)


def files_changed(base: str, head: str, root: str) -> list[str]:
    out = git("diff", "--name-only", base, head, cwd=root)
    return [f for f in out.splitlines() if f]


def file_content_at(commit: str, path: str, root: str) -> str:
    return git("show", f"{commit}:{path}", cwd=root)


# ---------------------------------------------------------------------------
# Export/import parsing
# ---------------------------------------------------------------------------

# Patterns for named exports in TS/JS/Python
_TS_EXPORT_RE = re.compile(
    r'^export\s+(?:(?:default|abstract|declare)\s+)*'
    r'(?:const|let|var|function\*?|class|type|interface|enum|async\s+function\*?)\s+'
    r'(\w+)',
)
_TS_EXPORT_BRACE_RE = re.compile(r'^export\s*\{([^}]+)\}')
_PY_DEF_RE = re.compile(r'^(?:def|class|async\s+def)\s+(\w+)')
_PY_ALL_RE  = re.compile(r'__all__\s*=\s*\[([^\]]+)\]')

# Patterns for imports
_TS_IMPORT_RE  = re.compile(r'\bimport\s*\{([^}]+)\}')      # import { a, b }
_TS_IMPORT2_RE = re.compile(r'\bimport\s+(\w+)\b')           # import Foo from
_PY_IMPORT_RE  = re.compile(r'from\s+\S+\s+import\s+(.+)')   # from x import a, b


def extract_removed_exports(diff: str, exts: set[str]) -> dict[str, list[str]]:
    """
    Returns {export_name: [files_it_was_removed_from]}.
    Only looks at lines starting with '-' (removed) in relevant file sections.
    """
    removed: dict[str, list[str]] = {}
    current_file = ""
    in_target = False

    for line in diff.splitlines():
        if line.startswith("diff --git "):
            current_file = ""
            in_target = False
        elif line.startswith("+++ b/"):
            current_file = line[6:]
            ext = Path(current_file).suffix
            in_target = ext in exts
        elif in_target and line.startswith("-") and not line.startswith("---"):
            content = line[1:].strip()
            names = _names_from_export_line(content, current_file)
            for name in names:
                removed.setdefault(name, []).append(current_file)

    return removed


def _names_from_export_line(line: str, path: str) -> list[str]:
    """Extract exported name(s) from a single source line."""
    ext = Path(path).suffix

    if ext in {".ts", ".tsx", ".js", ".jsx", ".mjs"}:
        # export const/function/class/type/interface/enum Name
        m = _TS_EXPORT_RE.match(line)
        if m:
            return [m.group(1)]
        # export { Foo, Bar as Baz }
        m = _TS_EXPORT_BRACE_RE.match(line)
        if m:
            names = []
            for token in m.group(1).split(","):
                token = token.strip()
                # "Bar as Baz" → external name is Baz
                if " as " in token:
                    token = token.split(" as ")[-1].strip()
                if token and re.match(r'^\w+$', token):
                    names.append(token)
            return names

    elif ext == ".py":
        # def foo / class Foo
        m = _PY_DEF_RE.match(line)
        if m and not m.group(1).startswith("_"):
            return [m.group(1)]

    return []


def find_broken_imports(
    removed: dict[str, list[str]],
    root: str,
    exts: set[str],
    head: str,
) -> list[tuple[str, str, str]]:
    """
    Returns list of (importer_file, import_name, removed_from_file) for each
    import that references a removed export name, confirmed still present in
    the post-merge tree.
    """
    if not removed:
        return []

    broken: list[tuple[str, str, str]] = []
    removed_names = set(removed.keys())

    # Build list of source files in the post-merge tree
    all_files_raw = git("ls-tree", "-r", "--name-only", head, cwd=root)
    all_files = [
        f for f in all_files_raw.splitlines()
        if Path(f).suffix in exts
    ]

    for path in all_files:
        content = file_content_at(head, path, root)
        if not content:
            continue
        ext = Path(path).suffix
        found = _extract_imported_names(content, ext)
        for name in found:
            if name in removed_names:
                # Avoid self-reference (same file that exported it)
                origin_files = removed[name]
                if path not in origin_files:
                    broken.append((path, name, origin_files[0]))

    return broken


def _extract_imported_names(content: str, ext: str) -> list[str]:
    names = []
    if ext in {".ts", ".tsx", ".js", ".jsx", ".mjs"}:
        for line in content.splitlines():
            for m in _TS_IMPORT_RE.finditer(line):
                for tok in m.group(1).split(","):
                    tok = tok.strip()
                    if " as " in tok:
                        tok = tok.split(" as ")[0].strip()
                    if tok and re.match(r'^\w+$', tok):
                        names.append(tok)
    elif ext == ".py":
        for line in content.splitlines():
            m = _PY_IMPORT_RE.match(line.strip())
            if m:
                for tok in m.group(1).split(","):
                    tok = tok.strip()
                    if " as " in tok:
                        tok = tok.split(" as ")[0].strip()
                    if tok and re.match(r'^\w+$', tok):
                        names.append(tok)
    return names


# ---------------------------------------------------------------------------
# Conflict marker detection
# ---------------------------------------------------------------------------

_MARKERS = ("<<<<<<< ", "=======", ">>>>>>> ")


@dataclass
class MarkerHit:
    file: str
    lineno: int
    content: str


def find_conflict_markers(
    changed_files: list[str],
    head: str,
    root: str,
) -> list[MarkerHit]:
    hits: list[MarkerHit] = []
    for path in changed_files:
        content = file_content_at(head, path, root)
        if not content:
            continue
        for lineno, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if any(stripped.startswith(m) for m in _MARKERS):
                hits.append(MarkerHit(file=path, lineno=lineno, content=stripped[:80]))
    return hits


# ---------------------------------------------------------------------------
# Task creation
# ---------------------------------------------------------------------------

def post_task(title: str, description: str, api_url: str) -> str | None:
    payload = json.dumps({
        "title": title,
        "description": description,
        "priority": 1,
        "phase_type": "fix",
        "source": "detect_merge_regressions",
        "tags": ["regression", "auto-detected"],
        "role": "Delta",
        "domain": "qa",
    }).encode()
    url = f"{api_url.rstrip('/')}/api/debug/task-board/add"
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read()).get("task_id")
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"  [warn] task creation failed: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("merge_commit", nargs="?",
                        help="SHA of merge commit (default: auto-detect)")
    parser.add_argument("--create-tasks", action="store_true")
    parser.add_argument("--api-url", default="http://localhost:5001")
    parser.add_argument("--json", dest="json_out", action="store_true")
    parser.add_argument("--root", default=None,
                        help="Repo root (default: git rev-parse --show-toplevel)")
    parser.add_argument("--ext", nargs="+",
                        default=[".ts", ".tsx", ".js", ".jsx", ".py"],
                        help="File extensions to scan")
    args = parser.parse_args()

    root = repo_root(args.root)
    exts = set(args.ext)
    commit = find_merge_commit(args.merge_commit, root)
    p1, p2 = merge_parents(commit, root)

    if not args.json_out:
        print(f"\nMerge: {commit[:12]}  ({p1[:8]} ← {p2[:8]})")

    diff = diff_text(p1, commit, root)
    changed = files_changed(p1, commit, root)

    # --- Check 1: removed exports → broken imports ---
    removed = extract_removed_exports(diff, exts)
    broken  = find_broken_imports(removed, root, exts, commit)

    # --- Check 2: conflict markers ---
    markers = find_conflict_markers(changed, commit, root)

    found_any = bool(broken or markers)

    if args.json_out:
        print(json.dumps({
            "merge_commit": commit,
            "broken_imports": [
                {"importer": b[0], "name": b[1], "removed_from": b[2]}
                for b in broken
            ],
            "conflict_markers": [
                {"file": h.file, "line": h.lineno, "content": h.content}
                for h in markers
            ],
            "regression_found": found_any,
        }, indent=2))
        return 1 if found_any else 0

    if not found_any:
        print("PASS — no regressions detected.")
        return 0

    print("=" * 60)
    print("REGRESSION DETECTED")
    print("=" * 60)

    if broken:
        print(f"\n[BROKEN IMPORTS] {len(broken)} broken reference(s):")
        for importer, name, origin in broken:
            print(f"  {importer} imports '{name}' — no longer exported from {origin}")
            if args.create_tasks:
                title = f"DELTA-BUG: '{name}' removed from {origin} but still imported in {importer}"
                desc  = (f"Merge {commit[:12]} removed the export of `{name}` from `{origin}`,\n"
                         f"but `{importer}` still imports it. This will cause a build failure.\n\n"
                         f"Fix: re-export `{name}` from `{origin}` or update the import in `{importer}`.")
                tid = post_task(title, desc, args.api_url)
                print(f"  → task: {tid or 'creation failed'}")

    if markers:
        print(f"\n[CONFLICT MARKERS] {len(markers)} unresolved marker(s):")
        for h in markers:
            print(f"  {h.file}:{h.lineno}  {h.content!r}")
            if args.create_tasks:
                title = f"DELTA-BUG: conflict marker in {h.file}:{h.lineno} after merge {commit[:8]}"
                desc  = (f"Merge commit {commit[:12]} shipped an unresolved conflict marker "
                         f"in `{h.file}` at line {h.lineno}:\n\n  {h.content}")
                tid = post_task(title, desc, args.api_url)
                print(f"  → task: {tid or 'creation failed'}")

    print(f"\nFAIL — {len(broken)} broken import(s), {len(markers)} conflict marker(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
