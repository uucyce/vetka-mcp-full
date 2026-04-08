"""
Viewport-aware contextual retrieval helpers for VETKA search.

MARKER_146.STEP1_CONTEXTUAL_RETRIEVAL_CORE
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Set


MAX_FOCUS_PATHS = int(os.getenv("VETKA_CTX_MAX_FOCUS_PATHS", "24"))
MAX_FOCUS_TOKENS = int(os.getenv("VETKA_CTX_MAX_FOCUS_TOKENS", "48"))


def _tokenize(text: str) -> Set[str]:
    if not text:
        return set()
    raw = re.findall(r"[a-zA-Z0-9_]{3,}", text.lower())
    return {t for t in raw if t not in {"src", "data", "docs", "main", "file"}}


def _safe_path(path_like: str) -> str:
    raw = (path_like or "").strip()
    if raw.startswith("file://"):
        raw = raw[7:]
    return raw.strip()


def build_viewport_profile(viewport_context: Dict[str, Any] | None) -> Dict[str, Any]:
    """
    Build a compact retrieval profile from viewport context.
    """
    if not viewport_context:
        return {
            "focus_paths": [],
            "focus_dirs": [],
            "focus_tokens": [],
        }

    pinned_nodes = viewport_context.get("pinned_nodes", []) or []
    viewport_nodes = viewport_context.get("viewport_nodes", []) or []

    # Prioritize pinned and center-visible nodes.
    ordered = []
    ordered.extend(pinned_nodes)
    center_nodes = [n for n in viewport_nodes if n.get("is_center")]
    non_center_nodes = [n for n in viewport_nodes if not n.get("is_center")]
    ordered.extend(center_nodes)
    ordered.extend(non_center_nodes)

    focus_paths: List[str] = []
    focus_dirs: Set[str] = set()
    focus_tokens: Set[str] = set()

    for node in ordered:
        if len(focus_paths) >= MAX_FOCUS_PATHS:
            break

        node_type = str(node.get("type", "")).strip().lower()
        if node_type not in {"file", "folder"}:
            continue

        node_path = _safe_path(str(node.get("path", "")))
        node_name = str(node.get("name", ""))
        if not node_path:
            continue

        focus_paths.append(node_path)
        parent = str(Path(node_path).parent)
        if parent and parent != ".":
            focus_dirs.add(parent)

        focus_tokens |= _tokenize(node_name)
        focus_tokens |= _tokenize(Path(node_path).name)

    # Keep token set bounded.
    token_list = list(focus_tokens)[:MAX_FOCUS_TOKENS]

    return {
        "focus_paths": focus_paths,
        "focus_dirs": list(focus_dirs),
        "focus_tokens": token_list,
    }


def _score_file_branch_affinity(path_candidate: str, profile: Dict[str, Any]) -> float:
    path_candidate = _safe_path(path_candidate)
    if not path_candidate:
        return 0.0

    focus_paths = profile.get("focus_paths", []) or []
    focus_dirs = profile.get("focus_dirs", []) or []

    if path_candidate in focus_paths:
        return 0.35

    for prefix in focus_dirs:
        if prefix and path_candidate.startswith(prefix):
            return 0.2

    return 0.0


def _score_token_affinity(text: str, profile: Dict[str, Any], cap: float = 0.12) -> float:
    focus_tokens = set(profile.get("focus_tokens", []) or [])
    if not focus_tokens:
        return 0.0
    hit_count = len(_tokenize(text) & focus_tokens)
    if hit_count <= 0:
        return 0.0
    return min(cap, 0.03 * hit_count)


def compute_context_boost(row: Dict[str, Any], profile: Dict[str, Any]) -> float:
    """
    Compute viewport-context boost for one search row.
    """
    source = str(row.get("source", "")).lower()
    title = str(row.get("title", ""))
    snippet = str(row.get("snippet", ""))
    url = str(row.get("url", ""))

    file_like = source.startswith(("file", "semantic", "qdrant", "weaviate", "hybrid"))

    if file_like:
        path_candidate = _safe_path(url or title)
        boost = _score_file_branch_affinity(path_candidate, profile)
        boost += _score_token_affinity(f"{title} {snippet}", profile, cap=0.08)
        return round(boost, 4)

    # For web rows, only lexical affinity with visible branch names.
    return round(_score_token_affinity(f"{title} {snippet}", profile, cap=0.12), 4)


def contextual_rerank(
    rows: List[Dict[str, Any]],
    viewport_context: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """
    Apply viewport-aware reranking to generic search rows.
    """
    if not rows:
        return rows

    profile = build_viewport_profile(viewport_context)
    if not profile.get("focus_paths") and not profile.get("focus_tokens"):
        return rows

    enriched: List[Dict[str, Any]] = []
    for row in rows:
        score = float(row.get("score", 0.0) or 0.0)
        boost = compute_context_boost(row, profile)
        if boost <= 0:
            enriched.append(row)
            continue
        updated = dict(row)
        updated["context_boost"] = boost
        updated["context_score"] = round(score + boost, 4)
        enriched.append(updated)

    enriched.sort(
        key=lambda x: (
            float(x.get("context_score", x.get("score", 0.0)) or 0.0),
            float(x.get("score", 0.0) or 0.0),
        ),
        reverse=True,
    )
    return enriched
