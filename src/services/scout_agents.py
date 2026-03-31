"""
LiteRT Scout agents — fast local context gatherers for pipeline.

MARKER_196.SCOUT-1: Scout agents for parallel codebase reconnaissance.

Scouts run BEFORE the Architect phase to gather context:
- Each scout gets a focused sub-query
- Runs grep + semantic search + file reads in parallel
- Returns structured facts for Architect planning

Usage:
    from src.services.scout_agents import run_scout_mission
    result = await run_scout_mission(
        query="How does authentication work?",
        num_scouts=3,
    )
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("vetka.scout_agents")

# MARKER_196.SCOUT-1: Scout sub-query templates
SCOUT_TEMPLATES = [
    "Find all files related to: {topic} — focus on function/class definitions",
    "Search for patterns: {topic} — look for imports, decorators, and key logic",
    "Map the architecture around: {topic} — trace call chains and dependencies",
    "Find configuration and setup for: {topic} — look for config files, env vars, init code",
    "Search for error handling around: {topic} — find try/except, validation, guards",
    "Find tests and examples for: {topic} — look for test files, usage patterns",
    "Search for TODO/FIXME/HACK comments related to: {topic}",
    "Find documentation and comments about: {topic}",
    "Search for hardcoded values and magic numbers related to: {topic}",
]


@dataclass
class ScoutFact:
    """A single fact discovered by a scout."""

    description: str
    file_path: str = ""
    line_number: int = 0
    code_snippet: str = ""
    confidence: float = 1.0
    source: str = "grep"  # grep, semantic, read


@dataclass
class ScoutResult:
    """Result from a single scout mission."""

    scout_id: int
    query: str
    facts: List[ScoutFact] = field(default_factory=list)
    files_read: List[str] = field(default_factory=list)
    relevant_code: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class MissionResult:
    """Aggregated result from all scouts."""

    query: str
    all_facts: List[ScoutFact] = field(default_factory=list)
    all_files: List[str] = field(default_factory=list)
    relevant_code: Dict[str, str] = field(default_factory=dict)
    scout_results: List[ScoutResult] = field(default_factory=list)
    total_facts: int = 0
    total_files: int = 0
    duration_ms: float = 0.0


def _grep_files(
    pattern: str, base_path: str = None, max_results: int = 50
) -> List[Dict[str, Any]]:
    """Run ripgrep search and return structured results."""
    import subprocess

    try:
        cmd = ["rg", "--json", "--max-count", str(max_results), "--line-number"]
        if base_path:
            cmd.append(base_path)
        else:
            cmd.append(".")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )

        facts = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                import json

                entry = json.loads(line)
                if entry.get("type") == "match":
                    data = entry["data"]
                    facts.append(
                        {
                            "file": data["path"]["text"],
                            "line": data["line_number"],
                            "text": data["lines"]["text"].strip(),
                        }
                    )
            except (json.JSONDecodeError, KeyError):
                continue

        return facts
    except FileNotFoundError:
        logger.debug("ripgrep not found, falling back to Python grep")
        return _python_grep(pattern, base_path, max_results)
    except subprocess.TimeoutExpired:
        logger.warning(f"ripgrep timeout for pattern: {pattern}")
        return []
    except Exception as e:
        logger.debug(f"ripgrep failed: {e}")
        return []


def _python_grep(
    pattern: str, base_path: str = None, max_results: int = 50
) -> List[Dict[str, Any]]:
    """Fallback Python-based grep for when ripgrep is unavailable."""
    facts = []
    search_path = Path(base_path) if base_path else Path(".")
    count = 0

    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error:
        regex = re.compile(re.escape(pattern), re.IGNORECASE)

    for ext in (
        "*.py",
        "*.ts",
        "*.tsx",
        "*.js",
        "*.jsx",
        "*.json",
        "*.yaml",
        "*.yml",
        "*.md",
        "*.rs",
        "*.go",
    ):
        for fpath in search_path.rglob(ext):
            if count >= max_results:
                break
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if regex.search(line):
                            facts.append(
                                {
                                    "file": str(fpath),
                                    "line": i,
                                    "text": line.strip()[:200],
                                }
                            )
                            count += 1
                            if count >= max_results:
                                break
            except (PermissionError, OSError):
                continue

    return facts


def _read_file_snippet(file_path: str, context_lines: int = 5) -> Optional[str]:
    """Read a file and return a snippet (first 100 lines)."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        snippet = "".join(lines[:100])
        if len(lines) > 100:
            snippet += f"\n... ({len(lines) - 100} more lines)"
        return snippet
    except Exception:
        return None


