"""
Premiere adapter boundary for VETKA interchange and future live bridge lanes.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Protocol

from src.services.converters.fcpxml_converter import build_fcpxml_from_transcript
from src.services.converters.premiere_xml_converter import build_premiere_xml_from_transcript


@dataclass(frozen=True)
class PremiereExportRequest:
    source_path: str
    transcript_normalized_json: Dict[str, Any]
    sequence_name: str = "VETKA_Sequence"
    fps: float = 30.0
    lane: str = "premiere_xml"  # premiere_xml | fcpxml


@dataclass(frozen=True)
class PremiereExportArtifact:
    lane: str
    media_type: str
    file_ext: str
    xml_text: str
    bridge_mode: str = ""
    degraded_mode: bool = False
    degraded_reason: str = ""


class PremiereAdapter(Protocol):
    def adapter_id(self) -> str:
        ...

    def export_from_transcript(self, request: PremiereExportRequest) -> PremiereExportArtifact:
        ...


class XMLInterchangePremiereAdapter:
    """
    Production-safe adapter that builds XML interchange payloads only.
    No live Premiere process control is performed here.
    """

    def adapter_id(self) -> str:
        return "xml_interchange_adapter"

    def export_from_transcript(self, request: PremiereExportRequest) -> PremiereExportArtifact:
        lane = str(request.lane or "premiere_xml").strip().lower()
        if lane == "premiere_xml":
            xml_text = build_premiere_xml_from_transcript(
                source_path=request.source_path,
                transcript_normalized_json=request.transcript_normalized_json,
                sequence_name=request.sequence_name,
                fps=float(request.fps),
            )
            return PremiereExportArtifact(
                lane="premiere_xml",
                media_type="application/xml",
                file_ext=".xml",
                xml_text=xml_text,
                bridge_mode="xml_interchange",
            )
        if lane == "fcpxml":
            xml_text = build_fcpxml_from_transcript(
                source_path=request.source_path,
                transcript_normalized_json=request.transcript_normalized_json,
                sequence_name=request.sequence_name,
                fps=float(request.fps),
            )
            return PremiereExportArtifact(
                lane="fcpxml",
                media_type="application/xml",
                file_ext=".fcpxml",
                xml_text=xml_text,
                bridge_mode="xml_interchange",
            )
        raise ValueError(f"Unsupported premiere export lane: {request.lane}")


class MCPLiveBridgePremiereAdapter:
    """
    Sub-MCP lane for live Premiere bridge.
    v1 behavior is safe:
    - attempts bridge exchange via temp-dir command/result files
    - degrades to xml_interchange adapter on timeout/unavailable bridge
    """

    def __init__(
        self,
        *,
        bridge_dir: str | None = None,
        timeout_sec: float | None = None,
        poll_interval_sec: float | None = None,
    ) -> None:
        self.bridge_dir = Path(
            bridge_dir
            or os.environ.get("VETKA_PREMIERE_BRIDGE_DIR")
            or os.environ.get("PREMIERE_TEMP_DIR")
            or "/tmp/premiere-mcp-bridge"
        )
        self.timeout_sec = float(timeout_sec or os.environ.get("VETKA_PREMIERE_BRIDGE_TIMEOUT_SEC", 2.0) or 2.0)
        self.poll_interval_sec = float(
            poll_interval_sec or os.environ.get("VETKA_PREMIERE_BRIDGE_POLL_SEC", 0.05) or 0.05
        )
        self.fallback = XMLInterchangePremiereAdapter()

    def adapter_id(self) -> str:
        return "mcp_live_bridge_adapter"

    def _try_bridge_exchange(self, request: PremiereExportRequest) -> PremiereExportArtifact | None:
        if not self.bridge_dir.exists() or not self.bridge_dir.is_dir():
            return None
        command_dir = self.bridge_dir / "commands"
        result_dir = self.bridge_dir / "results"
        command_dir.mkdir(parents=True, exist_ok=True)
        result_dir.mkdir(parents=True, exist_ok=True)

        req_id = str(uuid.uuid4())
        command_file = command_dir / f"{req_id}.json"
        result_file = result_dir / f"{req_id}.json"

        payload = {
            "request_id": req_id,
            "action": "export_from_transcript",
            "lane": request.lane,
            "source_path": request.source_path,
            "sequence_name": request.sequence_name,
            "fps": float(request.fps),
            "transcript_normalized_json": request.transcript_normalized_json,
            "issued_at_ms": int(time.time() * 1000),
        }
        command_file.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")

        deadline = time.perf_counter() + max(0.2, self.timeout_sec)
        while time.perf_counter() <= deadline:
            if result_file.exists():
                try:
                    data = json.loads(result_file.read_text(encoding="utf-8"))
                    xml_text = str(data.get("xml_text") or "")
                    lane = str(data.get("lane") or request.lane).strip().lower()
                    if xml_text and lane in {"premiere_xml", "fcpxml"}:
                        return PremiereExportArtifact(
                            lane=lane,
                            media_type="application/xml",
                            file_ext=".fcpxml" if lane == "fcpxml" else ".xml",
                            xml_text=xml_text,
                            bridge_mode="mcp_live_bridge",
                            degraded_mode=False,
                            degraded_reason="",
                        )
                except Exception:
                    return None
            time.sleep(max(0.01, self.poll_interval_sec))
        return None

    def export_from_transcript(self, request: PremiereExportRequest) -> PremiereExportArtifact:
        live = self._try_bridge_exchange(request)
        if live is not None:
            return live
        fallback_artifact = self.fallback.export_from_transcript(request)
        return PremiereExportArtifact(
            lane=fallback_artifact.lane,
            media_type=fallback_artifact.media_type,
            file_ext=fallback_artifact.file_ext,
            xml_text=fallback_artifact.xml_text,
            bridge_mode="mcp_live_bridge",
            degraded_mode=True,
            degraded_reason="bridge_unavailable_or_timeout",
        )


def get_premiere_adapter(mode: str = "xml_interchange") -> PremiereAdapter:
    m = str(mode or "xml_interchange").strip().lower()
    if m == "xml_interchange":
        return XMLInterchangePremiereAdapter()
    if m in {"mcp_live_bridge", "mcp_bridge"}:
        return MCPLiveBridgePremiereAdapter()
    raise ValueError(f"Unsupported premiere adapter mode: {mode}")
