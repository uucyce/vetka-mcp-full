"""
MARKER_153.4B: Architect Prefetch Pipeline.

One button [Execute] triggers this CHAIN of preparation BEFORE the main pipeline:
  1. prefetch_files:   Qdrant semantic search by task description → top 5 files
  2. prefetch_markers: ripgrep MARKER_* in found files
  3. prefetch_docs:    Context7 library docs (if framework in stack)
  4. prefetch_history: pipeline_history.json → how similar tasks were solved
  5. select_workflow:  pick template from library by task type
  6. select_team:      pick preset by complexity + history

The entire prefetch context is injected into Scout/Architect/Coder
so they don't waste FC turns on searching.

@phase 153
@wave 4
@status active
"""

import json
import os
import glob as glob_module
import subprocess
from dataclasses import dataclass, field, asdict
from typing import Optional

from src.services.project_config import ProjectConfig, DATA_DIR


# Workflow templates directory
WORKFLOWS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "templates", "workflows"
)

# Pipeline history
HISTORY_PATH = os.path.join(DATA_DIR, "pipeline_history.json")


@dataclass
class PrefetchContext:
    """Result of prefetch pipeline — injected into agent context."""

    # Files found by semantic search
    relevant_files: list = field(default_factory=list)      # [{path, relevance}]
    # Markers found in those files
    markers: list = field(default_factory=list)              # [{file, line, marker_id}]
    # Library docs snippets
    docs_snippets: list = field(default_factory=list)        # [{library, snippet}]
    # Similar past tasks
    similar_tasks: list = field(default_factory=list)        # [{task_id, description, outcome}]
    # Selected workflow template
    workflow_id: str = ""                                    # e.g., "quick_fix"
    workflow_name: str = ""
    # Selected team preset
    preset: str = "dragon_silver"
    # Summary for injection
    summary: str = ""


class WorkflowTemplateLibrary:
    """
    MARKER_153.4C: Workflow Template Library — "Дебюты Гроссмейстера".

    Loads and manages workflow templates from data/templates/workflows/.
    Architect selects template based on task characteristics.
    """

    _templates: dict = {}
    _loaded: bool = False

    @classmethod
    def load_all(cls, templates_dir: Optional[str] = None) -> dict:
        """Load all workflow templates from disk."""
        templates_dir = templates_dir or WORKFLOWS_DIR
        cls._templates = {}
        if not os.path.isdir(templates_dir):
            return cls._templates

        for filepath in glob_module.glob(os.path.join(templates_dir, "*.json")):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                template_key = os.path.splitext(os.path.basename(filepath))[0]
                cls._templates[template_key] = data
            except (json.JSONDecodeError, OSError):
                continue

        cls._loaded = True
        return cls._templates

    @classmethod
    def get_template(cls, key: str) -> Optional[dict]:
        """Get a specific workflow template by key."""
        if not cls._loaded:
            cls.load_all()
        return cls._templates.get(key)

    @classmethod
    def list_templates(cls) -> list:
        """List all available templates with metadata."""
        if not cls._loaded:
            cls.load_all()
        result = []
        for key, tpl in cls._templates.items():
            result.append({
                "key": key,
                "id": tpl.get("id", key),
                "name": tpl.get("name", key),
                "description": tpl.get("description", ""),
                "node_count": len(tpl.get("nodes", [])),
                "task_types": tpl.get("metadata", {}).get("task_types", []),
                "complexity_range": tpl.get("metadata", {}).get("complexity_range", [1, 10]),
            })
        return result

    @classmethod
    def select_workflow(cls, task_type: str = "", complexity: int = 5) -> str:
        """
        MARKER_153.4D: Workflow Selector — Grandmaster opening selection.

        Logic:
        - fix/patch + complexity < 3 → quick_fix
        - build/integrate + unknown libs → research_first
        - refactor/restructure → refactor
        - test/coverage → test_only
        - docs/readme → docs_update
        - default or complexity > 5 → bmad_default
        """
        if not cls._loaded:
            cls.load_all()

        task_lower = task_type.lower() if task_type else ""

        # Match by task type
        for key, tpl in cls._templates.items():
            meta = tpl.get("metadata", {})
            tpl_types = [t.lower() for t in meta.get("task_types", [])]
            comp_range = meta.get("complexity_range", [1, 10])

            if task_lower in tpl_types:
                if comp_range[0] <= complexity <= comp_range[1]:
                    return key

        # Fallback heuristics
        if task_lower in ("fix", "patch", "hotfix", "bug") and complexity <= 3:
            return "quick_fix"
        if task_lower in ("test", "coverage", "e2e"):
            return "test_only"
        if task_lower in ("docs", "readme", "comment"):
            return "docs_update"
        if task_lower in ("refactor", "restructure", "migrate"):
            return "refactor"
        if task_lower in ("build", "integrate", "learn"):
            return "research_first"

        # Default: full BMAD
        return "bmad_default"


