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
import logging
import os
import subprocess
from dataclasses import dataclass, field, asdict
from typing import Optional, List
from datetime import datetime, timezone

from src.services.project_config import ProjectConfig, DATA_DIR

logger = logging.getLogger(__name__)

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


# MARKER_176.5: JEPA semantic clustering — cosine similarity for normalized vectors
def _cosine_sim(a: List[float], b: List[float]) -> float:
    """Dot product of two L2-normalized vectors = cosine similarity."""
    return sum(x * y for x, y in zip(a, b))


def _jepa_refine_modules(
    nodes: List[dict],
    edges: List[dict],
    similarity_threshold: float = 0.70,
) -> tuple:
    """
    MARKER_176.5: Refine roadmap nodes using JEPA semantic embeddings.

    Groups semantically similar modules (e.g. "auth" across api + middleware + tests)
    into single clustered nodes. Uses union-find for transitive clustering.

    Args:
        nodes: list of RoadmapNode dicts from generate_static_roadmap
        edges: list of RoadmapEdge dicts
        similarity_threshold: minimum cosine similarity to merge (0.0-1.0)

    Returns:
        (refined_nodes, refined_edges) — with clustered nodes tagged jepa_clustered=True
    """
    from src.services.mcc_jepa_adapter import embed_texts_for_overlay

    # Only cluster leaf nodes (non-root, non-branch nodes that have a parent)
    # Identify branch/root nodes by checking which nodes are sources of edges
    parent_ids = {e["source"] for e in edges}
    leaf_nodes = [n for n in nodes if n["id"] not in parent_ids]
    non_leaf_nodes = [n for n in nodes if n["id"] in parent_ids]

    if len(leaf_nodes) < 2:
        return nodes, edges

    # Build text representations for embedding: combine label + description + file_patterns
    texts = []
    for n in leaf_nodes:
        parts = [n.get("label", ""), n.get("description", "")]
        patterns = n.get("file_patterns", [])
        if patterns:
            parts.extend(patterns[:3])
        texts.append(" ".join(p for p in parts if p))

    # Get JEPA embeddings
    result = embed_texts_for_overlay(texts, target_dim=128)
    vectors = result.vectors

    if len(vectors) != len(leaf_nodes):
        logger.warning("MARKER_176.5: vector count mismatch, skipping clustering")
        return nodes, edges

    # Union-find for transitive clustering
    parent_map = list(range(len(leaf_nodes)))

    def find(i: int) -> int:
        while parent_map[i] != i:
            parent_map[i] = parent_map[parent_map[i]]
            i = parent_map[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent_map[ri] = rj

    # Cluster nodes that share the same parent edge AND are semantically similar
    # (only merge siblings — nodes under the same branch)
    child_to_parent = {}
    for e in edges:
        child_to_parent[e["target"]] = e["source"]

    for i in range(len(leaf_nodes)):
        for j in range(i + 1, len(leaf_nodes)):
            # Only merge siblings (same parent in the DAG)
            pid_i = child_to_parent.get(leaf_nodes[i]["id"])
            pid_j = child_to_parent.get(leaf_nodes[j]["id"])
            if pid_i != pid_j:
                continue
            sim = _cosine_sim(vectors[i], vectors[j])
            if sim >= similarity_threshold:
                union(i, j)

    # Group by cluster root
    clusters: dict[int, list[int]] = {}
    for i in range(len(leaf_nodes)):
        root = find(i)
        clusters.setdefault(root, []).append(i)

    # Build refined node list
    refined_nodes = list(non_leaf_nodes)  # keep branch/root nodes as-is
    old_id_to_new_id: dict[str, str] = {}

    for root_idx, member_indices in clusters.items():
        if len(member_indices) == 1:
            # Single node — keep as-is
            refined_nodes.append(leaf_nodes[member_indices[0]])
            continue

        # Merge: pick the node with the most files as representative
        members = [leaf_nodes[i] for i in member_indices]
        # Sort by file count hint in label (e.g., "API Layer (12)" -> 12)
        def _extract_count(n: dict) -> int:
            label = n.get("label", "")
            if "(" in label and ")" in label:
                try:
                    return int(label.rsplit("(", 1)[1].rstrip(")").strip())
                except (ValueError, IndexError):
                    pass
            return 0

        members.sort(key=_extract_count, reverse=True)
        representative = dict(members[0])  # copy

        # Merge metadata from all members
        all_labels = [m.get("label", "").split(" (")[0] for m in members]
        all_patterns = []
        total_files = sum(_extract_count(m) for m in members)
        for m in members:
            all_patterns.extend(m.get("file_patterns", []))

        representative["label"] = f"{' + '.join(all_labels)} ({total_files})"
        representative["file_patterns"] = all_patterns
        representative["jepa_clustered"] = True  # MARKER_176.5
        representative["description"] = (
            f"Semantic cluster of {len(members)} modules: "
            + ", ".join(all_labels)
        )

        refined_nodes.append(representative)

        # Map old IDs to the representative's ID for edge rewiring
        rep_id = representative["id"]
        for m in members:
            if m["id"] != rep_id:
                old_id_to_new_id[m["id"]] = rep_id

    # Rewire edges: replace merged node IDs, remove duplicates
    refined_edges = []
    seen_edges: set[tuple[str, str]] = set()
    for e in edges:
        src = old_id_to_new_id.get(e["source"], e["source"])
        tgt = old_id_to_new_id.get(e["target"], e["target"])
        if src == tgt:
            continue  # self-loop from merging
        key = (src, tgt)
        if key not in seen_edges:
            refined_edges.append({"source": src, "target": tgt})
            seen_edges.add(key)

    cluster_count = sum(1 for c in clusters.values() if len(c) > 1)
    merged_count = sum(len(c) for c in clusters.values() if len(c) > 1)
    logger.info(
        f"MARKER_176.5: JEPA clustering — {cluster_count} clusters formed, "
        f"{merged_count} nodes merged into {cluster_count}, "
        f"provider={result.provider_mode}"
    )

    return refined_nodes, refined_edges


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

        # MARKER_155.1A: Get tree structure — depth 4, skip junk, process ALL lines
        tree_lines = []
        skip_dirs = {
            "node_modules", ".git", "__pycache__", ".DS_Store", "dist",
            "build", ".next", ".vetka_backups", ".pytest_cache", "venv",
            ".venv", ".tox", ".mypy_cache", ".ruff_cache", "coverage",
        }
        try:
            cmd = ["find", sandbox_path, "-maxdepth", "5", "-type", "f"]
            for d in skip_dirs:
                cmd.extend(["-not", "-path", f"*/{d}/*"])
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().splitlines():
                    rel = os.path.relpath(line, sandbox_path)
                    if not rel.startswith("."):
                        tree_lines.append(rel)
        except (subprocess.TimeoutExpired, OSError):
            pass

        # Detect key config files (check root + common subdirs)
        key_file_names = [
            "package.json", "Cargo.toml", "setup.py", "pyproject.toml",
            "requirements.txt", "go.mod", "pom.xml", "build.gradle",
            "Makefile", "Dockerfile", "docker-compose.yml",
            "tsconfig.json", ".eslintrc.json", "vite.config.ts",
        ]
        # MARKER_155.1A: Also check client/ and client/src/ for frontend config
        check_prefixes = ["", "client/", "client/src/", "frontend/", "web/"]
        key_files = {}
        for prefix in check_prefixes:
            for name in key_file_names:
                lookup = f"{prefix}{name}"
                if lookup in key_files:
                    continue
                fpath = os.path.join(sandbox_path, lookup)
                if os.path.exists(fpath):
                    try:
                        with open(fpath, 'r', errors='ignore') as f:
                            content = f.read(2000)  # First 2KB
                        key_files[lookup] = content
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
        # MARKER_155.1A: Check all package.json files (root, client/, etc.)
        for key, content in key_files.items():
            if key.endswith("package.json"):
                for fw in ["react", "vue", "angular", "next", "express", "fastify", "three", "zustand", "vite"]:
                    if f'"{fw}"' in content.lower() and fw not in frameworks:
                        frameworks.append(fw)
        # Check Python configs
        py_content = ""
        for key in key_files:
            if key.endswith(("requirements.txt", "pyproject.toml", "setup.py")):
                py_content += key_files[key]
        if py_content:
            for fw in ["fastapi", "django", "flask", "pytorch", "tensorflow", "socketio"]:
                if fw in py_content.lower() and fw not in frameworks:
                    frameworks.append(fw)

        return {
            "tree": "\n".join(tree_lines),  # MARKER_155.1A: no cap — generator parses all
            "key_files": key_files,
            "languages": languages,
            "frameworks": frameworks,
        }

    # MARKER_155.1A: Heuristic layer detection for directory modules
    LAYER_RULES = {
        # Core backend
        'api': 'core', 'routes': 'core', 'services': 'core',
        'orchestration': 'core', 'models': 'core', 'tools': 'core',
        'layout': 'core', 'mcp': 'core', 'elisya': 'core',
        'handlers': 'core', 'middleware': 'core',
        # Frontend features
        'components': 'feature', 'hooks': 'feature', 'store': 'feature',
        'pages': 'feature', 'views': 'feature', 'panels': 'feature',
        'canvas': 'feature',
        # Enhancement / utility
        'utils': 'enhancement', 'config': 'enhancement', 'scripts': 'enhancement',
        'types': 'enhancement', 'styles': 'enhancement',
        # Tests
        'tests': 'test', 'test': 'test', '__tests__': 'test', 'spec': 'test',
        # Docs
        'docs': 'docs', 'documentation': 'docs',
    }

    # MARKER_155.1A: Human-readable labels for known directories
    DIR_LABELS = {
        'api': 'API Layer', 'routes': 'API Routes', 'services': 'Services',
        'orchestration': 'Orchestration', 'models': 'Data Models',
        'tools': 'Tools', 'layout': 'Layout Engine', 'mcp': 'MCP Server',
        'elisya': 'Elisya Engine', 'handlers': 'Handlers',
        'components': 'Components', 'hooks': 'Hooks', 'store': 'State Store',
        'pages': 'Pages', 'views': 'Views', 'panels': 'Panels',
        'canvas': 'Canvas / 3D', 'utils': 'Utilities', 'config': 'Config',
        'tests': 'Tests', 'test': 'Tests', 'docs': 'Documentation',
        'types': 'Types', 'styles': 'Styles', 'scripts': 'Scripts',
    }

    @staticmethod
    def generate_static_roadmap(scan_result: dict, project_id: str) -> RoadmapDAG:
        """
        MARKER_155.1A: Generate hierarchical architecture DAG from project scan.

        Strategy:
        1. Parse tree lines into a directory→file_count map
        2. Find "source roots" (dirs containing code subdirectories: src/, client/src/, lib/)
        3. Create module nodes from child directories of each source root
        4. Group into backend/frontend/tests top-level branches
        5. Create edges: project_root → branch → modules
        """
        nodes = []
        edges = []
        tree = scan_result.get("tree", "")
        tree_lines = [l.strip() for l in tree.split("\n") if l.strip()]

        # --- Step 1: Count files per directory (depth 1 and 2 segments) ---
        dir_files: dict[str, int] = {}  # "src/api" -> 12
        for line in tree_lines:
            parts = line.split("/")
            if len(parts) >= 2:
                # Top-level dir
                d1 = parts[0]
                if not d1.startswith("."):
                    dir_files[d1] = dir_files.get(d1, 0) + 1
                # Second-level dir (src/api, client/src, etc.)
                if len(parts) >= 3:
                    d2 = f"{parts[0]}/{parts[1]}"
                    dir_files[d2] = dir_files.get(d2, 0) + 1
                # Third-level (client/src/components, src/api/routes)
                if len(parts) >= 4:
                    d3 = f"{parts[0]}/{parts[1]}/{parts[2]}"
                    dir_files[d3] = dir_files.get(d3, 0) + 1

        # --- Step 2: Identify source roots and their children ---
        # Source root = a dir whose children are code modules (not just files)
        source_roots: list[tuple[str, str, str]] = []  # (path, branch_id, branch_label)

        # Check known source root patterns
        root_patterns = [
            ("src", "backend", "Backend"),
            ("lib", "backend", "Backend"),
            ("server", "backend", "Backend"),
            ("client/src", "frontend", "Frontend"),
            ("frontend/src", "frontend", "Frontend"),
            ("web/src", "frontend", "Frontend"),
            ("app", "app", "Application"),
        ]
        for root_path, branch_id, branch_label in root_patterns:
            # Check if this root has child directories with files
            children = [d for d in dir_files if d.startswith(f"{root_path}/") and d.count("/") == root_path.count("/") + 1]
            if children:
                source_roots.append((root_path, branch_id, branch_label))

        # Also check bare top-level dirs that ARE modules (tests/, docs/, config/)
        standalone_dirs = set()
        for d, count in dir_files.items():
            if "/" not in d and count >= 1:
                d_lower = d.lower()
                if d_lower in RoadmapGenerator.LAYER_RULES:
                    standalone_dirs.add(d)

        # --- Step 3: Build nodes from source root children ---
        seen_ids: set[str] = set()

        # Project root node
        root_id = "project"
        nodes.append(asdict(RoadmapNode(
            id=root_id,
            label=project_id or "Project",
            layer="core",
            status="active",
            description=f"{len(tree_lines)} files scanned",
        )))
        seen_ids.add(root_id)

        for root_path, branch_id, branch_label in source_roots:
            # Branch node (Backend / Frontend)
            if branch_id not in seen_ids:
                # Count total files under this root
                total_files = sum(c for p, c in dir_files.items() if p.startswith(f"{root_path}/"))
                nodes.append(asdict(RoadmapNode(
                    id=branch_id,
                    label=f"{branch_label} ({total_files})",
                    layer="core" if branch_id == "backend" else "feature",
                    status="active",
                    description=f"{root_path}/",
                    file_patterns=[f"{root_path}/**"],
                )))
                edges.append(asdict(RoadmapEdge(source=root_id, target=branch_id)))
                seen_ids.add(branch_id)

            # MARKER_155.1A: Child module nodes — show top modules, collapse small ones
            MIN_FILES = 3         # Skip modules with fewer files
            MAX_MODULES = 10      # Show at most this many per branch
            children = sorted([
                d for d in dir_files
                if d.startswith(f"{root_path}/") and d.count("/") == root_path.count("/") + 1
            ])

            # Sort by file count descending to prioritize important modules
            children_with_count = []
            for child_path in children:
                module_name = child_path.split("/")[-1]
                if module_name.startswith(".") or module_name.startswith("__"):
                    continue
                file_count = dir_files.get(child_path, 0)
                if file_count < 1:
                    continue
                children_with_count.append((child_path, module_name, file_count))

            children_with_count.sort(key=lambda x: -x[2])  # largest first

            added_count = 0
            collapsed_files = 0
            collapsed_names = []
            for child_path, module_name, file_count in children_with_count:
                module_id = f"{branch_id}_{module_name}"
                if module_id in seen_ids:
                    continue

                # Collapse small modules or those beyond the cap
                if file_count < MIN_FILES or added_count >= MAX_MODULES:
                    collapsed_files += file_count
                    collapsed_names.append(module_name)
                    continue

                module_lower = module_name.lower()
                layer = RoadmapGenerator.LAYER_RULES.get(module_lower, "core" if branch_id == "backend" else "feature")
                label = RoadmapGenerator.DIR_LABELS.get(module_lower, module_name.replace("_", " ").title())

                nodes.append(asdict(RoadmapNode(
                    id=module_id,
                    label=f"{label} ({file_count})",
                    layer=layer,
                    status="active",
                    description=f"{child_path}/",
                    file_patterns=[f"{child_path}/**"],
                )))
                edges.append(asdict(RoadmapEdge(source=branch_id, target=module_id)))
                seen_ids.add(module_id)
                added_count += 1

            # Add "Other" node for collapsed small modules
            if collapsed_files > 0:
                other_id = f"{branch_id}_other"
                if other_id not in seen_ids:
                    nodes.append(asdict(RoadmapNode(
                        id=other_id,
                        label=f"Other ({collapsed_files})",
                        layer="enhancement",
                        status="pending",
                        description=f"{len(collapsed_names)} small modules",
                        file_patterns=[f"{root_path}/{n}/**" for n in collapsed_names[:5]],
                    )))
                    edges.append(asdict(RoadmapEdge(source=branch_id, target=other_id)))
                    seen_ids.add(other_id)

        # --- Step 4: Add standalone top-level dirs (tests/, config/, scripts/) ---
        # MARKER_155.1A: Skip dirs already covered by source roots or not useful
        skip_standalone = {"data", "output", "datasets", "backups", "backup", "archive"}
        for d in sorted(standalone_dirs):
            d_lower = d.lower()
            if d_lower in skip_standalone:
                continue
            # Skip huge documentation dumps (not architecture)
            file_count_check = dir_files.get(d, 0)
            if d_lower == "docs" and file_count_check > 200:
                continue
            # Skip if this exact ID already exists (e.g., 'backend' from source roots)
            node_id = d_lower
            if node_id in seen_ids:
                continue

            file_count = dir_files.get(d, 0)
            layer = RoadmapGenerator.LAYER_RULES.get(d_lower, "enhancement")
            label = RoadmapGenerator.DIR_LABELS.get(d_lower, d.title())

            nodes.append(asdict(RoadmapNode(
                id=node_id,
                label=f"{label} ({file_count})",
                layer=layer,
                status="active" if layer in ("core", "feature") else "pending",
                description=f"{d}/",
                file_patterns=[f"{d}/**"],
            )))
            edges.append(asdict(RoadmapEdge(source=root_id, target=node_id)))
            seen_ids.add(node_id)

        # --- Step 5: Fallback — if we got nothing besides root, add generic nodes ---
        if len(nodes) <= 1:
            nodes.append(asdict(RoadmapNode(
                id="core", label="Core", layer="core",
                status="active", description="Core project logic",
            )))
            nodes.append(asdict(RoadmapNode(
                id="features", label="Features", layer="feature",
                description="Project features",
            )))
            edges.append(asdict(RoadmapEdge(source=root_id, target="core")))
            edges.append(asdict(RoadmapEdge(source="core", target="features")))

        # --- Step 6: MARKER_176.5 — JEPA semantic clustering ---
        # Refine directory-only modules by grouping semantically similar ones.
        # Graceful fallback: any failure leaves nodes/edges unchanged.
        try:
            nodes, edges = _jepa_refine_modules(nodes, edges, similarity_threshold=0.70)
        except Exception as exc:
            logger.warning(f"MARKER_176.5: JEPA clustering skipped: {exc}")

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
        1. Scan directory structure (prefer sandbox_path for isolated MCC project scope)
        2. Generate roadmap (static for now, LLM in future)
        3. Save to disk
        """
        # MARKER_161.9.MULTIPROJECT.ISOLATION.ROADMAP_SANDBOX_FIRST.V1:
        # MCC project tabs must be isolated by playground/workspace.
        scan_path = config.sandbox_path
        if not scan_path or not os.path.isdir(scan_path):
            scan_path = config.source_path
        scan = cls.scan_project_structure(scan_path)
        dag = cls.generate_static_roadmap(scan, config.project_id)
        dag.save()
        return dag
