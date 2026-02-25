"""
MARKER_155.ARCHITECT_BUILD.V1:
Architect build service for Design DAG generation.

Builds a planning-ready design graph from deterministic runtime graph,
plus optional predictive overlay and verifier/eval diagnostics.
"""

from __future__ import annotations

import math
import os
from collections import defaultdict, deque
from typing import Any, Dict, List, Set, Tuple

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore

try:
    from sklearn.cluster import DBSCAN  # type: ignore
except Exception:  # pragma: no cover
    DBSCAN = None  # type: ignore

try:
    import hdbscan  # type: ignore
except Exception:  # pragma: no cover
    hdbscan = None  # type: ignore

from src.services.mcc_predictive_overlay import build_predictive_overlay
from src.services.mcc_scc_graph import build_condensed_graph


def _path_dir(path: str) -> str:
    clean = str(path or "").replace("\\", "/").strip("/")
    if "/" not in clean:
        return "(root)"
    parent = os.path.dirname(clean).replace("\\", "/").strip("/")
    return parent or "(root)"


def _ancestors(path: str) -> List[str]:
    if path in ("", "(root)"):
        return []
    parts = [p for p in str(path).split("/") if p]
    out: List[str] = []
    cur = ""
    for part in parts:
        cur = f"{cur}/{part}" if cur else part
        out.append(cur)
    return out


def _depth(path: str) -> int:
    if path in ("", "(root)"):
        return 0
    return len([p for p in str(path).split("/") if p])


def _stable_text_vector(text: str, dim: int = 96) -> List[float]:
    """Deterministic fallback embedding when runtime embedder is unavailable."""
    import hashlib

    clean = (text or "").strip().lower()
    if not clean:
        return [0.0] * dim
    vec = [0.0] * dim
    tokens = [t for t in clean.replace("\\", "/").replace("_", "/").replace("-", "/").split("/") if t]
    if not tokens:
        tokens = [clean]
    for tok in tokens:
        h = hashlib.md5(tok.encode("utf-8")).hexdigest()
        for i in range(0, min(len(h), dim * 2), 2):
            idx = (i // 2) % dim
            val = int(h[i : i + 2], 16) / 255.0
            vec[idx] += (val - 0.5)
    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 1e-9:
        return vec
    return [v / norm for v in vec]


def _embed_texts(texts: List[str]) -> Tuple[List[List[float]], str]:
    """
    Vectorize text labels for clustering/prediction.
    Prefers runtime embedding service, falls back to deterministic vectors.
    """
    if not texts:
        return [], "none"

    vectors: List[List[float]] = []
    model_name = "deterministic_fallback"

    get_embedding = None
    try:
        from src.utils.embedding_service import get_embedding as _get_embedding  # type: ignore
        get_embedding = _get_embedding
        model_name = "embedding_service"
    except Exception:
        get_embedding = None

    # Keep dimensions bounded for fast DAG generation.
    target_dim = 128
    for text in texts:
        if get_embedding is not None:
            try:
                emb = get_embedding(text)
                if emb and isinstance(emb, list):
                    if len(emb) >= target_dim:
                        v = [float(x) for x in emb[:target_dim]]
                    else:
                        v = [float(x) for x in emb] + [0.0] * (target_dim - len(emb))
                    norm = math.sqrt(sum(x * x for x in v))
                    if norm > 1e-9:
                        vectors.append([x / norm for x in v])
                        continue
            except Exception:
                pass
        vectors.append(_stable_text_vector(text, dim=target_dim))

    return vectors, model_name


def _whiten_vectors(vectors: List[List[float]]) -> Tuple[List[List[float]], Dict[str, Any]]:
    """
    Tao-inspired whitening pass before clustering.
    Uses eigendecomposition on covariance with stable fallback.
    """
    if np is None or not vectors:
        return vectors, {"enabled": False, "reason": "numpy_unavailable_or_empty"}

    X = np.array(vectors, dtype=float)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    X = np.clip(X, -10.0, 10.0)
    n, d = X.shape
    if n < 3 or d < 2:
        return vectors, {"enabled": False, "reason": "insufficient_shape", "n": int(n), "d": int(d)}

    Xc = X - X.mean(axis=0, keepdims=True)
    Xc = np.nan_to_num(Xc, nan=0.0, posinf=0.0, neginf=0.0)
    try:
        with np.errstate(all="ignore"):
            cov = (Xc.T @ Xc) / max(1, n - 1)
        cov = np.nan_to_num(cov, nan=0.0, posinf=0.0, neginf=0.0)
        vals, vecs = np.linalg.eigh(cov)
        order = np.argsort(vals)[::-1]
        vals = vals[order]
        vecs = vecs[:, order]
        # Keep principal directions explaining ~95% variance.
        vals_clip = np.maximum(vals, 1e-9)
        total = float(vals_clip.sum())
        if total <= 1e-9:
            return vectors, {"enabled": False, "reason": "zero_variance"}
        cumulative = np.cumsum(vals_clip) / total
        keep = int(np.searchsorted(cumulative, 0.95) + 1)
        keep = max(4, min(keep, min(d, 96)))
        proj = vecs[:, :keep]
        scaled = np.diag(1.0 / np.sqrt(vals_clip[:keep] + 1e-6))
        with np.errstate(all="ignore"):
            Xw = Xc @ proj @ scaled
        Xw = np.nan_to_num(Xw, nan=0.0, posinf=0.0, neginf=0.0)
        return Xw.tolist(), {
            "enabled": True,
            "n_components": int(keep),
            "variance_retained": float(cumulative[keep - 1]),
        }
    except Exception as e:
        return vectors, {"enabled": False, "reason": f"whiten_failed:{e.__class__.__name__}"}


def _cluster_vectors(vectors: List[List[float]]) -> Tuple[List[int], Dict[str, Any]]:
    """
    Cluster directory embeddings for architecture branches.
    Prefers HDBSCAN, falls back to DBSCAN/quantile bins.
    """
    n = len(vectors)
    if n == 0:
        return [], {"method": "none", "clusters": 0}
    if n <= 3 or np is None:
        return list(range(n)), {"method": "identity", "clusters": n}

    X = np.array(vectors, dtype=float)

    if hdbscan is not None:
        try:
            min_cluster_size = max(2, int(round(math.sqrt(n))))
            model = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, min_samples=1, metric="euclidean")
            labels = model.fit_predict(X).tolist()
            non_noise = sorted({int(x) for x in labels if int(x) >= 0})
            if non_noise:
                return labels, {
                    "method": "hdbscan",
                    "clusters": len(non_noise),
                    "noise": int(sum(1 for x in labels if int(x) < 0)),
                    "min_cluster_size": min_cluster_size,
                }
        except Exception:
            pass

    if DBSCAN is not None:
        try:
            model = DBSCAN(eps=1.25, min_samples=2, metric="euclidean")
            labels = model.fit_predict(X).tolist()
            non_noise = sorted({int(x) for x in labels if int(x) >= 0})
            if non_noise:
                return labels, {
                    "method": "dbscan",
                    "clusters": len(non_noise),
                    "noise": int(sum(1 for x in labels if int(x) < 0)),
                }
        except Exception:
            pass

    # Quantile fallback on first component (deterministic equitable bins).
    x = X[:, 0]
    k = max(2, min(8, int(round(math.sqrt(n)))))
    order = np.argsort(x)
    labels = [-1] * n
    for rank, idx in enumerate(order.tolist()):
        labels[idx] = min(k - 1, int(rank * k / max(1, n)))
    return labels, {"method": "quantile_fallback", "clusters": k}


