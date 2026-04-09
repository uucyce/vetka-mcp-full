# MARKER_136.UNIFIED_SEARCH_BACKEND
# MARKER_137.S1_2_TAVILY_WIRE
"""
Unified search handler for federated backend search.

Task: tb_1770805979_6
Provides one entrypoint that dispatches query to multiple sources and normalizes output:
{source, title, snippet, score, url}
"""

from __future__ import annotations

import os
import time
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.search.file_search_service import search_files

DESCRIPTIVE_MIN_WORDS = max(4, int(os.getenv("VETKA_DESCRIPTIVE_MIN_WORDS", "4")))

TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".md", ".txt", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".html", ".css", ".sql", ".go", ".rs", ".java", ".c", ".cpp",
}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
SCAN_ROOTS = ("src", "data")


def _provider_available(provider_name: str, env_var: str = "") -> bool:
    """
    Provider availability contract for search capabilities.

    Order:
    1) explicit env var (fast path)
    2) UnifiedKeyManager provider pool (source of truth for runtime)
    """
    if env_var and os.getenv(env_var):
        return True

    try:
        from src.utils.unified_key_manager import get_key_manager, ProviderType

        km = get_key_manager()
        provider_key = getattr(ProviderType, provider_name.upper(), provider_name.lower())
        return km.get_provider_keys_count(provider_key) > 0
    except Exception:
        return False


def _normalize_item(
    source: str,
    title: str,
    snippet: str,
    score: float,
    url: str = "",
) -> Dict[str, Any]:
    return {
        "source": source,
        "title": (title or "").strip()[:300],
        "snippet": (snippet or "").strip()[:500],
        "score": round(float(score or 0.0), 4),
        "url": (url or "").strip()[:500],
    }


def _file_search(query: str, limit: int) -> List[Dict[str, Any]]:
    # Prefer Phase 157 file search engine (intent-aware + JEPA-assisted rerank).
    try:
        payload = search_files(query=query, limit=limit, mode="keyword")
        rows = payload.get("results", []) if payload.get("success") else []
        out: List[Dict[str, Any]] = []
        for item in rows[:limit]:
            path = item.get("path") or item.get("title") or ""
            out.append(
                _normalize_item(
                    source="file",
                    title=str(path),
                    snippet=str(item.get("snippet", "")),
                    score=float(item.get("score", 0.0)),
                    url=f"file://{path}",
                )
            )
        if out:
            return out
    except Exception:
        pass

    # Legacy fallback path.
    query_l = query.lower().strip()
    if not query_l:
        return []

    results: List[Dict[str, Any]] = []
    project_root = Path.cwd()

    for root_name in SCAN_ROOTS:
        root = project_root / root_name
        if not root.exists():
            continue

        for current_root, dir_names, file_names in os.walk(root):
            dir_names[:] = [d for d in dir_names if d not in SKIP_DIRS]
            current_path = Path(current_root)

            for filename in file_names:
                file_path = current_path / filename
                if file_path.suffix.lower() not in TEXT_EXTENSIONS:
                    continue

                rel_path = str(file_path.relative_to(project_root))
                name_hit = query_l in filename.lower() or query_l in rel_path.lower()

                snippet = ""
                content_hit = False
                if not name_hit:
                    try:
                        with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                            for line in f:
                                if query_l in line.lower():
                                    snippet = line.strip()
                                    content_hit = True
                                    break
                    except Exception:
                        continue
                else:
                    snippet = rel_path

                if name_hit or content_hit:
                    score = 0.95 if name_hit else 0.7
                    results.append(
                        _normalize_item(
                            source="file",
                            title=rel_path,
                            snippet=snippet,
                            score=score,
                            url=f"file://{rel_path}",
                        )
                    )

                if len(results) >= limit:
                    return results

    return results


def _is_descriptive_query(query: str) -> bool:
    q = (query or "").lower().strip()
    words = [w for w in re.split(r"[^a-zA-Zа-яА-Я0-9_]+", q) if w]
    file_like = any(x in q for x in [".py", ".md", ".txt", "marker_", "/", "\\"])
    markers = ["найди файл где", "не помню", "документ", "где ", "про ", "какой файл"]
    return (len(words) >= DESCRIPTIVE_MIN_WORDS and not file_like) or any(m in q for m in markers)


def _semantic_search(query: str, limit: int) -> List[Dict[str, Any]]:
    try:
        from src.mcp.tools.search_tool import SearchTool

        payload = SearchTool().execute({"query": query, "limit": limit, "min_score": 0.2})
        files = payload.get("result", {}).get("files", []) if payload.get("success") else []

        results: List[Dict[str, Any]] = []
        for item in files[:limit]:
            path = item.get("path") or item.get("name") or "unknown"
            snippet = item.get("snippet") or path
            score = item.get("score", 0.0)
            results.append(
                _normalize_item(
                    source="semantic",
                    title=path,
                    snippet=snippet,
                    score=score,
                    url=f"file://{path}",
                )
            )
        return results
    except Exception:
        return []


