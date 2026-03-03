"""
Unified extractor registry for multimodal ingest paths.

MARKER_158.INGEST.MEDIA_EXTRACTOR_REGISTRY
"""

from __future__ import annotations

import hashlib
import mimetypes
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.scanners.mime_policy import classify_extension
from src.scanners.multimodal_contracts import MediaChunk, normalize_media_chunks


TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".html",
    ".css",
    ".sh",
    ".sql",
    ".go",
    ".rs",
}

OCR_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}
MEDIA_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".flac",
    ".ogg",
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
}


@dataclass
class ExtractionResult:
    text: str
    media_chunks: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    extractor_id: str = "text_reader"


class MediaExtractorRegistry:
    """Unified OCR/STT/text registry used by watcher/reindex/updater flows."""

    def extract_file(
        self,
        file_path: str | Path,
        *,
        rel_path: Optional[str] = None,
        max_text_chars: int = 8000,
    ) -> ExtractionResult:
        path = Path(file_path)
        ext = path.suffix.lower()
        mime_type, _ = mimetypes.guess_type(str(path))
        mime_type = mime_type or "application/octet-stream"
        rel = rel_path or str(path)
        modality = classify_extension(str(path))[1]

        if ext in TEXT_EXTENSIONS or mime_type.startswith("text/"):
            text = path.read_text(encoding="utf-8", errors="replace")
            result = ExtractionResult(
                text=text[:max_text_chars],
                metadata={
                    "extraction_route": "text",
                    "mime_type": mime_type,
                    "modality": modality,
                },
                extractor_id="text_reader",
            )
            return self._apply_optional_enrichments(
                path=path,
                rel_path=rel,
                mime_type=mime_type,
                modality=modality,
                extraction=result,
            )

        if ext in OCR_EXTENSIONS:
            result = self._extract_ocr(path=path, rel_path=rel, mime_type=mime_type, max_text_chars=max_text_chars)
            return self._apply_optional_enrichments(
                path=path,
                rel_path=rel,
                mime_type=mime_type,
                modality=modality,
                extraction=result,
            )

        if ext in MEDIA_EXTENSIONS:
            result = self._extract_av(path=path, rel_path=rel, mime_type=mime_type, max_text_chars=max_text_chars)
            return self._apply_optional_enrichments(
                path=path,
                rel_path=rel,
                mime_type=mime_type,
                modality=modality,
                extraction=result,
            )

        result = self._build_binary_summary(path=path, rel_path=rel, mime_type=mime_type, prefix="Binary file summary")
        return self._apply_optional_enrichments(
            path=path,
            rel_path=rel,
            mime_type=mime_type,
            modality=modality,
            extraction=result,
        )

    def _get_optional_enrichers(
        self,
        *,
        path: Path,
        rel_path: str,
        mime_type: str,
        modality: str,
    ) -> List[tuple[str, Any, float]]:
        """
        Optional JEPA/PULSE hooks.
        Return: list[(name, callable, max_latency_ms)].
        Default implementation is empty and safe.
        """
        return []

    def _apply_optional_enrichments(
        self,
        *,
        path: Path,
        rel_path: str,
        mime_type: str,
        modality: str,
        extraction: ExtractionResult,
    ) -> ExtractionResult:
        enrichers = self._get_optional_enrichers(
            path=path,
            rel_path=rel_path,
            mime_type=mime_type,
            modality=modality,
        )
        if not enrichers:
            return extraction

        metadata = dict(extraction.metadata or {})
        enrich_payload: Dict[str, Dict[str, Any]] = {}
        has_non_ok = False
        for name, hook, max_latency_ms in enrichers:
            t0 = time.perf_counter()
            try:
                payload = hook(
                    path=path,
                    rel_path=rel_path,
                    mime_type=mime_type,
                    modality=modality,
                    extraction=extraction,
                )
                latency_ms = max(0.0, (time.perf_counter() - t0) * 1000.0)
                status = "ok" if latency_ms <= float(max_latency_ms or 0.0) else "over_budget"
                if status != "ok":
                    has_non_ok = True
                enrich_payload[str(name)] = {
                    "status": status,
                    "latency_ms": round(latency_ms, 3),
                    "max_latency_ms": float(max_latency_ms or 0.0),
                    "payload": payload if isinstance(payload, dict) else {},
                }
            except Exception as err:
                latency_ms = max(0.0, (time.perf_counter() - t0) * 1000.0)
                has_non_ok = True
                enrich_payload[str(name)] = {
                    "status": "error",
                    "latency_ms": round(latency_ms, 3),
                    "max_latency_ms": float(max_latency_ms or 0.0),
                    "error": str(err)[:200],
                }

        metadata["optional_enrichments"] = enrich_payload
        metadata["optional_enrichment_count"] = len(enrich_payload)
        metadata["optional_enrichment_degraded"] = has_non_ok
        return ExtractionResult(
            text=extraction.text,
            media_chunks=extraction.media_chunks,
            metadata=metadata,
            extractor_id=extraction.extractor_id,
        )

    def _extract_ocr(
        self,
        *,
        path: Path,
        rel_path: str,
        mime_type: str,
        max_text_chars: int,
    ) -> ExtractionResult:
        try:
            from src.ocr.ocr_processor import get_ocr_processor

            ocr = get_ocr_processor()
            ocr_result = ocr.process_pdf(str(path)) if path.suffix.lower() == ".pdf" else ocr.process_image(str(path))
            text = (ocr_result.get("text") or "").strip()
            if text:
                return ExtractionResult(
                    text=text[:max_text_chars],
                    metadata={
                        "extraction_route": "ocr",
                        "ocr_source": ocr_result.get("source", "unknown"),
                        "ocr_confidence": float(ocr_result.get("confidence", 0.0) or 0.0),
                        "mime_type": mime_type,
                        "modality": classify_extension(str(path))[1],
                    },
                    extractor_id="ocr_processor",
                )
            return ExtractionResult(
                text=f"[OCR empty] file={rel_path}",
                metadata={
                    "extraction_route": "ocr_empty",
                    "mime_type": mime_type,
                    "modality": classify_extension(str(path))[1],
                },
                extractor_id="ocr_processor",
            )
        except Exception as err:
            return ExtractionResult(
                text=f"[OCR error] file={rel_path} error={str(err)[:160]}",
                metadata={
                    "extraction_route": "ocr_error",
                    "mime_type": mime_type,
                    "modality": classify_extension(str(path))[1],
                },
                extractor_id="ocr_processor",
            )

    def _extract_av(
        self,
        *,
        path: Path,
        rel_path: str,
        mime_type: str,
        max_text_chars: int,
    ) -> ExtractionResult:
        try:
            from src.voice.stt_engine import WhisperSTT

            stt = WhisperSTT(model_name="base")
            tr = stt.transcribe(str(path))
            transcript_text = (tr.get("text") or "").strip()
            segments = tr.get("segments", []) or []
            raw_media_chunks: List[Dict[str, Any]] = []
            for seg in segments[:128]:
                try:
                    raw_media_chunks.append(
                        MediaChunk(
                            start_sec=float(seg.get("start", 0.0) or 0.0),
                            end_sec=float(seg.get("end", 0.0) or 0.0),
                            text=str(seg.get("text", "") or ""),
                            confidence=float(tr.get("confidence", 0.0) or 0.0),
                        ).to_dict()
                    )
                except Exception:
                    continue

            media_chunks = normalize_media_chunks(
                raw_media_chunks,
                parent_file_path=rel_path,
                modality=classify_extension(str(path))[1],
                extractor_id="whisper_stt",
                limit=128,
            )

            if transcript_text:
                return ExtractionResult(
                    text=transcript_text[:max_text_chars],
                    media_chunks=media_chunks,
                    metadata={
                        "extraction_route": "stt",
                        "transcript_source": "mlx_whisper",
                        "transcript_confidence": float(tr.get("confidence", 0.0) or 0.0),
                        "media_chunks_count": len(media_chunks),
                        "mime_type": mime_type,
                        "modality": classify_extension(str(path))[1],
                    },
                    extractor_id="whisper_stt",
                )
        except Exception:
            pass

        return self._build_binary_summary(path=path, rel_path=rel_path, mime_type=mime_type, prefix="Media file summary")

    def _build_binary_summary(
        self,
        *,
        path: Path,
        rel_path: str,
        mime_type: str,
        prefix: str,
    ) -> ExtractionResult:
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        text = (
            f"[{prefix}]\n"
            f"path={rel_path}\n"
            f"mime={mime_type}\n"
            f"size_bytes={len(raw)}\n"
            f"sha256={digest}"
        )
        return ExtractionResult(
            text=text,
            metadata={
                "extraction_route": "summary_fallback",
                "mime_type": mime_type,
                "modality": classify_extension(str(path))[1],
            },
            extractor_id="summary_fallback",
        )


_EXTRACTOR_REGISTRY: Optional[MediaExtractorRegistry] = None


def get_media_extractor_registry() -> MediaExtractorRegistry:
    global _EXTRACTOR_REGISTRY
    if _EXTRACTOR_REGISTRY is None:
        _EXTRACTOR_REGISTRY = MediaExtractorRegistry()
    return _EXTRACTOR_REGISTRY
