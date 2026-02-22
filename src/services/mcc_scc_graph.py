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


def _build_l2_nodes(
    scc_nodes: List[Dict[str, Any]],
    layers: Dict[str, int],
    module_by_id: Dict[str, _ModuleNode],
) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
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
                "scope": "architecture",
                "members": members,
                "scc_size": int(n.get("scc_size", len(members))),
                "scc_health": n.get("scc_health", {}),
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
            0 if degree.get(n["id"], 0) > 0 else 1,  # keep connected nodes first
            int(n.get("layer", 0)),
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


def build_condensed_graph(
    scope_root: str,
    max_nodes: int = 600,
    include_artifacts: bool = False,
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
    cache_key = f"{scope_root}|{max_nodes}|{int(include_artifacts)}"
    if (
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

    layers = _compute_layers(scc_nodes, scc_edges)
    l2_nodes = _build_l2_nodes(scc_nodes, layers, module_by_id)
    l2_nodes, l2_edges = _trim_view_graph(l2_nodes, scc_edges, max_nodes=max_nodes)

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
            "l0_nodes": l0_nodes_count,
            "l0_edges": l0_edges_count,
            "l0_explicit_edges": len(explicit_edges),
            "l0_reference_edges": len(reference_edges),
            "l0_channel_hist": channel_hist,
            "l1_scc_nodes": len(scc_nodes),
            "l1_scc_edges": len(scc_edges),
            "cyclic_scc_count": sum(1 for s in scc_nodes if int(s.get("scc_size", 1)) > 1),
            "max_scc_size": max([int(s.get("scc_size", 1)) for s in scc_nodes], default=1),
            "l2_nodes": len(l2_nodes),
            "l2_edges": len(l2_edges),
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
            "edges": scc_edges,
            "node_to_scc": node_to_scc,
        },
        "l2": {
            "nodes": l2_nodes,
            "edges": l2_edges,
        },
        "markers": [
            "MARKER_155.MODE_ARCH.V11.P1",
            "MARKER_155.INPUT_MATRIX.SCANNERS.V1",
            "MARKER_155.MODE_ARCH.V11.GRAPH_LEVELS",
            "MARKER_155.MODE_ARCH.V11.CYCLE_POLICY",
        ],
    }

    _cache["key"] = cache_key
    _cache["source_mtime"] = src_mtime
    _cache["ts"] = time.time()
    _cache["result"] = response
    return response
