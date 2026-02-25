"""
MARKER_155.MODE_ARCH.V11.P1: MCC module graph -> SCC DAG -> L2 view builder.

Narrow backend implementation for /api/mcc/graph/condensed.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

# Ignore heavy/unrelated folders while scanning code modules.
_IGNORED_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "target",
    "__pycache__",
    ".venv",
    "venv",
    "venv_mcp",
    ".codex",
    ".next",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "coverage",
    "data",
}

_CODE_EXTS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".rs",
    ".go",
    ".java",
}

_PY_IMPORT_RE = re.compile(r"^\s*import\s+([^#\n]+)", re.MULTILINE)
_PY_FROM_RE = re.compile(r"^\s*from\s+([.\w]+)\s+import\s+", re.MULTILINE)
_TS_FROM_RE = re.compile(r"(?:import|export)\s+[^;\n]*?\s+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE)
_TS_REQUIRE_RE = re.compile(r"require\(\s*['\"]([^'\"]+)['\"]\s*\)")
_TS_DYNAMIC_IMPORT_RE = re.compile(r"import\(\s*['\"]([^'\"]+)['\"]\s*\)")
_REF_PATH_RE = re.compile(r"(?<![\w/])(?:\.{1,2}/|/)?[A-Za-z0-9_\-./]+(?:\.[A-Za-z0-9_]+)")

_DOC_EXTS = {".md", ".txt", ".rst"}
_MEDIA_EXTS = {".mp4", ".mov", ".mkv", ".wav", ".mp3", ".m4a"}


@dataclass
class _ModuleNode:
    module_id: str
    abs_path: str
    rel_path: str
    language: str
    parent: str
    ext: str
    mtime: float


_cache: Dict[str, Any] = {
    "key": "",
    "source_mtime": 0.0,
    "ts": 0.0,
    "result": None,
}

_ALGO_REV = "marker155-archdir-v2"


def _build_artifact_l0(scope_root: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    artifact_dir = os.path.join(scope_root, "data", "artifacts")
    if not os.path.isdir(artifact_dir):
        artifact_dir = os.path.join("data", "artifacts")
    if not os.path.isdir(artifact_dir):
        return [], []

    nodes: List[Dict[str, Any]] = [
        {
            "id": "__artifact_root__",
            "kind": "artifact_root",
            "path": "data/artifacts",
            "language": "artifact",
        }
    ]
    edges: List[Dict[str, Any]] = []

    for root, _dirs, files in os.walk(artifact_dir):
        for name in files:
            if name.startswith("."):
                continue
            abs_path = os.path.join(root, name)
            rel_path = os.path.relpath(abs_path, scope_root).replace("\\", "/")
            node_id = f"artifact:{rel_path}"
            nodes.append(
                {
                    "id": node_id,
                    "kind": "artifact",
                    "path": rel_path,
                    "language": "artifact",
                }
            )
            edges.append(
                {
                    "source": "__artifact_root__",
                    "target": node_id,
                    "type": "contains",
                    "evidence": [f"artifact file {rel_path}"],
                    "confidence": 1.0,
                }
            )
    return nodes, edges


def _source_mtime(scope_root: str) -> float:
    mtimes: List[float] = []
    for candidate in [scope_root, "data/artifacts/staging.json", "data/artifacts"]:
        try:
            if os.path.exists(candidate):
                mtimes.append(os.path.getmtime(candidate))
        except Exception:
            pass
    return max(mtimes) if mtimes else 0.0


def _walk_code_files(scope_root: str) -> List[str]:
    files: List[str] = []
    for root, dirs, filenames in os.walk(scope_root):
        dirs[:] = [
            d
            for d in dirs
            if d not in _IGNORED_DIRS
            and not d.startswith(".")
            and not d.startswith("venv")
        ]
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext not in _CODE_EXTS:
                continue
            files.append(os.path.join(root, name))
    return files


def _lang_for_ext(ext: str) -> str:
    if ext in {".py"}:
        return "python"
    if ext in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}:
        return "typescript"
    if ext in {".rs"}:
        return "rust"
    if ext in {".go"}:
        return "go"
    if ext in {".java"}:
        return "java"
    if ext in _DOC_EXTS:
        return "doc"
    if ext in _MEDIA_EXTS:
        return "media"
    return "other"


def _node_type_for_ext(ext: str) -> str:
    if ext in _CODE_EXTS:
        return "code"
    if ext in _DOC_EXTS:
        return "doc"
    if ext in _MEDIA_EXTS:
        return "media"
    return "other"


def _tokenize_module_id(module_id: str) -> Set[str]:
    stem = module_id.lower()
    stem = re.sub(r"[^a-z0-9/_\-\.]", " ", stem)
    parts = re.split(r"[\/_\-\.]+", stem)
    return {p for p in parts if len(p) >= 3}


def _build_module_index(scope_root: str, files: Iterable[str]) -> Tuple[Dict[str, _ModuleNode], Dict[str, str], Dict[str, str]]:
    """
    Returns:
    - module_by_id: rel-path id -> module node
    - abs_to_id: abs-path -> module id
    - py_module_to_id: py module import path -> module id
    """
    module_by_id: Dict[str, _ModuleNode] = {}
    abs_to_id: Dict[str, str] = {}
    py_module_to_id: Dict[str, str] = {}

    for abs_path in files:
        rel = os.path.relpath(abs_path, scope_root).replace("\\", "/")
        ext = os.path.splitext(rel)[1].lower()
        module_id = rel
        parent = os.path.dirname(rel)
        node = _ModuleNode(
            module_id=module_id,
            abs_path=abs_path,
            rel_path=rel,
            language=_lang_for_ext(ext),
            parent=parent,
            ext=ext,
            mtime=os.path.getmtime(abs_path) if os.path.exists(abs_path) else 0.0,
        )
        module_by_id[module_id] = node
        abs_to_id[abs_path] = module_id

        if ext == ".py":
            base = rel[:-3]  # trim .py
            if base.endswith("/__init__"):
                mod = base[: -len("/__init__")]
                if mod:
                    py_module_to_id[mod.replace("/", ".")] = module_id
            else:
                py_module_to_id[base.replace("/", ".")] = module_id

    return module_by_id, abs_to_id, py_module_to_id


def _safe_read(path: str, max_len: int = 250_000) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(max_len)
    except Exception:
        return ""


def _resolve_relative_import(current_rel: str, spec: str, module_by_id: Dict[str, _ModuleNode]) -> Optional[str]:
    if not spec.startswith("."):
        return None

    cur_dir = os.path.dirname(current_rel)
    base_dir = os.path.normpath(os.path.join(cur_dir, spec)).replace("\\", "/")

    candidates = []
    if os.path.splitext(base_dir)[1]:
        candidates.append(base_dir)
    else:
        for ext in [".ts", ".tsx", ".js", ".jsx", ".py", ".mjs", ".cjs"]:
            candidates.append(base_dir + ext)
        candidates.append(base_dir + "/index.ts")
        candidates.append(base_dir + "/index.tsx")
        candidates.append(base_dir + "/index.js")
        candidates.append(base_dir + "/index.jsx")
        candidates.append(base_dir + "/__init__.py")

    for cand in candidates:
        if cand in module_by_id:
            return cand
    return None


def _resolve_py_import(
    current_rel: str,
    spec: str,
    py_module_to_id: Dict[str, str],
    module_by_id: Dict[str, _ModuleNode],
) -> Optional[str]:
    # relative python import: .foo / ..bar
    if spec.startswith("."):
        dots = len(spec) - len(spec.lstrip("."))
        suffix = spec[dots:]
        cur_pkg = os.path.dirname(current_rel).replace("/", ".")
        parts = [p for p in cur_pkg.split(".") if p]
        keep = max(0, len(parts) - dots + 1)
        base = parts[:keep]
        if suffix:
            base.extend([p for p in suffix.split(".") if p])
        candidate = ".".join(base)
        if candidate in py_module_to_id:
            return py_module_to_id[candidate]
        return None

    if spec in py_module_to_id:
        return py_module_to_id[spec]

    # Try package root fallback: import src.api.routes => src.api.routes.__init__
    prefix = spec
    while "." in prefix:
        prefix = prefix.rsplit(".", 1)[0]
        if prefix in py_module_to_id:
            return py_module_to_id[prefix]

    return None


def _extract_edges(
    scope_root: str,
    module_by_id: Dict[str, _ModuleNode],
    py_module_to_id: Dict[str, str],
) -> Tuple[List[Dict[str, Any]], Dict[str, Set[str]]]:
    edges: List[Dict[str, Any]] = []
    adj: Dict[str, Set[str]] = defaultdict(set)

    for module_id, node in module_by_id.items():
        content = _safe_read(node.abs_path)
        if not content:
            continue

        if node.language == "python":
            # import a, b.c
            for match in _PY_IMPORT_RE.findall(content):
                for raw in match.split(","):
                    spec = raw.strip().split(" as ")[0].strip()
                    if not spec:
                        continue
                    target = _resolve_py_import(module_id, spec, py_module_to_id, module_by_id)
                    if target and target != module_id:
                        adj[module_id].add(target)
                        edges.append({
                            "source": module_id,
                            "target": target,
                            "type": "explicit",
                            "evidence": [f"import {spec}"],
                            "confidence": 1.0,
                        })

            # from x import y
            for spec in _PY_FROM_RE.findall(content):
                target = _resolve_py_import(module_id, spec.strip(), py_module_to_id, module_by_id)
                if target and target != module_id:
                    adj[module_id].add(target)
                    edges.append({
                        "source": module_id,
                        "target": target,
                        "type": "explicit",
                        "evidence": [f"from {spec} import ..."],
                        "confidence": 1.0,
                    })

        elif node.language == "typescript":
            specs = []
            specs.extend(_TS_FROM_RE.findall(content))
            specs.extend(_TS_REQUIRE_RE.findall(content))
            specs.extend(_TS_DYNAMIC_IMPORT_RE.findall(content))
            for spec in specs:
                target = None
                if spec.startswith("."):
                    target = _resolve_relative_import(module_id, spec, module_by_id)
                elif spec.startswith("src/"):
                    target = _resolve_relative_import(module_id, f"./../../{spec[4:]}", module_by_id)
                    if not target:
                        for ext in [".ts", ".tsx", ".js", ".jsx"]:
                            cand = f"src/{spec[4:]}{ext}"
                            if cand in module_by_id:
                                target = cand
                                break
                if target and target != module_id:
                    adj[module_id].add(target)
                    edges.append({
                        "source": module_id,
                        "target": target,
                        "type": "explicit",
                        "evidence": [f"import {spec}"],
                        "confidence": 1.0,
                    })

    dedup = {}
    for e in edges:
        key = (e["source"], e["target"], e["type"])
        if key not in dedup:
            dedup[key] = e
    return list(dedup.values()), adj


def _resolve_reference_to_module(
    current_rel: str,
    ref_spec: str,
    module_by_id: Dict[str, _ModuleNode],
) -> Optional[str]:
    spec = ref_spec.strip().strip("\"'`")
    if len(spec) < 4:
        return None
    if spec.startswith("http://") or spec.startswith("https://"):
        return None

    if spec.startswith("./") or spec.startswith("../"):
        resolved = _resolve_relative_import(current_rel, spec, module_by_id)
        if resolved:
            return resolved

    spec = spec.lstrip("/")
    if spec in module_by_id:
        return spec

    # soft match by suffix path
    for mid in module_by_id.keys():
        if mid.endswith(spec):
            return mid
    return None


def _extract_reference_edges(
    module_by_id: Dict[str, _ModuleNode],
) -> List[Dict[str, Any]]:
    edges: List[Dict[str, Any]] = []
    for module_id, node in module_by_id.items():
        content = _safe_read(node.abs_path, max_len=120_000)
        if not content:
            continue
        seen_targets: Set[str] = set()
        matches = _REF_PATH_RE.findall(content)
        if not matches:
            continue
        for ref in matches[:120]:
            target = _resolve_reference_to_module(module_id, ref, module_by_id)
            if not target or target == module_id or target in seen_targets:
                continue
            seen_targets.add(target)
            edges.append(
                {
                    "source": module_id,
                    "target": target,
                    "channel": "reference",
                    "score": 0.62,
                    "confidence": 0.72,
                    "evidence": [f"ref:{ref[:120]}"],
                }
            )
    return edges


def _pair_weights(source_type: str, target_type: str) -> Dict[str, float]:
    matrix: Dict[Tuple[str, str], Dict[str, float]] = {
        ("code", "code"): {"structural": 0.58, "semantic": 0.16, "temporal": 0.14, "reference": 0.10, "contextual": 0.02},
        ("doc", "doc"): {"structural": 0.05, "semantic": 0.45, "temporal": 0.20, "reference": 0.25, "contextual": 0.05},
        ("media", "media"): {"structural": 0.05, "semantic": 0.40, "temporal": 0.35, "reference": 0.10, "contextual": 0.10},
        ("doc", "code"): {"structural": 0.10, "semantic": 0.28, "temporal": 0.20, "reference": 0.37, "contextual": 0.05},
        ("code", "doc"): {"structural": 0.12, "semantic": 0.24, "temporal": 0.20, "reference": 0.38, "contextual": 0.06},
    }
    return matrix.get((source_type, target_type), {"structural": 0.20, "semantic": 0.35, "temporal": 0.25, "reference": 0.15, "contextual": 0.05})


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-12.0 * (x - 0.35)))


def _aggregate_input_matrix_edges(
    module_by_id: Dict[str, _ModuleNode],
    explicit_edges: List[Dict[str, Any]],
    reference_edges: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Set[str]], Dict[str, int]]:
    by_pair: Dict[Tuple[str, str], Dict[str, Any]] = {}
    token_map = {mid: _tokenize_module_id(mid) for mid in module_by_id.keys()}

    def ensure_pair(source: str, target: str) -> Dict[str, Any]:
        key = (source, target)
        if key not in by_pair:
            by_pair[key] = {
                "source": source,
                "target": target,
                "channels": {"structural": 0.0, "semantic": 0.0, "temporal": 0.0, "reference": 0.0, "contextual": 0.0},
                "evidence": [],
            }
        return by_pair[key]

    # Structural channel from explicit imports.
    for e in explicit_edges:
        p = ensure_pair(e["source"], e["target"])
        p["channels"]["structural"] = max(p["channels"]["structural"], 1.0)
        p["evidence"].extend(e.get("evidence") or [])

    # Reference channel from path refs.
    for e in reference_edges:
        p = ensure_pair(e["source"], e["target"])
        p["channels"]["reference"] = max(p["channels"]["reference"], float(e.get("score", 0.0)))
        p["evidence"].extend(e.get("evidence") or [])

    # Temporal + semantic candidates only in local neighborhoods (parent buckets).
    bucket: Dict[str, List[str]] = defaultdict(list)
    for mid, node in module_by_id.items():
        key = node.parent or "__root__"
        bucket[key].append(mid)

    for mids in bucket.values():
        if len(mids) < 2:
            continue
        mids_sorted = sorted(mids, key=lambda m: module_by_id[m].mtime)
        for i, src in enumerate(mids_sorted):
            src_node = module_by_id[src]
            src_tokens = token_map.get(src, set())
            for tgt in mids_sorted[i + 1 : i + 6]:
                tgt_node = module_by_id[tgt]
                dt_days = max(0.0, (tgt_node.mtime - src_node.mtime) / 86400.0)
                temporal = 0.2 + 0.8 * math.exp(-(dt_days / 30.0))
                p = ensure_pair(src, tgt)
                p["channels"]["temporal"] = max(p["channels"]["temporal"], temporal)
                if dt_days > 0:
                    p["evidence"].append(f"temporal:{src_node.mtime:.0f}->{tgt_node.mtime:.0f}")

                tgt_tokens = token_map.get(tgt, set())
                if src_tokens and tgt_tokens:
                    inter = len(src_tokens & tgt_tokens)
                    union = len(src_tokens | tgt_tokens)
                    if union > 0:
                        sem = inter / union
                        if sem >= 0.22:
                            sem_norm = max(0.0, (sem - 0.22) / 0.78)
                            p["channels"]["semantic"] = max(p["channels"]["semantic"], sem_norm)
                            p["evidence"].append(f"semantic_jaccard:{sem:.3f}")

    accepted_edges: List[Dict[str, Any]] = []
    adj: Dict[str, Set[str]] = defaultdict(set)
    channel_hist: Dict[str, int] = defaultdict(int)

    for (source, target), data in by_pair.items():
        src_node = module_by_id.get(source)
        tgt_node = module_by_id.get(target)
        if not src_node or not tgt_node:
            continue
        source_type = _node_type_for_ext(src_node.ext)
        target_type = _node_type_for_ext(tgt_node.ext)
        weights = _pair_weights(source_type, target_type)
        channels = data["channels"]

        weighted = (
            channels["structural"] * weights["structural"]
            + channels["semantic"] * weights["semantic"]
            + channels["temporal"] * weights["temporal"]
            + channels["reference"] * weights["reference"]
            + channels["contextual"] * weights["contextual"]
        )
        score = _sigmoid(weighted)
        has_explicit = channels["structural"] >= 0.99
        semantic_v = float(channels.get("semantic", 0.0))
        temporal_v = float(channels.get("temporal", 0.0))
        reference_v = float(channels.get("reference", 0.0))
        non_structural_gate = (
            (semantic_v >= 0.55 and temporal_v >= 0.35)
            or (reference_v >= 0.72)
            or (semantic_v >= 0.68)
        )
        if not has_explicit and score < 0.52 and not non_structural_gate:
            continue

        channel_name, channel_value = max(channels.items(), key=lambda item: item[1])
        if channel_value <= 0:
            channel_name = "structural"
        channel_hist[channel_name] += 1

        edge = {
            "source": source,
            "target": target,
            "type": channel_name,
            "relation_kind": channel_name,
            "score": float(score),
            "confidence": float(max(score, channel_value)),
            "channels": channels,
            "pair_types": {"source": source_type, "target": target_type},
            "evidence": sorted(set(data["evidence"]))[:10],
        }
        accepted_edges.append(edge)
        adj[source].add(target)

    accepted_edges.sort(key=lambda e: (e["source"], e["target"]))
    return accepted_edges, adj, dict(channel_hist)


def _tarjan_scc(nodes: List[str], adj: Dict[str, Set[str]]) -> List[List[str]]:
    index = 0
    indices: Dict[str, int] = {}
    lowlink: Dict[str, int] = {}
    stack: List[str] = []
    on_stack: Set[str] = set()
    sccs: List[List[str]] = []

    def strongconnect(v: str) -> None:
        nonlocal index
        indices[v] = index
        lowlink[v] = index
        index += 1
        stack.append(v)
        on_stack.add(v)

        for w in adj.get(v, set()):
            if w not in indices:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], indices[w])

        if lowlink[v] == indices[v]:
            component: List[str] = []
            while stack:
                w = stack.pop()
                on_stack.discard(w)
                component.append(w)
                if w == v:
                    break
            sccs.append(sorted(component))

    for v in sorted(nodes):
        if v not in indices:
            strongconnect(v)
    return sccs


def _condense_graph(
    sccs: List[List[str]],
    adj: Dict[str, Set[str]],
    raw_edges: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, str]]:
    node_to_scc: Dict[str, str] = {}
    scc_nodes: List[Dict[str, Any]] = []

    for i, comp in enumerate(sccs):
        sid = f"scc_{i}"
        for node in comp:
            node_to_scc[node] = sid
        warning = "singleton"
        if len(comp) > 1:
            warning = "dense" if len(comp) >= 8 else "cyclic"
        scc_nodes.append(
            {
                "id": sid,
                "kind": "scc" if len(comp) > 1 else "module",
                "members": comp,
                "scc_size": len(comp),
                "scc_health": {
                    "size": len(comp),
                    "density": 1.0 if len(comp) == 1 else 0.0,
                    "max_cycle_len": len(comp) if len(comp) > 1 else 0,
                    "warning": warning,
                },
            }
        )

    scc_edge_acc: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for edge in raw_edges:
        src = edge.get("source")
        tgt = edge.get("target")
        if src not in node_to_scc or tgt not in node_to_scc:
            continue
        src_scc = node_to_scc[src]
        tgt_scc = node_to_scc[tgt]
        if src_scc == tgt_scc:
            continue
        key = (src_scc, tgt_scc)
        if key not in scc_edge_acc:
            scc_edge_acc[key] = {
                "source": src_scc,
                "target": tgt_scc,
                "score": 0.0,
                "confidence": 0.0,
                "channels": defaultdict(float),
                "evidence": [],
            }
        acc = scc_edge_acc[key]
        acc["score"] = max(acc["score"], float(edge.get("score", 0.0)))
        acc["confidence"] = max(acc["confidence"], float(edge.get("confidence", 0.0)))
        for ch, val in (edge.get("channels") or {}).items():
            acc["channels"][ch] = max(float(acc["channels"][ch]), float(val))
        acc["evidence"].extend(edge.get("evidence") or [])

    scc_edges: List[Dict[str, Any]] = []
    for key, acc in sorted(scc_edge_acc.items()):
        channels = dict(acc["channels"])
        edge_type = "structural"
        if channels:
            edge_type = max(channels.items(), key=lambda item: item[1])[0]
        scc_edges.append(
            {
                "source": acc["source"],
                "target": acc["target"],
                "type": edge_type,
                "relation_kind": edge_type,
                "mode_layer": 0,
                "is_condensed": True,
                "score": float(acc["score"]),
                "confidence": float(acc["confidence"]),
                "channels": channels,
                "evidence": sorted(set(acc["evidence"]))[:8],
            }
        )
    return scc_nodes, scc_edges, node_to_scc


def _compute_layers(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, int]:
    indeg: Dict[str, int] = {n["id"]: 0 for n in nodes}
    succ: Dict[str, Set[str]] = {n["id"]: set() for n in nodes}

    for e in edges:
        s = e["source"]
        t = e["target"]
        if s in succ and t in indeg and t not in succ[s]:
            succ[s].add(t)
            indeg[t] += 1

    queue = [n for n in indeg if indeg[n] == 0]
    queue.sort()
    dq = deque(queue)
    layer: Dict[str, int] = {n: 0 for n in indeg}

    while dq:
        cur = dq.popleft()
        cur_l = layer[cur]
        for nxt in sorted(succ[cur]):
            layer[nxt] = max(layer[nxt], cur_l + 1)
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                dq.append(nxt)

    return layer


def _normalize(values: Dict[str, float]) -> Dict[str, float]:
    if not values:
        return {}
    min_v = min(values.values())
    max_v = max(values.values())
    if abs(max_v - min_v) < 1e-12:
        return {k: 0.5 for k in values.keys()}
    return {k: (v - min_v) / (max_v - min_v) for k, v in values.items()}


# MARKER_155.INPUT_MATRIX.ROOT_SCORE.V1:
# Compute algorithmic roots from graph statistics and time signals (no path hardcode).
def _compute_root_scores(
    scc_nodes: List[Dict[str, Any]],
    scc_edges: List[Dict[str, Any]],
    module_by_id: Dict[str, _ModuleNode],
) -> Dict[str, Dict[str, float]]:
    node_ids = [n["id"] for n in scc_nodes]
    indeg: Dict[str, int] = {nid: 0 for nid in node_ids}
    outdeg: Dict[str, int] = {nid: 0 for nid in node_ids}
    ref_out: Dict[str, float] = {nid: 0.0 for nid in node_ids}
    earliest_ts: Dict[str, float] = {}
    cycle_penalty_raw: Dict[str, float] = {}

    for n in scc_nodes:
        nid = n["id"]
        members = n.get("members") or []
        member_times = [module_by_id[m].mtime for m in members if m in module_by_id]
        earliest_ts[nid] = min(member_times) if member_times else 0.0
        density = float((n.get("scc_health") or {}).get("density", 0.0))
        size = max(1.0, float(n.get("scc_size", 1)))
        cycle_penalty_raw[nid] = min(1.0, density * 0.7 + ((size - 1.0) / 20.0))

    for e in scc_edges:
        s = e["source"]
        t = e["target"]
        if s in outdeg:
            outdeg[s] += 1
        if t in indeg:
            indeg[t] += 1
        ref_out[s] = ref_out.get(s, 0.0) + float((e.get("channels") or {}).get("reference", 0.0))

    out_power_raw = {nid: float(outdeg.get(nid, 0)) for nid in node_ids}
    sink_penalty_raw = {nid: float(indeg.get(nid, 0)) for nid in node_ids}
    earliness_raw = _normalize({nid: -earliest_ts.get(nid, 0.0) for nid in node_ids})
    authority_raw = _normalize(ref_out)
    cycle_penalty = _normalize(cycle_penalty_raw)
    out_power = _normalize(out_power_raw)
    sink_penalty = _normalize(sink_penalty_raw)

    result: Dict[str, Dict[str, float]] = {}
    for nid in node_ids:
        score = (
            0.45 * out_power.get(nid, 0.0)
            + 0.25 * authority_raw.get(nid, 0.0)
            + 0.20 * earliness_raw.get(nid, 0.0)
            - 0.10 * cycle_penalty.get(nid, 0.0)
            - 0.05 * sink_penalty.get(nid, 0.0)
        )
        result[nid] = {
            "root_score": float(score),
            "source_centrality": float(out_power.get(nid, 0.0)),
            "time_earliness": float(earliness_raw.get(nid, 0.0)),
            "authority": float(authority_raw.get(nid, 0.0)),
            "sink_penalty": float(sink_penalty.get(nid, 0.0)),
            "cycle_penalty": float(cycle_penalty.get(nid, 0.0)),
        }
    return result


def _choose_roots_by_component(
    scc_nodes: List[Dict[str, Any]],
    scc_edges: List[Dict[str, Any]],
    root_scores: Dict[str, Dict[str, float]],
) -> List[str]:
    node_ids = [n["id"] for n in scc_nodes]
    undirected: Dict[str, Set[str]] = {nid: set() for nid in node_ids}
    for e in scc_edges:
        s = e["source"]
        t = e["target"]
        if s in undirected and t in undirected:
            undirected[s].add(t)
            undirected[t].add(s)

    roots: List[str] = []
    seen: Set[str] = set()
    for nid in sorted(node_ids):
        if nid in seen:
            continue
        # BFS component
        comp: List[str] = []
        dq = deque([nid])
        seen.add(nid)
        while dq:
            cur = dq.popleft()
            comp.append(cur)
            for nxt in sorted(undirected.get(cur, set())):
                if nxt not in seen:
                    seen.add(nxt)
                    dq.append(nxt)

        # Pick algorithmic source of component by root_score only.
        best = max(comp, key=lambda x: (root_scores.get(x, {}).get("root_score", -1e9), x))
        roots.append(best)
    return sorted(set(roots))


def _tokens_for_scc(
    scc_nodes: List[Dict[str, Any]],
) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = {}
    for n in scc_nodes:
        nid = n["id"]
        members = n.get("members") or []
        sample = members[0] if members else nid
        out[nid] = _tokenize_module_id(sample)
    return out


# MARKER_155.INPUT_MATRIX.ROOT_COALESCE.V1:
# Keep root count bounded for readable architecture while preserving algorithmic derivation.
def _coalesce_roots(
    roots: List[str],
    root_scores: Dict[str, Dict[str, float]],
    scc_nodes: List[Dict[str, Any]],
    limit: int,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    if len(roots) <= max(1, limit):
        return roots, []

    ranked = sorted(
        roots,
        key=lambda rid: (-float(root_scores.get(rid, {}).get("root_score", 0.0)), rid),
    )
    keep = ranked[: max(1, limit)]
    keep_set = set(keep)
    dropped = ranked[max(1, limit) :]

    token_map = _tokens_for_scc(scc_nodes)
    synthetic_edges: List[Dict[str, Any]] = []

    for child in dropped:
        child_toks = token_map.get(child, set())
        best_parent = keep[0]
        best_score = -1.0
        for parent in keep:
            parent_toks = token_map.get(parent, set())
            overlap = 0.0
            if child_toks and parent_toks:
                inter = len(child_toks & parent_toks)
                union = len(child_toks | parent_toks)
                overlap = float(inter) / float(union) if union > 0 else 0.0
            score = overlap + 0.25 * float(root_scores.get(parent, {}).get("root_score", 0.0))
            if score > best_score:
                best_score = score
                best_parent = parent
        synthetic_edges.append(
            {
                "source": best_parent,
                "target": child,
                "type": "hier_root",
                "relation_kind": "hier_root",
                "score": 0.55,
                "confidence": 0.65,
                "channels": {"structural": 0.0, "semantic": 0.0, "temporal": 0.0, "reference": 0.0, "contextual": 0.0},
                "evidence": ["root_coalesce"],
                "is_backbone": True,
                "mode_layer": 0,
            }
        )
    return sorted(keep), synthetic_edges


# MARKER_155.INPUT_MATRIX.BACKBONE_DAG.V1:
# Build deterministic causal backbone: one best parent per non-root node.
def _build_backbone_edges(
    scc_nodes: List[Dict[str, Any]],
    scc_edges: List[Dict[str, Any]],
    roots: List[str],
    preferred_layers: Optional[Dict[str, int]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    incoming: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for e in scc_edges:
        incoming[e["target"]].append(e)

    root_set = set(roots)
    backbone: List[Dict[str, Any]] = []
    cross: List[Dict[str, Any]] = []
    chosen_keys: Set[Tuple[str, str]] = set()

    for n in sorted(scc_nodes, key=lambda x: x["id"]):
        nid = n["id"]
        if nid in root_set:
            continue
        candidates = incoming.get(nid, [])
        if not candidates:
            continue
        ranked = sorted(
            candidates,
            key=lambda e: (
                # Prefer deeper parents when provisional layering is available.
                -(preferred_layers.get(e.get("source", ""), 0) if preferred_layers else 0),
                -float(e.get("score", 0.0)),
                -float(e.get("confidence", 0.0)),
                str(e.get("source", "")),
                str(e.get("target", "")),
            ),
        )
        winner = ranked[0]
        backbone.append({**winner, "is_backbone": True, "mode_layer": 0})
        chosen_keys.add((winner["source"], winner["target"]))
        for rest in ranked[1:]:
            cross.append({**rest, "is_backbone": False, "mode_layer": 1, "type": "cross_link"})

    # Keep remaining edges as cross-links.
    for e in scc_edges:
        key = (e["source"], e["target"])
        if key in chosen_keys:
            continue
        if any(c["source"] == e["source"] and c["target"] == e["target"] for c in cross):
            continue
        cross.append({**e, "is_backbone": False, "mode_layer": 1, "type": "cross_link"})

    return backbone, cross


def _compute_layers_from_roots(
    scc_nodes: List[Dict[str, Any]],
    backbone_edges: List[Dict[str, Any]],
    roots: List[str],
) -> Dict[str, int]:
    node_ids = [n["id"] for n in scc_nodes]
    succ: Dict[str, Set[str]] = {nid: set() for nid in node_ids}
    indeg: Dict[str, int] = {nid: 0 for nid in node_ids}
    undirected: Dict[str, Set[str]] = {nid: set() for nid in node_ids}
    for e in backbone_edges:
        s = e["source"]
        t = e["target"]
        if s in succ and t in indeg and t not in succ[s]:
            succ[s].add(t)
            indeg[t] += 1
            undirected[s].add(t)
            undirected[t].add(s)

    # Topological longest-path layering over DAG edges.
    q = deque(sorted([nid for nid in node_ids if indeg.get(nid, 0) == 0]))
    indeg_work = dict(indeg)
    layer: Dict[str, int] = {nid: 0 for nid in node_ids}
    seen_order: List[str] = []
    while q:
        cur = q.popleft()
        seen_order.append(cur)
        for nxt in sorted(succ.get(cur, set())):
            layer[nxt] = max(int(layer.get(nxt, 0)), int(layer.get(cur, 0)) + 1)
            indeg_work[nxt] = int(indeg_work.get(nxt, 0)) - 1
            if indeg_work[nxt] == 0:
                q.append(nxt)

    # Defensive fallback if graph has unresolved nodes.
    unresolved = [nid for nid in node_ids if nid not in set(seen_order)]
    if unresolved:
        for _ in range(len(node_ids)):
            changed = False
            for e in backbone_edges:
                s = e["source"]
                t = e["target"]
                if s in layer and t in layer:
                    cand = int(layer[s]) + 1
                    if cand > int(layer[t]):
                        layer[t] = cand
                        changed = True
            if not changed:
                break

    # Normalize each weak component so designated roots (or component minimum) start at layer 0.
    roots_set = set(roots)
    visited: Set[str] = set()
    for nid in sorted(node_ids):
        if nid in visited:
            continue
        comp: List[str] = []
        dq = deque([nid])
        visited.add(nid)
        while dq:
            cur = dq.popleft()
            comp.append(cur)
            for nxt in undirected.get(cur, set()):
                if nxt not in visited:
                    visited.add(nxt)
                    dq.append(nxt)
        comp_roots = [r for r in comp if r in roots_set]
        if comp_roots:
            base = min(int(layer.get(r, 0)) for r in comp_roots)
        else:
            base = min(int(layer.get(x, 0)) for x in comp)
        for x in comp:
            layer[x] = int(layer.get(x, 0)) - int(base)

    return layer


def _build_l2_nodes(
    scc_nodes: List[Dict[str, Any]],
    layers: Dict[str, int],
    module_by_id: Dict[str, _ModuleNode],
    root_scores: Dict[str, Dict[str, float]],
    roots: List[str],
) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    max_layer = max([int(layers.get(n["id"], 0)) for n in scc_nodes], default=1)
    max_layer = max(1, max_layer)
    root_set = set(roots)
    for n in scc_nodes:
        sid = n["id"]
        members = n.get("members") or []
        label = members[0] if len(members) == 1 else f"SCC ({len(members)})"
        parent_hint = ""
        if members:
            parent_hint = os.path.dirname(members[0])
        result.append(
            {
                "id": sid,
                "kind": n.get("kind", "module"),
                "label": label,
                "layer": int(layers.get(sid, 0)),
                "knowledge_level": float(int(layers.get(sid, 0)) / float(max_layer)),
                "is_root": sid in root_set,
                "scope": "architecture",
                "members": members,
                "scc_size": int(n.get("scc_size", len(members))),
                "scc_health": n.get("scc_health", {}),
                "root_metrics": root_scores.get(sid, {}),
                "ports": {
                    "inputs": ["in.default"],
                    "outputs": ["out.default"],
                },
                "metadata": {
                    "parent": parent_hint,
                },
            }
        )
    result.sort(key=lambda x: (x["layer"], x["label"]))
    return result


def _trim_view_graph(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    max_nodes: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if max_nodes <= 0 or len(nodes) <= max_nodes:
        return nodes, edges

    degree: Dict[str, int] = defaultdict(int)
    for e in edges:
        degree[e["source"]] += 1
        degree[e["target"]] += 1

    ranked = sorted(
        nodes,
        key=lambda n: (
            0 if bool(n.get("is_root")) else 1,
            0 if degree.get(n["id"], 0) > 0 else 1,  # keep connected nodes first
            int(n.get("layer", 0)),
            -float((n.get("root_metrics") or {}).get("authority", 0.0)),
            -float((n.get("root_metrics") or {}).get("source_centrality", 0.0)),
            -int(degree.get(n["id"], 0)),
            str(n.get("label", "")),
        ),
    )

    by_id = {n["id"]: n for n in nodes}
    neighbors: Dict[str, Set[str]] = defaultdict(set)
    for e in edges:
        s = e["source"]
        t = e["target"]
        neighbors[s].add(t)
        neighbors[t].add(s)

    selected_ids: Set[str] = set()
    # Connectivity-first fill: seed from highest-degree nodes, then expand local frontier.
    for seed in [n["id"] for n in ranked]:
        if len(selected_ids) >= max_nodes:
            break
        if seed in selected_ids:
            continue
        queue = deque([seed])
        while queue and len(selected_ids) < max_nodes:
            cur = queue.popleft()
            if cur in selected_ids:
                continue
            selected_ids.add(cur)
            for nxt in sorted(neighbors.get(cur, set()), key=lambda nid: (-degree.get(nid, 0), nid)):
                if nxt not in selected_ids:
                    queue.append(nxt)

    if len(selected_ids) < max_nodes:
        for n in ranked:
            if len(selected_ids) >= max_nodes:
                break
            selected_ids.add(n["id"])

    selected = [by_id[nid] for nid in selected_ids if nid in by_id]
    allowed = set(selected_ids)
    trimmed_edges = [e for e in edges if e["source"] in allowed and e["target"] in allowed]
    selected.sort(key=lambda x: (x["layer"], x["label"]))
    return selected, trimmed_edges


def _cap_overview_edges(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    per_source_limit: int = 6,
) -> List[Dict[str, Any]]:
    if per_source_limit <= 0 or not edges:
        return edges
    layer_by_id = {n["id"]: int(n.get("layer", 0)) for n in nodes}
    by_source: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for e in edges:
        by_source[e["source"]].append(e)

    kept: List[Dict[str, Any]] = []
    for src, arr in by_source.items():
        arr_sorted = sorted(
            arr,
            key=lambda e: (
                -float(e.get("score", e.get("confidence", 0.0))),
                # keep short layer jumps on overview
                abs(int(layer_by_id.get(e.get("target", ""), 0)) - int(layer_by_id.get(src, 0))),
                str(e.get("target", "")),
            ),
        )
        kept.extend(arr_sorted[: per_source_limit])
    return kept


def _folder_key_for_node(node: Dict[str, Any]) -> str:
    parent = str((node.get("metadata") or {}).get("parent", "")).replace("\\", "/").strip("/")
    if not parent:
        members = node.get("members") or []
        if members:
            parent = os.path.dirname(str(members[0]).replace("\\", "/")).strip("/")
    parts = [p for p in parent.split("/") if p and p != "."]
    if not parts:
        return "(root)"
    if len(parts) >= 2:
        return "/".join(parts[:2])
    return parts[0]


def _build_l2_folder_overview(
    l2_nodes: List[Dict[str, Any]],
    l2_edges: List[Dict[str, Any]],
    max_folders: int = 90,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not l2_nodes:
        return [], []

    folder_meta: Dict[str, Dict[str, Any]] = {}
    node_to_folder: Dict[str, str] = {}
    for n in l2_nodes:
        fid = _folder_key_for_node(n)
        node_to_folder[n["id"]] = fid
        meta = folder_meta.setdefault(
            fid,
            {
                "id": f"dir:{fid}",
                "kind": "folder",
                "label": fid,
                "members_count": 0,
                "layer": int(n.get("layer", 0)),
                "is_root": False,
                "metadata": {"parent": fid},
            },
        )
        meta["members_count"] += 1
        meta["layer"] = min(int(meta.get("layer", 0)), int(n.get("layer", 0)))
        if bool(n.get("is_root")):
            meta["is_root"] = True

    edge_strength: Dict[Tuple[str, str], float] = defaultdict(float)
    for e in l2_edges:
        sf = node_to_folder.get(e.get("source", ""))
        tf = node_to_folder.get(e.get("target", ""))
        if not sf or not tf or sf == tf:
            continue
        edge_strength[(sf, tf)] += float(e.get("score", e.get("confidence", 1.0)))

    folder_nodes = list(folder_meta.values())
    if len(folder_nodes) > max_folders:
        degree: Dict[str, int] = defaultdict(int)
        for (s, t), _w in edge_strength.items():
            degree[s] += 1
            degree[t] += 1
        ranked = sorted(
            folder_nodes,
            key=lambda x: (
                0 if bool(x.get("is_root")) else 1,
                -int(x.get("members_count", 0)),
                -int(degree.get(x.get("label", ""), 0)),
                int(x.get("layer", 0)),
                str(x.get("label", "")),
            ),
        )
        keep = {str(n.get("label", "")) for n in ranked[:max_folders]}
        folder_nodes = [n for n in folder_nodes if str(n.get("label", "")) in keep]
    else:
        keep = {str(n.get("label", "")) for n in folder_nodes}

    layer_by_folder = {str(n.get("label", "")): int(n.get("layer", 0)) for n in folder_nodes}
    folder_edges: List[Dict[str, Any]] = []
    for (s, t), w in edge_strength.items():
        if s not in keep or t not in keep:
            continue
        if int(layer_by_folder.get(t, 0)) <= int(layer_by_folder.get(s, 0)):
            continue
        folder_edges.append(
            {
                "source": f"dir:{s}",
                "target": f"dir:{t}",
                "type": "structural",
                "score": float(w),
                "confidence": 0.8,
            }
        )

    folder_nodes.sort(key=lambda x: (int(x.get("layer", 0)), -int(x.get("members_count", 0)), str(x.get("label", ""))))
    folder_edges = _cap_overview_edges(folder_nodes, folder_edges, per_source_limit=4)
    return folder_nodes, folder_edges


def build_condensed_graph(
    scope_root: str,
    max_nodes: int = 600,
    include_artifacts: bool = False,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Build the 3-layer graph package:
    - l0: raw module graph
    - l1: SCC condensed DAG
    - l2: view graph (layered + trimmed)
    """
    scope_root = os.path.abspath(os.path.expanduser(scope_root))
    if not os.path.isdir(scope_root):
        raise ValueError(f"Invalid scope root: {scope_root}")

    src_mtime = _source_mtime(scope_root)
    cache_key = f"{_ALGO_REV}|{scope_root}|{max_nodes}|{int(include_artifacts)}"
    if (
        not force_refresh
        and
        _cache.get("result") is not None
        and _cache.get("key") == cache_key
        and float(_cache.get("source_mtime", 0.0)) == float(src_mtime)
    ):
        return _cache["result"]

    started = time.time()
    files = _walk_code_files(scope_root)
    module_by_id, _abs_to_id, py_module_to_id = _build_module_index(scope_root, files)
    explicit_edges, _adj_explicit = _extract_edges(scope_root, module_by_id, py_module_to_id)
    reference_edges = _extract_reference_edges(module_by_id)
    l0_edges, adj, channel_hist = _aggregate_input_matrix_edges(module_by_id, explicit_edges, reference_edges)

    all_nodes = sorted(module_by_id.keys())
    sccs = _tarjan_scc(all_nodes, adj)
    scc_nodes, scc_edges, node_to_scc = _condense_graph(sccs, adj, l0_edges)
    # MARKER_155.INPUT_MATRIX.ARCH_DIRECTION_INVERT.V1:
    # Scanner edges are importer -> imported (dependent -> prerequisite).
    # For MCC architecture tree semantics we need prerequisite -> derivative,
    # so roots stay at the bottom (BT) as knowledge sources.
    scc_edges_arch: List[Dict[str, Any]] = [
        {**e, "source": e.get("target"), "target": e.get("source")}
        for e in scc_edges
        if e.get("source") and e.get("target") and e.get("source") != e.get("target")
    ]

    # MARKER_155.ALGORITHMIC_DAG_FORMULAS.V1:
    # computed roots + backbone DAG as default architecture view.
    root_scores = _compute_root_scores(scc_nodes, scc_edges_arch, module_by_id)
    roots_raw = _choose_roots_by_component(scc_nodes, scc_edges_arch, root_scores)
    root_limit = max(4, min(14, int(math.sqrt(max(1, len(scc_nodes))))))
    roots, synthetic_root_edges = _coalesce_roots(roots_raw, root_scores, scc_nodes, root_limit)
    # MARKER_155.INPUT_MATRIX.LAYER_FROM_FULL_DAG.V1:
    # Derive semantic depth from full SCC DAG first, then select backbone edges with layer bias.
    layers_full = _compute_layers_from_roots(scc_nodes, scc_edges_arch, roots)
    backbone_edges, cross_edges = _build_backbone_edges(
        scc_nodes, scc_edges_arch, roots, preferred_layers=layers_full
    )
    if synthetic_root_edges:
        backbone_edges = synthetic_root_edges + backbone_edges
    layers = _compute_layers_from_roots(scc_nodes, backbone_edges, roots)
    # Preserve deeper knowledge strata from the full DAG to avoid rank collapse.
    for nid, full_l in layers_full.items():
        layers[nid] = max(int(layers.get(nid, 0)), int(full_l))
    l2_nodes = _build_l2_nodes(scc_nodes, layers, module_by_id, root_scores, roots)
    l2_nodes, l2_edges = _trim_view_graph(l2_nodes, backbone_edges, max_nodes=max_nodes)
    # Enforce strict DAG monotonicity in view graph (source layer < target layer).
    l2_layer = {n["id"]: int(n.get("layer", 0)) for n in l2_nodes}
    l2_edges = [
        e
        for e in l2_edges
        if int(l2_layer.get(e.get("source", ""), 0)) < int(l2_layer.get(e.get("target", ""), 0))
    ]
    # MARKER_155.INPUT_MATRIX.OVERVIEW_EDGE_BUDGET.V1:
    # Keep first-screen DAG readable; rich links remain available in l1/cross for drill.
    l2_edges = _cap_overview_edges(l2_nodes, l2_edges, per_source_limit=6)
    # MARKER_155.INPUT_MATRIX.FOLDER_OVERVIEW.V1:
    # Build architecture-first directory DAG for readable first-screen overview.
    l2_overview_nodes, l2_overview_edges = _build_l2_folder_overview(l2_nodes, l2_edges)

    artifact_nodes: List[Dict[str, Any]] = []
    artifact_edges: List[Dict[str, Any]] = []
    if include_artifacts:
        artifact_nodes, artifact_edges = _build_artifact_l0(scope_root)
    l0_nodes_count = len(all_nodes) + len(artifact_nodes)
    l0_edges_count = len(l0_edges) + len(artifact_edges)

    response = {
        "scope_root": scope_root,
        "signature": hashlib.md5(f"{scope_root}:{src_mtime}:{len(files)}".encode("utf-8")).hexdigest()[:12],
        "generated_at": int(time.time()),
        "stats": {
            "algo_rev": _ALGO_REV,
            "l0_nodes": l0_nodes_count,
            "l0_edges": l0_edges_count,
            "l0_explicit_edges": len(explicit_edges),
            "l0_reference_edges": len(reference_edges),
            "l0_channel_hist": channel_hist,
            "l1_scc_nodes": len(scc_nodes),
            "l1_scc_edges": len(scc_edges),
            "l1_roots": len(roots),
            "l1_roots_raw": len(roots_raw),
            "l1_backbone_edges": len(backbone_edges),
            "l1_cross_edges": len(cross_edges),
            "cyclic_scc_count": sum(1 for s in scc_nodes if int(s.get("scc_size", 1)) > 1),
            "max_scc_size": max([int(s.get("scc_size", 1)) for s in scc_nodes], default=1),
            "l2_nodes": len(l2_nodes),
            "l2_edges": len(l2_edges),
            "l2_overview_nodes": len(l2_overview_nodes),
            "l2_overview_edges": len(l2_overview_edges),
            "build_ms": int((time.time() - started) * 1000),
        },
        "l0": {
            "nodes": [
                {
                    "id": mid,
                    "kind": "module",
                    "path": module_by_id[mid].rel_path,
                    "language": module_by_id[mid].language,
                }
                for mid in all_nodes
            ] + artifact_nodes,
            "edges": l0_edges + artifact_edges,
        },
        "l1": {
            "nodes": scc_nodes,
            "edges": scc_edges_arch,
            "node_to_scc": node_to_scc,
            "roots": roots,
            "roots_raw": roots_raw,
            "root_scores": root_scores,
            "backbone_edges": backbone_edges,
            "cross_edges": cross_edges,
        },
        "l2": {
            "nodes": l2_nodes,
            "edges": l2_edges,
        },
        "l2_overview": {
            "nodes": l2_overview_nodes,
            "edges": l2_overview_edges,
        },
        "markers": [
            "MARKER_155.MODE_ARCH.V11.P1",
            "MARKER_155.INPUT_MATRIX.SCANNERS.V1",
            "MARKER_155.INPUT_MATRIX.ROOT_SCORE.V1",
            "MARKER_155.INPUT_MATRIX.BACKBONE_DAG.V1",
            "MARKER_155.ALGORITHMIC_DAG_FORMULAS.V1",
            "MARKER_155.MODE_ARCH.V11.GRAPH_LEVELS",
            "MARKER_155.MODE_ARCH.V11.CYCLE_POLICY",
            "MARKER_155.INPUT_MATRIX.ARCH_DIRECTION_INVERT.V1",
            "MARKER_155.INPUT_MATRIX.FOLDER_OVERVIEW.V1",
            _ALGO_REV,
        ],
    }

    _cache["key"] = cache_key
    _cache["source_mtime"] = src_mtime
    _cache["ts"] = time.time()
    _cache["result"] = response
    return response