class ArchitectPrefetch:
    """
    MARKER_153.4E: Prefetch Pipeline — prepares context before main pipeline.

    Called by [Execute] button chain:
    1. Prefetch files + markers + docs + history
    2. Select workflow template
    3. Select team preset
    4. Return PrefetchContext for pipeline injection
    """

    @staticmethod
    def prefetch_files_static(sandbox_path: str, task_description: str) -> list:
        """
        Static file prefetch using keyword extraction + grep.
        (Qdrant semantic search is available via REST API but requires async.)
        """
        if not os.path.isdir(sandbox_path):
            return []

        # Extract keywords from task description
        words = task_description.lower().split()
        keywords = [w for w in words if len(w) > 3 and w.isalpha()][:5]

        found_files = set()
        for kw in keywords:
            try:
                result = subprocess.run(
                    ["grep", "-rl", "--include=*.py", "--include=*.ts",
                     "--include=*.tsx", "--include=*.js", kw, sandbox_path],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().splitlines()[:3]:
                        rel = os.path.relpath(line, sandbox_path)
                        found_files.add(rel)
            except (subprocess.TimeoutExpired, OSError):
                pass

        return [{"path": f, "relevance": "keyword_match"} for f in sorted(found_files)][:5]

    @staticmethod
    def prefetch_markers(sandbox_path: str, files: list) -> list:
        """Find MARKER_* tags in the found files."""
        markers = []
        for f_info in files:
            fpath = os.path.join(sandbox_path, f_info["path"]) if isinstance(f_info, dict) else os.path.join(sandbox_path, f_info)
            if not os.path.exists(fpath):
                continue
            try:
                result = subprocess.run(
                    ["grep", "-n", "MARKER_", fpath],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().splitlines()[:10]:
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            markers.append({
                                "file": f_info["path"] if isinstance(f_info, dict) else f_info,
                                "line": int(parts[0]) if parts[0].isdigit() else 0,
                                "content": parts[1].strip()[:100],
                            })
            except (subprocess.TimeoutExpired, OSError):
                pass
        return markers[:20]

    @staticmethod
    def prefetch_history(task_description: str) -> list:
        """Find similar past tasks from pipeline_history.json."""
        if not os.path.exists(HISTORY_PATH):
            return []
        try:
            with open(HISTORY_PATH, 'r') as f:
                history = json.load(f)
            if not isinstance(history, list):
                return []

            # Simple keyword matching (could use embeddings later)
            words = set(task_description.lower().split())
            scored = []
            for entry in history[-50:]:  # Last 50 entries
                desc = entry.get("task_description", "").lower()
                overlap = len(words.intersection(desc.split()))
                if overlap > 1:
                    scored.append({
                        "task_id": entry.get("task_id", ""),
                        "description": entry.get("task_description", "")[:100],
                        "outcome": entry.get("status", "unknown"),
                        "preset": entry.get("preset", ""),
                        "score": overlap,
                    })
            scored.sort(key=lambda x: x["score"], reverse=True)
            return scored[:3]
        except (json.JSONDecodeError, OSError):
            return []

    @classmethod
    def prepare(
        cls,
        task_description: str,
        task_type: str = "",
        complexity: int = 5,
        config: Optional[ProjectConfig] = None,
    ) -> PrefetchContext:
        """
        Full prefetch pipeline (sync version).
        Returns PrefetchContext ready for injection.
        """
        ctx = PrefetchContext()

        sandbox_path = config.sandbox_path if config else ""

        # 1. Prefetch files
        if sandbox_path and os.path.isdir(sandbox_path):
            ctx.relevant_files = cls.prefetch_files_static(sandbox_path, task_description)

        # 2. Prefetch markers
        if ctx.relevant_files and sandbox_path:
            ctx.markers = cls.prefetch_markers(sandbox_path, ctx.relevant_files)

        # 3. Docs (placeholder — needs async Context7 call)
        # ctx.docs_snippets = await cls.prefetch_docs(frameworks)

        # 4. History
        ctx.similar_tasks = cls.prefetch_history(task_description)

        # 5. Select workflow
        workflow_key = WorkflowTemplateLibrary.select_workflow(task_type, complexity)
        ctx.workflow_id = workflow_key
        tpl = WorkflowTemplateLibrary.get_template(workflow_key)
        ctx.workflow_name = tpl.get("name", workflow_key) if tpl else workflow_key

        # 6. Select team (simple for now — complexity-based)
        if complexity <= 3:
            ctx.preset = "dragon_bronze"
        elif complexity <= 6:
            ctx.preset = "dragon_silver"
        else:
            ctx.preset = "dragon_gold"

        # Build summary for injection
        file_list = ", ".join(f["path"] for f in ctx.relevant_files[:3]) if ctx.relevant_files else "none"
        ctx.summary = (
            f"Prefetch: {len(ctx.relevant_files)} files found ({file_list}), "
            f"{len(ctx.markers)} markers, "
            f"{len(ctx.similar_tasks)} similar past tasks. "
            f"Workflow: {ctx.workflow_name}. Team: {ctx.preset}."
        )

        return ctx
