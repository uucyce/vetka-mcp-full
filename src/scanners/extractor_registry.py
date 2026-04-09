"""
Unified extractor registry for multimodal ingest paths.

MARKER_158.INGEST.MEDIA_EXTRACTOR_REGISTRY
"""

from __future__ import annotations

import hashlib
import mimetypes
import os
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

    _JEPA_MODALITIES = {"audio", "video", "image", "pdf"}
    _PULSE_MODALITIES = {"audio", "video"}

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
        Hooks are feature-flagged and remain graceful on runtime errors.
        """
        hooks: List[tuple[str, Any, float]] = []
        if self._is_optional_jepa_enabled(modality=modality):
            hooks.append(("jepa", self._run_optional_jepa_enrichment, self._optional_jepa_latency_budget_ms()))
        if self._is_optional_pulse_enabled(modality=modality):
            hooks.append(("pulse", self._run_optional_pulse_enrichment, self._optional_pulse_latency_budget_ms()))
        return hooks

    def _is_optional_jepa_enabled(self, *, modality: str) -> bool:
        if str(modality or "").strip().lower() not in self._JEPA_MODALITIES:
            return False
        raw = str(os.getenv("VETKA_EXTRACTOR_JEPA_ENABLE", "true")).strip().lower()
        return raw not in {"0", "false", "no", "off"}

    def _optional_jepa_latency_budget_ms(self) -> float:
        raw = str(os.getenv("VETKA_EXTRACTOR_JEPA_MAX_LATENCY_MS", "180")).strip()
        try:
            return max(1.0, float(raw))
        except Exception:
            return 180.0

    def _collect_optional_jepa_texts(self, *, extraction: ExtractionResult, rel_path: str, modality: str) -> List[str]:
        texts: List[str] = []
        root_text = str(extraction.text or "").strip()
        if root_text:
            texts.append(root_text[:1200])
        max_chunk_texts_raw = str(os.getenv("VETKA_EXTRACTOR_JEPA_MAX_CHUNK_TEXTS", "24")).strip()
        try:
            max_chunk_texts = max(0, min(64, int(max_chunk_texts_raw)))
        except Exception:
            max_chunk_texts = 24
        for row in (extraction.media_chunks or [])[:max_chunk_texts]:
            chunk_text = str((row or {}).get("text") or "").strip()
            if chunk_text:
                texts.append(chunk_text[:240])
        if not texts:
            texts.append(f"{modality}:{rel_path}")
        return texts[:65]

    def _run_optional_jepa_enrichment(
        self,
        *,
        path: Path,
        rel_path: str,
        mime_type: str,
        modality: str,
        extraction: ExtractionResult,
    ) -> Dict[str, Any]:
        from src.services.mcc_jepa_adapter import embed_texts_for_overlay

        dim_raw = str(os.getenv("VETKA_EXTRACTOR_JEPA_TARGET_DIM", "128")).strip()
        timeout_ms_raw = str(os.getenv("VETKA_EXTRACTOR_JEPA_TIMEOUT_MS", "250")).strip()
        strict_raw = str(os.getenv("VETKA_EXTRACTOR_JEPA_STRICT_RUNTIME", "false")).strip().lower()
        provider_override = str(os.getenv("VETKA_EXTRACTOR_JEPA_PROVIDER", "auto")).strip() or None
        runtime_module_override = str(os.getenv("VETKA_EXTRACTOR_JEPA_RUNTIME_MODULE", "src.services.jepa_runtime")).strip() or None

        try:
            target_dim = max(16, min(2048, int(dim_raw)))
        except Exception:
            target_dim = 128
        try:
            timeout_sec = max(0.02, min(10.0, float(timeout_ms_raw) / 1000.0))
        except Exception:
            timeout_sec = 0.25

        texts = self._collect_optional_jepa_texts(extraction=extraction, rel_path=rel_path, modality=modality)
        result = embed_texts_for_overlay(
            texts,
            target_dim=target_dim,
            provider_override=provider_override,
            runtime_module_override=runtime_module_override,
            strict_runtime=(strict_raw in {"1", "true", "yes", "on"}),
            timeout_sec=timeout_sec,
            allow_local_fallback=True,
        )

        vectors = result.vectors if isinstance(result.vectors, list) else []
        vector_dim = len(vectors[0]) if vectors and isinstance(vectors[0], list) else target_dim
        return {
            "provider_mode": str(result.provider_mode or ""),
            "detail": str(result.detail or "")[:200],
            "vector_count": len(vectors),
            "vector_dim": int(vector_dim),
            "texts_count": len(texts),
            "modality": str(modality or ""),
            "mime_type": str(mime_type or ""),
            "source_path": str(rel_path or path),
        }

    def _is_optional_pulse_enabled(self, *, modality: str) -> bool:
        if str(modality or "").strip().lower() not in self._PULSE_MODALITIES:
            return False
        raw = str(os.getenv("VETKA_EXTRACTOR_PULSE_ENABLE", "true")).strip().lower()
        return raw not in {"0", "false", "no", "off"}

    def _optional_pulse_latency_budget_ms(self) -> float:
        raw = str(os.getenv("VETKA_EXTRACTOR_PULSE_MAX_LATENCY_MS", "140")).strip()
        try:
            return max(1.0, float(raw))
        except Exception:
            return 140.0

    def _is_optional_pulse_native_enabled(self) -> bool:
        raw = str(os.getenv("VETKA_EXTRACTOR_PULSE_NATIVE_ENABLE", "true")).strip().lower()
        return raw not in {"0", "false", "no", "off"}

    def _optional_pulse_native_target_sr(self) -> int:
        raw = str(os.getenv("VETKA_EXTRACTOR_PULSE_NATIVE_TARGET_SR", "22050")).strip()
        try:
            return max(8000, min(48000, int(raw)))
        except Exception:
            return 22050

    def _optional_pulse_native_max_sec(self) -> float | None:
        raw = str(os.getenv("VETKA_EXTRACTOR_PULSE_NATIVE_MAX_SEC", "0")).strip()
        try:
            sec = float(raw)
        except Exception:
            return None
        if sec <= 0.0:
            return None
        return max(2.0, min(600.0, sec))

    def _run_optional_pulse_native_analysis(self, *, path: Path) -> Dict[str, Any]:
        try:
            import librosa  # type: ignore
            import numpy as np  # type: ignore
        except Exception as err:
            return {
                "ok": False,
                "reason": f"native_deps_unavailable:{err.__class__.__name__}",
            }

        target_sr = self._optional_pulse_native_target_sr()
        max_sec = self._optional_pulse_native_max_sec()
        try:
            y, sr = librosa.load(str(path), sr=target_sr, mono=True, duration=max_sec)
            if y is None or len(y) < int(sr * 1.5):
                return {"ok": False, "reason": "audio_too_short"}
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
            beats_sec = librosa.frames_to_time(beat_frames, sr=sr)
            bpm = float(np.asarray(tempo).reshape(-1)[0]) if np.asarray(tempo).size > 0 else 0.0
            bpm = max(0.0, min(240.0, bpm))
            beat_count = int(len(beats_sec))
            if beat_count < 3 or bpm <= 0.0:
                return {"ok": False, "reason": "beats_unresolved"}
            intervals = np.diff(beats_sec)
            mean_int = float(np.mean(intervals)) if intervals.size else 0.0
            std_int = float(np.std(intervals)) if intervals.size else 0.0
            cv = (std_int / mean_int) if mean_int > 1e-6 else 1.0
            regularity = max(0.0, min(1.0, 1.0 - cv))
            coverage = max(0.0, min(1.0, beat_count / 24.0))
            confidence = round(max(0.0, min(0.99, 0.45 * regularity + 0.55 * coverage)), 3)
            duration_sec = float(len(y) / float(sr))
            return {
                "ok": True,
                "mode": "native_audio_v1",
                "estimated_bpm": round(float(bpm), 3),
                "confidence": confidence,
                "beats_count": beat_count,
                "analysis_sec": round(duration_sec, 3),
                "sample_rate": int(sr),
                "regularity_cv": round(float(cv), 4),
            }
        except Exception as err:
            return {
                "ok": False,
                "reason": f"native_runtime_error:{err.__class__.__name__}",
            }

    def _estimate_pulse_bpm_from_chunks(self, chunks: List[Dict[str, Any]]) -> float:
        anchors: List[float] = []
        for row in chunks:
            try:
                start = float((row or {}).get("start_sec", 0.0) or 0.0)
                if start >= 0:
                    anchors.append(start)
            except Exception:
                continue
        anchors = sorted(anchors)
        if len(anchors) < 3:
            return 0.0
        deltas = [anchors[i + 1] - anchors[i] for i in range(len(anchors) - 1)]
        deltas = [d for d in deltas if d > 0.05]
        if not deltas:
            return 0.0
        deltas.sort()
        median = deltas[len(deltas) // 2]
        if median <= 1e-6:
            return 0.0
        bpm = 60.0 / median
        return max(40.0, min(220.0, bpm))

    def _run_optional_pulse_enrichment(
        self,
        *,
        path: Path,
        rel_path: str,
        mime_type: str,
        modality: str,
        extraction: ExtractionResult,
    ) -> Dict[str, Any]:
        chunks = list(extraction.media_chunks or [])
        chunk_count = len(chunks)
        pulse_repo = Path(__file__).resolve().parents[2] / "pulse"
        pulse_available = pulse_repo.exists() and pulse_repo.is_dir()

        native = {"ok": False, "reason": "native_disabled"}
        if self._is_optional_pulse_native_enabled():
            native = self._run_optional_pulse_native_analysis(path=path)
        if native.get("ok"):
            return {
                "mode": str(native.get("mode") or "native_audio_v1"),
                "available": pulse_available,
                "estimated_bpm": float(native.get("estimated_bpm", 0.0) or 0.0),
                "confidence": float(native.get("confidence", 0.0) or 0.0),
                "chunks_count": chunk_count,
                "modality": str(modality or ""),
                "mime_type": str(mime_type or ""),
                "source_path": str(rel_path or path),
                "degraded_reason": "",
                "native_used": True,
                "native_reason": "",
                "native_beats_count": int(native.get("beats_count", 0) or 0),
                "native_analysis_sec": float(native.get("analysis_sec", 0.0) or 0.0),
                "native_sample_rate": int(native.get("sample_rate", 0) or 0),
                "native_regularity_cv": float(native.get("regularity_cv", 0.0) or 0.0),
            }

        bpm = self._estimate_pulse_bpm_from_chunks(chunks)
        degraded_reason = ""
        mode = "segment_cadence_v1"
        if chunk_count < 3:
            degraded_reason = "insufficient_segments"
        if bpm <= 0.0:
            degraded_reason = degraded_reason or "bpm_unresolved"
            mode = "metadata_proxy_v1"
        confidence = 0.0
        if bpm > 0.0 and chunk_count >= 3:
            confidence = min(0.95, 0.25 + min(0.7, chunk_count / 40.0))
        return {
            "mode": mode,
            "available": pulse_available,
            "estimated_bpm": round(float(bpm), 3) if bpm > 0.0 else 0.0,
            "confidence": round(float(confidence), 3),
            "chunks_count": chunk_count,
            "modality": str(modality or ""),
            "mime_type": str(mime_type or ""),
            "source_path": str(rel_path or path),
            "degraded_reason": degraded_reason,
            "native_used": False,
            "native_reason": str(native.get("reason") or ""),
        }

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