def _web_search(query: str, limit: int) -> tuple[List[Dict[str, Any]], Optional[str]]:
    def _normalize_web_score(raw_score: Any, rank: int) -> float:
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            # Stable fallback when provider does not return score.
            return max(0.1, 0.75 - (rank * 0.05))

        if score < 0:
            return 0.0
        # Tavily usually returns 0..1, but normalize defensively if scale differs.
        if score > 1.0:
            score = score / 10.0
        return min(score, 1.0)

    try:
        from src.mcp.tools.web_search_tool import WebSearchTool

        payload = WebSearchTool().execute({"query": query, "max_results": min(limit, 10)})
        if not payload.get("success"):
            return [], str(payload.get("error") or "web search unavailable")

        rows = payload.get("result", {}).get("results", [])

        results: List[Dict[str, Any]] = []
        seen_urls = set()
        for idx, item in enumerate(rows[:limit]):
            url = item.get("url", "") or ""
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)

            score = _normalize_web_score(item.get("score", 0.0), idx)
            results.append(
                _normalize_item(
                    source="web",
                    title=item.get("title", ""),
                    snippet=item.get("content", ""),
                    score=score,
                    url=url,
                )
            )
        return results, None
    except Exception as e:
        return [], str(e)


def _social_search(query: str, limit: int) -> List[Dict[str, Any]]:  # noqa: ARG001
    # Future source placeholder per task spec.
    return []


def run_unified_search(
    query: str,
    limit: int = 20,
    sources: Optional[List[str]] = None,
    mode: Optional[str] = None,  # kept for route compatibility
    viewport_context: Optional[dict] = None,  # kept for route compatibility
) -> Dict[str, Any]:
    _ = mode
    _ = viewport_context
    selected_sources = sources or ["file", "semantic", "web", "social"]
    selected_sources = [s for s in selected_sources if s in {"file", "semantic", "web", "social"}]
    # Phase 157: descriptive document queries in vetka context must include file source.
    if _is_descriptive_query(query) and "file" not in selected_sources:
        selected_sources.append("file")

    started = time.time()
    if not query or len(query.strip()) < 2:
        return {
            "success": False,
            "error": "Query too short (min 2 characters)",
            "query": query,
            "results": [],
            "by_source": {},
            "took_ms": 0,
        }

    by_source: Dict[str, List[Dict[str, Any]]] = {}
    source_errors: Dict[str, str] = {}

    if "file" in selected_sources:
        by_source["file"] = _file_search(query, limit)
    if "semantic" in selected_sources:
        by_source["semantic"] = _semantic_search(query, limit)
    if "web" in selected_sources:
        web_results, web_error = _web_search(query, limit)
        by_source["web"] = web_results
        if web_error:
            source_errors["web"] = web_error
    if "social" in selected_sources:
        by_source["social"] = _social_search(query, limit)

    merged: List[Dict[str, Any]] = []
    for source_name in selected_sources:
        merged.extend(by_source.get(source_name, []))

    merged.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    merged = merged[:limit]

    return {
        "success": True,
        "query": query,
        "results": merged,
        "by_source": by_source,
        "source_errors": source_errors,
        "sources": selected_sources,
        "count": len(merged),
        "took_ms": int((time.time() - started) * 1000),
    }


def get_search_capabilities(context: str = "vetka") -> Dict[str, Any]:
    """
    Route-level capabilities contract used by UnifiedSearchBar.
    """
    ctx = (context or "vetka").strip().lower()
    if ctx == "web":
        # MARKER_169.TAVILY_CAPABILITY_ENV_FIX: resolve provider health from env OR UnifiedKeyManager.
        tavily_ready = _provider_available("tavily", env_var="TAVILY_API_KEY")
        serper_ready = _provider_available("serper", env_var="SERPER_API_KEY")
        return {
            "success": True,
            "context": "web",
            "supported_modes": ["hybrid", "keyword"],
            "provider_health": {
                "tavily": {"available": tavily_ready},
                "serper": {"available": serper_ready},
            },
        }
    if ctx == "file":
        return {
            "success": True,
            "context": "file",
            "supported_modes": ["keyword", "filename"],
            "provider_health": {},
        }
    return {
        "success": True,
        "context": "vetka",
        "supported_modes": ["hybrid", "semantic", "keyword", "filename"],
        "provider_health": {},
    }
