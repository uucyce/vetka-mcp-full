"""URL intake extraction (fallback implementation).

Processes a URL and returns title/text/metadata. The private intake stack
added document and YouTube processing on top; this keeps the REST API path
functional with plain HTTP fetching and light HTML-to-text conversion.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import httpx

_TAG_RE = re.compile(r"<(script|style|noscript)[\s\S]*?</\1>", re.I)
_SCRIPT_RE = re.compile(r"<\s*script[\s\S]*?<\s*/\s*script\s*>", re.I)
_STYLE_RE = re.compile(r"<\s*style[\s\S]*?<\s*/\s*style\s*>", re.I)
_TITLE_RE = re.compile(r"<title[^>]*>([\s\S]*?)</title>", re.I)
_TAG_CLEAN_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

_UA = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    )
}


@dataclass
class URLContent:
    title: str = ""
    text: str = ""
    url: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


def _extract_title(html: str) -> str:
    m = _TITLE_RE.search(html)
    if m:
        return _WS_RE.sub(" ", m.group(1)).strip()
    return ""


def _html_to_text(html: str) -> str:
    html = _SCRIPT_RE.sub(" ", html)
    html = _STYLE_RE.sub(" ", html)
    return _WS_RE.sub(" ", _TAG_CLEAN_RE.sub(" ", html)).strip()


class WebIntake:
    """Minimal URL -> (title, text, metadata) extractor."""

    def __init__(self, timeout: float = 20.0) -> None:
        self.timeout = timeout

    async def process(
        self,
        url: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Optional[URLContent]:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, follow_redirects=True, headers=_UA
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text
            title = _extract_title(html)
            text = _html_to_text(html)
            return URLContent(
                title=title,
                text=text,
                url=str(resp.url),
                metadata={
                    "status_code": resp.status_code,
                    "content_type": resp.headers.get("content-type", ""),
                    "text_length": len(text),
                },
            )
        except Exception as exc:  # pragma: no cover - resilient by design
            return None