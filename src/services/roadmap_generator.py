"""
MARKER_153.4A: Roadmap Generator — analyzes project and generates DAG.

Scans project structure, reads key config files, calls Architect LLM
to generate a hierarchical roadmap. The roadmap is a DAG of modules,
features, and phases that the Matryoshka navigation uses.

@phase 153
@wave 4
@status active
"""

import json
import os
import subprocess
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime, timezone

from src.services.project_config import ProjectConfig, DATA_DIR

# Roadmap persistence
ROADMAP_PATH = os.path.join(DATA_DIR, "roadmap_dag.json")


@dataclass
class RoadmapNode:
    """A node in the project roadmap DAG."""
    id: str
    label: str
    layer: str = "core"         # core | feature | enhancement | test | docs
    status: str = "pending"     # pending | active | completed
    description: str = ""
    file_patterns: list = field(default_factory=list)  # glob patterns for related files


@dataclass
class RoadmapEdge:
    """Dependency edge between roadmap nodes."""
    source: str
    target: str


@dataclass
class RoadmapDAG:
    """Full roadmap as a DAG structure."""
    project_id: str = ""
    generated_at: str = ""
    generator: str = "static"   # "static" | "llm"
    nodes: list = field(default_factory=list)
    edges: list = field(default_factory=list)

    def save(self, path: Optional[str] = None) -> bool:
        """Save roadmap DAG to disk."""
        path = path or ROADMAP_PATH
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                json.dump(asdict(self), f, indent=2)
            return True
        except OSError:
            return False

    @classmethod
    def load(cls, path: Optional[str] = None) -> Optional['RoadmapDAG']:
        """Load roadmap from disk. Returns None if no roadmap."""
        path = path or ROADMAP_PATH
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            dag = cls()
            dag.project_id = data.get("project_id", "")
            dag.generated_at = data.get("generated_at", "")
            dag.generator = data.get("generator", "static")
            dag.nodes = data.get("nodes", [])
            dag.edges = data.get("edges", [])
            return dag
        except (json.JSONDecodeError, TypeError):
            return None

    def to_frontend_format(self) -> dict:
        """Convert to format expected by DAGView component."""
        return {
            "nodes": [
                {
                    "id": n["id"] if isinstance(n, dict) else n.id,
                    "type": "task",
                    "label": n["label"] if isinstance(n, dict) else n.label,
                    "position": {"x": i * 200 + 100, "y": 200},
                    "data": {
                        "layer": n.get("layer", "core") if isinstance(n, dict) else n.layer,
                        "status": n.get("status", "pending") if isinstance(n, dict) else n.status,
                        "description": n.get("description", "") if isinstance(n, dict) else n.description,
                    },
                }
                for i, n in enumerate(self.nodes)
            ],
            "edges": [
                {
                    "id": f"e-{e['source']}-{e['target']}" if isinstance(e, dict) else f"e-{e.source}-{e.target}",
                    "source": e["source"] if isinstance(e, dict) else e.source,
                    "target": e["target"] if isinstance(e, dict) else e.target,
                }
                for e in self.edges
            ],
        }


