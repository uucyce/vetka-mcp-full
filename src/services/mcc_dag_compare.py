"""
MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.V1

Auto-compare harness for Design DAG variants.
Runs multiple build variants, computes scorecards, and can persist snapshots.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.services.mcc_architect_builder import build_design_dag, build_design_dag_from_arrays
from src.services.mcc_dag_versions import create_dag_version, set_primary_version


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _to_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return int(default)


def _safe_name(raw: Any, idx: int) -> str:
    text = str(raw or "").strip()
    return text or f"variant_{idx + 1}"


def _score_verifier(verifier: Dict[str, Any], node_count: int, edge_count: int) -> Dict[str, Any]:
    """
    MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.SCORECARD.V1
    Score DAG quality for compare-runs (0..100).
    """
    decision = str(verifier.get("decision") or "warn").lower()
    acyclic = bool(verifier.get("acyclic", False))
    monotonic = bool(verifier.get("monotonic_layers", False))
    orphan_rate = _clamp01(verifier.get("orphan_rate", 1.0))
    density = max(0.0, _to_float(verifier.get("density"), 0.0))
    spectral = verifier.get("spectral") or {}
    spectral_status = str(spectral.get("status") or "warn").lower()
    component_count = max(1, _to_int(spectral.get("component_count"), 1))

    score = 0.0
    breakdown: Dict[str, float] = {}

    decision_pts = {"pass": 30.0, "warn": 18.0, "fail": 0.0}.get(decision, 12.0)
    breakdown["decision"] = decision_pts
    score += decision_pts

    acyclic_pts = 18.0 if acyclic else 0.0
    monotonic_pts = 14.0 if monotonic else 0.0
    breakdown["acyclic"] = acyclic_pts
    breakdown["monotonic"] = monotonic_pts
    score += acyclic_pts + monotonic_pts

    orphan_pts = max(0.0, 14.0 * (1.0 - orphan_rate))
    breakdown["orphan_rate"] = orphan_pts
    score += orphan_pts

    spectral_pts = {"ok": 12.0, "warn": 6.0, "fail": 0.0}.get(spectral_status, 4.0)
    breakdown["spectral_status"] = spectral_pts
    score += spectral_pts

    components_pts = max(0.0, 6.0 - 1.5 * float(component_count - 1))
    breakdown["components"] = components_pts
    score += components_pts

    # Prefer medium sparse architecture overview; punish over-dense results.
    density_target = 0.12
    density_pts = max(0.0, 6.0 - abs(density - density_target) * 35.0)
    breakdown["density"] = density_pts
    score += density_pts

    # Soft readability preference by design graph size (not hard budget gate).
    if node_count <= 0:
        size_pts = 0.0
    elif node_count <= 260:
        size_pts = 4.0
    elif node_count <= 420:
        size_pts = 2.5
    else:
        size_pts = 1.0
    breakdown["size"] = size_pts
    score += size_pts

    final_score = max(0.0, min(100.0, score))
    return {
        "score": round(final_score, 3),
        "breakdown": breakdown,
        "decision": decision,
        "acyclic": acyclic,
        "monotonic_layers": monotonic,
        "orphan_rate": orphan_rate,
        "density": density,
        "component_count": component_count,
        "node_count": int(node_count),
        "edge_count": int(edge_count),
    }


def _run_scope_variant(
    scope_root: str,
    variant: Dict[str, Any],
    default_max_nodes: int,
    include_artifacts: bool,
) -> Dict[str, Any]:
    max_nodes = max(50, min(_to_int(variant.get("max_nodes"), default_max_nodes), 5000))
    max_predicted_edges = max(0, min(_to_int(variant.get("max_predicted_edges"), 120), 2000))
    min_confidence = max(0.0, min(_to_float(variant.get("min_confidence"), 0.55), 0.99))
    use_predictive_overlay = bool(variant.get("use_predictive_overlay", False))
    problem_statement = str(variant.get("problem_statement") or "")
    target_outcome = str(variant.get("target_outcome") or "")

    return build_design_dag(
        scope_root=scope_root,
        max_nodes=max_nodes,
        include_artifacts=include_artifacts,
        problem_statement=problem_statement,
        target_outcome=target_outcome,
        use_predictive_overlay=use_predictive_overlay,
        max_predicted_edges=max_predicted_edges,
        min_confidence=min_confidence,
    )


def _run_array_variant(
    records: List[Dict[str, Any]],
    relations: List[Dict[str, Any]],
    scope_name: str,
    variant: Dict[str, Any],
    default_max_nodes: int,
) -> Dict[str, Any]:
    max_nodes = max(50, min(_to_int(variant.get("max_nodes"), default_max_nodes), 5000))
    max_predicted_edges = max(0, min(_to_int(variant.get("max_predicted_edges"), 120), 2000))
    min_confidence = max(0.0, min(_to_float(variant.get("min_confidence"), 0.55), 0.99))
    use_predictive_overlay = bool(variant.get("use_predictive_overlay", False))

    return build_design_dag_from_arrays(
        records=records,
        relations=relations,
        scope_name=scope_name,
        max_nodes=max_nodes,
        use_predictive_overlay=use_predictive_overlay,
        max_predicted_edges=max_predicted_edges,
        min_confidence=min_confidence,
    )


def _extract_counts(result: Dict[str, Any]) -> Tuple[int, int]:
    design = result.get("design_graph") or {}
    nodes = design.get("nodes") if isinstance(design, dict) else []
    edges = design.get("edges") if isinstance(design, dict) else []
    return len(nodes) if isinstance(nodes, list) else 0, len(edges) if isinstance(edges, list) else 0


def run_dag_auto_compare(
    *,
    project_id: str,
    variants: List[Dict[str, Any]],
    source_kind: str = "scope",
    scope_root: str = "",
    include_artifacts: bool = False,
    records: Optional[List[Dict[str, Any]]] = None,
    relations: Optional[List[Dict[str, Any]]] = None,
    scope_name: str = "array_scope",
    default_max_nodes: int = 600,
    persist_versions: bool = True,
    set_primary_best: bool = False,
) -> Dict[str, Any]:
    """
    MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.AUTORUN.V1
    Run compare harness and return ranked scorecard.
    """
    raw_variants = [v for v in (variants or []) if isinstance(v, dict)]
    if not raw_variants:
        raise ValueError("variants array is empty")

    source_kind_safe = str(source_kind or "scope").strip().lower()
    if source_kind_safe not in ("scope", "array"):
        raise ValueError("source_kind must be 'scope' or 'array'")

    rows: List[Dict[str, Any]] = []
    for idx, variant in enumerate(raw_variants):
        name = _safe_name(variant.get("name"), idx)
        try:
            if source_kind_safe == "scope":
                built = _run_scope_variant(
                    scope_root=scope_root,
                    variant=variant,
                    default_max_nodes=default_max_nodes,
                    include_artifacts=include_artifacts,
                )
            else:
                recs = [dict(x) for x in (records or []) if isinstance(x, dict)]
                rels = [dict(x) for x in (relations or []) if isinstance(x, dict)]
                if not recs:
                    raise ValueError("records array is required for source_kind=array")
                built = _run_array_variant(
                    records=recs,
                    relations=rels,
                    scope_name=scope_name,
                    variant=variant,
                    default_max_nodes=default_max_nodes,
                )

            verifier = built.get("verifier") or {}
            node_count, edge_count = _extract_counts(built)
            scorecard = _score_verifier(verifier, node_count=node_count, edge_count=edge_count)

            version_record: Optional[Dict[str, Any]] = None
            if persist_versions:
                # MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.PERSIST.V1
                version_record = create_dag_version(
                    project_id=project_id,
                    dag_payload={
                        "design_graph": built.get("design_graph") or {},
                        "runtime_graph": built.get("runtime_graph") or {},
                        "verifier": verifier,
                        "predictive_overlay": built.get("predictive_overlay") or {},
                        "markers": list(built.get("markers") or []),
                    },
                    name=name,
                    author="architect",
                    source="auto_compare",
                    build_meta={
                        "verifier": verifier,
                        "scorecard": scorecard,
                        "variant_params": dict(variant),
                        "runner": {
                            "source_kind": source_kind_safe,
                            "default_max_nodes": int(default_max_nodes),
                            "include_artifacts": bool(include_artifacts),
                        },
                    },
                    markers=[
                        "MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.V1",
                        "MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.SCORECARD.V1",
                        "MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.AUTORUN.V1",
                        "MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.PERSIST.V1",
                    ],
                    set_primary=False,
                )

            rows.append(
                {
                    "name": name,
                    "variant_params": dict(variant),
                    "scorecard": scorecard,
                    "verifier": verifier,
                    "version_id": str((version_record or {}).get("version_id") or ""),
                    "created_at": str((version_record or {}).get("created_at") or ""),
                }
            )
        except Exception as e:
            rows.append(
                {
                    "name": name,
                    "variant_params": dict(variant),
                    "error": str(e),
                    "scorecard": {
                        "score": 0.0,
                        "decision": "fail",
                        "acyclic": False,
                        "monotonic_layers": False,
                    },
                    "version_id": "",
                    "created_at": "",
                }
            )

    ranked = sorted(rows, key=lambda x: float((x.get("scorecard") or {}).get("score") or 0.0), reverse=True)
    best = ranked[0] if ranked else {}
    best_version_id = str(best.get("version_id") or "")

    primary_update: Dict[str, Any] | None = None
    if set_primary_best and best_version_id:
        try:
            primary_update = set_primary_version(project_id=project_id, version_id=best_version_id)
        except Exception:
            primary_update = None

    return {
        "success": True,
        "project_id": project_id,
        "source_kind": source_kind_safe,
        "count": len(ranked),
        "best": {
            "name": str(best.get("name") or ""),
            "version_id": best_version_id,
            "score": float((best.get("scorecard") or {}).get("score") or 0.0),
        },
        "set_primary_best": bool(set_primary_best and bool(primary_update)),
        "primary_update": primary_update,
        "variants": ranked,
        "markers": [
            "MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.V1",
            "MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.SCORECARD.V1",
            "MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.AUTORUN.V1",
            "MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.PERSIST.V1",
        ],
    }

