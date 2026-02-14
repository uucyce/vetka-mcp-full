# MARKER_136.ARTIFACT_API_HANDLER
"""Artifact API business logic for MCC panel."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pathlib import Path
import re
import uuid
import json
import html

import httpx

from src.services.artifact_scanner import (
    scan_artifacts,
    approve_artifact,
    reject_artifact,
)
from src.intake.web import WebIntake


def _normalize_artifact_list(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for node in nodes:
        meta = node.get("metadata", {})
        out.append(
            {
                "id": node.get("id"),
                "name": node.get("name"),
                "status": meta.get("status", "done"),
                "artifact_type": meta.get("artifact_type", "document"),
                "language": meta.get("language", "text"),
                "file_path": meta.get("file_path", ""),
                "size_bytes": meta.get("size_bytes", 0),
                "modified_at": meta.get("modified_at"),
            }
        )
    return out


def list_artifacts_for_panel() -> Dict[str, Any]:
    nodes = scan_artifacts()
    return {
        "success": True,
        "artifacts": _normalize_artifact_list(nodes),
        "count": len(nodes),
    }


def approve_artifact_for_panel(artifact_id: str, reason: str = "Approved via API") -> Dict[str, Any]:
    return approve_artifact(artifact_id=artifact_id, reason=reason)


def reject_artifact_for_panel(artifact_id: str, reason: str = "Rejected via API") -> Dict[str, Any]:
    return reject_artifact(artifact_id=artifact_id, reason=reason)


def _slugify(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9\-_]+", "-", (value or "").strip())
    text = re.sub(r"-{2,}", "-", text).strip("-").lower()
    return text[:80] or "web-page"


def _resolve_project_file_path(file_path: str) -> Path:
    p = Path(file_path)
    # MARKER_148.WEB_SAVE_ABS_REL_RESOLVE: treat "/docs" as project-relative docs/ when applicable.
    if p.is_absolute():
        try_rel = Path.cwd() / str(p).lstrip("/\\")
        if try_rel.exists():
            return try_rel
        return p
    return Path.cwd() / p


def _infer_save_directory_from_node_path(target_node_path: str, default_dir: Path) -> Path:
    raw = (target_node_path or "").strip()
    if not raw:
        return default_dir

    candidate = _resolve_project_file_path(raw)
    try:
        # MARKER_149.WEB_SAVE_PATH_SANITIZE_ROOT_ONLY:
        # allow user-selected worktree paths when they are inside current project root;
        # reject only paths outside project root.
        project_root = Path.cwd().resolve()
        try:
            candidate.resolve().relative_to(project_root)
        except Exception:
            return default_dir

        if candidate.exists() and candidate.is_dir():
            return candidate
        if candidate.exists() and candidate.is_file():
            return candidate.parent
        if candidate.suffix:
            return candidate.parent
        return candidate
    except Exception:
        return default_dir


async def _fetch_raw_html(url: str) -> Optional[str]:
    headers = {
        "User-Agent": "VETKA-Web-Saver/1.0",
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
        if resp.status_code >= 400:
            return None
        content_type = (resp.headers.get("content-type") or "").lower()
        if "html" not in content_type:
            return None
        return (resp.text or "")[:1_500_000]
    except Exception:
        return None


def _extract_text_from_raw_html(raw_html: str) -> str:
    html_text = (raw_html or "").strip()
    if not html_text:
        return ""
    # Try trafilatura on downloaded HTML first.
    try:
        import trafilatura
        extracted = trafilatura.extract(
            html_text,
            include_comments=False,
            include_tables=True,
            output_format="txt",
            with_metadata=False,
        )
        if extracted and extracted.strip():
            return extracted.strip()[:250000]
    except Exception:
        pass

    # Fallback: BeautifulSoup visible text extraction.
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        main = soup.find("main") or soup.find("article") or soup.find("body") or soup
        text = main.get_text(separator="\n", strip=True) if main else ""
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text[:250000]
    except Exception:
        return ""


# MARKER_128.9D_BACKEND_SAVE: Save full web page extraction as markdown artifact
# MARKER_145.VIEWPORT_SAVE_ANCHOR: Optional target node path and output format for directed mode save.
async def save_webpage_artifact(
    url: str,
    title: str = "",
    snippet: str = "",
    raw_html: str = "",
    raw_text: str = "",
    output_format: str = "md",
    file_name: str = "",
    target_node_path: str = "",
) -> Dict[str, Any]:
    cleaned_url = (url or "").strip()
    if not cleaned_url or not re.match(r"^https?://", cleaned_url, flags=re.IGNORECASE):
        return {"success": False, "error": "Invalid URL"}

    extractor = WebIntake()
    extracted_title = title.strip()
    extracted_text = (raw_text or snippet or "").strip()
    metadata: Dict[str, Any] = {}

    try:
        result = await extractor.process(cleaned_url, options={})
        if result:
            extracted_title = (result.title or extracted_title or cleaned_url).strip()
            extracted_text = (result.text or extracted_text or "").strip()
            metadata = result.metadata or {}
    except Exception as e:
        metadata = {"extract_error": str(e)[:200]}

    page_html: Optional[str] = (raw_html or "").strip() or None
    # MARKER_149.WEB_SAVE_FULL_TEXT_FALLBACK: if intake returned weak/empty text, parse raw HTML directly.
    if len(extracted_text) < 500:
        if not page_html:
            page_html = await _fetch_raw_html(cleaned_url)
        if page_html:
            parsed_text = _extract_text_from_raw_html(page_html)
            if len(parsed_text) > len(extracted_text):
                extracted_text = parsed_text
                metadata = {
                    **metadata,
                    "text_source": "raw_html_fallback",
                    "text_length": len(extracted_text),
                }

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    short_id = uuid.uuid4().hex[:8]
    safe_name = _slugify(file_name or extracted_title or cleaned_url)
    normalized_format = "html" if str(output_format or "").strip().lower() == "html" else "md"
    filename = f"web_{ts}_{safe_name}_{short_id}.{normalized_format}"

    default_dir = Path("data/artifacts/web_research")
    artifacts_dir = _infer_save_directory_from_node_path(target_node_path, default_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    target = artifacts_dir / filename

    markdown = "\n".join([
        f"# {extracted_title or cleaned_url}",
        "",
        f"Source: [{cleaned_url}]({cleaned_url})",
        f"Saved at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Extracted Content",
        "",
        extracted_text or "_No extractable text found. Use LIVE mode for interactive page._",
        "",
        "## Metadata",
        "",
        f"```json\n{json.dumps(metadata, ensure_ascii=False, indent=2)}\n```",
    ])

    if normalized_format == "html":
        if not page_html:
            page_html = await _fetch_raw_html(cleaned_url)
        if page_html:
            target.write_text(page_html, encoding="utf-8")
        else:
            fallback_html = "\n".join([
                "<!doctype html>",
                "<html><head><meta charset=\"utf-8\"><title>VETKA Saved Page</title></head><body>",
                f"<h1>{html.escape(extracted_title or cleaned_url)}</h1>",
                f"<p><strong>Source:</strong> <a href=\"{html.escape(cleaned_url)}\">{html.escape(cleaned_url)}</a></p>",
                "<h2>Extracted Content</h2>",
                f"<pre>{html.escape((extracted_text or '')[:250000])}</pre>",
                "</body></html>",
            ])
            target.write_text(fallback_html, encoding="utf-8")
    else:
        target.write_text(markdown[:250000], encoding="utf-8")

    # MARKER_148.WEB_SAVE_ACTUAL_TARGET: return effective target path used for persistence.
    return {
        "success": True,
        "file_path": str(target),
        "filename": filename,
        "title": extracted_title or cleaned_url,
        "url": cleaned_url,
        "markdown": markdown[:250000],
        "text_length": len(extracted_text or ""),
        "format": normalized_format,
        "target_node_path": str(artifacts_dir),
        "requested_target_node_path": target_node_path,
    }


def _save_file_result_artifact(path: str, title: str = "", snippet: str = "") -> Dict[str, Any]:
    source_path = _resolve_project_file_path((path or "").strip())
    if not str(source_path):
        return {"success": False, "error": "File path is required"}
    if not source_path.exists() or not source_path.is_file():
        return {"success": False, "error": f"File not found: {path}"}

    try:
        content = source_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return {"success": False, "error": f"Failed to read file: {exc}"}

    text_block = content[:120000]
    rel_path = ""
    try:
        rel_path = str(source_path.relative_to(Path.cwd()))
    except Exception:
        rel_path = str(source_path)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    short_id = uuid.uuid4().hex[:8]
    safe_name = _slugify(title or source_path.name)
    filename = f"file_{ts}_{safe_name}_{short_id}.md"
    artifacts_dir = Path("data/artifacts/search_saved")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    target = artifacts_dir / filename

    markdown = "\n".join([
        f"# {title or source_path.name}",
        "",
        f"Source file: {rel_path}",
        f"Saved at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Search Snippet",
        "",
        snippet.strip() or "_No snippet provided._",
        "",
        "## File Content",
        "",
        "```",
        text_block,
        "```",
    ])

    target.write_text(markdown[:250000], encoding="utf-8")
    return {
        "success": True,
        "file_path": str(target),
        "filename": filename,
        "title": title or source_path.name,
        "source_file": rel_path,
    }


async def save_search_result_artifact(
    source: str,
    path: str = "",
    url: str = "",
    title: str = "",
    snippet: str = "",
    output_format: str = "md",
    file_name: str = "",
    target_node_path: str = "",
) -> Dict[str, Any]:
    normalized_source = (source or "").strip().lower()
    if normalized_source == "web":
        target_url = (url or path or "").strip()
        return await save_webpage_artifact(
            url=target_url,
            title=title,
            snippet=snippet,
            output_format=output_format,
            file_name=file_name,
            target_node_path=target_node_path,
        )
    if normalized_source == "file":
        target_path = (path or url or "").strip()
        return _save_file_result_artifact(path=target_path, title=title, snippet=snippet)
    return {"success": False, "error": f"Unsupported source: {normalized_source}"}
