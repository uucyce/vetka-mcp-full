# MARKER_136.UNIFIED_SEARCH_ROUTE
"""Routes for unified federated search."""

import html
import ipaddress
import re
from urllib.parse import urlparse
from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel
import httpx

from src.api.handlers.unified_search import get_search_capabilities, run_unified_search
from src.search.file_search_service import search_files, get_file_search_capabilities


router = APIRouter(prefix="/api/search", tags=["unified-search"])


class UnifiedSearchRequest(BaseModel):
    query: str
    limit: int = 20
    sources: Optional[List[str]] = None
    mode: Optional[str] = None
    viewport_context: Optional[dict] = None


class WebPreviewRequest(BaseModel):
    url: str
    timeout_s: float = 8.0


class FileSearchRequest(BaseModel):
    query: str
    limit: int = 20
    mode: str = "keyword"  # keyword|filename


def _is_private_or_local_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower()
    if not host:
        return True
    if host in {"localhost", "::1"} or host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except ValueError:
        return False


def _sanitize_html(raw_html: str) -> str:
    """MARKER_139.S1_3_WEB_PROXY: Basic server-side HTML sanitization for preview iframe."""
    cleaned = raw_html or ""
    cleaned = re.sub(r"(?is)<script\b.*?>.*?</script>", "", cleaned)
    cleaned = re.sub(r"(?is)<style\b.*?>.*?</style>", "", cleaned)
    cleaned = re.sub(r"(?is)<iframe\b.*?>.*?</iframe>", "", cleaned)
    cleaned = re.sub(r"(?is)<object\b.*?>.*?</object>", "", cleaned)
    cleaned = re.sub(r"(?is)<embed\b.*?>.*?</embed>", "", cleaned)
    cleaned = re.sub(r"(?is)<form\b.*?>.*?</form>", "", cleaned)
    cleaned = re.sub(r"(?i)\son\w+\s*=\s*(['\"]).*?\1", "", cleaned)
    cleaned = re.sub(r"(?i)\s(href|src)\s*=\s*(['\"])javascript:.*?\2", r" \1=\"#\"", cleaned)
    cleaned = re.sub(r"(?i)<meta[^>]+http-equiv\s*=\s*(['\"])refresh\1[^>]*>", "", cleaned)
    return cleaned


def _extract_title(raw_html: str, fallback: str) -> str:
    match = re.search(r"(?is)<title[^>]*>(.*?)</title>", raw_html or "")
    if match:
        title = re.sub(r"\s+", " ", match.group(1)).strip()
        if title:
            return title[:200]
    return fallback[:200]


def _build_srcdoc(safe_html: str, source_url: str) -> str:
    escaped_base = html.escape(source_url, quote=True)
    return (
        "<!doctype html><html><head>"
        f"<base href=\"{escaped_base}\" target=\"_blank\">"
        "<meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<style>body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
        "margin:0;padding:16px;line-height:1.5;background:#fff;color:#111}"
        "img,video{max-width:100%;height:auto}pre{white-space:pre-wrap;word-break:break-word}"
        "a{color:#0a66c2;text-decoration:none}a:hover{text-decoration:underline}"
        "</style></head><body>"
        f"{safe_html}"
        "</body></html>"
    )


def _is_probably_js_app(raw_html: str, safe_html: str) -> bool:
    """
    Heuristic: page is mostly JS-driven and sanitized preview is likely blank.
    """
    raw = raw_html or ""
    safe = safe_html or ""
    has_app_root = bool(re.search(r'(?i)id\s*=\s*["\'](app|root|__next|react-root)["\']', raw))
    has_many_scripts = len(re.findall(r"(?is)<script\b", raw)) >= 3
    # Remove tags and check visible text footprint.
    text_only = re.sub(r"(?is)<[^>]+>", " ", safe)
    text_only = re.sub(r"\s+", " ", text_only).strip()
    low_visible_text = len(text_only) < 180
    return low_visible_text and (has_app_root or has_many_scripts)


def _is_frame_blocked_by_headers(headers: dict) -> bool:
    """
    Heuristic: detect if site is likely blocked inside iframe/webview frame.
    """
    xfo = str(headers.get("x-frame-options", "")).lower()
    if "deny" in xfo or "sameorigin" in xfo:
        return True

    csp = str(headers.get("content-security-policy", "")).lower()
    if "frame-ancestors" in csp:
        # Most restrictive common cases
        if "'none'" in csp or "'self'" in csp:
            return True
        # If frame-ancestors exists but does not allow wildcards/protocols, treat as likely blocked.
        if "*" not in csp and "https:" not in csp and "http:" not in csp:
            return True

    return False


@router.post("/unified")
async def unified_search_endpoint(body: UnifiedSearchRequest):
    safe_limit = max(1, min(body.limit, 100))
    return run_unified_search(
        query=body.query,
        limit=safe_limit,
        sources=body.sources,
        mode=body.mode,
        viewport_context=body.viewport_context,
    )


@router.get("/capabilities")
async def unified_search_capabilities(
    context: str = Query("vetka", description="Search context (vetka|web|file|cloud|social)"),
):
    return get_search_capabilities(context=context)


@router.post("/file")
async def file_search_endpoint(body: FileSearchRequest):
    safe_limit = max(1, min(body.limit, 100))
    mode = "filename" if str(body.mode).strip().lower() == "filename" else "keyword"
    return search_files(
        query=body.query,
        limit=safe_limit,
        mode=mode,
    )


@router.get("/file/capabilities")
async def file_search_capabilities_endpoint():
    return get_file_search_capabilities()


@router.post("/web-preview")
async def web_preview_endpoint(body: WebPreviewRequest):
    """MARKER_139.S1_3_WEB_PROXY: Fetch and sanitize full webpage HTML for Artifact preview."""
    raw_url = (body.url or "").strip()
    parsed = urlparse(raw_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return {"success": False, "error": "Invalid URL (http/https only)", "url": raw_url}

    if _is_private_or_local_host(parsed.hostname or ""):
        return {"success": False, "error": "Blocked host", "url": raw_url}

    timeout_s = max(2.0, min(float(body.timeout_s or 8.0), 20.0))
    headers = {
        "User-Agent": "VETKA-PreviewBot/1.0 (+https://vetka.local)",
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
    }

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout_s) as client:
            resp = await client.get(raw_url, headers=headers)
    except Exception as e:
        return {"success": False, "error": f"Fetch failed: {e}", "url": raw_url}

    content_type = (resp.headers.get("content-type") or "").lower()
    frame_blocked = _is_frame_blocked_by_headers(dict(resp.headers))
    text = resp.text or ""
    final_url = str(resp.url)

    if "html" in content_type:
        safe_html = _sanitize_html(text)
        title = _extract_title(text, fallback=parsed.netloc)
        srcdoc = _build_srcdoc(safe_html, final_url)
        js_app_like = _is_probably_js_app(text, safe_html)
    else:
        title = parsed.netloc
        escaped_text = html.escape(text[:50000])
        srcdoc = _build_srcdoc(f"<pre>{escaped_text}</pre>", final_url)
        js_app_like = False

    return {
        "success": True,
        "url": final_url,
        "title": title,
        "content_type": content_type or "unknown",
        "status_code": resp.status_code,
        "html": srcdoc,
        "is_probably_js_app": js_app_like,
        "frame_blocked": frame_blocked,
    }
