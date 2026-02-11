# MARKER_136.ARTIFACT_API_HANDLER
"""Artifact API business logic for MCC panel."""

from __future__ import annotations

from typing import Any, Dict, List
from datetime import datetime, timezone
from pathlib import Path
import re
import uuid
import json

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


# MARKER_128.9D_BACKEND_SAVE: Save full web page extraction as markdown artifact
async def save_webpage_artifact(url: str, title: str = "", snippet: str = "") -> Dict[str, Any]:
    cleaned_url = (url or "").strip()
    if not cleaned_url or not re.match(r"^https?://", cleaned_url, flags=re.IGNORECASE):
        return {"success": False, "error": "Invalid URL"}

    extractor = WebIntake()
    extracted_title = title.strip()
    extracted_text = (snippet or "").strip()
    metadata: Dict[str, Any] = {}

    try:
        result = await extractor.process(cleaned_url, options={})
        if result:
            extracted_title = (result.title or extracted_title or cleaned_url).strip()
            extracted_text = (result.text or extracted_text or "").strip()
            metadata = result.metadata or {}
    except Exception as e:
        metadata = {"extract_error": str(e)[:200]}

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    short_id = uuid.uuid4().hex[:8]
    safe_name = _slugify(extracted_title or cleaned_url)
    filename = f"web_{ts}_{safe_name}_{short_id}.md"

    artifacts_dir = Path("data/artifacts/web_research")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    target = artifacts_dir / filename

    markdown = "\n".join([
        f"# {extracted_title or cleaned_url}",
        "",
        f"Source: {cleaned_url}",
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

    target.write_text(markdown[:250000], encoding="utf-8")

    return {
        "success": True,
        "file_path": str(target),
        "filename": filename,
        "title": extracted_title or cleaned_url,
        "url": cleaned_url,
        "markdown": markdown[:250000],
        "text_length": len(extracted_text or ""),
    }