def _assign_equitable_buckets(nodes: List[Dict[str, Any]]) -> None:
    """
    Discrepancy/equitable-coloring style balancing:
    spread nodes within each layer across row buckets to avoid rail effect.
    """
    by_layer: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for n in nodes:
        by_layer[int(n.get("layer", 0))].append(n)

    for layer, layer_nodes in by_layer.items():
        if not layer_nodes:
            continue
        target_buckets = max(1, min(8, int(math.ceil(len(layer_nodes) / 10))))
        loads = [0 for _ in range(target_buckets)]

        # Interleave clusters to reduce local concentration.
        sorted_nodes = sorted(
            layer_nodes,
            key=lambda n: (
                int((n.get("metadata") or {}).get("cluster_id", -1)),
                -int(n.get("members_count", 0)),
                str(n.get("label", "")),
            ),
        )
        for n in sorted_nodes:
            cluster_id = int((n.get("metadata") or {}).get("cluster_id", -1))
            # Prefer lightest bucket; slight jitter by cluster for spread.
            candidate = sorted(
                range(target_buckets),
                key=lambda b: (loads[b], abs((cluster_id % target_buckets) - b)),
            )[0]
            loads[candidate] += 1
            n.setdefault("metadata", {})["rank_bucket"] = int(candidate)
            n["metadata"]["bucket_count"] = int(target_buckets)
            n["metadata"]["layer_index"] = int(layer)