def _generate_scout_queries(topic: str, num_scouts: int = 3) -> List[str]:
    """Generate diverse scout queries from a topic."""
    queries = []
    for i in range(min(num_scouts, len(SCOUT_TEMPLATES))):
        queries.append(SCOUT_TEMPLATES[i].format(topic=topic))
    return queries


async def _run_single_scout(
    scout_id: int,
    query: str,
    topic: str,
    paths: Optional[List[str]] = None,
) -> ScoutResult:
    """Run a single scout: grep + read + analyze."""
    import time

    start = time.monotonic()
    facts = []
    files_read = []
    relevant_code = {}

    try:
        # Search for the topic in codebase
        search_terms = [topic] + re.findall(r"\w{4,}", topic)
        seen_files = set()

        for term in search_terms[:3]:
            results = _grep_files(term, max_results=20)
            for r in results:
                file_path = r.get("file", "")
                if file_path and file_path not in seen_files:
                    seen_files.add(file_path)
                    facts.append(
                        ScoutFact(
                            description=f"Found '{term}' in {file_path}:{r.get('line', '?')}",
                            file_path=file_path,
                            line_number=r.get("line", 0),
                            code_snippet=r.get("text", "")[:200],
                            source="grep",
                        )
                    )

        # Read top files for context
        for file_path in list(seen_files)[:5]:
            snippet = _read_file_snippet(file_path)
            if snippet:
                files_read.append(file_path)
                relevant_code[file_path] = snippet[:2000]

        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            f"[Scout-{scout_id}] Found {len(facts)} facts, "
            f"read {len(files_read)} files ({duration_ms:.0f}ms)"
        )

        return ScoutResult(
            scout_id=scout_id,
            query=query,
            facts=facts,
            files_read=files_read,
            relevant_code=relevant_code,
            duration_ms=duration_ms,
        )

    except Exception as e:
        logger.error(f"[Scout-{scout_id}] Failed: {e}")
        return ScoutResult(
            scout_id=scout_id,
            query=query,
            error=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )


async def run_scout_mission(
    query: str,
    paths: Optional[List[str]] = None,
    num_scouts: int = 3,
    topic: Optional[str] = None,
) -> MissionResult:
    """
    Run N scouts in parallel to gather codebase context.

    Args:
        query: High-level question or topic to investigate
        paths: Optional list of paths to limit search
        num_scouts: Number of parallel scouts (1-9)
        topic: Override topic for search (defaults to query)

    Returns:
        MissionResult with aggregated facts from all scouts
    """
    import time

    start = time.monotonic()

    search_topic = topic or query
    scout_queries = _generate_scout_queries(search_topic, num_scouts)

    logger.info(
        f"[ScoutMission] Launching {len(scout_queries)} scouts for: {search_topic[:80]}"
    )

    # Run scouts in parallel
    tasks = [
        _run_single_scout(i, q, search_topic, paths)
        for i, q in enumerate(scout_queries)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Aggregate results
    all_facts = []
    all_files = []
    all_code = {}
    scout_results = []

    for r in results:
        if isinstance(r, Exception):
            logger.error(f"Scout exception: {r}")
            continue
        if not isinstance(r, ScoutResult):
            continue

        scout_results.append(r)
        all_facts.extend(r.facts)
        for f in r.files_read:
            if f not in all_files:
                all_files.append(f)
        all_code.update(r.relevant_code)

    # Deduplicate facts by file+line
    seen = set()
    unique_facts = []
    for fact in all_facts:
        key = (fact.file_path, fact.line_number)
        if key not in seen:
            seen.add(key)
            unique_facts.append(fact)

    duration_ms = (time.monotonic() - start) * 1000
    logger.info(
        f"[ScoutMission] Complete: {len(unique_facts)} facts, "
        f"{len(all_files)} files ({duration_ms:.0f}ms)"
    )

    return MissionResult(
        query=query,
        all_facts=unique_facts,
        all_files=all_files,
        relevant_code=all_code,
        scout_results=scout_results,
        total_facts=len(unique_facts),
        total_files=len(all_files),
        duration_ms=duration_ms,
    )


def scout_to_context_dict(result: MissionResult) -> Dict[str, Any]:
    """Convert MissionResult to context dict for pipeline injection."""
    return {
        "scout_summary": (
            f"Found {result.total_facts} facts across {result.total_files} files "
            f"in {result.duration_ms:.0f}ms"
        ),
        "relevant_files": result.all_files[:20],
        "facts": [
            {
                "description": f.description,
                "file": f.file_path,
                "line": f.line_number,
                "snippet": f.code_snippet,
            }
            for f in result.all_facts[:30]
        ],
        "file_count": result.total_files,
        "fact_count": result.total_facts,
    }
