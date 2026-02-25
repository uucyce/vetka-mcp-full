"""
MARKER_155.MODE_ARCH.V11.P15: Predictive overlay service.

Hybrid predictor over L2 SCC DAG:
- topology priors (layer progression, parent affinity)
- path token similarity
- vector similarity from runtime embeddings (JEPA-compatible channel)
"""

from __future__ import annotations

import hashlib
import os
import time
from collections import defaultdict
from typing import Any, Dict, List, Set, Tuple
import math

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore

from src.services.mcc_scc_graph import build_condensed_graph
from src.services.mcc_jepa_adapter import embed_texts_for_overlay


_overlay_cache: Dict[str, Any] = {
    "key": "",
    "result": None,
    "ts": 0.0,
}


def _path_tokens(path: str) -> Set[str]:
    clean = (path or "").replace("\\", "/")
    return {t for t in clean.split("/") if t}


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    if union <= 0:
        return 0.0
    return inter / union


def _existing_edge_set(edges: List[Dict[str, Any]]) -> Set[Tuple[str, str]]:
    return {(e.get("source", ""), e.get("target", "")) for e in edges}


def _extract_parent_hint(node: Dict[str, Any]) -> str:
    meta = node.get("metadata") or {}
    return str(meta.get("parent", "") or "")


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    if np is not None:
        aa = np.array(a, dtype=float)
        bb = np.array(b, dtype=float)
        den = (np.linalg.norm(aa) * np.linalg.norm(bb))
        if den <= 1e-12:
            return 0.0
        return float(np.dot(aa, bb) / den)
    num = sum(x * y for x, y in zip(a, b))
    da = math.sqrt(sum(x * x for x in a))
    db = math.sqrt(sum(x * x for x in b))
    den = da * db
    if den <= 1e-12:
        return 0.0
    return float(num / den)