def _build_design_graph(base: Dict[str, Any], scope_root: str, max_nodes: int) -> Dict[str, Any]:
    """
    Build architecture-first design graph from L0 module facts.
    No fixed node-count hardcode; selection is budget/readability driven.
    """
    l0 = base.get("l0") or {}
    l0_nodes = list(l0.get("nodes") or [])
    l0_edges = list(l0.get("edges") or [])

    if not l0_nodes:
        # Fallback to existing overview/l2 when L0 is unexpectedly empty.
        overview = base.get("l2_overview") or {}
        nodes = list(overview.get("nodes") or [])
        edges = list(overview.get("edges") or [])
        if not nodes:
            l2 = base.get("l2") or {}
            nodes = list(l2.get("nodes") or [])
            edges = list(l2.get("edges") or [])
        nodes.sort(key=lambda n: (int(n.get("layer", 0)), str(n.get("label", ""))))
        edges.sort(key=lambda e: (str(e.get("source", "")), str(e.get("target", ""))))
        return {
            "nodes": [{**n, "state": "white"} for n in nodes],
            "edges": edges,
            "roots": list((base.get("l1") or {}).get("roots") or []),
            "source": "fallback_l2",
        }

    project_name = os.path.basename(os.path.abspath(scope_root)) or "project"
    root_key = "(root)"

    # Directory importance from file counts + inter-dir dependency activity.
    file_count: Dict[str, int] = defaultdict(int)
    children: Dict[str, Set[str]] = defaultdict(set)
    for n in l0_nodes:
        if str(n.get("kind")) != "module":
            continue
        p = str(n.get("path", ""))
        if not p:
            continue
        d = _path_dir(p)
        file_count[d] += 1
        for anc in _ancestors(d):
            file_count[anc] += 1
        for anc in _ancestors(d):
            par = os.path.dirname(anc).replace("\\", "/").strip("/") or root_key
            children[par].add(anc)
    file_count[root_key] += sum(1 for n in l0_nodes if str(n.get("kind")) == "module")

    l0_by_id = {str(n.get("id", "")): n for n in l0_nodes}
    dir_flow: Dict[Tuple[str, str], float] = defaultdict(float)
    flow_degree: Dict[str, int] = defaultdict(int)
    for e in l0_edges:
        src = str(e.get("source", ""))
        tgt = str(e.get("target", ""))
        src_node = l0_by_id.get(src)
        tgt_node = l0_by_id.get(tgt)
        if not src_node or not tgt_node:
            continue
        if str(src_node.get("kind")) != "module" or str(tgt_node.get("kind")) != "module":
            continue
        sd = _path_dir(str(src_node.get("path", "")))
        td = _path_dir(str(tgt_node.get("path", "")))
        if not sd or not td or sd == td:
            continue
        s_rank = (_depth(sd), sd)
        t_rank = (_depth(td), td)
        a, b = (sd, td) if s_rank <= t_rank else (td, sd)
        w = float(e.get("score", e.get("confidence", 0.6)))
        dir_flow[(a, b)] += w
        flow_degree[a] += 1
        flow_degree[b] += 1

    importance: Dict[str, float] = {}
    all_dirs = set(file_count.keys())
    for d in all_dirs:
        importance[d] = float(file_count.get(d, 0)) + 0.9 * float(flow_degree.get(d, 0))

    # Build clear hierarchy tiers instead of global soup.
    selected_dirs: Set[str] = {root_key}
    top_dirs_all = sorted([d for d in all_dirs if _depth(d) == 1], key=lambda d: (-importance.get(d, 0.0), d))
    # Keep architecture overview readable: limit only top-level fanout adaptively.
    total_budget = max(24, min(260, int(max_nodes * 0.9)))
    max_top_dirs = max(5, min(14, int(round(total_budget ** 0.42))))
    top_dirs = top_dirs_all[:max_top_dirs]
    for d in top_dirs:
        selected_dirs.add(d)

    # Adaptive expansion budget across level-2 and level-3 by readability.
    # No fixed-node hardcode: limits derived from scope budget and branch count.
    branch_count = max(1, len(top_dirs))
    lvl2_per_branch = max(2, min(10, int(math.sqrt(total_budget / branch_count)) + 1))
    lvl3_per_lvl2 = max(1, min(5, int(math.sqrt(lvl2_per_branch)) + 1))

    for top in top_dirs:
        lvl2_candidates = sorted(
            [d for d in all_dirs if _depth(d) == 2 and d.startswith(f"{top}/")],
            key=lambda d: (-importance.get(d, 0.0), d),
        )[:lvl2_per_branch]
        for d2 in lvl2_candidates:
            selected_dirs.add(d2)
            lvl3_candidates = sorted(
                [d for d in all_dirs if _depth(d) == 3 and d.startswith(f"{d2}/")],
                key=lambda d: (-importance.get(d, 0.0), d),
            )[:lvl3_per_lvl2]
            for d3 in lvl3_candidates:
                selected_dirs.add(d3)

    # Ensure budget cap while keeping topological layers.
    if len(selected_dirs) > total_budget:
        must_keep = {root_key, *top_dirs}
        ranked_rest = sorted(
            [d for d in selected_dirs if d not in must_keep],
            key=lambda d: (-importance.get(d, 0.0), _depth(d), d),
        )
        selected_dirs = set(must_keep)
        for d in ranked_rest:
            if len(selected_dirs) >= total_budget:
                break
            selected_dirs.add(d)
            for anc in _ancestors(d):
                if len(selected_dirs) >= total_budget:
                    break
                selected_dirs.add(anc)

    dir_list_sorted = sorted(selected_dirs, key=lambda x: (_depth(x), x))
    embed_inputs = [f"{d} | files={file_count.get(d,0)} | depth={_depth(d)}" for d in dir_list_sorted]
    dir_vectors, embed_model = _embed_texts(embed_inputs)
    white_vectors, whiten_stats = _whiten_vectors(dir_vectors)
    cluster_labels, cluster_stats = _cluster_vectors(white_vectors)

    cluster_by_dir: Dict[str, int] = {}
    for i, d in enumerate(dir_list_sorted):
        cluster_by_dir[d] = int(cluster_labels[i]) if i < len(cluster_labels) else -1

    # Add intermediate branch nodes to reduce root star-shape and improve topology readability.
    top_cluster_members: Dict[int, List[str]] = defaultdict(list)
    for d in top_dirs:
        cid = int(cluster_by_dir.get(d, -1))
        if cid >= 0:
            top_cluster_members[cid].append(d)
    active_clusters = {cid: members for cid, members in top_cluster_members.items() if len(members) >= 2}
    use_branch_layer = len(active_clusters) > 0
    branch_node_id: Dict[int, str] = {cid: f"branch:{cid}" for cid in active_clusters.keys()}

    nodes: List[Dict[str, Any]] = []
    # Root first.
    nodes.append(
        {
            "id": f"dir:{root_key}",
            "kind": "root",
            "label": f"{project_name} (root)",
            "layer": 0,
            "members_count": int(file_count.get(root_key, 0)),
            "state": "white",
            "metadata": {"parent": ""},
            "scc_size": 1,
        }
    )

    # Branch layer (cluster trunks).
    if use_branch_layer:
        for cid, members in sorted(active_clusters.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            anchor = sorted(members, key=lambda d: (-importance.get(d, 0.0), d))[0]
            trunk_name = anchor.split("/")[0] if anchor and "/" in anchor else anchor
            nodes.append(
                {
                    "id": branch_node_id[cid],
                    "kind": "group",
                    "label": f"{trunk_name}:branch",
                    "layer": 1,
                    "members_count": int(sum(file_count.get(m, 0) for m in members)),
                    "state": "white",
                    "metadata": {"parent": root_key, "cluster_id": int(cid), "is_branch": True},
                    "scc_size": 1,
                }
            )

    for d in dir_list_sorted:
        if d == root_key:
            continue
        nid = f"dir:{d}"
        label = d
        layer = _depth(d) + (1 if use_branch_layer else 0)
        kind = "folder"
        parent = os.path.dirname(d).replace("\\", "/").strip("/") or root_key
        nodes.append(
            {
                "id": nid,
                "kind": kind,
                "label": label,
                "layer": int(layer),
                "members_count": int(file_count.get(d, 0)),
                "state": "white",
                "metadata": {
                    "parent": parent,
                    "cluster_id": int(cluster_by_dir.get(d, -1)),
                },
                "scc_size": 1,
            }
        )

    _assign_equitable_buckets(nodes)

    selected_lookup = {n["id"] for n in nodes}
    by_dir = {d: f"dir:{d}" for d in selected_dirs}
    for cid, bid in branch_node_id.items():
        by_dir[f"branch:{cid}"] = bid

    # Base topology: tree edges only for primary view readability.
    edges: List[Dict[str, Any]] = []
    for d in selected_dirs:
        if d == root_key:
            continue
        raw_parent = os.path.dirname(d).replace("\\", "/").strip("/") or root_key
        parent = raw_parent
        if use_branch_layer and _depth(d) == 1:
            cid = int(cluster_by_dir.get(d, -1))
            if cid in branch_node_id:
                parent = branch_node_id[cid]
        s = by_dir.get(parent)
        t = by_dir.get(d)
        if not s or not t or s not in selected_lookup or t not in selected_lookup:
            continue
        edges.append(
            {
                "source": s,
                "target": t,
                "type": "structural",
                "score": 1.0,
                "confidence": 1.0,
            }
        )

    # Connect root to branch nodes.
    if use_branch_layer:
        root_id = f"dir:{root_key}"
        for cid, bid in branch_node_id.items():
            if bid not in selected_lookup:
                continue
            edges.append(
                {
                    "source": root_id,
                    "target": bid,
                    "type": "structural",
                    "score": 1.0,
                    "confidence": 1.0,
                }
            )

    # Build limited cross dependency edges for focus mode (not main topology).
    cross_edges: List[Dict[str, Any]] = []
    dep_by_source: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for (a, b), w in dir_flow.items():
        if a not in selected_dirs or b not in selected_dirs:
            continue
        sa = by_dir.get(a)
        sb = by_dir.get(b)
        if not sa or not sb or sa == sb:
            continue
        if _depth(a) >= _depth(b):
            continue
        dep_by_source[sa].append((sb, w))

    for src, arr in dep_by_source.items():
        limit = max(1, min(3, int(math.sqrt(len(arr)))))
        for tgt, w in sorted(arr, key=lambda x: (-x[1], x[0]))[:limit]:
            cross_edges.append(
                {
                    "source": src,
                    "target": tgt,
                    "type": "dependency",
                    "score": float(w),
                    "confidence": 0.68,
                }
            )

    # Deduplicate and sort.
    seen = set()
    dedup_edges: List[Dict[str, Any]] = []
    for e in edges:
        k = (str(e.get("source", "")), str(e.get("target", "")), str(e.get("type", "")))
        if k in seen:
            continue
        seen.add(k)
        dedup_edges.append(e)
    dedup_edges.sort(key=lambda e: (str(e.get("source", "")), str(e.get("target", "")), str(e.get("type", ""))))
    cross_edges.sort(key=lambda e: (str(e.get("source", "")), str(e.get("target", "")), -float(e.get("score", 0.0))))
    nodes.sort(key=lambda n: (int(n.get("layer", 0)), str(n.get("label", ""))))

    return {
        "nodes": nodes,
        "edges": dedup_edges,
        "cross_edges": cross_edges,
        "roots": [f"dir:{root_key}"],
        "source": "l0_directory_aggregated",
        "pipeline": {
            "embedding_model": embed_model,
            "whitening": whiten_stats,
            "clustering": cluster_stats,
            "techniques": [
                "tao_whitening",
                "hdbscan_or_fallback",
                "discrepancy_equitable_coloring",
            ],
        },
    }


def _is_acyclic(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> bool:
    node_ids = [str(n.get("id", "")) for n in nodes if n.get("id")]
    indeg: Dict[str, int] = {nid: 0 for nid in node_ids}
    succ: Dict[str, Set[str]] = {nid: set() for nid in node_ids}

    for e in edges:
        s = str(e.get("source", ""))
        t = str(e.get("target", ""))
        if s in succ and t in indeg and t not in succ[s]:
            succ[s].add(t)
            indeg[t] += 1

    q = deque(sorted([nid for nid, d in indeg.items() if d == 0]))
    seen = 0
    while q:
        cur = q.popleft()
        seen += 1
        for nxt in sorted(succ.get(cur, set())):
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                q.append(nxt)

    return seen == len(node_ids)


def _monotonic_layers(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> bool:
    layer = {str(n.get("id", "")): int(n.get("layer", 0)) for n in nodes if n.get("id")}
    for e in edges:
        s = str(e.get("source", ""))
        t = str(e.get("target", ""))
        if s in layer and t in layer and layer[s] >= layer[t]:
            return False
    return True


def _connected_components(node_ids: List[str], edges: List[Dict[str, Any]]) -> int:
    g: Dict[str, Set[str]] = {nid: set() for nid in node_ids}
    for e in edges:
        s = str(e.get("source", ""))
        t = str(e.get("target", ""))
        if s in g and t in g:
            g[s].add(t)
            g[t].add(s)

    seen: Set[str] = set()
    comp = 0
    for nid in node_ids:
        if nid in seen:
            continue
        comp += 1
        dq = deque([nid])
        seen.add(nid)
        while dq:
            cur = dq.popleft()
            for nxt in g.get(cur, set()):
                if nxt not in seen:
                    seen.add(nxt)
                    dq.append(nxt)
    return comp


def _spectral_metrics(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
    node_ids = [str(n.get("id", "")) for n in nodes if n.get("id")]
    n = len(node_ids)
    if n == 0:
        return {"lambda2": 0.0, "eigengap": 0.0, "component_count": 0, "status": "fail"}

    comp_count = _connected_components(node_ids, edges)

    if np is None:
        return {
            "lambda2": 0.0,
            "eigengap": 0.0,
            "component_count": int(comp_count),
            "status": "warn",
            "note": "numpy_unavailable",
        }

    # Keep dense eigendecomposition bounded and deterministic.
    max_n = 220
    if n > max_n:
        degree: Dict[str, int] = defaultdict(int)
        for e in edges:
            degree[str(e.get("source", ""))] += 1
            degree[str(e.get("target", ""))] += 1
        node_ids = sorted(node_ids, key=lambda nid: (-degree.get(nid, 0), nid))[:max_n]
        n = len(node_ids)

    idx = {nid: i for i, nid in enumerate(node_ids)}
    A = np.zeros((n, n), dtype=float)

    for e in edges:
        s = str(e.get("source", ""))
        t = str(e.get("target", ""))
        if s in idx and t in idx and s != t:
            i = idx[s]
            j = idx[t]
            A[i, j] = 1.0
            A[j, i] = 1.0

    D = np.diag(A.sum(axis=1))
    L = D - A

    try:
        vals = np.linalg.eigvalsh(L)
        vals = np.sort(vals)
        lambda2 = float(vals[1]) if len(vals) > 1 else 0.0
        lambda3 = float(vals[2]) if len(vals) > 2 else lambda2
        eigengap = max(0.0, lambda3 - lambda2)
    except Exception:
        return {
            "lambda2": 0.0,
            "eigengap": 0.0,
            "component_count": int(comp_count),
            "status": "warn",
            "note": "spectral_compute_failed",
        }

    status = "ok"
    if comp_count > 2 or lambda2 < 1e-6:
        status = "warn"
    if comp_count > 5:
        status = "fail"

    return {
        "lambda2": float(lambda2),
        "eigengap": float(eigengap),
        "component_count": int(comp_count),
        "status": status,
    }


def _verifier_report(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
    node_ids = [str(n.get("id", "")) for n in nodes if n.get("id")]
    n = len(node_ids)
    m = len(edges)

    outdeg: Dict[str, int] = defaultdict(int)
    indeg: Dict[str, int] = defaultdict(int)
    for e in edges:
        s = str(e.get("source", ""))
        t = str(e.get("target", ""))
        outdeg[s] += 1
        indeg[t] += 1

    orphans = sum(1 for nid in node_ids if outdeg.get(nid, 0) + indeg.get(nid, 0) == 0)
    orphan_rate = float(orphans / n) if n else 1.0
    density = float(m / (n * (n - 1))) if n > 1 else 0.0
    avg_out_degree = float(sum(outdeg.values()) / n) if n else 0.0

    acyclic = _is_acyclic(nodes, edges)
    monotonic = _monotonic_layers(nodes, edges)
    spectral = _spectral_metrics(nodes, edges)

    decision = "pass"
    if (not acyclic) or (not monotonic) or spectral.get("status") == "fail":
        decision = "fail"
    elif orphan_rate > 0.35 or spectral.get("status") == "warn":
        decision = "warn"

    return {
        "acyclic": bool(acyclic),
        "monotonic_layers": bool(monotonic),
        "orphan_rate": float(orphan_rate),
        "density": float(density),
        "avg_out_degree": float(avg_out_degree),
        "spectral": spectral,
        "decision": decision,
    }


def _safe_path_fragment(raw: Any, fallback: str) -> str:
    base = str(raw or fallback).strip().replace("\\", "/")
    base = base.replace(" ", "_")
    parts = [p for p in base.split("/") if p and p not in (".", "..")]
    clean = "/".join(parts)
    if not clean:
        return fallback
    return clean


def _record_text_signature(rec: Dict[str, Any]) -> str:
    tags = rec.get("tags")
    if isinstance(tags, list):
        tags_s = " ".join(str(t) for t in tags[:8])
    else:
        tags_s = ""
    return " | ".join(
        [
            str(rec.get("label") or rec.get("name") or rec.get("title") or ""),
            str(rec.get("path") or rec.get("module") or rec.get("file_path") or ""),
            str(rec.get("type") or rec.get("kind") or rec.get("group") or ""),
            tags_s,
        ]
    ).strip()


def _normalize_array_records_to_l0(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    MARKER_155.ARCHITECT_BUILD.ARRAY_CORE.V1:
    Normalize arbitrary array records into L0 module-like payload expected by design builder.
    """
    out: List[Dict[str, Any]] = []
    for idx, raw in enumerate(records):
        rec = raw if isinstance(raw, dict) else {}
        rid = str(
            rec.get("id")
            or rec.get("uuid")
            or rec.get("key")
            or f"arr_{idx}"
        )
        label = str(rec.get("label") or rec.get("name") or rec.get("title") or rid)
        group = str(rec.get("group") or rec.get("type") or rec.get("kind") or "items")
        raw_path = rec.get("path") or rec.get("file_path") or rec.get("module") or rec.get("filepath") or ""
        if raw_path:
            path = _safe_path_fragment(raw_path, fallback=f"{group}/{label}")
        else:
            path = _safe_path_fragment(f"{group}/{label}", fallback=f"items/{rid}")
        out.append(
            {
                "id": rid,
                "kind": "module",
                "path": path,
                "label": label,
                "score": float(rec.get("score", 0.6) or 0.6),
                "metadata": {
                    "source": "array_record",
                    "group": group,
                    "record_index": idx,
                },
            }
        )
    return out


def _infer_l0_edges_from_records(records: List[Dict[str, Any]], l0_nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    MARKER_155.ARCHITECT_BUILD.ARRAY_INFER_EDGES.V1:
    Deterministic fallback edge inference for array inputs with missing relation graph.
    """
    if len(l0_nodes) <= 1:
        return []
    ids = [str(n.get("id", "")) for n in l0_nodes]
    by_id = {str(n.get("id", "")): n for n in l0_nodes}
    signatures = [_record_text_signature(rec if isinstance(rec, dict) else {}) for rec in records]
    vectors, _ = _embed_texts(signatures)
    if not vectors or len(vectors) != len(ids):
        # Stable chain fallback keeps graph connected and acyclic.
        edges: List[Dict[str, Any]] = []
        for i in range(len(ids) - 1):
            edges.append(
                {
                    "source": ids[i],
                    "target": ids[i + 1],
                    "type": "depends_on",
                    "score": 0.58,
                    "confidence": 0.58,
                }
            )
        return edges

    arr = np.array(vectors, dtype=float) if np is not None else None
    edges_out: List[Dict[str, Any]] = []
    if arr is None:
        return edges_out

    # Cosine similarity from normalized vectors = dot product.
    sims = arr @ arr.T
    per_src_limit = max(1, min(3, int(math.sqrt(len(ids)))))
    min_sim = 0.55
    for i, src in enumerate(ids):
        candidates: List[Tuple[str, float]] = []
        for j, tgt in enumerate(ids):
            if i == j:
                continue
            sim = float(sims[i, j])
            if sim < min_sim:
                continue
            s_node = by_id.get(src) or {}
            t_node = by_id.get(tgt) or {}
            sp = str(s_node.get("path", ""))
            tp = str(t_node.get("path", ""))
            # Keep inferred relations acyclic by stable rank order.
            s_rank = (_depth(_path_dir(sp)), sp, src)
            t_rank = (_depth(_path_dir(tp)), tp, tgt)
            if s_rank >= t_rank:
                continue
            candidates.append((tgt, sim))
        for tgt, sim in sorted(candidates, key=lambda x: (-x[1], x[0]))[:per_src_limit]:
            edges_out.append(
                {
                    "source": src,
                    "target": tgt,
                    "type": "depends_on",
                    "score": sim,
                    "confidence": max(0.55, min(0.9, sim)),
                }
            )
    return edges_out


def _runtime_graph_from_arrays(
    records: List[Dict[str, Any]],
    relations: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    MARKER_155.ARCHITECT_BUILD.ARRAY_RUNTIME_BRIDGE.V1:
    Build minimal runtime graph shape compatible with _build_design_graph from arbitrary arrays.
    """
    l0_nodes = _normalize_array_records_to_l0(records)
    id_set = {str(n.get("id", "")) for n in l0_nodes}
    l0_edges: List[Dict[str, Any]] = []

    for rel in relations:
        if not isinstance(rel, dict):
            continue
        s = str(rel.get("source") or rel.get("from") or "")
        t = str(rel.get("target") or rel.get("to") or "")
        if not s or not t or s == t or s not in id_set or t not in id_set:
            continue
        l0_edges.append(
            {
                "source": s,
                "target": t,
                "type": str(rel.get("type") or rel.get("relation") or "depends_on"),
                "score": float(rel.get("score", rel.get("confidence", 0.62)) or 0.62),
                "confidence": float(rel.get("confidence", rel.get("score", 0.62)) or 0.62),
            }
        )

    if not l0_edges:
        l0_edges = _infer_l0_edges_from_records(records, l0_nodes)

    signature_seed = "|".join(sorted(str(n.get("path", "")) for n in l0_nodes))
    signature = f"array:{len(l0_nodes)}:{abs(hash(signature_seed)) % 10_000_000}"
    return {
        "signature": signature,
        "stats": {
            "node_count": len(l0_nodes),
            "edge_count": len(l0_edges),
            "source": "array_runtime_bridge",
        },
        "l0": {
            "nodes": l0_nodes,
            "edges": l0_edges,
        },
        "l1": {"roots": ["(root)"]},
        "l2": {"nodes": [], "edges": []},
        "l2_overview": {"nodes": [], "edges": []},
    }


def build_design_dag(
    scope_root: str,
    max_nodes: int = 600,
    include_artifacts: bool = False,
    problem_statement: str = "",
    target_outcome: str = "",
    use_predictive_overlay: bool = True,
    max_predicted_edges: int = 120,
    min_confidence: float = 0.55,
) -> Dict[str, Any]:
    """
    Build architecture Design DAG package for Architect flow.

    Returns runtime graph, design graph, optional predictive overlay,
    and verifier/eval diagnostics.
    """
    scope_root = os.path.abspath(os.path.expanduser(scope_root))
    if not os.path.isdir(scope_root):
        raise ValueError(f"Invalid scope root: {scope_root}")

    max_nodes = max(50, min(int(max_nodes), 5000))
    max_predicted_edges = max(0, min(int(max_predicted_edges), 2000))
    min_confidence = max(0.0, min(float(min_confidence), 0.99))

    runtime_graph = build_condensed_graph(
        scope_root=scope_root,
        max_nodes=max_nodes,
        include_artifacts=include_artifacts,
    )

    design_graph = _build_design_graph(runtime_graph, scope_root=scope_root, max_nodes=max_nodes)

    overlay = {
        "predicted_edges": [],
        "stats": {
            "predicted_edges": 0,
            "enabled": False,
        },
        "markers": ["MARKER_155.ARCHITECT_BUILD.JEPA_OVERLAY.V1"],
    }

    if use_predictive_overlay:
        overlay = build_predictive_overlay(
            scope_root=scope_root,
            max_nodes=max_nodes,
            max_predicted_edges=max_predicted_edges,
            include_artifacts=include_artifacts,
            min_confidence=min_confidence,
        )

    verifier = _verifier_report(design_graph["nodes"], design_graph["edges"])

    return {
        "scope_root": scope_root,
        "architect_context": {
            "problem_statement": (problem_statement or "").strip(),
            "target_outcome": (target_outcome or "").strip(),
        },
        "runtime_graph": {
            "signature": runtime_graph.get("signature", ""),
            "stats": runtime_graph.get("stats", {}),
            "l1": runtime_graph.get("l1", {}),
            "l2": runtime_graph.get("l2", {}),
            "l2_overview": runtime_graph.get("l2_overview", {}),
        },
        "design_graph": design_graph,
        "predictive_overlay": overlay,
        "verifier": verifier,
        "markers": [
            "MARKER_155.ARCHITECT_BUILD.CONTRACT.V1",
            "MARKER_155.ARCHITECT_BUILD.VERIFIER.V1",
            "MARKER_155.ARCHITECT_BUILD.JEPA_OVERLAY.V1",
        ],
    }


def build_design_dag_from_arrays(
    records: List[Dict[str, Any]],
    relations: List[Dict[str, Any]] | None = None,
    scope_name: str = "array_scope",
    max_nodes: int = 600,
    use_predictive_overlay: bool = False,
    max_predicted_edges: int = 120,
    min_confidence: float = 0.55,
) -> Dict[str, Any]:
    """
    MARKER_155.ARCHITECT_BUILD.ARRAY_CORE.V1
    Working core for algorithmic offload:
    transforms arbitrary data arrays into architecture-style Design DAG package.

    Future marker:
    - MARKER_155.ARCHITECT_BUILD.ARRAY_CORE.V2_POLICY
      TODO: pluggable schema adapters + policy-driven edge arbitration.
    """
    records = [r for r in (records or []) if isinstance(r, dict)]
    relations = [r for r in (relations or []) if isinstance(r, dict)]
    if not records:
        raise ValueError("records array is empty")

    max_nodes = max(50, min(int(max_nodes), 5000))
    max_predicted_edges = max(0, min(int(max_predicted_edges), 2000))
    min_confidence = max(0.0, min(float(min_confidence), 0.99))

    runtime_graph = _runtime_graph_from_arrays(records, relations)
    design_graph = _build_design_graph(runtime_graph, scope_root=scope_name, max_nodes=max_nodes)

    overlay = {
        "predicted_edges": [],
        "stats": {"predicted_edges": 0, "enabled": False},
        "markers": ["MARKER_155.ARCHITECT_BUILD.JEPA_OVERLAY.V1"],
    }
    if use_predictive_overlay:
        # For array core we keep JEPA optional and non-blocking.
        try:
            overlay = build_predictive_overlay(
                scope_root=scope_name,
                max_nodes=max_nodes,
                max_predicted_edges=max_predicted_edges,
                include_artifacts=False,
                min_confidence=min_confidence,
            )
        except Exception:
            overlay = {
                "predicted_edges": [],
                "stats": {"predicted_edges": 0, "enabled": False, "detail": "overlay_unavailable"},
                "markers": ["MARKER_155.ARCHITECT_BUILD.JEPA_OVERLAY.V1"],
            }

    verifier = _verifier_report(design_graph["nodes"], design_graph["edges"])
    return {
        "scope_root": scope_name,
        "architect_context": {
            "problem_statement": "",
            "target_outcome": "",
        },
        "runtime_graph": {
            "signature": runtime_graph.get("signature", ""),
            "stats": runtime_graph.get("stats", {}),
            "l0": runtime_graph.get("l0", {}),
            "l1": runtime_graph.get("l1", {}),
            "l2": runtime_graph.get("l2", {}),
            "l2_overview": runtime_graph.get("l2_overview", {}),
        },
        "design_graph": design_graph,
        "predictive_overlay": overlay,
        "verifier": verifier,
        "markers": [
            "MARKER_155.ARCHITECT_BUILD.CONTRACT.V1",
            "MARKER_155.ARCHITECT_BUILD.ARRAY_CORE.V1",
            "MARKER_155.ARCHITECT_BUILD.VERIFIER.V1",
            "MARKER_155.ARCHITECT_BUILD.JEPA_OVERLAY.V1",
        ],
    }