class RoadmapGenerator:
    """
    Generates project roadmap DAG.

    Phase 153 Wave 4: Static analysis first (scan project structure).
    LLM analysis can be added via analyze_with_llm() when the Architect
    prompt is ready (uses pipeline_prompts.json "architect_roadmap").
    """

    @staticmethod
    def scan_project_structure(sandbox_path: str) -> dict:
        """
        Scan project directory and extract structure info.
        Returns: {tree, key_files, languages, frameworks}
        """
        if not os.path.isdir(sandbox_path):
            return {"tree": "", "key_files": {}, "languages": set(), "frameworks": []}

        # Get tree structure (limited depth)
        tree_lines = []
        try:
            result = subprocess.run(
                ["find", sandbox_path, "-maxdepth", "3", "-type", "f"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().splitlines()[:200]:
                    rel = os.path.relpath(line, sandbox_path)
                    tree_lines.append(rel)
        except (subprocess.TimeoutExpired, OSError):
            pass

        # Detect key config files
        key_file_names = [
            "package.json", "Cargo.toml", "setup.py", "pyproject.toml",
            "requirements.txt", "go.mod", "pom.xml", "build.gradle",
            "Makefile", "Dockerfile", "docker-compose.yml",
            "tsconfig.json", ".eslintrc.json", "vite.config.ts",
        ]
        key_files = {}
        for name in key_file_names:
            path = os.path.join(sandbox_path, name)
            if os.path.exists(path):
                try:
                    with open(path, 'r', errors='ignore') as f:
                        content = f.read(2000)  # First 2KB
                    key_files[name] = content
                except OSError:
                    pass

        # Detect languages from file extensions
        ext_map = {
            ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript",
            ".js": "JavaScript", ".jsx": "JavaScript", ".rs": "Rust",
            ".go": "Go", ".java": "Java", ".rb": "Ruby", ".php": "PHP",
            ".swift": "Swift", ".kt": "Kotlin", ".cpp": "C++", ".c": "C",
        }
        languages = set()
        for f in tree_lines:
            ext = os.path.splitext(f)[1].lower()
            if ext in ext_map:
                languages.add(ext_map[ext])

        # Detect frameworks from key files
        frameworks = []
        if "package.json" in key_files:
            pkg = key_files["package.json"]
            for fw in ["react", "vue", "angular", "next", "express", "fastify", "three"]:
                if f'"{fw}"' in pkg.lower():
                    frameworks.append(fw)
        if "requirements.txt" in key_files or "pyproject.toml" in key_files:
            content = key_files.get("requirements.txt", "") + key_files.get("pyproject.toml", "")
            for fw in ["fastapi", "django", "flask", "pytorch", "tensorflow"]:
                if fw in content.lower():
                    frameworks.append(fw)

        return {
            "tree": "\n".join(tree_lines[:100]),
            "key_files": key_files,
            "languages": languages,
            "frameworks": frameworks,
        }

    @staticmethod
    def generate_static_roadmap(scan_result: dict, project_id: str) -> RoadmapDAG:
        """
        Generate a roadmap from static analysis (no LLM needed).
        Uses heuristics based on project structure and detected stack.
        """
        nodes = []
        edges = []
        languages = scan_result.get("languages", set())
        frameworks = scan_result.get("frameworks", [])
        tree = scan_result.get("tree", "")

        # Always start with core node
        nodes.append(asdict(RoadmapNode(
            id="core",
            label="Core / Backend",
            layer="core",
            status="active",
            description="Core backend logic and API",
        )))

        # Detect modules from directory structure
        top_dirs = set()
        for line in tree.split("\n"):
            if "/" in line:
                top_dir = line.split("/")[0]
                if top_dir and not top_dir.startswith("."):
                    top_dirs.add(top_dir)

        # Map common directories to roadmap nodes
        dir_mapping = {
            "src": ("source", "Source Code", "core"),
            "lib": ("library", "Libraries", "core"),
            "api": ("api", "API Layer", "core"),
            "client": ("frontend", "Frontend", "feature"),
            "frontend": ("frontend", "Frontend", "feature"),
            "web": ("frontend", "Frontend", "feature"),
            "components": ("ui", "UI Components", "feature"),
            "tests": ("tests", "Test Suite", "test"),
            "test": ("tests", "Test Suite", "test"),
            "docs": ("docs", "Documentation", "docs"),
            "scripts": ("scripts", "Build Scripts", "enhancement"),
            "config": ("config", "Configuration", "core"),
            "data": ("data", "Data Layer", "core"),
            "models": ("models", "Data Models", "core"),
            "services": ("services", "Services", "core"),
            "hooks": ("hooks", "React Hooks", "feature"),
            "store": ("store", "State Management", "feature"),
            "utils": ("utils", "Utilities", "enhancement"),
        }

        seen_ids = {"core"}
        for d in sorted(top_dirs):
            d_lower = d.lower()
            if d_lower in dir_mapping:
                node_id, label, layer = dir_mapping[d_lower]
                if node_id not in seen_ids:
                    nodes.append(asdict(RoadmapNode(
                        id=node_id,
                        label=label,
                        layer=layer,
                        description=f"Module: {d}/",
                        file_patterns=[f"{d}/**"],
                    )))
                    seen_ids.add(node_id)
                    # Core nodes depend on core, feature nodes depend on core
                    if layer in ("feature", "enhancement"):
                        edges.append(asdict(RoadmapEdge(source="core", target=node_id)))
                    elif layer == "test" and "source" in seen_ids:
                        edges.append(asdict(RoadmapEdge(source="source", target=node_id)))
                    elif layer == "docs":
                        pass  # Docs are independent

        # Add framework-specific nodes
        if "react" in frameworks or "TypeScript" in languages:
            if "ui" not in seen_ids:
                nodes.append(asdict(RoadmapNode(
                    id="ui", label="UI Components", layer="feature",
                    description="React components and views",
                )))
                seen_ids.add("ui")
                edges.append(asdict(RoadmapEdge(source="core", target="ui")))

        # If we only have core, add a generic "features" node
        if len(nodes) == 1:
            nodes.append(asdict(RoadmapNode(
                id="features",
                label="Features",
                layer="feature",
                description="Project features and functionality",
            )))
            edges.append(asdict(RoadmapEdge(source="core", target="features")))

        dag = RoadmapDAG(
            project_id=project_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            generator="static",
            nodes=nodes,
            edges=edges,
        )
        return dag

    @classmethod
    async def analyze_project(cls, config: ProjectConfig) -> RoadmapDAG:
        """
        Full project analysis:
        1. Scan directory structure
        2. Generate roadmap (static for now, LLM in future)
        3. Save to disk
        """
        scan = cls.scan_project_structure(config.sandbox_path)
        dag = cls.generate_static_roadmap(scan, config.project_id)
        dag.save()
        return dag