def build_predictive_overlay(
    scope_root: str,
    max_nodes: int = 600,
    max_predicted_edges: int = 120,
    include_artifacts: bool = False,
    min_confidence: float = 0.55,
    focus_node_ids: List[str] | None = None,
    jepa_provider: str = "",
    jepa_runtime_module: str = "",
    jepa_strict: bool = False,
) -> Dict[str, Any]:
    """
    Build deterministic predictive edge overlay from the condensed graph.

    Output contract mirrors future JEPA output:
    - predicted_edges with confidence + evidence + mode_layer
    - does not mutate base graph
    """
    scope_root = os.path.abspath(os.path.expanduser(scope_root))
    base = build_condensed_graph(
        scope_root=scope_root,
        max_nodes=max_nodes,
        include_artifacts=include_artifacts,
    )

    cache_key = (
        f"{base.get('signature','')}|{max_nodes}|{max_predicted_edges}|"
        f"{int(include_artifacts)}|{min_confidence:.3f}|"
        f"{','.join(sorted(set(focus_node_ids or [])))}|"
        f"{(jepa_provider or '').strip().lower()}|{(jepa_runtime_module or '').strip()}"
        f"|{1 if bool(jepa_strict) else 0}"
    )
    if _overlay_cache.get("key") == cache_key and _overlay_cache.get("result") is not None:
        return _overlay_cache["result"]

    nodes = base.get("l2", {}).get("nodes", [])
    edges = base.get("l2", {}).get("edges", [])
    existing = _existing_edge_set(edges)

    by_layer: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    node_by_id: Dict[str, Dict[str, Any]] = {}
    token_map: Dict[str, Set[str]] = {}

    for n in nodes:
        nid = str(n.get("id", ""))
        if not nid:
            continue
        layer = int(n.get("layer", 0))
        by_layer[layer].append(n)
        node_by_id[nid] = n

        members = n.get("members") or []
        path_hint = members[0] if members else _extract_parent_hint(n)
        token_map[nid] = _path_tokens(path_hint)

    # Build JEPA adapter channel.
    node_ids: List[str] = []
    node_texts: List[str] = []
    for n in nodes:
        nid = str(n.get("id", ""))
        if not nid:
            continue
        members = n.get("members") or []
        path_hint = members[0] if members else _extract_parent_hint(n)
        label = str(n.get("label", ""))
        node_ids.append(nid)
        node_texts.append(f"{label} | {path_hint}")
    adapter_result = embed_texts_for_overlay(
        node_texts,
        target_dim=128,
        provider_override=(jepa_provider or "").strip() or None,
        runtime_module_override=(jepa_runtime_module or "").strip() or None,
        strict_runtime=bool(jepa_strict),
    )
    text_vectors = adapter_result.vectors
    vector_model = adapter_result.provider_mode
    vec_by_id: Dict[str, List[float]] = {
        nid: text_vectors[i] for i, nid in enumerate(node_ids) if i < len(text_vectors)
    }

    candidates: List[Dict[str, Any]] = []
    focus_ids: Set[str] = {str(x) for x in (focus_node_ids or []) if str(x)}

    # Predict causal continuation from layer k -> k+1 using token overlap + parent affinity.
    for layer in sorted(by_layer.keys()):
        current = by_layer[layer]
        nxt = by_layer.get(layer + 1, [])
        if not current or not nxt:
            continue

        for src in current:
            src_id = str(src.get("id", ""))
            src_parent = _extract_parent_hint(src)
            src_tokens = token_map.get(src_id, set())
            if not src_id:
                continue

            for dst in nxt:
                dst_id = str(dst.get("id", ""))
                if not dst_id or dst_id == src_id:
                    continue
                if (src_id, dst_id) in existing:
                    continue

                dst_tokens = token_map.get(dst_id, set())
                sim = _jaccard(src_tokens, dst_tokens)
                vec_sim = max(0.0, _cosine(vec_by_id.get(src_id, []), vec_by_id.get(dst_id, [])))
                dst_parent = _extract_parent_hint(dst)
                parent_bonus = 0.15 if src_parent and dst_parent and src_parent == dst_parent else 0.0
                temporal_bonus = 0.07 if layer + 1 == int(dst.get("layer", layer + 1)) else 0.0
                focus_bonus = 0.10 if (src_id in focus_ids or dst_id in focus_ids) else 0.0

                # Penalize very large SCC nodes to avoid noisy overlays.
                src_scc = int(src.get("scc_size", 1) or 1)
                dst_scc = int(dst.get("scc_size", 1) or 1)
                scc_penalty = 0.08 if max(src_scc, dst_scc) > 20 else 0.0

                confidence = max(
                    0.0,
                    min(
                        0.99,
                        0.28
                        + (sim * 0.35)
                        + (vec_sim * 0.28)
                        + parent_bonus
                        + temporal_bonus
                        + focus_bonus
                        - scc_penalty,
                    ),
                )
                if focus_ids and (src_id not in focus_ids and dst_id not in focus_ids):
                    # Focus mode: keep runtime overlay local to selected context.
                    continue
                if confidence < min_confidence:
                    continue

                evidence = [
                    f"layer+1 progression: {layer}->{layer+1}",
                    f"path_token_overlap={sim:.3f}",
                    f"vector_similarity={vec_sim:.3f}",
                ]
                if parent_bonus > 0:
                    evidence.append("same_parent_hint")
                if focus_bonus > 0:
                    evidence.append("focus_bonus_applied")
                if scc_penalty > 0:
                    evidence.append("scc_penalty_applied")

                candidates.append(
                    {
                        "source": src_id,
                        "target": dst_id,
                        "sourcePort": "out.pred",
                        "targetPort": "in.future",
                        "type": "predicted",
                        "mode_layer": 1,
                        "weight": round(confidence, 4),
                        "confidence": round(confidence, 4),
                        "prediction_mode": vector_model,
                        "evidence": evidence,
                        "is_condensed": True,
                    }
                )

    # Sort deterministic: highest confidence first, then lexical ids
    candidates.sort(key=lambda e: (-float(e["confidence"]), e["source"], e["target"]))
    predicted_edges = candidates[: max(0, int(max_predicted_edges))]

    result = {
        "scope_root": scope_root,
        "base_signature": base.get("signature", ""),
        "overlay_signature": hashlib.md5(
            f"{base.get('signature','')}:{len(predicted_edges)}:{max_predicted_edges}:{min_confidence}".encode("utf-8")
        ).hexdigest()[:12],
        "generated_at": int(time.time()),
        "stats": {
            "base_l2_nodes": len(nodes),
            "base_l2_edges": len(edges),
            "candidate_edges": len(candidates),
            "predicted_edges": len(predicted_edges),
            "min_confidence": float(min_confidence),
            "max_predicted_edges": int(max_predicted_edges),
            "vector_model": vector_model,
            "predictor_mode": vector_model,
            "predictor_detail": adapter_result.detail,
            "strict_runtime": bool(jepa_strict),
            "focus_nodes": len(focus_ids),
        },
        "predicted_edges": predicted_edges,
        "markers": [
            "MARKER_155.MODE_ARCH.V11.P15",
            "MARKER_155.MODE_ARCH.V11.MODE_OVERLAY",
            "MARKER_155.MODE_ARCH.V11.WHY_EDGE_EXPLAINABILITY",
        ],
    }

    _overlay_cache["key"] = cache_key
    _overlay_cache["result"] = result
    _overlay_cache["ts"] = time.time()
    return result
