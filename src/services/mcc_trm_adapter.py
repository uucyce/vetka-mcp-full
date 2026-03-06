"""
MARKER_161.TRM.ADAPTER.ENTRY.V1
Phase-161 W2 TRM adapter skeleton.

Adapter responsibilities in W2:
- deterministic feature bridge from runtime/design graphs
- deterministic candidate generation (no topology mutation)
- graceful degradation to no-op payload
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Tuple

from src.services.mcc_trm_config import resolve_trm_policy


def _stable_score(seed: int, *parts: str) -> float:
    raw = "|".join([str(seed)] + [str(p) for p in parts])
    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return int(h[:8], 16) / float(0xFFFFFFFF)


def _safe_nodes(design_graph: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [dict(n) for n in (design_graph.get("nodes") or []) if isinstance(n, dict)]


def _safe_edges(design_graph: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for e in (design_graph.get("edges") or []):
        if not isinstance(e, dict):
            continue
        s = str(e.get("source") or "").strip()
        t = str(e.get("target") or "").strip()
        if s and t and s != t:
            out.append({"source": s, "target": t, **e})
    return out


def _feature_bridge(
    runtime_graph: Dict[str, Any],
    design_graph: Dict[str, Any],
) -> Dict[str, Any]:
    """
    MARKER_161.TRM.ADAPTER.FEATURE_BRIDGE.V1
    """
    nodes = _safe_nodes(design_graph)
    edges = _safe_edges(design_graph)
    node_ids = {str(n.get("id") or "") for n in nodes}

    indeg = {nid: 0 for nid in node_ids}
    outdeg = {nid: 0 for nid in node_ids}
    for e in edges:
        s = str(e["source"])
        t = str(e["target"])
        if s in outdeg:
            outdeg[s] += 1
        if t in indeg:
            indeg[t] += 1

    layers = [int(n.get("layer", 0) or 0) for n in nodes]
    roots = [nid for nid in node_ids if indeg.get(nid, 0) == 0]
    leaves = [nid for nid in node_ids if outdeg.get(nid, 0) == 0]

    return {
        "runtime_signature": str(runtime_graph.get("signature") or ""),
        "runtime_stats": dict(runtime_graph.get("stats") or {}),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "layer_span": {
            "min": min(layers) if layers else 0,
            "max": max(layers) if layers else 0,
        },
        "root_count": len(roots),
        "leaf_count": len(leaves),
        "indegree": indeg,
        "outdegree": outdeg,
        "roots": sorted(roots),
        "leaves": sorted(leaves),
    }


def _candidate_edges(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    indeg: Dict[str, int],
    outdeg: Dict[str, int],
    seed: int,
    max_candidate_edges: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    existing = {(str(e["source"]), str(e["target"])) for e in edges}
    node_by_id = {str(n.get("id") or ""): n for n in nodes if str(n.get("id") or "")}

    rerank_raw: List[Dict[str, Any]] = []
    for e in edges:
        s = str(e["source"])
        t = str(e["target"])
        src_layer = int((node_by_id.get(s) or {}).get("layer", 0) or 0)
        dst_layer = int((node_by_id.get(t) or {}).get("layer", 0) or 0)
        layer_bonus = 1.0 if src_layer < dst_layer else 0.0
        degree_bonus = float(outdeg.get(s, 0) + indeg.get(t, 0))
        hash_bonus = _stable_score(seed, "rerank", s, t)
        confidence = min(0.99, max(0.05, 0.2 + 0.12 * layer_bonus + 0.03 * degree_bonus + 0.4 * hash_bonus))
        rerank_raw.append(
            {
                "source": s,
                "target": t,
                "confidence": round(confidence, 6),
                "kind": "edge_rerank",
                "reason": "structural_priority",
            }
        )

    rerank = sorted(rerank_raw, key=lambda r: (-float(r["confidence"]), r["source"], r["target"]))[
        : max(0, min(len(rerank_raw), max_candidate_edges))
    ]

    insertion_limit = max(0, min(max_candidate_edges, 64))
    by_layer = sorted(
        [
            (
                str(n.get("id") or ""),
                int(n.get("layer", 0) or 0),
                int(outdeg.get(str(n.get("id") or ""), 0)),
                int(indeg.get(str(n.get("id") or ""), 0)),
            )
            for n in nodes
            if str(n.get("id") or "")
        ],
        key=lambda row: (-row[2], row[3], row[1], row[0]),
    )
    top = by_layer[: min(28, len(by_layer))]

    inserts_raw: List[Dict[str, Any]] = []
    for s_id, s_layer, _, _ in top:
        for t_id, t_layer, _, _ in top:
            if s_id == t_id:
                continue
            if s_layer >= t_layer:
                continue
            if (s_id, t_id) in existing:
                continue
            affinity = _stable_score(seed, "insert", s_id, t_id)
            if affinity < 0.82:
                continue
            inserts_raw.append(
                {
                    "source": s_id,
                    "target": t_id,
                    "confidence": round(min(0.99, max(0.05, affinity)), 6),
                    "kind": "edge_insertion",
                    "reason": "cross_branch_affinity",
                }
            )

    inserts = sorted(inserts_raw, key=lambda r: (-float(r["confidence"]), r["source"], r["target"]))[
        :insertion_limit
    ]
    return rerank, inserts


def _candidate_node_adjustments(
    nodes: List[Dict[str, Any]],
    indeg: Dict[str, int],
    outdeg: Dict[str, int],
    seed: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    node_ids = [str(n.get("id") or "") for n in nodes if str(n.get("id") or "")]
    rank_adjustments: List[Dict[str, Any]] = []
    for nid in sorted(node_ids):
        priority = _stable_score(seed, "rank", nid)
        if priority < 0.75:
            continue
        rank_adjustments.append(
            {
                "node_id": nid,
                "priority": round(priority, 6),
                "kind": "rank_adjustment",
                "reason": "layout_readability",
            }
        )
    rank_adjustments = sorted(rank_adjustments, key=lambda r: (-float(r["priority"]), str(r["node_id"])))[:24]

    roots = [nid for nid in node_ids if indeg.get(nid, 0) == 0]
    root_adjustments: List[Dict[str, Any]] = []
    if not roots:
        fallback = sorted(node_ids, key=lambda nid: (-int(outdeg.get(nid, 0)), int(indeg.get(nid, 0)), nid))
        if fallback:
            root_adjustments.append(
                {
                    "node_id": fallback[0],
                    "action": "promote_root",
                    "confidence": 0.66,
                    "kind": "root_adjustment",
                    "reason": "no_explicit_root_found",
                }
            )
    else:
        for rid in sorted(roots):
            confidence = _stable_score(seed, "root", rid)
            root_adjustments.append(
                {
                    "node_id": rid,
                    "action": "keep_root",
                    "confidence": round(confidence, 6),
                    "kind": "root_adjustment",
                    "reason": "existing_root_stability",
                }
            )
        root_adjustments = sorted(root_adjustments, key=lambda r: (-float(r["confidence"]), str(r["node_id"])))[:8]

    return rank_adjustments, root_adjustments


def propose_trm_candidates(
    runtime_graph: Dict[str, Any],
    design_graph: Dict[str, Any],
    trm_profile: str = "off",
    trm_policy: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    MARKER_161.TRM.ADAPTER.ENTRY.V1
    MARKER_161.TRM.ADAPTER.CANDIDATES.V1
    """
    policy = resolve_trm_policy(trm_profile=trm_profile, trm_policy=trm_policy or {})
    markers = [
        "MARKER_161.TRM.ADAPTER.ENTRY.V1",
        "MARKER_161.TRM.ADAPTER.FEATURE_BRIDGE.V1",
        "MARKER_161.TRM.ADAPTER.CANDIDATES.V1",
    ]
    try:
        features = _feature_bridge(runtime_graph=runtime_graph, design_graph=design_graph)
        nodes = _safe_nodes(design_graph)
        edges = _safe_edges(design_graph)
        indeg = dict(features.get("indegree") or {})
        outdeg = dict(features.get("outdegree") or {})

        if not bool(policy.get("enabled")):
            return {
                "status": "disabled",
                "profile": str(policy.get("profile") or "off"),
                "policy": policy,
                "features": features,
                "candidates": {
                    "edge_rerank": [],
                    "edge_insertions": [],
                    "node_rank_adjustments": [],
                    "root_adjustments": [],
                },
                "accepted_count": 0,
                "markers": markers,
            }

        seed = int(policy.get("seed") or 42)
        max_candidate_edges = int(policy.get("max_candidate_edges") or 0)
        rerank, insertions = _candidate_edges(
            nodes=nodes,
            edges=edges,
            indeg=indeg,
            outdeg=outdeg,
            seed=seed,
            max_candidate_edges=max_candidate_edges,
        )
        rank_adjustments, root_adjustments = _candidate_node_adjustments(
            nodes=nodes,
            indeg=indeg,
            outdeg=outdeg,
            seed=seed,
        )
        return {
            "status": "ready",
            "profile": str(policy.get("profile") or "off"),
            "policy": policy,
            "features": features,
            "candidates": {
                "edge_rerank": rerank,
                "edge_insertions": insertions,
                "node_rank_adjustments": rank_adjustments,
                "root_adjustments": root_adjustments,
            },
            "accepted_count": int(len(rerank) + len(insertions) + len(rank_adjustments) + len(root_adjustments)),
            "markers": markers,
        }
    except Exception as exc:
        return {
            "status": "degraded",
            "profile": str(policy.get("profile") or "off"),
            "policy": policy,
            "features": {},
            "candidates": {
                "edge_rerank": [],
                "edge_insertions": [],
                "node_rank_adjustments": [],
                "root_adjustments": [],
            },
            "accepted_count": 0,
            "error": f"{exc.__class__.__name__}: {exc}",
            "markers": markers,
        }

