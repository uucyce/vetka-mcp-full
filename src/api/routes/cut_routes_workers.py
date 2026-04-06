"""
MARKER_B70 — Worker & Background Jobs sub-router.
Extracted from cut_routes.py for modularity.

Contains: background job runners (scan-matrix, waveform, thumbnail, audio-sync,
timecode-sync, music-sync, pause-slice, scene-assembly, transcript-normalize),
worker endpoints, job status/cancel endpoints, and helper functions.

~3100 lines extracted.

@status: active
@phase: B70
@task: tb_1774311967_29
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import tempfile
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal
from uuid import uuid4

import numpy as np
from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.services.cut_codec_probe import probe_file, probe_duration
from src.services.cut_project_store import (
    CutProjectStore,
    quick_scan_cut_source,
)
from src.services.cut_mcp_job_store import get_cut_mcp_job_store
from src.services.cut_scene_graph_taxonomy import (
    SCENE_GRAPH_EDGE_CONTAINS,
    SCENE_GRAPH_EDGE_FOLLOWS,
    SCENE_GRAPH_EDGE_REFERENCES,
    SCENE_GRAPH_EDGE_SEMANTIC_MATCH,
    SCENE_GRAPH_NODE_ASSET,
    SCENE_GRAPH_NODE_SCENE,
    SCENE_GRAPH_NODE_TAKE,
)
from src.api.routes.cut_routes_bootstrap import (
    CutBootstrapRequest,
    _bootstrap_error,
    _build_initial_timeline_state,
    _execute_cut_bootstrap,
    _infer_cut_media_modality,
    _run_cut_bootstrap_job,
    _utc_now_iso,
)

# Import Request models (now safe after moving import of this file in cut_routes.py)
from src.api.routes.cut_routes import (
    CutAudioSyncRequest,
    CutMusicSyncRequest,
    CutPauseSliceRequest,
    CutScanMatrixRequest,
    CutSceneAssemblyRequest,
    CutThumbnailBuildRequest,
    CutTimecodeSyncRequest,
    CutTranscriptNormalizeRequest,
    CutWaveformBuildRequest,
)

logger = logging.getLogger("cut.workers")

worker_router = APIRouter(tags=["CUT-Workers"])

_ACTIVE_JOB_STATES = {"queued", "running", "partial"}
_SANDBOX_BACKGROUND_LIMIT = 2


def _worker_job_error(code: str, message: str, *, existing_job: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "success": False,
        "schema_version": "cut_mcp_job_v1",
        "error": {
            "code": code,
            "message": message,
            "recoverable": True,
        },
    }
    if existing_job is not None:
        payload["job"] = existing_job
        payload["job_id"] = str(existing_job.get("job_id") or "")
    return payload


def _discover_worker_media_files(source_root: str, limit: int) -> list[str]:
    media_ext = {
        ".mp4",
        ".mov",
        ".m4v",
        ".avi",
        ".mkv",
        ".webm",
        ".mp3",
        ".wav",
        ".m4a",
        ".aac",
        ".flac",
        ".ogg",
    }
    if not os.path.isdir(source_root):
        return []
    paths: list[str] = []
    for entry in sorted(os.scandir(source_root), key=lambda item: item.name.lower()):
        if not entry.is_file():
            continue
        if os.path.splitext(entry.name)[1].lower() not in media_ext:
            continue
        paths.append(entry.path)
        if len(paths) >= limit:
            break
    return paths


def _build_waveform_proxy_from_bytes(path: str, bins: int) -> tuple[list[float], bool, str]:
    try:
        with open(path, "rb") as f:
            data = f.read(8192)
    except Exception as exc:
        return ([0.0] * bins, True, f"read_failed:{str(exc)[:48]}")
    if not data:
        return ([0.0] * bins, True, "empty_file")
    chunk_size = max(1, len(data) // bins)
    values: list[float] = []
    for index in range(bins):
        chunk = data[index * chunk_size : (index + 1) * chunk_size]
        if not chunk:
            values.append(0.0)
            continue
        avg = sum(abs(byte - 128) for byte in chunk) / (len(chunk) * 128.0)
        values.append(round(max(0.0, min(1.0, avg)), 4))
    return (values, False, "")


def _build_signal_proxy_from_bytes(path: str, sample_bytes: int) -> tuple[list[float], bool, str]:
    try:
        with open(path, "rb") as f:
            data = f.read(sample_bytes)
    except Exception as exc:
        return ([], True, f"read_failed:{str(exc)[:48]}")
    if not data:
        return ([], True, "empty_file")
    signal = [round((byte - 128) / 128.0, 6) for byte in data]
    return (signal, False, "")


def _sidecar_timecode_info(path: str) -> tuple[str | None, int | None]:
    sidecar = f"{path}.timecode.json"
    if not os.path.isfile(sidecar):
        return (None, None)
    try:
        with open(sidecar, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        return (None, None)
    if not isinstance(payload, dict):
        return (None, None)
    value = str(payload.get("start_tc") or payload.get("timecode") or "").strip()
    fps = int(payload.get("fps") or 0) or None
    return (value or None, fps)


def _extract_timecode_from_path(path: str, default_fps: int) -> tuple[str | None, int]:
    sidecar_value, sidecar_fps = _sidecar_timecode_info(path)
    if sidecar_value:
        return sidecar_value, int(sidecar_fps or default_fps)
    name = os.path.basename(path)
    match = re.search(r"(?:tc|timecode)[_-]?(\d{2})[:._-](\d{2})[:._-](\d{2})[:._-](\d{2})", name, re.IGNORECASE)
    if not match:
        return None, int(default_fps)
    hh, mm, ss, ff = match.groups()
    return f"{hh}:{mm}:{ss}:{ff}", int(default_fps)


def _timecode_to_seconds(value: str, fps: int) -> float | None:
    parts = re.split(r"[:]", str(value or "").strip())
    if len(parts) != 4:
        return None
    try:
        hh, mm, ss, ff = [int(part) for part in parts]
    except ValueError:
        return None
    return (hh * 3600) + (mm * 60) + ss + (ff / max(1, fps))


def _pick_audio_sync_media_paths(source_root: str, limit: int) -> list[str]:
    candidates = _discover_worker_media_files(source_root, limit * 2)
    preferred_audio_ext = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}
    audio_paths = [path for path in candidates if os.path.splitext(path)[1].lower() in preferred_audio_ext]
    if len(audio_paths) >= 2:
        return audio_paths[:limit]
    return candidates[:limit]


def _pick_timecode_sync_media_paths(source_root: str, limit: int) -> list[str]:
    return _discover_worker_media_files(source_root, limit)


def _find_active_duplicate_job(
    *,
    job_type: str,
    project_id: str,
    sandbox_root: str,
) -> dict[str, Any] | None:
    store = get_cut_mcp_job_store()
    for job in store.list_jobs():
        if str(job.get("job_type") or "") != str(job_type):
            continue
        if str(job.get("state") or "") not in _ACTIVE_JOB_STATES:
            continue
        input_payload = job.get("input") or {}
        if str(input_payload.get("project_id") or "") != str(project_id):
            continue
        if str(input_payload.get("sandbox_root") or "") != str(sandbox_root):
            continue
        return job
    return None


def _count_active_background_jobs_for_sandbox(sandbox_root: str) -> int:
    store = get_cut_mcp_job_store()
    count = 0
    for job in store.list_jobs():
        if str(job.get("state") or "") not in _ACTIVE_JOB_STATES:
            continue
        if str(job.get("route_mode") or "") != "background":
            continue
        input_payload = job.get("input") or {}
        if str(input_payload.get("sandbox_root") or "") != str(sandbox_root):
            continue
        count += 1
    return count


def _collect_project_jobs(*, project_id: str, sandbox_root: str, limit: int = 8) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    jobs: list[dict[str, Any]] = []
    for job in get_cut_mcp_job_store().list_jobs():
        input_payload = job.get("input") or {}
        if str(input_payload.get("project_id") or "") != str(project_id):
            continue
        if str(input_payload.get("sandbox_root") or "") != str(sandbox_root):
            continue
        jobs.append(job)
    jobs = sorted(jobs, key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""), reverse=True)
    active_jobs = [job for job in jobs if str(job.get("state") or "") in _ACTIVE_JOB_STATES]
    return jobs[:limit], active_jobs


def _compute_time_marker_ranking_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    kind_counts = {kind: 0 for kind in ("favorite", "comment", "cam", "insight", "chat")}
    media_scores: dict[str, float] = {}
    active_count = 0
    for item in items:
        if str(item.get("status") or "active") != "active":
            continue
        active_count += 1
        kind = str(item.get("kind") or "")
        if kind in kind_counts:
            kind_counts[kind] += 1
        media_path = str(item.get("media_path") or "")
        media_scores[media_path] = float(media_scores.get(media_path, 0.0)) + float(item.get("score") or 0.0)
    top_media = [
        {"media_path": media_path, "score": round(score, 4)}
        for media_path, score in sorted(media_scores.items(), key=lambda item: (-item[1], item[0]))[:8]
    ]
    return {
        "total_markers": len(items),
        "active_markers": active_count,
        "kind_counts": kind_counts,
        "top_media": top_media,
    }


def _build_sync_surface(
    *,
    project_id: str,
    timecode_sync_result: dict[str, Any] | None,
    audio_sync_result: dict[str, Any] | None,
    meta_sync_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    by_source: dict[str, dict[str, Any]] = {}

    def _ensure_item(source_path: str, reference_path: str) -> dict[str, Any]:
        item = by_source.get(source_path)
        if item is None:
            item = {
                "item_id": f"sync_surface_{len(by_source) + 1:04d}",
                "source_path": source_path,
                "reference_path": reference_path,
                "timecode": None,
                "waveform": None,
                "meta_sync": None,
                "recommended_method": None,
                "recommended_offset_sec": 0.0,
                "confidence": 0.0,
            }
            by_source[source_path] = item
        return item

    for entry in (timecode_sync_result or {}).get("items", []):
        source_path = str(entry.get("source_path") or "")
        reference_path = str(entry.get("reference_path") or "")
        if not source_path:
            continue
        item = _ensure_item(source_path, reference_path)
        item["timecode"] = dict(entry)
        item["recommended_method"] = "timecode"
        item["recommended_offset_sec"] = float(entry.get("detected_offset_sec") or 0.0)
        item["confidence"] = float(entry.get("confidence") or 0.0)

    for entry in (audio_sync_result or {}).get("items", []):
        source_path = str(entry.get("source_path") or "")
        reference_path = str(entry.get("reference_path") or "")
        if not source_path:
            continue
        item = _ensure_item(source_path, reference_path)
        item["waveform"] = dict(entry)
        if item["timecode"] is None:
            item["recommended_method"] = "waveform"
            item["recommended_offset_sec"] = float(entry.get("detected_offset_sec") or 0.0)
            item["confidence"] = float(entry.get("confidence") or 0.0)

    for entry in (meta_sync_result or {}).get("items", []):
        source_path = str(entry.get("source_path") or "")
        reference_path = str(entry.get("reference_path") or "")
        if not source_path:
            continue
        item = _ensure_item(source_path, reference_path)
        item["meta_sync"] = dict(entry)
        if item["timecode"] is None and item["waveform"] is None:
            item["recommended_method"] = "meta_sync"
            item["recommended_offset_sec"] = float(entry.get("suggested_offset_sec") or 0.0)
            item["confidence"] = float(entry.get("confidence") or 0.0)

    return {
        "schema_version": "cut_sync_surface_v1",
        "project_id": str(project_id),
        "items": list(by_source.values()),
        "generated_at": _utc_now_iso(),
    }


def _build_music_cue_summary(
    *,
    bootstrap_state: dict[str, Any] | None,
    music_sync_result: dict[str, Any] | None,
) -> dict[str, Any] | None:
    profile = (bootstrap_state or {}).get("profile") if isinstance(bootstrap_state, dict) else None
    profile = profile if isinstance(profile, dict) else {}
    music_track = profile.get("music_track") if isinstance(profile.get("music_track"), dict) else {}
    music_path = str((music_sync_result or {}).get("music_path") or music_track.get("path") or "")
    if not music_path:
        return None

    cue_points = [cue for cue in (music_sync_result or {}).get("cue_points", []) if isinstance(cue, dict)]
    phrases = [phrase for phrase in (music_sync_result or {}).get("phrases", []) if isinstance(phrase, dict)]
    downbeats = [value for value in (music_sync_result or {}).get("downbeats", []) if isinstance(value, (int, float))]
    tempo = (music_sync_result or {}).get("tempo") if isinstance((music_sync_result or {}).get("tempo"), dict) else {}
    track_label = str(music_track.get("relative_path") or os.path.basename(music_path) or music_path)
    top_cues = [
        {
            "cue_id": str(cue.get("cue_id") or ""),
            "label": str(cue.get("label") or ""),
            "start_sec": float(cue.get("start_sec") or 0.0),
            "cue_type": str(cue.get("cue_type") or ""),
            "confidence": float(cue.get("confidence") or 0.0),
        }
        for cue in sorted(
            cue_points,
            key=lambda item: (-float(item.get("confidence") or 0.0), float(item.get("start_sec") or 0.0)),
        )[:3]
    ]
    return {
        "schema_version": "cut_music_cue_summary_v1",
        "track_label": track_label,
        "music_path": music_path,
        "primary_candidate": True,
        "cue_point_count": len(cue_points),
        "phrase_count": len(phrases),
        "downbeat_count": len(downbeats),
        "tempo_bpm": float(tempo.get("bpm") or 0.0) if tempo else None,
        "tempo_confidence": float(tempo.get("confidence") or 0.0) if tempo else None,
        "top_cues": top_cues,
    }


def _resolve_music_sync_path(
    *,
    store: CutProjectStore,
    project: dict[str, Any],
    requested_path: str,
) -> tuple[str, str]:
    source_root = str(project.get("source_path") or "")

    def _normalize_candidate(raw: str) -> str:
        value = str(raw or "").strip()
        if not value:
            return ""
        if not os.path.isabs(value):
            value = os.path.join(source_root, value)
        return os.path.realpath(os.path.abspath(value))

    bootstrap_state = store.load_bootstrap_state()
    profile = (bootstrap_state or {}).get("profile") if isinstance(bootstrap_state, dict) else None
    profile = profile if isinstance(profile, dict) else {}
    music_track = profile.get("music_track") if isinstance(profile.get("music_track"), dict) else {}

    candidates: list[tuple[int, str, str]] = []
    explicit_path = _normalize_candidate(requested_path)
    if explicit_path:
        candidates.append((10, explicit_path, "request_path"))
    profile_path = _normalize_candidate(str(music_track.get("path") or music_track.get("relative_path") or ""))
    if profile_path:
        candidates.append((9, profile_path, "bootstrap_profile"))

    for path in _pick_audio_sync_media_paths(source_root, 12):
        name = os.path.basename(path).lower()
        score = 3 if any(token in name for token in ("punch", "music", "song", "score", "ost")) else 1
        candidates.append((score, os.path.realpath(path), "source_autodiscovery"))

    for _, path, reason in sorted(candidates, key=lambda item: (-item[0], item[1])):
        if os.path.isfile(path):
            return path, reason
    return "", "music_track_missing"


def _build_music_peak_times_from_signal(
    signal: list[float],
    *,
    sample_rate: int,
    frame_ms: int = 20,
) -> tuple[list[float], list[float]]:
    envelope = build_energy_envelope(signal, sample_rate, frame_ms=frame_ms)
    if not envelope:
        return [], []
    mean_value = sum(envelope) / max(1, len(envelope))
    variance = sum((value - mean_value) ** 2 for value in envelope) / max(1, len(envelope))
    std_value = math.sqrt(max(0.0, variance))
    threshold = max(0.08, mean_value + std_value * 0.45)
    frame_sec = frame_ms / 1000.0
    min_gap_frames = max(1, int(0.24 / max(frame_sec, 1e-6)))

    peaks: list[float] = []
    last_peak_idx = -min_gap_frames
    for idx in range(1, len(envelope) - 1):
        current = float(envelope[idx])
        if current < threshold:
            continue
        if current < float(envelope[idx - 1]) or current < float(envelope[idx + 1]):
            continue
        if idx - last_peak_idx < min_gap_frames:
            continue
        peaks.append(round(idx * frame_sec, 4))
        last_peak_idx = idx

    if not peaks:
        ranked = sorted(envelope, reverse=True)[: min(8, len(envelope))]
        if ranked:
            fallback_threshold = ranked[-1]
            peaks = [
                round(idx * frame_sec, 4)
                for idx, value in enumerate(envelope)
                if value >= fallback_threshold
            ][:8]
    return peaks, envelope


def _normalize_tempo_candidate(raw_bpm: float, bpm_hint: float | None) -> float:
    bpm = float(raw_bpm or 0.0)
    if bpm <= 0.0:
        return 0.0
    while bpm < 60.0:
        bpm *= 2.0
    while bpm > 180.0:
        bpm /= 2.0
    if bpm_hint is not None and bpm_hint > 0.0:
        candidates = [bpm / 4.0, bpm / 2.0, bpm, bpm * 2.0, bpm * 4.0]
        valid = [value for value in candidates if 40.0 <= value <= 240.0]
        if valid:
            bpm = min(valid, key=lambda value: abs(value - float(bpm_hint)))
    return round(max(40.0, min(240.0, bpm)), 3)


def _estimate_bpm_from_peak_times(peak_times: list[float], bpm_hint: float | None) -> tuple[float, float]:
    intervals = [
        float(peak_times[idx + 1] - peak_times[idx])
        for idx in range(len(peak_times) - 1)
        if 0.18 <= float(peak_times[idx + 1] - peak_times[idx]) <= 1.5
    ]
    if not intervals:
        fallback_bpm = _normalize_tempo_candidate(float(bpm_hint or 120.0), bpm_hint)
        fallback_confidence = 0.52 if bpm_hint is not None else 0.24
        return fallback_bpm, round(fallback_confidence, 3)

    ordered = sorted(intervals)
    median_interval = ordered[len(ordered) // 2]
    bpm = _normalize_tempo_candidate(60.0 / max(median_interval, 1e-6), bpm_hint)
    mean_interval = sum(intervals) / len(intervals)
    variance = sum((value - mean_interval) ** 2 for value in intervals) / len(intervals)
    cv = math.sqrt(max(0.0, variance)) / max(mean_interval, 1e-6)
    regularity = max(0.0, min(1.0, 1.0 - cv))
    coverage = max(0.0, min(1.0, len(intervals) / 24.0))
    confidence = max(0.18, min(0.97, 0.55 * regularity + 0.45 * coverage))
    return bpm, round(confidence, 3)


def _build_music_phrases(anchors: list[float], duration_sec: float) -> list[dict[str, Any]]:
    if duration_sec <= 0.0:
        return []
    clean = [round(max(0.0, float(value)), 4) for value in anchors if isinstance(value, (int, float))]
    clean = sorted({value for value in clean if value < duration_sec})
    if not clean or clean[0] > 0.001:
        clean.insert(0, 0.0)
    if clean[-1] < duration_sec:
        clean.append(round(duration_sec, 4))
    labels = ["Intro", "Lift", "Drive", "Break", "Push", "Finale", "Outro"]
    phrases: list[dict[str, Any]] = []
    for index in range(len(clean) - 1):
        start_sec = float(clean[index])
        end_sec = float(clean[index + 1])
        if end_sec - start_sec < 0.12:
            continue
        phrases.append(
            {
                "phrase_id": f"phrase_{index + 1:02d}",
                "start_sec": round(start_sec, 4),
                "end_sec": round(end_sec, 4),
                "label": labels[index % len(labels)],
                "energy": round(min(0.98, 0.58 + (0.07 * (index % 5))), 3),
            }
        )
    return phrases


def _build_music_cues(
    *,
    downbeats: list[float],
    envelope: list[float],
    duration_sec: float,
    tempo_bpm: float,
) -> list[dict[str, Any]]:
    if duration_sec <= 0.0:
        return []

    def _energy_at(time_sec: float) -> float:
        if not envelope:
            return 0.6
        idx = int((time_sec / max(duration_sec, 1e-6)) * max(0, len(envelope) - 1))
        idx = max(0, min(len(envelope) - 1, idx))
        peak = max(envelope) or 1.0
        return max(0.0, min(1.0, float(envelope[idx]) / peak))

    beat_period = 60.0 / max(float(tempo_bpm or 120.0), 1.0)
    selected: list[tuple[int, float, str]] = []
    for beat_index, time_sec in enumerate(downbeats):
        cue_type = ""
        energy = _energy_at(time_sec)
        if beat_index == 0:
            cue_type = "intro"
        elif beat_index % 8 == 0:
            cue_type = "phrase_turn"
        elif energy >= 0.78:
            cue_type = "drop"
        elif beat_index % 4 == 0:
            cue_type = "accent"
        if cue_type:
            selected.append((beat_index, float(time_sec), cue_type))

    if len(selected) < 2:
        for beat_index, time_sec in enumerate(downbeats[1:], start=1):
            if len(selected) >= 3:
                break
            selected.append((beat_index, float(time_sec), "accent"))

    label_map = {
        "intro": "Intro anchor",
        "phrase_turn": "Phrase turn",
        "drop": "Drop lead",
        "accent": "Accent hit",
    }
    cues: list[dict[str, Any]] = []
    for cue_index, (beat_index, time_sec, cue_type) in enumerate(selected[:8], start=1):
        energy = _energy_at(time_sec)
        confidence = max(0.45, min(0.98, 0.45 + energy * 0.45))
        cues.append(
            {
                "cue_id": f"cue_{cue_index:02d}",
                "start_sec": round(time_sec, 4),
                "end_sec": round(min(duration_sec, time_sec + max(0.18, beat_period * 0.35)), 4),
                "label": label_map.get(cue_type, "Music cue"),
                "cue_type": cue_type,
                "confidence": round(confidence, 3),
                "energy": round(max(0.2, energy), 3),
            }
        )
    return cues


def _analyze_music_track_fallback(
    *,
    path: str,
    bpm_hint: float | None,
    max_analysis_sec: int,
) -> dict[str, Any]:
    sample_rate = 1000
    sample_bytes = max(4096, min(262144, int(max_analysis_sec) * sample_rate))
    signal, degraded_mode, degraded_reason = _build_signal_proxy_from_bytes(path, sample_bytes)
    if not signal:
        bpm = _normalize_tempo_candidate(float(bpm_hint or 120.0), bpm_hint)
        return {
            "tempo_bpm": bpm,
            "tempo_confidence": 0.12,
            "downbeats": [0.0],
            "phrases": _build_music_phrases([0.0], 1.0),
            "cue_points": [
                {
                    "cue_id": "cue_01",
                    "start_sec": 0.0,
                    "end_sec": 0.2,
                    "label": "Intro anchor",
                    "cue_type": "intro",
                    "confidence": 0.3,
                    "energy": 0.3,
                }
            ],
            "derived_from": "music_sync_proxy_v1",
            "degraded_mode": True,
            "degraded_reason": degraded_reason or "signal_proxy_unavailable",
        }

    duration_sec = max(0.2, len(signal) / sample_rate)
    peak_times, envelope = _build_music_peak_times_from_signal(signal, sample_rate=sample_rate)
    tempo_bpm, tempo_confidence = _estimate_bpm_from_peak_times(peak_times, bpm_hint)
    beat_period = 60.0 / max(tempo_bpm, 1.0)
    if len(peak_times) < 4:
        peak_times = [
            round(step * beat_period, 4)
            for step in range(max(4, int(duration_sec / max(beat_period, 1e-6)) + 1))
            if (step * beat_period) < duration_sec
        ]
    downbeats = [round(value, 4) for idx, value in enumerate(peak_times) if idx % 4 == 0]
    if not downbeats:
        downbeats = [0.0]
    phrase_anchors = [value for idx, value in enumerate(downbeats) if idx % 2 == 0]
    phrases = _build_music_phrases(phrase_anchors, duration_sec)
    cue_points = _build_music_cues(
        downbeats=downbeats,
        envelope=envelope,
        duration_sec=duration_sec,
        tempo_bpm=tempo_bpm,
    )
    return {
        "tempo_bpm": tempo_bpm,
        "tempo_confidence": tempo_confidence,
        "downbeats": downbeats,
        "phrases": phrases,
        "cue_points": cue_points,
        "derived_from": "music_sync_proxy_v1",
        "degraded_mode": bool(degraded_mode),
        "degraded_reason": degraded_reason,
    }


def _try_native_music_sync_analysis(
    *,
    path: str,
    bpm_hint: float | None,
    max_analysis_sec: int,
) -> dict[str, Any]:
    try:
        import librosa  # type: ignore
        import numpy as np  # type: ignore
    except Exception as exc:
        return {"ok": False, "reason": f"native_deps_unavailable:{exc.__class__.__name__}"}

    try:
        y, sr = librosa.load(str(path), sr=22050, mono=True, duration=max_analysis_sec)
        if y is None or len(y) < int(sr * 0.8):
            return {"ok": False, "reason": "audio_too_short"}
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        tempo, beat_frames = librosa.beat.beat_track(
            onset_envelope=onset_env,
            sr=sr,
            start_bpm=float(bpm_hint or 120.0),
        )
        beat_times = [round(float(value), 4) for value in librosa.frames_to_time(beat_frames, sr=sr)]
        tempo_raw = float(np.asarray(tempo).reshape(-1)[0]) if np.asarray(tempo).size > 0 else 0.0
        tempo_bpm, tempo_confidence = _estimate_bpm_from_peak_times(beat_times, bpm_hint)
        if tempo_raw > 0.0:
            tempo_bpm = _normalize_tempo_candidate(tempo_raw, bpm_hint)
            tempo_confidence = min(0.98, max(tempo_confidence, 0.74))
        duration_sec = float(len(y) / max(1, sr))
        peak = float(np.max(onset_env)) if np.asarray(onset_env).size else 1.0
        envelope = [
            max(0.0, min(1.0, round(float(value) / max(peak, 1e-6), 4)))
            for value in np.asarray(onset_env).reshape(-1).tolist()
        ]
        downbeats = [round(value, 4) for idx, value in enumerate(beat_times) if idx % 4 == 0] or ([0.0] if beat_times else [])
        phrase_anchors = [value for idx, value in enumerate(downbeats) if idx % 2 == 0]
        phrases = _build_music_phrases(phrase_anchors, duration_sec)
        cue_points = _build_music_cues(
            downbeats=downbeats or beat_times,
            envelope=envelope,
            duration_sec=duration_sec,
            tempo_bpm=tempo_bpm,
        )
        return {
            "ok": True,
            "tempo_bpm": tempo_bpm,
            "tempo_confidence": tempo_confidence,
            "downbeats": downbeats or [0.0],
            "phrases": phrases,
            "cue_points": cue_points,
            "derived_from": "music_sync_native_v1",
            "degraded_mode": False,
            "degraded_reason": "",
        }
    except Exception as exc:
        return {"ok": False, "reason": f"native_runtime_error:{exc.__class__.__name__}"}


def _lookup_pulse_manifest_entry(path: str) -> dict[str, Any] | None:
    manifest_path = Path(__file__).resolve().parents[4] / "pulse" / "data" / "processed" / "jepa_training_manifest.jsonl"
    if not manifest_path.is_file():
        return None
    target_path = os.path.realpath(path)
    target_name = os.path.basename(target_path)
    try:
        with manifest_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    payload = json.loads(line)
                except Exception:
                    continue
                if not isinstance(payload, dict):
                    continue
                manifest_file = os.path.realpath(str(payload.get("path") or ""))
                if manifest_file == target_path or os.path.basename(manifest_file) == target_name:
                    return payload
    except Exception:
        return None
    return None


def _analyze_music_track(
    *,
    path: str,
    bpm_hint: float | None,
    max_analysis_sec: int,
) -> dict[str, Any]:
    manifest_entry = _lookup_pulse_manifest_entry(path)
    manifest_bpm = float((manifest_entry or {}).get("bpm_ref") or 0.0)
    native = _try_native_music_sync_analysis(path=path, bpm_hint=bpm_hint, max_analysis_sec=max_analysis_sec)
    if native.get("ok") is True:
        native.pop("ok", None)
        if manifest_bpm > 0.0:
            native["tempo_bpm"] = round(manifest_bpm, 3)
            native["tempo_confidence"] = max(float(native.get("tempo_confidence") or 0.0), 0.94)
            native["derived_from"] = "pulse_manifest_v1+native_audio_v1"
        return native
    fallback = _analyze_music_track_fallback(path=path, bpm_hint=bpm_hint, max_analysis_sec=max_analysis_sec)
    reason = str(native.get("reason") or "")
    if reason:
        fallback["degraded_mode"] = True
        fallback["degraded_reason"] = reason
    if manifest_bpm > 0.0:
        fallback["tempo_bpm"] = round(manifest_bpm, 3)
        fallback["tempo_confidence"] = max(float(fallback.get("tempo_confidence") or 0.0), 0.96)
        fallback["derived_from"] = "pulse_manifest_v1"
    return fallback


def _estimate_scene_target_bpm_from_timeline(
    timeline_state: dict[str, Any] | None,
    *,
    music_tempo_bpm: float | None,
) -> dict[str, Any]:
    lanes = (timeline_state or {}).get("lanes") if isinstance((timeline_state or {}).get("lanes"), list) else []
    video_clips: list[dict[str, Any]] = []
    for lane in lanes:
        if not isinstance(lane, dict):
            continue
        lane_type = str(lane.get("lane_type") or "")
        if "audio" in lane_type:
            continue
        for clip in lane.get("clips", []):
            if isinstance(clip, dict):
                video_clips.append(clip)
    if not video_clips:
        fallback_bpm = round(max(72.0, min(168.0, float(music_tempo_bpm or 96.0))))
        return {
            "target_bpm": fallback_bpm,
            "rhythm_profile": "steady",
            "cut_density_per_min": 0.0,
            "source_engine": "pulse_scene_fallback_v1",
        }

    ordered = sorted(video_clips, key=lambda clip: float(clip.get("start_sec") or 0.0))
    durations: list[float] = []
    total_duration = 0.0
    for index, clip in enumerate(ordered):
        start_sec = float(clip.get("start_sec") or 0.0)
        end_value = clip.get("end_sec")
        if isinstance(end_value, (int, float)):
            end_sec = float(end_value)
        elif isinstance(clip.get("duration_sec"), (int, float)):
            end_sec = start_sec + float(clip.get("duration_sec") or 0.0)
        elif index + 1 < len(ordered):
            end_sec = float(ordered[index + 1].get("start_sec") or start_sec + 2.0)
        else:
            end_sec = start_sec + 2.5
        duration = max(0.1, end_sec - start_sec)
        durations.append(duration)
        total_duration = max(total_duration, end_sec)

    cut_count = max(0, len(ordered) - 1)
    cut_density_per_min = (cut_count / max(total_duration, 1e-6)) * 60.0
    mean_duration = sum(durations) / max(1, len(durations))
    variance = sum((value - mean_duration) ** 2 for value in durations) / max(1, len(durations))
    duration_cv = math.sqrt(max(0.0, variance)) / max(mean_duration, 1e-6)
    motion_volatility = max(0.0, min(1.0, duration_cv))
    if cut_density_per_min > 28.0:
        rhythm_profile = "aggressive"
    elif cut_density_per_min > 16.0:
        rhythm_profile = "dynamic"
    else:
        rhythm_profile = "steady"
    target_bpm = int(max(72, min(168, round(78 + cut_density_per_min * 1.6 + motion_volatility * 22.0))))
    return {
        "target_bpm": target_bpm,
        "rhythm_profile": rhythm_profile,
        "cut_density_per_min": round(cut_density_per_min, 2),
        "source_engine": "pulse_scene_proxy_v1",
    }


def _build_rhythm_surface(
    *,
    project_id: str,
    music_sync_result: dict[str, Any] | None,
    timeline_state: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(music_sync_result, dict):
        return None

    music_path = str(music_sync_result.get("music_path") or "")
    tempo = music_sync_result.get("tempo") if isinstance(music_sync_result.get("tempo"), dict) else {}
    music_tempo_bpm = float(tempo.get("bpm") or 0.0) if tempo else 0.0
    scene_binding = _estimate_scene_target_bpm_from_timeline(
        timeline_state,
        music_tempo_bpm=music_tempo_bpm or None,
    )
    target_bpm = float(scene_binding.get("target_bpm") or 0.0)
    bpm_delta = round(target_bpm - music_tempo_bpm, 3) if music_tempo_bpm > 0.0 and target_bpm > 0.0 else None
    cue_points = [cue for cue in music_sync_result.get("cue_points", []) if isinstance(cue, dict)]
    downbeats = [float(value) for value in music_sync_result.get("downbeats", []) if isinstance(value, (int, float))]

    items: list[dict[str, Any]] = []
    recommendation_map = {
        "drop": "accent_cut",
        "phrase_turn": "phrase_bridge",
        "accent": "micro_hit",
        "intro": "establish",
        "downbeat": "downbeat_lock",
    }
    for index, cue in enumerate(cue_points[:24], start=1):
        cue_type = str(cue.get("cue_type") or "accent")
        items.append(
            {
                "item_id": f"rhythm_{index:04d}",
                "start_sec": round(float(cue.get("start_sec") or 0.0), 4),
                "end_sec": round(float(cue.get("end_sec") or cue.get("start_sec") or 0.0), 4),
                "label": str(cue.get("label") or "Music cue"),
                "cue_type": cue_type,
                "confidence": round(float(cue.get("confidence") or 0.0), 3),
                "energy": round(float(cue.get("energy") or 0.0), 3),
                "target_bpm": target_bpm or None,
                "music_bpm": music_tempo_bpm or None,
                "bpm_delta": bpm_delta,
                "recommendation": recommendation_map.get(cue_type, "accent_cut"),
            }
        )
    if not items:
        for index, time_sec in enumerate(downbeats[:12], start=1):
            items.append(
                {
                    "item_id": f"rhythm_{index:04d}",
                    "start_sec": round(float(time_sec), 4),
                    "end_sec": round(float(time_sec), 4),
                    "label": f"Downbeat {index}",
                    "cue_type": "downbeat",
                    "confidence": 0.55,
                    "energy": 0.5,
                    "target_bpm": target_bpm or None,
                    "music_bpm": music_tempo_bpm or None,
                    "bpm_delta": bpm_delta,
                    "recommendation": "downbeat_lock",
                }
            )

    return {
        "schema_version": "cut_rhythm_surface_v1",
        "project_id": str(project_id),
        "music_path": music_path,
        "music_tempo_bpm": music_tempo_bpm or None,
        "scene_target_bpm": target_bpm or None,
        "bpm_delta": bpm_delta,
        "rhythm_profile": str(scene_binding.get("rhythm_profile") or "steady"),
        "cut_density_per_min": float(scene_binding.get("cut_density_per_min") or 0.0),
        "source_engine": str(scene_binding.get("source_engine") or "pulse_scene_fallback_v1"),
        "items": items,
        "generated_at": _utc_now_iso(),
    }


def _run_audio_sync_method(
    method: str,
    reference_signal: list[float],
    candidate_signal: list[float],
    sample_rate: int,
) -> Any:
    if method == "peak_only":
        return detect_peak_offset(reference_signal, candidate_signal, sample_rate)
    if method == "correlation":
        return detect_offset_via_correlation(reference_signal, candidate_signal, sample_rate)
    return detect_offset_hybrid(reference_signal, candidate_signal, sample_rate)


def _build_slice_windows_from_signal(
    signal: list[float],
    *,
    frame_ms: int,
    silence_threshold: float,
    min_silence_ms: int,
    keep_silence_ms: int,
) -> list[dict[str, Any]]:
    windows = derive_pause_windows_from_silence(
        signal,
        1000,
        frame_ms=frame_ms,
        silence_threshold=silence_threshold,
        min_silence_ms=min_silence_ms,
        keep_silence_ms=keep_silence_ms,
    )
    return [
        {
            "start_sec": float(window.start_sec),
            "end_sec": float(window.end_sec),
            "duration_sec": round(float(window.end_sec) - float(window.start_sec), 4),
            "confidence": float(window.confidence),
            "method": str(window.method),
        }
        for window in windows
    ]


def _build_time_marker(body: CutTimeMarkerApplyRequest, project_id: str, timeline_id: str) -> dict[str, Any]:
    if body.end_sec < body.start_sec:
        raise ValueError("end_sec must be >= start_sec")
    media_path = str(body.media_path or "").strip()
    if not media_path:
        raise ValueError("media_path is required for marker creation")
    anchor_sec = body.anchor_sec
    if anchor_sec is not None and (anchor_sec < body.start_sec or anchor_sec > body.end_sec):
        raise ValueError("anchor_sec must be inside [start_sec, end_sec]")
    now = _utc_now_iso()
    return {
        "marker_id": str(body.marker_id or f"marker_{uuid4().hex[:12]}"),
        "schema_version": "cut_time_marker_v1",
        "project_id": str(project_id),
        "timeline_id": str(timeline_id),
        "media_path": media_path,
        "kind": str(body.kind),
        "start_sec": float(body.start_sec),
        "end_sec": float(body.end_sec),
        "anchor_sec": anchor_sec,
        "score": float(body.score),
        "label": str(body.label or ""),
        "text": str(body.text or ""),
        "author": str(body.author or "cut_mcp"),
        "context_slice": deepcopy(body.context_slice) if body.context_slice is not None else None,
        "cam_payload": deepcopy(body.cam_payload) if body.cam_payload is not None else None,
        "chat_thread_id": body.chat_thread_id,
        "comment_thread_id": body.comment_thread_id,
        "source_engine": str(body.source_engine or "cut_mcp"),
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }


# MARKER_B1.5: Maximum codec/container coverage
PRODUCTION_VIDEO_FORMATS = {
    "camera_codecs": [
        "H.264", "H.265/HEVC", "H.265 10-bit",
        "ProRes Proxy", "ProRes LT", "ProRes 422", "ProRes 422 HQ", "ProRes 4444", "ProRes 4444 XQ",
        "DNxHD", "DNxHR LB", "DNxHR SQ", "DNxHR HQ", "DNxHR HQX", "DNxHR 444",
        "RED R3D", "BRAW", "ARRIRAW", "CinemaDNG",
        "Sony XAVC", "Sony XAVC-S", "Canon XF-AVC", "Panasonic V-Log",
        "GoPro CineForm", "AV1", "VP9",
        "MPEG-2", "MJPEG", "FFV1",
    ],
    "containers": [
        "MOV", "MP4", "MXF", "AVI", "MKV", "MTS", "M2TS", "TS",
        "WebM", "OGG", "FLV", "GXF", "3GP", "WMV", "ASF", "F4V",
    ],
    "audio": [
        "WAV", "AIFF", "MP3", "AAC", "AAC-LC", "AAC-HE",
        "FLAC", "ALAC", "M4A", "OGG/Vorbis", "Opus",
        "AC-3", "E-AC-3", "DTS", "DTS-HD", "Dolby TrueHD",
        "PCM 16-bit", "PCM 24-bit", "PCM 32-bit float",
    ],
    "images": ["JPEG", "PNG", "TIFF", "EXR", "DPX", "BMP", "WebP", "JPEG 2000", "TGA"],
    "documents": ["MD", "TXT", "PDF", "SRT", "VTT", "ASS", "SSA"],
    "projects": ["FCP XML", "FCPXML", "AAF", "EDL", "OTIO"],
    "resolutions": ["SD", "HD", "FHD", "2K", "DCI 2K", "4K", "DCI 4K", "6K", "8K"],
    "frame_rates": [23.976, 24, 25, 29.97, 30, 48, 50, 59.94, 60, 100, 120, 240],
}

# Browser/Electron native playback — no proxy needed
NATIVE_VIDEO_EXT = {"mp4", "m4v", "webm", "ogg", "mov", "m4a", "3gp"}

# Heavy/broadcast containers — proxy recommended for smooth editing
PROXY_RECOMMENDED_EXT = {
    "mxf", "avi", "mkv", "mts", "m2ts", "ts", "gxf",
    "flv", "f4v", "wmv", "asf", "vob", "mpg", "mpeg",
}

# Camera RAW — always needs transcode
TRANSCODE_REQUIRED_EXT = {"r3d", "braw", "ari", "dng", "cin", "dpx", "exr"}

# All supported audio extensions
AUDIO_EXT = {
    "wav", "aiff", "aif", "mp3", "aac", "m4a", "flac", "alac",
    "ogg", "oga", "opus", "wma", "ac3", "eac3", "dts", "mka",
}


def _resolve_asset_path(path: str, sandbox_root: str = "") -> Path:
    p = Path(str(path or "").strip())
    if p.is_absolute():
        return p
    if sandbox_root:
        return (Path(sandbox_root) / p).resolve()
    return p.resolve()


# MARKER_B1-CLEANUP: _probe_ffprobe_metadata and _probe_clip_duration removed.
# Use cut_codec_probe.probe_file() and probe_duration() instead.


def _collect_export_material(
    *,
    store: CutProjectStore,
    project_id: str,
    timeline_id: str,
    include_archived_markers: bool,
) -> dict[str, Any]:
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(project_id):
        raise HTTPException(status_code=404, detail="CUT project not found")

    timeline = store.load_timeline_state()
    if timeline is None:
        raise HTTPException(status_code=404, detail="CUT timeline state not found")
    resolved_timeline_id = str(timeline.get("timeline_id") or "main")
    if timeline_id and str(timeline_id) != resolved_timeline_id:
        raise HTTPException(status_code=404, detail="CUT timeline not found")

    clips: list[dict[str, Any]] = []
    duration_sec = 0.0
    for lane in timeline.get("lanes", []) or []:
        for clip in lane.get("clips", []) or []:
            start_sec = float(clip.get("start_sec") or 0.0)
            clip_duration = max(0.0, float(clip.get("duration_sec") or 0.0))
            end_sec = start_sec + clip_duration
            duration_sec = max(duration_sec, end_sec)
            clips.append(
                {
                    "clip_id": str(clip.get("clip_id") or ""),
                    "name": str(Path(str(clip.get("source_path") or "")).name or clip.get("clip_id") or "clip"),
                    "source_path": str(clip.get("source_path") or ""),
                    "lane_id": str(lane.get("lane_id") or ""),
                    "start_sec": start_sec,
                    "end_sec": end_sec,
                    "duration_sec": clip_duration,
                }
            )

    marker_bundle = store.load_time_marker_bundle() or {}
    raw_items = list(marker_bundle.get("items") or [])
    markers: list[dict[str, Any]] = []
    for item in raw_items:
        status = str(item.get("status") or "active")
        if status != "active" and not include_archived_markers:
            continue
        markers.append(
            {
                "marker_id": str(item.get("marker_id") or ""),
                "media_path": str(item.get("media_path") or ""),
                "time_sec": float(item.get("anchor_sec") if item.get("anchor_sec") is not None else item.get("start_sec") or 0.0),
                "start_sec": float(item.get("start_sec") or 0.0),
                "end_sec": float(item.get("end_sec") or item.get("start_sec") or 0.0),
                "kind": str(item.get("kind") or "comment"),
                "comment": str(item.get("text") or item.get("label") or ""),
                "color": str(item.get("kind") or "comment"),
                "comment_thread_id": str(item.get("comment_thread_id") or ""),
            }
        )

    return {
        "project": project,
        "timeline": timeline,
        "clips": clips,
        "markers": markers,
        "duration_sec": duration_sec,
    }


def _build_otio_export(project_name: str, sequence_name: str, clips: list[dict[str, Any]], fps: int) -> dict[str, Any]:
    track_children = []
    for clip in clips:
        start = float(clip.get("start_sec") or 0.0)
        dur = float(clip.get("duration_sec") or 0.0)
        track_children.append(
            {
                "OTIO_SCHEMA": "Clip.2",
                "name": str(clip.get("name") or "clip"),
                "source_range": {
                    "OTIO_SCHEMA": "TimeRange.1",
                    "start_time": {"OTIO_SCHEMA": "RationalTime.1", "value": 0, "rate": fps},
                    "duration": {"OTIO_SCHEMA": "RationalTime.1", "value": round(dur * fps), "rate": fps},
                },
                "metadata": {
                    "vetka": {
                        "source_path": str(clip.get("source_path") or ""),
                        "timeline_start_sec": start,
                    }
                },
            }
        )
    return {
        "OTIO_SCHEMA": "Timeline.1",
        "name": sequence_name,
        "metadata": {"project_name": project_name},
        "tracks": {
            "OTIO_SCHEMA": "Stack.1",
            "children": [
                {
                    "OTIO_SCHEMA": "Track.1",
                    "name": "V1",
                    "kind": "Video",
                    "children": track_children,
                }
            ],
        },
    }


def _build_edl_export(sequence_name: str, clips: list[dict[str, Any]], fps: int) -> str:
    def tc(sec: float) -> str:
        total_frames = max(0, int(round(sec * fps)))
        hh = total_frames // (fps * 3600)
        mm = (total_frames // (fps * 60)) % 60
        ss = (total_frames // fps) % 60
        ff = total_frames % fps
        return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"

    lines = [f"TITLE: {sequence_name}", "FCM: NON-DROP FRAME"]
    for idx, clip in enumerate(clips, start=1):
        start = float(clip.get("start_sec") or 0.0)
        end = float(clip.get("end_sec") or start)
        name = str(clip.get("name") or f"clip_{idx}")
        event = f"{idx:03d}  AX       V     C        00:00:00:00 {tc(end-start)} {tc(start)} {tc(end)}"
        lines.append(event)
        lines.append(f"* FROM CLIP NAME: {name}")
    return "\n".join(lines) + "\n"


def _srt_ts(sec: float) -> str:
    total_ms = max(0, int(round(sec * 1000)))
    hh = total_ms // 3_600_000
    mm = (total_ms // 60_000) % 60
    ss = (total_ms // 1_000) % 60
    ms = total_ms % 1_000
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


def _serialize_srt_marker(index: int, marker: dict[str, Any]) -> str:
    start_sec = float(marker.get("start_sec") or marker.get("time_sec") or 0.0)
    end_sec = max(start_sec, float(marker.get("end_sec") or start_sec + 1.0))
    meta = {
        "kind": str(marker.get("kind") or "comment"),
        "marker_id": str(marker.get("marker_id") or ""),
        "media_path": str(marker.get("media_path") or ""),
        "comment_thread_id": str(marker.get("comment_thread_id") or ""),
    }
    meta_text = json.dumps(meta, ensure_ascii=False, separators=(",", ":"))
    comment = str(marker.get("comment") or "")
    return f"{index}\n{_srt_ts(start_sec)} --> {_srt_ts(end_sec)}\n{{{meta_text}}} {comment}\n"


def _extract_marker_meta_from_srt(text: str) -> tuple[dict[str, Any], str]:
    line = str(text or "").strip()
    if not line.startswith("{"):
        return {}, line
    try:
        end = line.index("}")
        raw_meta = line[1:end]
        meta = json.loads(raw_meta)
        note = line[end + 1 :].strip()
        return (meta if isinstance(meta, dict) else {}), note
    except Exception:
        return {}, line


def _social_presets_manifest() -> dict[str, Any]:
    return {
        "youtube": {"aspect_ratio": "16:9", "recommended": {"codec": "H.264", "resolution": "1920x1080"}, "extras": ["chapters_from_markers", "thumbnail_from_favorite"]},
        "instagram_reels": {"aspect_ratio": "9:16", "recommended": {"codec": "H.264", "resolution": "1080x1920"}},
        "instagram_feed_1x1": {"aspect_ratio": "1:1", "recommended": {"codec": "H.264", "resolution": "1080x1080"}},
        "instagram_feed_4x5": {"aspect_ratio": "4:5", "recommended": {"codec": "H.264", "resolution": "1080x1350"}},
        "tiktok": {"aspect_ratio": "9:16", "recommended": {"codec": "H.264", "resolution": "1080x1920"}},
        "telegram": {"aspect_ratio": "16:9|9:16", "recommended": {"codec": "H.264", "resolution": "1280x720"}},
        "vk": {"aspect_ratio": "16:9", "recommended": {"codec": "H.264", "resolution": "1920x1080"}},
        "x": {"aspect_ratio": "16:9|1:1", "recommended": {"codec": "H.264", "resolution": "1280x720"}},
    }


def _player_lab_marker_to_apply_request(
    payload: PlayerLabMarkerImportItem | PlayerLabProvisionalEventImportItem,
    *,
    sandbox_root: str,
    project_id: str,
    timeline_id: str,
    author: str,
) -> CutTimeMarkerApplyRequest:
    if isinstance(payload, PlayerLabMarkerImportItem):
        end_sec = max(float(payload.end_sec), float(payload.start_sec))
        anchor_sec = payload.anchor_sec
        if anchor_sec is None:
            anchor_sec = round((float(payload.start_sec) + end_sec) / 2.0, 4)
        return CutTimeMarkerApplyRequest(
            sandbox_root=sandbox_root,
            project_id=project_id,
            timeline_id=timeline_id,
            author=str(payload.author or author or "player_lab_import"),
            op="create",
            marker_id=str(payload.marker_id or ""),
            media_path=str(payload.media_path or ""),
            kind=payload.kind,
            start_sec=float(payload.start_sec),
            end_sec=end_sec,
            anchor_sec=anchor_sec,
            score=float(payload.score),
            label=str(payload.label or ""),
            text=str(payload.text or ""),
            context_slice=deepcopy(payload.context_slice) if payload.context_slice is not None else None,
            cam_payload=deepcopy(payload.cam_payload) if payload.cam_payload is not None else None,
            chat_thread_id=payload.chat_thread_id,
            comment_thread_id=payload.comment_thread_id,
            source_engine=str(payload.source_engine or "player_lab"),
        )

    end_sec = max(float(payload.end_sec), float(payload.start_sec))
    anchor_sec = round((float(payload.start_sec) + end_sec) / 2.0, 4)
    return CutTimeMarkerApplyRequest(
        sandbox_root=sandbox_root,
        project_id=project_id,
        timeline_id=timeline_id,
        author=str(author or "player_lab_import"),
        op="create",
        marker_id=str(payload.provisional_event_id or ""),
        media_path=str(payload.media_path or ""),
        kind="comment",
        start_sec=float(payload.start_sec),
        end_sec=end_sec,
        anchor_sec=anchor_sec,
        score=0.55,
        label="Player Lab capture",
        text=str(payload.text or payload.event_type or "Player Lab provisional event"),
        context_slice={
            "mode": "player_lab_provisional_v1",
            "event_type": str(payload.event_type or ""),
            "export_mode": str(payload.export_mode or ""),
            "migration_status": str(payload.migration_status or ""),
        },
        source_engine="player_lab_provisional",
    )



def _default_editorial_intent_for_marker(marker: dict[str, Any]) -> str:
    kind = str(marker.get("kind") or "")
    return {
        "favorite": "accent_cut",
        "comment": "commentary_hold",
        "cam": "camera_emphasis",
        "insight": "insight_emphasis",
        "chat": "dialogue_anchor",
    }.get(kind, "accent_cut")


def _build_montage_decision_from_marker(
    marker: dict[str, Any],
    *,
    marker_bundle_revision: int,
    decision_id: str,
    lane_id: str,
    decision_status: str,
    author: str,
    editorial_intent: str,
) -> dict[str, Any]:
    start_sec = float(marker.get("start_sec") or 0.0)
    end_sec = float(marker.get("end_sec") or start_sec)
    anchor_sec = marker.get("anchor_sec")
    if anchor_sec is None:
        anchor_sec = round((start_sec + end_sec) / 2.0, 4)
    now = _utc_now_iso()
    return {
        "decision_id": decision_id,
        "source_family": "marker",
        "cue_provenance_ids": [str(marker.get("marker_id") or "")],
        "confidence": float(marker.get("score") or 0.0),
        "score": float(marker.get("score") or 0.0),
        "editorial_intent": editorial_intent or _default_editorial_intent_for_marker(marker),
        "status": decision_status,
        "timeline_id": str(marker.get("timeline_id") or "main"),
        "lane_id": str(lane_id or "V1"),
        "anchor_sec": float(anchor_sec),
        "start_sec": start_sec,
        "end_sec": end_sec,
        "source_bundle_id": "time_marker_bundle",
        "source_bundle_revision": int(marker_bundle_revision),
        "created_at": now,
        "updated_at": now,
        "author": str(author or "cut_mcp"),
    }



# _run_cut_bootstrap_job — moved to cut_routes_bootstrap.py (MARKER_B65)


# MARKER_B74: Moved from cut_routes.py — needed by _run_cut_scene_assembly_job
def _infer_cut_asset_kind(modality: str, lane_type: str) -> str:
    if modality in {"video", "audio"}:
        return modality
    if lane_type.startswith("video"):
        return "video"
    if lane_type.startswith("audio"):
        return "audio"
    return "media"


def _build_initial_scene_graph(
    project: dict[str, Any], timeline_state: dict[str, Any], graph_id: str,
    *, store: CutProjectStore | None = None,
) -> dict[str, Any]:
    """Build initial scene graph from timeline state. MARKER_B74: moved from cut_routes.py."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    scenes: dict[str, dict[str, Any]] = {}
    scene_order: list[str] = []
    take_node_ids: dict[tuple[str, str], str] = {}
    take_index_by_scene: dict[str, int] = {}
    asset_counter = 0
    take_counter = 0

    for lane in timeline_state.get("lanes", []):
        lane_id = str(lane.get("lane_id") or "")
        lane_type = str(lane.get("lane_type") or "")
        for clip in lane.get("clips", []):
            scene_id = str(clip.get("scene_id") or "").strip() or "scene_01"
            take_id = str(clip.get("take_id") or "").strip() or "take_01"
            record_id = str(clip.get("record_id") or "").strip() or take_id
            source_path = str(clip.get("source_path") or "")
            clip_id = str(clip.get("clip_id") or "")
            duration_sec = float(clip.get("duration_sec") or 0.0)
            modality = _infer_cut_media_modality(source_path)
            if scene_id not in scenes:
                scene_order.append(scene_id)
                scene_label = scene_id.replace("_", " ").title()
                scene_node = {
                    "node_id": scene_id,
                    "node_type": SCENE_GRAPH_NODE_SCENE,
                    "label": scene_label,
                    "record_ref": None,
                    "metadata": {
                        "timeline_id": str(timeline_state.get("timeline_id") or "main"),
                        "timeline_lane": lane_id,
                        "scene_index": len(scene_order),
                        "summary": "",
                        "lane_ids": [lane_id],
                        "source_paths": [],
                        "take_count": 0,
                        "asset_count": 0,
                        "clip_count": 0,
                        "duration_sec": 0.0,
                    },
                }
                scenes[scene_id] = scene_node
                nodes.append(scene_node)
            take_key = (scene_id, take_id)
            if take_key not in take_node_ids:
                take_counter += 1
                take_index_by_scene[scene_id] = take_index_by_scene.get(scene_id, 0) + 1
                take_node_id = f"take_node_{take_counter:04d}"
                take_node_ids[take_key] = take_node_id
                nodes.append(
                    {
                        "node_id": take_node_id,
                        "node_type": SCENE_GRAPH_NODE_TAKE,
                        "label": take_id.replace("_", " ").title(),
                        "record_ref": record_id,
                        "metadata": {
                            "scene_id": scene_id,
                            "take_id": take_id,
                            "take_index": take_index_by_scene[scene_id],
                            "lane_id": lane_id,
                            "lane_type": lane_type,
                            "clip_id": clip_id,
                            "source_path": source_path,
                            "duration_sec": duration_sec,
                            "modality": modality,
                        },
                    }
                )
                edges.append(
                    {
                        "edge_id": f"edge_contains_{scene_id}_{take_counter:04d}",
                        "edge_type": SCENE_GRAPH_EDGE_CONTAINS,
                        "source": scene_id,
                        "target": take_node_id,
                        "weight": 1.0,
                    }
                )
                scene_meta = scenes[scene_id]["metadata"]
                scene_meta["take_count"] = int(scene_meta.get("take_count") or 0) + 1
            asset_counter += 1
            asset_node_id = f"asset_{asset_counter:04d}"
            asset_label = os.path.basename(source_path) or asset_node_id
            asset_meta: dict[str, Any] = {
                        "scene_id": scene_id,
                        "take_id": take_id,
                        "clip_id": clip_id,
                        "source_path": source_path,
                        "start_sec": float(clip.get("start_sec") or 0.0),
                        "duration_sec": duration_sec,
                        "timeline_lane": lane_id,
                        "lane_type": lane_type,
                        "asset_kind": _infer_cut_asset_kind(modality, lane_type),
                        "modality": modality,
            }
            if clip.get("thumbnail_path"):
                asset_meta["thumbnail_path"] = clip["thumbnail_path"]
            if clip.get("source_in") is not None:
                asset_meta["source_in"] = clip["source_in"]
                asset_meta["source_out"] = clip.get("source_out", 0.0)
            nodes.append(
                {
                    "node_id": asset_node_id,
                    "node_type": SCENE_GRAPH_NODE_ASSET,
                    "label": asset_label,
                    "record_ref": record_id,
                    "metadata": asset_meta,
                }
            )
            edges.append(
                {
                    "edge_id": f"edge_references_{asset_counter:04d}",
                    "edge_type": SCENE_GRAPH_EDGE_REFERENCES,
                    "source": take_node_ids[take_key],
                    "target": asset_node_id,
                    "weight": 1.0,
                }
            )
            scene_meta = scenes[scene_id]["metadata"]
            scene_meta["asset_count"] = int(scene_meta.get("asset_count") or 0) + 1
            scene_meta["clip_count"] = int(scene_meta.get("clip_count") or 0) + 1
            scene_meta["duration_sec"] = round(float(scene_meta.get("duration_sec") or 0.0) + duration_sec, 4)
            if lane_id not in scene_meta["lane_ids"]:
                scene_meta["lane_ids"].append(lane_id)
            if source_path and source_path not in scene_meta["source_paths"]:
                scene_meta["source_paths"].append(source_path)

    for index in range(len(scene_order) - 1):
        edges.append(
            {
                "edge_id": f"edge_follows_{index + 1:04d}",
                "edge_type": SCENE_GRAPH_EDGE_FOLLOWS,
                "source": scene_order[index],
                "target": scene_order[index + 1],
                "weight": 1.0,
            }
        )

    # MARKER_189.4: Inject scanner SignalEdge[] as semantic_match edges
    if store is not None:
        smr = store.load_scan_matrix_result()
        if smr and isinstance(smr.get("items"), list):
            scanner_edge_counter = 0
            for item in smr["items"]:
                for scan_key in ("video_scan", "audio_scan"):
                    scan_data = item.get(scan_key) or {}
                    for edge in scan_data.get("edges") or []:
                        scanner_edge_counter += 1
                        edge_type = SCENE_GRAPH_EDGE_SEMANTIC_MATCH
                        channel = str(edge.get("channel", ""))
                        if channel == "temporal":
                            edge_type = SCENE_GRAPH_EDGE_FOLLOWS
                        edges.append({
                            "edge_id": f"edge_scanner_{scanner_edge_counter:04d}",
                            "edge_type": edge_type,
                            "source": str(edge.get("source", "")),
                            "target": str(edge.get("target", "")),
                            "weight": float(edge.get("confidence", 0.5)),
                            "metadata": {
                                "channel": channel,
                                "evidence": edge.get("evidence", []),
                                "source_type": edge.get("source_type", ""),
                                "target_type": edge.get("target_type", ""),
                            },
                        })

    for scene_id, scene_node in scenes.items():
        metadata = scene_node["metadata"]
        take_count = int(metadata.get("take_count") or 0)
        asset_count = int(metadata.get("asset_count") or 0)
        duration_sec = float(metadata.get("duration_sec") or 0.0)
        metadata["summary"] = f"{take_count} takes · {asset_count} assets · {duration_sec:.1f}s"
        metadata["source_paths"] = sorted(metadata.get("source_paths", []))

    return {
        "schema_version": "cut_scene_graph_v1",
        "project_id": str(project.get("project_id") or ""),
        "graph_id": str(graph_id or "main"),
        "revision": 1,
        "nodes": nodes,
        "edges": edges,
        "updated_at": _utc_now_iso(),
    }


def _run_cut_scene_assembly_job(job_id: str, body: CutSceneAssemblyRequest) -> None:
    job_store = get_cut_mcp_job_store()
    job_store.update_job(job_id, state="running", progress=0.2)
    try:
        store = CutProjectStore(body.sandbox_root)
        project = store.load_project()
        if project is None or str(project.get("project_id") or "") != str(body.project_id):
            job_store.update_job(
                job_id,
                state="error",
                progress=1.0,
                error={
                    "code": "project_not_found",
                    "message": "CUT project not found for scene assembly.",
                    "recoverable": True,
                },
            )
            return
        timeline_state = _build_initial_timeline_state(project, body.timeline_id, store=store)
        scene_graph = _build_initial_scene_graph(project, timeline_state, body.graph_id, store=store)
        store.save_timeline_state(timeline_state)
        store.save_scene_graph(scene_graph)
        job_store.update_job(
            job_id,
            state="done",
            progress=1.0,
            result={
                "success": True,
                "project_id": str(project.get("project_id") or ""),
                "timeline_state": timeline_state,
                "scene_graph": scene_graph,
            },
        )
    except Exception as exc:
        job_store.update_job(
            job_id,
            state="error",
            progress=1.0,
            error={
                "code": "scene_assembly_exception",
                "message": str(exc),
                "recoverable": False,
            },
        )


def _run_cut_waveform_build_job(job_id: str, body: CutWaveformBuildRequest) -> None:
    job_store = get_cut_mcp_job_store()
    job_store.update_job(job_id, state="running", progress=0.1)
    try:
        store = CutProjectStore(body.sandbox_root)
        project = store.load_project()
        if project is None or str(project.get("project_id") or "") != str(body.project_id):
            job_store.update_job(
                job_id,
                state="error",
                progress=1.0,
                error={
                    "code": "project_not_found",
                    "message": "CUT project not found for waveform build.",
                    "recoverable": True,
                },
            )
            return

        source_root = str(project.get("source_path") or "")
        media_paths = _discover_worker_media_files(source_root, int(body.limit))
        bundle_prev = store.load_waveform_bundle()
        revision = int((bundle_prev or {}).get("revision") or 0) + 1
        items: list[dict[str, Any]] = []
        degraded_count = 0

        if not media_paths:
            bundle = {
                "schema_version": "cut_waveform_bundle_v1",
                "project_id": str(project.get("project_id") or ""),
                "revision": revision,
                "items": [],
                "generated_at": _utc_now_iso(),
            }
            store.save_waveform_bundle(bundle)
            job_store.update_job(
                job_id,
                state="done",
                progress=1.0,
                degraded_mode=True,
                degraded_reason="no_media_files",
                result={
                    "success": True,
                    "worker_task": {
                        "schema_version": "cut_worker_task_v1",
                        "task_id": job_id,
                        "project_id": str(project.get("project_id") or ""),
                        "task_type": "waveform_build",
                        "route_mode": "background",
                        "priority": "normal",
                        "status": "done",
                        "input": {"bins": int(body.bins), "limit": int(body.limit)},
                        "output_ref": store.paths.waveform_bundle_path,
                        "degraded_mode": True,
                        "degraded_reason": "no_media_files",
                        "created_at": _utc_now_iso(),
                        "updated_at": _utc_now_iso(),
                    },
                    "waveform_bundle": bundle,
                },
            )
            return

        total = len(media_paths)
        for index, media_path in enumerate(media_paths, start=1):
            current_job = job_store.get_job(job_id)
            if current_job and bool(current_job.get("cancel_requested")):
                job_store.update_job(job_id, state="cancelled", progress=1.0)
                return
            bins, degraded_mode, degraded_reason = _build_waveform_proxy_from_bytes(media_path, int(body.bins))
            if degraded_mode:
                degraded_count += 1
            items.append(
                {
                    "item_id": f"waveform_{index:04d}",
                    "source_path": media_path,
                    "waveform_bins": bins,
                    "degraded_mode": degraded_mode,
                    "degraded_reason": degraded_reason,
                }
            )
            progress = 0.1 + (0.8 * index / total)
            job_store.update_job(job_id, progress=progress)

        bundle = {
            "schema_version": "cut_waveform_bundle_v1",
            "project_id": str(project.get("project_id") or ""),
            "revision": revision,
            "items": items,
            "generated_at": _utc_now_iso(),
        }
        store.save_waveform_bundle(bundle)
        degraded_mode = degraded_count > 0
        degraded_reason = "partial_waveform_proxy" if degraded_mode else ""
        worker_task = {
            "schema_version": "cut_worker_task_v1",
            "task_id": job_id,
            "project_id": str(project.get("project_id") or ""),
            "task_type": "waveform_build",
            "route_mode": "background",
            "priority": "normal",
            "status": "done",
            "input": {"bins": int(body.bins), "limit": int(body.limit)},
            "output_ref": store.paths.waveform_bundle_path,
            "degraded_mode": degraded_mode,
            "degraded_reason": degraded_reason,
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }
        job_store.update_job(
            job_id,
            state="done",
            progress=1.0,
            degraded_mode=degraded_mode,
            degraded_reason=degraded_reason,
            result={
                "success": True,
                "worker_task": worker_task,
                "waveform_bundle": bundle,
            },
        )
    except Exception as exc:
        job_store.update_job(
            job_id,
            state="error",
            progress=1.0,
            error={
                "code": "waveform_build_exception",
                "message": str(exc),
                "recoverable": False,
            },
        )


def _run_cut_transcript_normalize_job(job_id: str, body: CutTranscriptNormalizeRequest) -> None:
    job_store = get_cut_mcp_job_store()
    job_store.update_job(job_id, state="running", progress=0.1)
    try:
        store = CutProjectStore(body.sandbox_root)
        project = store.load_project()
        if project is None or str(project.get("project_id") or "") != str(body.project_id):
            job_store.update_job(
                job_id,
                state="error",
                progress=1.0,
                error={
                    "code": "project_not_found",
                    "message": "CUT project not found for transcript normalize.",
                    "recoverable": True,
                },
            )
            return

        source_root = str(project.get("source_path") or "")
        media_paths = _discover_worker_media_files(source_root, int(body.limit))
        bundle_prev = store.load_transcript_bundle()
        revision = int((bundle_prev or {}).get("revision") or 0) + 1
        items: list[dict[str, Any]] = []
        degraded_count = 0

        if not media_paths:
            bundle = {
                "schema_version": "cut_transcript_bundle_v1",
                "project_id": str(project.get("project_id") or ""),
                "revision": revision,
                "items": [],
                "generated_at": _utc_now_iso(),
            }
            store.save_transcript_bundle(bundle)
            job_store.update_job(
                job_id,
                state="done",
                progress=1.0,
                degraded_mode=True,
                degraded_reason="no_media_files",
                result={
                    "success": True,
                    "worker_task": {
                        "schema_version": "cut_worker_task_v1",
                        "task_id": job_id,
                        "project_id": str(project.get("project_id") or ""),
                        "task_type": "transcript_normalize",
                        "route_mode": "background",
                        "priority": "normal",
                        "status": "done",
                        "input": {
                            "limit": int(body.limit),
                            "segments_limit": int(body.segments_limit),
                            "max_transcribe_sec": body.max_transcribe_sec,
                        },
                        "output_ref": store.paths.transcript_bundle_path,
                        "degraded_mode": True,
                        "degraded_reason": "no_media_files",
                        "created_at": _utc_now_iso(),
                        "updated_at": _utc_now_iso(),
                    },
                    "transcript_bundle": bundle,
                },
            )
            return

        total = len(media_paths)
        request_context = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=None)))
        for index, media_path in enumerate(media_paths, start=1):
            current_job = job_store.get_job(job_id)
            if current_job and bool(current_job.get("cancel_requested")):
                job_store.update_job(job_id, state="cancelled", progress=1.0)
                return

            try:
                response = asyncio.run(
                    media_transcript_normalized(
                        MediaTranscriptNormalizeRequest(
                            path=media_path,
                            max_transcribe_sec=body.max_transcribe_sec,
                            segments_limit=int(body.segments_limit),
                        ),
                        request_context,
                    )
                )
                transcript_json = dict(response.get("transcript_normalized_json") or {})
                degraded_mode = bool(response.get("degraded_mode"))
                degraded_reason = str(response.get("degraded_reason") or "")
            except Exception as exc:
                transcript_json = {
                    "schema_version": "vetka_transcript_v1",
                    "path": media_path,
                    "modality": "",
                    "language": "",
                    "duration_sec": 0.0,
                    "source_engine": "none",
                    "text": "",
                    "segments": [],
                }
                degraded_mode = True
                degraded_reason = f"transcript_normalize_failed:{str(exc)[:80]}"

            if degraded_mode:
                degraded_count += 1
            items.append(
                {
                    "item_id": f"transcript_{index:04d}",
                    "source_path": media_path,
                    "transcript_normalized_json": transcript_json,
                    "degraded_mode": degraded_mode,
                    "degraded_reason": degraded_reason,
                }
            )
            progress = 0.1 + (0.8 * index / total)
            job_store.update_job(job_id, progress=progress)

        bundle = {
            "schema_version": "cut_transcript_bundle_v1",
            "project_id": str(project.get("project_id") or ""),
            "revision": revision,
            "items": items,
            "generated_at": _utc_now_iso(),
        }
        store.save_transcript_bundle(bundle)
        degraded_mode = degraded_count > 0
        degraded_reason = "partial_transcript_normalize" if degraded_mode else ""
        worker_task = {
            "schema_version": "cut_worker_task_v1",
            "task_id": job_id,
            "project_id": str(project.get("project_id") or ""),
            "task_type": "transcript_normalize",
            "route_mode": "background",
            "priority": "normal",
            "status": "done",
            "input": {
                "limit": int(body.limit),
                "segments_limit": int(body.segments_limit),
                "max_transcribe_sec": body.max_transcribe_sec,
            },
            "output_ref": store.paths.transcript_bundle_path,
            "degraded_mode": degraded_mode,
            "degraded_reason": degraded_reason,
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }
        job_store.update_job(
            job_id,
            state="done",
            progress=1.0,
            degraded_mode=degraded_mode,
            degraded_reason=degraded_reason,
            result={
                "success": True,
                "worker_task": worker_task,
                "transcript_bundle": bundle,
            },
        )
    except Exception as exc:
        job_store.update_job(
            job_id,
            state="error",
            progress=1.0,
            error={
                "code": "transcript_normalize_exception",
                "message": str(exc),
                "recoverable": False,
            },
        )


def _run_cut_thumbnail_build_job(job_id: str, body: CutThumbnailBuildRequest) -> None:
    job_store = get_cut_mcp_job_store()
    job_store.update_job(job_id, state="running", progress=0.1)
    try:
        store = CutProjectStore(body.sandbox_root)
        project = store.load_project()
        if project is None or str(project.get("project_id") or "") != str(body.project_id):
            job_store.update_job(
                job_id,
                state="error",
                progress=1.0,
                error={
                    "code": "project_not_found",
                    "message": "CUT project not found for thumbnail build.",
                    "recoverable": True,
                },
            )
            return

        source_root = str(project.get("source_path") or "")
        media_paths = _discover_worker_media_files(source_root, int(body.limit))
        bundle_prev = store.load_thumbnail_bundle()
        revision = int((bundle_prev or {}).get("revision") or 0) + 1
        items: list[dict[str, Any]] = []
        degraded_count = 0

        if not media_paths:
            bundle = {
                "schema_version": "cut_thumbnail_bundle_v1",
                "project_id": str(project.get("project_id") or ""),
                "revision": revision,
                "items": [],
                "generated_at": _utc_now_iso(),
            }
            store.save_thumbnail_bundle(bundle)
            job_store.update_job(
                job_id,
                state="done",
                progress=1.0,
                degraded_mode=True,
                degraded_reason="no_media_files",
                result={
                    "success": True,
                    "worker_task": {
                        "schema_version": "cut_worker_task_v1",
                        "task_id": job_id,
                        "project_id": str(project.get("project_id") or ""),
                        "task_type": "thumbnail_build",
                        "route_mode": "background",
                        "priority": "normal",
                        "status": "done",
                        "input": {
                            "limit": int(body.limit),
                            "waveform_bins": int(body.waveform_bins),
                            "preview_segments_limit": int(body.preview_segments_limit),
                        },
                        "output_ref": store.paths.thumbnail_bundle_path,
                        "degraded_mode": True,
                        "degraded_reason": "no_media_files",
                        "created_at": _utc_now_iso(),
                        "updated_at": _utc_now_iso(),
                    },
                    "thumbnail_bundle": bundle,
                },
            )
            return

        total = len(media_paths)
        request_context = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=None)))
        for index, media_path in enumerate(media_paths, start=1):
            current_job = job_store.get_job(job_id)
            if current_job and bool(current_job.get("cancel_requested")):
                job_store.update_job(job_id, state="cancelled", progress=1.0)
                return
            try:
                preview_payload = asyncio.run(
                    media_preview(
                        MediaPreviewRequest(
                            path=media_path,
                            waveform_bins=int(body.waveform_bins),
                            preview_segments_limit=int(body.preview_segments_limit),
                        ),
                        request_context,
                    )
                )
                preview_assets = preview_payload.get("preview_assets") or {}
                playback = preview_payload.get("playback") or {}
                degraded_mode = bool(preview_payload.get("degraded_mode"))
                degraded_reason = str(preview_payload.get("degraded_reason") or "")
                item = {
                    "item_id": f"thumbnail_{index:04d}",
                    "source_path": media_path,
                    "modality": str(preview_payload.get("modality") or "video"),
                    "duration_sec": float(preview_payload.get("duration_sec") or 0.0),
                    "poster_url": str(preview_assets.get("poster_url") or ""),
                    "animated_preview_url_300ms": str(preview_assets.get("animated_preview_url_300ms") or ""),
                    "source_url": str(playback.get("source_url") or ""),
                    "degraded_mode": degraded_mode,
                    "degraded_reason": degraded_reason,
                }
            except Exception as exc:
                degraded_mode = True
                degraded_reason = f"thumbnail_build_failed:{str(exc)[:80]}"
                item = {
                    "item_id": f"thumbnail_{index:04d}",
                    "source_path": media_path,
                    "modality": "video" if os.path.splitext(media_path)[1].lower() in {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"} else "audio",
                    "duration_sec": 0.0,
                    "poster_url": "",
                    "animated_preview_url_300ms": "",
                    "source_url": "",
                    "degraded_mode": True,
                    "degraded_reason": degraded_reason,
                }
            if degraded_mode:
                degraded_count += 1
            items.append(item)
            progress = 0.1 + (0.8 * index / total)
            job_store.update_job(job_id, progress=progress)

        bundle = {
            "schema_version": "cut_thumbnail_bundle_v1",
            "project_id": str(project.get("project_id") or ""),
            "revision": revision,
            "items": items,
            "generated_at": _utc_now_iso(),
        }
        store.save_thumbnail_bundle(bundle)
        degraded_mode = degraded_count > 0
        degraded_reason = "partial_thumbnail_build" if degraded_mode else ""
        worker_task = {
            "schema_version": "cut_worker_task_v1",
            "task_id": job_id,
            "project_id": str(project.get("project_id") or ""),
            "task_type": "thumbnail_build",
            "route_mode": "background",
            "priority": "normal",
            "status": "done",
            "input": {
                "limit": int(body.limit),
                "waveform_bins": int(body.waveform_bins),
                "preview_segments_limit": int(body.preview_segments_limit),
            },
            "output_ref": store.paths.thumbnail_bundle_path,
            "degraded_mode": degraded_mode,
            "degraded_reason": degraded_reason,
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }
        job_store.update_job(
            job_id,
            state="done",
            progress=1.0,
            degraded_mode=degraded_mode,
            degraded_reason=degraded_reason,
            result={
                "success": True,
                "worker_task": worker_task,
                "thumbnail_bundle": bundle,
            },
        )
    except Exception as exc:
        job_store.update_job(
            job_id,
            state="error",
            progress=1.0,
            error={
                "code": "thumbnail_build_exception",
                "message": str(exc),
                "recoverable": False,
            },
        )


def _run_cut_audio_sync_job(job_id: str, body: CutAudioSyncRequest) -> None:
    job_store = get_cut_mcp_job_store()
    job_store.update_job(job_id, state="running", progress=0.1)
    try:
        store = CutProjectStore(body.sandbox_root)
        project = store.load_project()
        if project is None or str(project.get("project_id") or "") != str(body.project_id):
            job_store.update_job(
                job_id,
                state="error",
                progress=1.0,
                error={
                    "code": "project_not_found",
                    "message": "CUT project not found for audio sync build.",
                    "recoverable": True,
                },
            )
            return

        source_root = str(project.get("source_path") or "")
        media_paths = _pick_audio_sync_media_paths(source_root, int(body.limit))
        result_prev = store.load_audio_sync_result()
        revision = int((result_prev or {}).get("revision") or 0) + 1
        items: list[dict[str, Any]] = []
        degraded_count = 0

        if len(media_paths) < 2:
            result = {
                "schema_version": "cut_audio_sync_result_v1",
                "project_id": str(project.get("project_id") or ""),
                "revision": revision,
                "items": [],
                "generated_at": _utc_now_iso(),
            }
            store.save_audio_sync_result(result)
            job_store.update_job(
                job_id,
                state="done",
                progress=1.0,
                degraded_mode=True,
                degraded_reason="insufficient_media_files",
                result={
                    "success": True,
                    "worker_task": {
                        "schema_version": "cut_worker_task_v1",
                        "task_id": job_id,
                        "project_id": str(project.get("project_id") or ""),
                        "task_type": "audio_sync",
                        "route_mode": "background",
                        "priority": "normal",
                        "status": "done",
                        "input": {
                            "limit": int(body.limit),
                            "sample_bytes": int(body.sample_bytes),
                            "method": str(body.method),
                        },
                        "output_ref": store.paths.audio_sync_result_path,
                        "degraded_mode": True,
                        "degraded_reason": "insufficient_media_files",
                        "created_at": _utc_now_iso(),
                        "updated_at": _utc_now_iso(),
                    },
                    "audio_sync_result": result,
                },
            )
            return

        reference_path = media_paths[0]
        reference_signal, reference_degraded, reference_reason = _build_signal_proxy_from_bytes(
            reference_path, int(body.sample_bytes)
        )
        if reference_degraded:
            degraded_count += 1

        total = max(1, len(media_paths) - 1)
        for index, media_path in enumerate(media_paths[1:], start=1):
            current_job = job_store.get_job(job_id)
            if current_job and bool(current_job.get("cancel_requested")):
                job_store.update_job(job_id, state="cancelled", progress=1.0)
                return
            candidate_signal, degraded_mode, degraded_reason = _build_signal_proxy_from_bytes(
                media_path, int(body.sample_bytes)
            )
            if reference_degraded or degraded_mode or not reference_signal or not candidate_signal:
                degraded_mode = True
                degraded_reason = degraded_reason or reference_reason or "signal_proxy_unavailable"
                sync_result = detect_offset_hybrid([], [], 1000)
            else:
                sync_result = _run_audio_sync_method(str(body.method), reference_signal, candidate_signal, 1000)
            if degraded_mode:
                degraded_count += 1
            items.append(
                {
                    "item_id": f"audio_sync_{index:04d}",
                    "reference_path": reference_path,
                    "source_path": media_path,
                    "detected_offset_sec": float(sync_result.detected_offset_sec),
                    "confidence": float(sync_result.confidence),
                    "method": str(sync_result.method),
                    "refinement_steps": 2 if "correlation" in str(sync_result.method) else 1,
                    "peak_value": float(sync_result.peak_value),
                    "degraded_mode": degraded_mode,
                    "degraded_reason": degraded_reason,
                }
            )
            progress = 0.1 + (0.8 * index / total)
            job_store.update_job(job_id, progress=progress)

        result = {
            "schema_version": "cut_audio_sync_result_v1",
            "project_id": str(project.get("project_id") or ""),
            "revision": revision,
            "items": items,
            "generated_at": _utc_now_iso(),
        }
        store.save_audio_sync_result(result)
        degraded_mode = degraded_count > 0
        degraded_reason = "partial_audio_sync" if degraded_mode else ""
        worker_task = {
            "schema_version": "cut_worker_task_v1",
            "task_id": job_id,
            "project_id": str(project.get("project_id") or ""),
            "task_type": "audio_sync",
            "route_mode": "background",
            "priority": "normal",
            "status": "done",
            "input": {
                "limit": int(body.limit),
                "sample_bytes": int(body.sample_bytes),
                "method": str(body.method),
            },
            "output_ref": store.paths.audio_sync_result_path,
            "degraded_mode": degraded_mode,
            "degraded_reason": degraded_reason,
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }
        job_store.update_job(
            job_id,
            state="done",
            progress=1.0,
            degraded_mode=degraded_mode,
            degraded_reason=degraded_reason,
            result={
                "success": True,
                "worker_task": worker_task,
                "audio_sync_result": result,
            },
        )
    except Exception as exc:
        job_store.update_job(
            job_id,
            state="error",
            progress=1.0,
            error={
                "code": "audio_sync_exception",
                "message": str(exc),
                "recoverable": False,
            },
        )


def _run_cut_scan_matrix_job(job_id: str, body: CutScanMatrixRequest) -> None:
    """MARKER_189.2 — Background job: run VideoScanner + AudioScanner on all media files."""
    from src.scanners.video_scanner import scan_video, VIDEO_EXTENSIONS
    from src.scanners.audio_scanner import scan_audio, AUDIO_EXTENSIONS

    job_store = get_cut_mcp_job_store()
    job_store.update_job(job_id, state="running", progress=0.05)
    try:
        store = CutProjectStore(body.sandbox_root)
        project = store.load_project()
        if project is None or str(project.get("project_id") or "") != str(body.project_id):
            job_store.update_job(
                job_id,
                state="error",
                progress=1.0,
                error={
                    "code": "project_not_found",
                    "message": "CUT project not found for scan matrix.",
                    "recoverable": True,
                },
            )
            return

        source_root = str(project.get("source_path") or "")
        media_paths = _discover_worker_media_files(source_root, int(body.limit))

        if not media_paths:
            job_store.update_job(
                job_id,
                state="done",
                progress=1.0,
                result={"success": True, "scan_results": [], "media_index": {}},
            )
            return

        scan_results: list[dict[str, Any]] = []
        media_index: dict[str, dict[str, Any]] = {}
        total = max(1, len(media_paths))
        thumb_dir = os.path.join(body.sandbox_root, "runtime_state", "thumbs")

        for idx, media_path in enumerate(media_paths):
            # Check cancel
            current_job = job_store.get_job(job_id)
            if current_job and bool(current_job.get("cancel_requested")):
                job_store.update_job(job_id, state="cancelled", progress=1.0)
                return

            ext = os.path.splitext(media_path)[1].lower()
            is_video = ext in VIDEO_EXTENSIONS
            is_audio = ext in AUDIO_EXTENSIONS

            file_result: dict[str, Any] = {
                "source_path": media_path,
                "video_scan": None,
                "audio_scan": None,
            }

            # Run VideoScanner on video files
            if is_video:
                vs = scan_video(
                    media_path,
                    thumbnail_dir=thumb_dir,
                    max_thumbs=int(body.max_thumbs_per_file),
                    scene_interval_sec=body.scene_interval_sec,
                    scene_threshold=body.scene_threshold,
                )
                file_result["video_scan"] = vs.to_dict()

                # Also run AudioScanner on the video (for waveform + STT)
                audio_meta = vs.metadata  # reuse ffprobe metadata
                aus = scan_audio(
                    media_path,
                    waveform_bins=int(body.waveform_bins),
                    run_stt=body.run_stt,
                    metadata=audio_meta,
                )
                file_result["audio_scan"] = aus.to_dict()

                # Build media_index entry
                meta = vs.metadata
                media_index[media_path] = {
                    "duration_sec": meta.duration_sec if meta else 0.0,
                    "codec": meta.codec if meta else "",
                    "width": meta.width if meta else 0,
                    "height": meta.height if meta else 0,
                    "fps": meta.fps if meta else 0.0,
                    "media_type": "video",
                    "segments_count": len(vs.segments),
                    "transcript_count": len(aus.transcript),
                    "thumbnail_count": len(vs.thumbnail_paths),
                    "extraction_status": vs.extraction_status,
                }
            elif is_audio:
                aus = scan_audio(
                    media_path,
                    waveform_bins=int(body.waveform_bins),
                    run_stt=body.run_stt,
                )
                file_result["audio_scan"] = aus.to_dict()
                media_index[media_path] = {
                    "duration_sec": aus.metadata.duration_sec if aus.metadata else 0.0,
                    "media_type": "audio",
                    "transcript_count": len(aus.transcript),
                    "extraction_status": aus.extraction_status,
                }

            scan_results.append(file_result)
            progress = 0.05 + 0.90 * (idx + 1) / total
            job_store.update_job(job_id, progress=round(progress, 3))

        # Save scan matrix result + media index
        scan_matrix_payload = {
            "schema_version": "cut_scan_matrix_result_v1",
            "project_id": str(project.get("project_id") or ""),
            "items": scan_results,
            "file_count": len(scan_results),
            "generated_at": _utc_now_iso(),
        }
        store.save_scan_matrix_result(scan_matrix_payload)

        media_index_payload = {
            "schema_version": "cut_media_index_v1",
            "project_id": str(project.get("project_id") or ""),
            "files": media_index,
            "generated_at": _utc_now_iso(),
        }
        store.save_media_index(media_index_payload)

        # MARKER_189.3: Triple memory write (Qdrant + JSON montage sheet)
        from src.services.cut_triple_write import cut_triple_write
        triple_result = cut_triple_write(
            scan_results,
            project_id=str(project.get("project_id") or ""),
            sandbox_root=str(body.sandbox_root),
        )

        # MARKER_B73_PRE: Pre-transcode non-native media for instant first Play.
        # Runs after scan completes — background thread pool, max 2 concurrent.
        pre_transcode_count = 0
        try:
            from src.api.routes.cut_routes_media import _get_or_transcode, _needs_browser_transcode
            from concurrent.futures import ThreadPoolExecutor

            non_native_paths: list[str] = []
            for mp in media_paths:
                mp_ext = os.path.splitext(mp)[1].lower()
                if mp_ext in VIDEO_EXTENSIONS:
                    try:
                        decision = _needs_browser_transcode(Path(mp))
                        if decision is not None:
                            non_native_paths.append(mp)
                    except Exception:
                        pass

            if non_native_paths:
                def _pretranscode(p: str) -> bool:
                    try:
                        result = _get_or_transcode(Path(p))
                        return result is not None
                    except Exception:
                        return False

                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(_pretranscode, p) for p in non_native_paths]
                    for f in futures:
                        try:
                            if f.result(timeout=600):
                                pre_transcode_count += 1
                        except Exception:
                            pass
        except ImportError:
            pass  # graceful if transcode module unavailable

        job_store.update_job(
            job_id,
            state="done",
            progress=1.0,
            result={
                "success": True,
                "file_count": len(scan_results),
                "media_index_path": store.paths.media_index_path,
                "scan_matrix_path": store.paths.scan_matrix_result_path,
                "triple_write": triple_result,
                "pre_transcoded": pre_transcode_count,
            },
        )
    except Exception as exc:
        job_store.update_job(
            job_id,
            state="error",
            progress=1.0,
            error={
                "code": "scan_matrix_exception",
                "message": str(exc),
                "recoverable": False,
            },
        )


def _run_cut_music_sync_job(job_id: str, body: CutMusicSyncRequest) -> None:
    job_store = get_cut_mcp_job_store()
    job_store.update_job(job_id, state="running", progress=0.1)
    try:
        store = CutProjectStore(body.sandbox_root)
        project = store.load_project()
        if project is None or str(project.get("project_id") or "") != str(body.project_id):
            job_store.update_job(
                job_id,
                state="error",
                progress=1.0,
                error={
                    "code": "project_not_found",
                    "message": "CUT project not found for music sync build.",
                    "recoverable": True,
                },
            )
            return

        music_path, path_resolution = _resolve_music_sync_path(
            store=store,
            project=project,
            requested_path=body.music_path,
        )
        if not music_path:
            job_store.update_job(
                job_id,
                state="error",
                progress=1.0,
                error={
                    "code": "music_path_not_found",
                    "message": "No music track found for CUT music sync build.",
                    "recoverable": True,
                },
            )
            return
        if not os.path.isfile(music_path):
            job_store.update_job(
                job_id,
                state="error",
                progress=1.0,
                error={
                    "code": "music_path_missing",
                    "message": f"CUT music sync source is missing: {music_path}",
                    "recoverable": True,
                },
            )
            return

        current_job = job_store.get_job(job_id)
        if current_job and bool(current_job.get("cancel_requested")):
            job_store.update_job(job_id, state="cancelled", progress=1.0)
            return

        result_prev = store.load_music_sync_result()
        revision = int((result_prev or {}).get("revision") or 0) + 1
        analysis = _analyze_music_track(
            path=music_path,
            bpm_hint=body.bpm_hint,
            max_analysis_sec=int(body.max_analysis_sec),
        )
        job_store.update_job(job_id, progress=0.85)

        music_sync_result = {
            "schema_version": "cut_music_sync_result_v1",
            "project_id": str(project.get("project_id") or ""),
            "revision": revision,
            "music_path": music_path,
            "tempo": {
                "bpm": float(analysis.get("tempo_bpm") or 0.0),
                "confidence": float(analysis.get("tempo_confidence") or 0.0),
            },
            "downbeats": [round(float(value), 4) for value in analysis.get("downbeats", [])],
            "phrases": list(analysis.get("phrases", [])),
            "cue_points": list(analysis.get("cue_points", [])),
            "derived_from": str(analysis.get("derived_from") or "music_sync_proxy_v1"),
            "generated_at": _utc_now_iso(),
        }
        store.save_music_sync_result(music_sync_result)

        degraded_mode = bool(analysis.get("degraded_mode"))
        degraded_reason_parts = [str(analysis.get("degraded_reason") or "").strip(), str(path_resolution or "").strip()]
        degraded_reason = ",".join([part for part in degraded_reason_parts if part])
        worker_task = {
            "schema_version": "cut_worker_task_v1",
            "task_id": job_id,
            "project_id": str(project.get("project_id") or ""),
            "task_type": "music_sync",
            "route_mode": "background",
            "priority": "normal",
            "status": "done",
            "input": {
                "music_path": music_path,
                "bpm_hint": body.bpm_hint,
                "max_analysis_sec": int(body.max_analysis_sec),
            },
            "output_ref": store.paths.music_sync_result_path,
            "degraded_mode": degraded_mode,
            "degraded_reason": degraded_reason,
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }
        job_store.update_job(
            job_id,
            state="done",
            progress=1.0,
            degraded_mode=degraded_mode,
            degraded_reason=degraded_reason,
            result={
                "success": True,
                "worker_task": worker_task,
                "music_sync_result": music_sync_result,
            },
        )
    except Exception as exc:
        job_store.update_job(
            job_id,
            state="error",
            progress=1.0,
            error={
                "code": "music_sync_exception",
                "message": str(exc),
                "recoverable": False,
            },
        )


def _run_cut_pause_slice_job(job_id: str, body: CutPauseSliceRequest) -> None:
    job_store = get_cut_mcp_job_store()
    job_store.update_job(job_id, state="running", progress=0.1)
    try:
        store = CutProjectStore(body.sandbox_root)
        project = store.load_project()
        if project is None or str(project.get("project_id") or "") != str(body.project_id):
            job_store.update_job(
                job_id,
                state="error",
                progress=1.0,
                error={
                    "code": "project_not_found",
                    "message": "CUT project not found for pause slice build.",
                    "recoverable": True,
                },
            )
            return

        source_root = str(project.get("source_path") or "")
        media_paths = _pick_audio_sync_media_paths(source_root, int(body.limit))
        bundle_prev = store.load_slice_bundle()
        revision = int((bundle_prev or {}).get("revision") or 0) + 1
        items: list[dict[str, Any]] = []
        degraded_count = 0

        if not media_paths:
            bundle = {
                "schema_version": "cut_slice_bundle_v1",
                "project_id": str(project.get("project_id") or ""),
                "revision": revision,
                "items": [],
                "generated_at": _utc_now_iso(),
            }
            store.save_slice_bundle(bundle)
            job_store.update_job(
                job_id,
                state="done",
                progress=1.0,
                degraded_mode=True,
                degraded_reason="no_media_files",
                result={
                    "success": True,
                    "worker_task": {
                        "schema_version": "cut_worker_task_v1",
                        "task_id": job_id,
                        "project_id": str(project.get("project_id") or ""),
                        "task_type": "pause_slice",
                        "route_mode": "background",
                        "priority": "normal",
                        "status": "done",
                        "input": {
                            "limit": int(body.limit),
                            "sample_bytes": int(body.sample_bytes),
                            "frame_ms": int(body.frame_ms),
                            "silence_threshold": float(body.silence_threshold),
                            "min_silence_ms": int(body.min_silence_ms),
                            "keep_silence_ms": int(body.keep_silence_ms),
                        },
                        "output_ref": store.paths.slice_bundle_path,
                        "degraded_mode": True,
                        "degraded_reason": "no_media_files",
                        "created_at": _utc_now_iso(),
                        "updated_at": _utc_now_iso(),
                    },
                    "slice_bundle": bundle,
                },
            )
            return

        total = len(media_paths)
        for index, media_path in enumerate(media_paths, start=1):
            current_job = job_store.get_job(job_id)
            if current_job and bool(current_job.get("cancel_requested")):
                job_store.update_job(job_id, state="cancelled", progress=1.0)
                return
            signal, degraded_mode, degraded_reason = _build_signal_proxy_from_bytes(media_path, int(body.sample_bytes))
            if signal:
                windows = _build_slice_windows_from_signal(
                    signal,
                    frame_ms=int(body.frame_ms),
                    silence_threshold=float(body.silence_threshold),
                    min_silence_ms=int(body.min_silence_ms),
                    keep_silence_ms=int(body.keep_silence_ms),
                )
            else:
                windows = []
                degraded_mode = True
                degraded_reason = degraded_reason or "signal_proxy_unavailable"
            if degraded_mode:
                degraded_count += 1
            items.append(
                {
                    "item_id": f"slice_{index:04d}",
                    "source_path": media_path,
                    "method": "energy_pause_v1",
                    "windows": windows,
                    "degraded_mode": degraded_mode,
                    "degraded_reason": degraded_reason,
                }
            )
            progress = 0.1 + (0.8 * index / total)
            job_store.update_job(job_id, progress=progress)

        bundle = {
            "schema_version": "cut_slice_bundle_v1",
            "project_id": str(project.get("project_id") or ""),
            "revision": revision,
            "items": items,
            "generated_at": _utc_now_iso(),
        }
        store.save_slice_bundle(bundle)
        degraded_mode = degraded_count > 0
        degraded_reason = "partial_pause_slice" if degraded_mode else ""
        worker_task = {
            "schema_version": "cut_worker_task_v1",
            "task_id": job_id,
            "project_id": str(project.get("project_id") or ""),
            "task_type": "pause_slice",
            "route_mode": "background",
            "priority": "normal",
            "status": "done",
            "input": {
                "limit": int(body.limit),
                "sample_bytes": int(body.sample_bytes),
                "frame_ms": int(body.frame_ms),
                "silence_threshold": float(body.silence_threshold),
                "min_silence_ms": int(body.min_silence_ms),
                "keep_silence_ms": int(body.keep_silence_ms),
            },
            "output_ref": store.paths.slice_bundle_path,
            "degraded_mode": degraded_mode,
            "degraded_reason": degraded_reason,
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }
        job_store.update_job(
            job_id,
            state="done",
            progress=1.0,
            degraded_mode=degraded_mode,
            degraded_reason=degraded_reason,
            result={
                "success": True,
                "worker_task": worker_task,
                "slice_bundle": bundle,
            },
        )
    except Exception as exc:
        job_store.update_job(
            job_id,
            state="error",
            progress=1.0,
            error={
                "code": "pause_slice_exception",
                "message": str(exc),
                "recoverable": False,
            },
        )


def _run_cut_timecode_sync_job(job_id: str, body: CutTimecodeSyncRequest) -> None:
    job_store = get_cut_mcp_job_store()
    job_store.update_job(job_id, state="running", progress=0.1)
    try:
        store = CutProjectStore(body.sandbox_root)
        project = store.load_project()
        if project is None or str(project.get("project_id") or "") != str(body.project_id):
            job_store.update_job(
                job_id,
                state="error",
                progress=1.0,
                error={
                    "code": "project_not_found",
                    "message": "CUT project not found for timecode sync build.",
                    "recoverable": True,
                },
            )
            return

        source_root = str(project.get("source_path") or "")
        media_paths = _pick_timecode_sync_media_paths(source_root, int(body.limit))
        result_prev = store.load_timecode_sync_result()
        revision = int((result_prev or {}).get("revision") or 0) + 1
        items: list[dict[str, Any]] = []
        degraded_count = 0

        if len(media_paths) < 2:
            result = {
                "schema_version": "cut_timecode_sync_result_v1",
                "project_id": str(project.get("project_id") or ""),
                "revision": revision,
                "items": [],
                "generated_at": _utc_now_iso(),
            }
            store.save_timecode_sync_result(result)
            job_store.update_job(
                job_id,
                state="done",
                progress=1.0,
                degraded_mode=True,
                degraded_reason="insufficient_media_files",
                result={
                    "success": True,
                    "worker_task": {
                        "schema_version": "cut_worker_task_v1",
                        "task_id": job_id,
                        "project_id": str(project.get("project_id") or ""),
                        "task_type": "timecode_sync",
                        "route_mode": "background",
                        "priority": "normal",
                        "status": "done",
                        "input": {"limit": int(body.limit), "fps": int(body.fps)},
                        "output_ref": store.paths.timecode_sync_result_path,
                        "degraded_mode": True,
                        "degraded_reason": "insufficient_media_files",
                        "created_at": _utc_now_iso(),
                        "updated_at": _utc_now_iso(),
                    },
                    "timecode_sync_result": result,
                },
            )
            return

        reference_path = media_paths[0]
        reference_tc, reference_fps = _extract_timecode_from_path(reference_path, int(body.fps))
        reference_sec = _timecode_to_seconds(str(reference_tc or ""), int(reference_fps))
        total = max(1, len(media_paths) - 1)

        for index, media_path in enumerate(media_paths[1:], start=1):
            current_job = job_store.get_job(job_id)
            if current_job and bool(current_job.get("cancel_requested")):
                job_store.update_job(job_id, state="cancelled", progress=1.0)
                return
            source_tc, source_fps = _extract_timecode_from_path(media_path, int(body.fps))
            source_sec = _timecode_to_seconds(str(source_tc or ""), int(source_fps))
            degraded_mode = reference_sec is None or source_sec is None
            degraded_reason = "" if not degraded_mode else "timecode_missing"
            detected_offset_sec = 0.0 if degraded_mode else round(float(source_sec) - float(reference_sec), 4)
            items.append(
                {
                    "item_id": f"timecode_sync_{index:04d}",
                    "reference_path": reference_path,
                    "source_path": media_path,
                    "reference_timecode": reference_tc or "",
                    "source_timecode": source_tc or "",
                    "fps": int(source_fps or reference_fps or body.fps),
                    "detected_offset_sec": detected_offset_sec,
                    "confidence": 0.99 if not degraded_mode else 0.0,
                    "method": "timecode_v1",
                    "degraded_mode": degraded_mode,
                    "degraded_reason": degraded_reason,
                }
            )
            if degraded_mode:
                degraded_count += 1
            progress = 0.1 + (0.8 * index / total)
            job_store.update_job(job_id, progress=progress)

        result = {
            "schema_version": "cut_timecode_sync_result_v1",
            "project_id": str(project.get("project_id") or ""),
            "revision": revision,
            "items": items,
            "generated_at": _utc_now_iso(),
        }
        store.save_timecode_sync_result(result)
        degraded_mode = degraded_count > 0
        degraded_reason = "partial_timecode_sync" if degraded_mode else ""
        worker_task = {
            "schema_version": "cut_worker_task_v1",
            "task_id": job_id,
            "project_id": str(project.get("project_id") or ""),
            "task_type": "timecode_sync",
            "route_mode": "background",
            "priority": "normal",
            "status": "done",
            "input": {"limit": int(body.limit), "fps": int(body.fps)},
            "output_ref": store.paths.timecode_sync_result_path,
            "degraded_mode": degraded_mode,
            "degraded_reason": degraded_reason,
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }
        job_store.update_job(
            job_id,
            state="done",
            progress=1.0,
            degraded_mode=degraded_mode,
            degraded_reason=degraded_reason,
            result={
                "success": True,
                "worker_task": worker_task,
                "timecode_sync_result": result,
            },
        )
    except Exception as exc:
        job_store.update_job(
            job_id,
            state="error",
            progress=1.0,
            error={
                "code": "timecode_sync_exception",
                "message": str(exc),
                "recoverable": False,
            },
        )


@worker_router.post("/bootstrap")
async def cut_bootstrap(body: CutBootstrapRequest = Body(...)) -> dict[str, Any]:
    """
    MARKER_170.MCP.BOOTSTRAP.FLOW_V1
    MARKER_170.MCP.BOOTSTRAP.CONTRACT_V1
    """
    return _execute_cut_bootstrap(body)


@worker_router.post("/bootstrap-async")
async def cut_bootstrap_async(body: CutBootstrapRequest = Body(...)) -> dict[str, Any]:
    """
    MARKER_170.MCP.BOOTSTRAP_ASYNC_V1
    """
    store = get_cut_mcp_job_store()
    job = store.create_job(
        "bootstrap",
        {
            "source_path": str(body.source_path or ""),
            "sandbox_root": str(body.sandbox_root or ""),
            "mode": str(body.mode),
            "bootstrap_profile": str(body.bootstrap_profile or "default"),
        },
    )
    thread = threading.Thread(target=_run_cut_bootstrap_job, args=(str(job["job_id"]), body), daemon=True)
    thread.start()
    return {
        "success": True,
        "schema_version": "cut_mcp_job_v1",
        "job_id": str(job["job_id"]),
        "job": job,
    }


@worker_router.post("/import-files")
async def cut_import_files(
    files: list[UploadFile] = File(...),
    sandbox_root: str = Form(""),
    project_name: str = Form("imported"),
) -> dict[str, Any]:
    """
    MARKER_188.2: Browser file upload → save to sandbox/imported/ folder.
    Returns source_path for use with bootstrap-async pipeline.
    """
    if not files:
        return {"success": False, "error": {"message": "No files uploaded"}}

    # Determine target directory
    sandbox = sandbox_root.strip() or f"/tmp/cut_sandbox_{uuid4().hex[:8]}"
    import_dir = Path(sandbox) / "imported"
    import_dir.mkdir(parents=True, exist_ok=True)

    saved_count = 0
    for upload_file in files:
        if not upload_file.filename:
            continue
        # Sanitize filename: keep basename only
        safe_name = Path(upload_file.filename).name
        target = import_dir / safe_name
        try:
            content = await upload_file.read()
            target.write_bytes(content)
            saved_count += 1
        except Exception as exc:
            logger.warning("Failed to save uploaded file %s: %s", safe_name, exc)

    if saved_count == 0:
        return {"success": False, "error": {"message": "No files could be saved"}}

    return {
        "success": True,
        "source_path": str(import_dir),
        "saved_count": saved_count,
        "sandbox_root": sandbox,
    }


@worker_router.post("/scene-assembly-async")
async def cut_scene_assembly_async(body: CutSceneAssemblyRequest = Body(...)) -> dict[str, Any]:
    """
    MARKER_170.MCP.SCENE_ASSEMBLY_ASYNC_V1
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _bootstrap_error(
            "project_not_found",
            "No existing CUT project found for this source and sandbox.",
            degraded_reason="project_not_found",
        )
    if _count_active_background_jobs_for_sandbox(str(body.sandbox_root)) >= _SANDBOX_BACKGROUND_LIMIT:
        return _worker_job_error(
            "worker_backpressure_limit",
            "CUT worker queue is saturated for this sandbox. Wait for active jobs to finish.",
        )
    duplicate_job = _find_active_duplicate_job(
        job_type="scene_assembly",
        project_id=str(body.project_id),
        sandbox_root=str(body.sandbox_root),
    )
    if duplicate_job is not None:
        return _worker_job_error(
            "duplicate_job_active",
            "A scene assembly job is already active for this CUT project.",
            existing_job=duplicate_job,
        )
    job_store = get_cut_mcp_job_store()
    job = job_store.create_job(
        "scene_assembly",
        {
            "project_id": str(body.project_id),
            "sandbox_root": str(body.sandbox_root),
            "timeline_id": str(body.timeline_id or "main"),
        },
    )
    bootstrap_state = store.load_bootstrap_state()
    if bootstrap_state is not None:
        bootstrap_state["last_job_id"] = str(job["job_id"])
        bootstrap_state["updated_at"] = _utc_now_iso()
        store.save_bootstrap_state(bootstrap_state)
    thread = threading.Thread(target=_run_cut_scene_assembly_job, args=(str(job["job_id"]), body), daemon=True)
    thread.start()
    return {
        "success": True,
        "schema_version": "cut_mcp_job_v1",
        "job_id": str(job["job_id"]),
        "job": job,
    }



# MARKER_B41: Media/Color/Probe/Preview/Waveform/Codec/Thumbnail/Audio routes
# moved to cut_routes_media.py (17 routes)

@worker_router.post("/worker/waveform-build-async")
async def cut_waveform_build_async(body: CutWaveformBuildRequest = Body(...)) -> dict[str, Any]:
    """
    MARKER_170.WORKER.MEDIA_SUBMCP
    MARKER_170.WORKER.DEGRADED_SAFE
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _worker_job_error("project_not_found", "CUT project not found for waveform worker task.")
    if _count_active_background_jobs_for_sandbox(str(body.sandbox_root)) >= _SANDBOX_BACKGROUND_LIMIT:
        return _worker_job_error(
            "worker_backpressure_limit",
            "CUT worker queue is saturated for this sandbox. Wait for active jobs to finish.",
        )
    duplicate_job = _find_active_duplicate_job(
        job_type="waveform_build",
        project_id=str(body.project_id),
        sandbox_root=str(body.sandbox_root),
    )
    if duplicate_job is not None:
        return _worker_job_error(
            "duplicate_job_active",
            "A waveform build job is already active for this CUT project.",
            existing_job=duplicate_job,
        )
    job_store = get_cut_mcp_job_store()
    job = job_store.create_job(
        "waveform_build",
        {
            "project_id": str(body.project_id),
            "sandbox_root": str(body.sandbox_root),
            "bins": int(body.bins),
            "limit": int(body.limit),
            "task_type": "waveform_build",
        },
    )
    thread = threading.Thread(target=_run_cut_waveform_build_job, args=(str(job["job_id"]), body), daemon=True)
    thread.start()
    return {
        "success": True,
        "schema_version": "cut_mcp_job_v1",
        "job_id": str(job["job_id"]),
        "job": job,
    }


@worker_router.post("/worker/transcript-normalize-async")
async def cut_transcript_normalize_async(body: CutTranscriptNormalizeRequest = Body(...)) -> dict[str, Any]:
    """
    MARKER_170.WORKER.MEDIA_SUBMCP
    MARKER_170.WORKER.TRANSCRIPT_NORMALIZE_V1
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _worker_job_error("project_not_found", "CUT project not found for transcript worker task.")
    if _count_active_background_jobs_for_sandbox(str(body.sandbox_root)) >= _SANDBOX_BACKGROUND_LIMIT:
        return _worker_job_error(
            "worker_backpressure_limit",
            "CUT worker queue is saturated for this sandbox. Wait for active jobs to finish.",
        )
    duplicate_job = _find_active_duplicate_job(
        job_type="transcript_normalize",
        project_id=str(body.project_id),
        sandbox_root=str(body.sandbox_root),
    )
    if duplicate_job is not None:
        return _worker_job_error(
            "duplicate_job_active",
            "A transcript normalize job is already active for this CUT project.",
            existing_job=duplicate_job,
        )
    job_store = get_cut_mcp_job_store()
    job = job_store.create_job(
        "transcript_normalize",
        {
            "project_id": str(body.project_id),
            "sandbox_root": str(body.sandbox_root),
            "limit": int(body.limit),
            "segments_limit": int(body.segments_limit),
            "max_transcribe_sec": body.max_transcribe_sec,
            "task_type": "transcript_normalize",
        },
    )
    thread = threading.Thread(target=_run_cut_transcript_normalize_job, args=(str(job["job_id"]), body), daemon=True)
    thread.start()
    return {
        "success": True,
        "schema_version": "cut_mcp_job_v1",
        "job_id": str(job["job_id"]),
        "job": job,
    }


@worker_router.post("/worker/thumbnail-build-async")
async def cut_thumbnail_build_async(body: CutThumbnailBuildRequest = Body(...)) -> dict[str, Any]:
    """
    MARKER_170.WORKER.MEDIA_SUBMCP
    MARKER_170.UI.STORYBOARD_THUMBNAILS_V1
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _worker_job_error("project_not_found", "CUT project not found for thumbnail worker task.")
    if _count_active_background_jobs_for_sandbox(str(body.sandbox_root)) >= _SANDBOX_BACKGROUND_LIMIT:
        return _worker_job_error(
            "worker_backpressure_limit",
            "CUT worker queue is saturated for this sandbox. Wait for active jobs to finish.",
        )
    duplicate_job = _find_active_duplicate_job(
        job_type="thumbnail_build",
        project_id=str(body.project_id),
        sandbox_root=str(body.sandbox_root),
    )
    if duplicate_job is not None:
        return _worker_job_error(
            "duplicate_job_active",
            "A thumbnail build job is already active for this CUT project.",
            existing_job=duplicate_job,
        )
    job_store = get_cut_mcp_job_store()
    job = job_store.create_job(
        "thumbnail_build",
        {
            "project_id": str(body.project_id),
            "sandbox_root": str(body.sandbox_root),
            "limit": int(body.limit),
            "waveform_bins": int(body.waveform_bins),
            "preview_segments_limit": int(body.preview_segments_limit),
            "task_type": "thumbnail_build",
        },
    )
    thread = threading.Thread(target=_run_cut_thumbnail_build_job, args=(str(job["job_id"]), body), daemon=True)
    thread.start()
    return {
        "success": True,
        "schema_version": "cut_mcp_job_v1",
        "job_id": str(job["job_id"]),
        "job": job,
    }


@worker_router.post("/worker/audio-sync-async")
async def cut_audio_sync_async(body: CutAudioSyncRequest = Body(...)) -> dict[str, Any]:
    """
    MARKER_170.WORKER.AUDIO_SYNC_V1
    MARKER_170.WORKER.AUDIO_SYNC_BAKEOFF
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _worker_job_error("project_not_found", "CUT project not found for audio sync worker task.")
    if _count_active_background_jobs_for_sandbox(str(body.sandbox_root)) >= _SANDBOX_BACKGROUND_LIMIT:
        return _worker_job_error(
            "worker_backpressure_limit",
            "CUT worker queue is saturated for this sandbox. Wait for active jobs to finish.",
        )
    duplicate_job = _find_active_duplicate_job(
        job_type="audio_sync",
        project_id=str(body.project_id),
        sandbox_root=str(body.sandbox_root),
    )
    if duplicate_job is not None:
        return _worker_job_error(
            "duplicate_job_active",
            "An audio sync job is already active for this CUT project.",
            existing_job=duplicate_job,
        )
    job_store = get_cut_mcp_job_store()
    job = job_store.create_job(
        "audio_sync",
        {
            "project_id": str(body.project_id),
            "sandbox_root": str(body.sandbox_root),
            "limit": int(body.limit),
            "sample_bytes": int(body.sample_bytes),
            "method": str(body.method),
            "task_type": "audio_sync",
        },
    )
    thread = threading.Thread(target=_run_cut_audio_sync_job, args=(str(job["job_id"]), body), daemon=True)
    thread.start()
    return {
        "success": True,
        "schema_version": "cut_mcp_job_v1",
        "job_id": str(job["job_id"]),
        "job": job,
    }


@worker_router.post("/worker/scan-matrix-async")
async def cut_scan_matrix_async(body: CutScanMatrixRequest = Body(...)) -> dict[str, Any]:
    """
    MARKER_189.2.SCAN_MATRIX_ASYNC
    Run VideoScanner + AudioScanner on all media files in the project.
    Extracts: ffprobe metadata, scene boundaries, thumbnails, waveforms, STT.
    Saves: scan_matrix_result.latest.json + media_index.latest.json.
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _worker_job_error("project_not_found", "CUT project not found for scan matrix.")
    if _count_active_background_jobs_for_sandbox(str(body.sandbox_root)) >= _SANDBOX_BACKGROUND_LIMIT:
        return _worker_job_error(
            "worker_backpressure_limit",
            "CUT worker queue is saturated for this sandbox. Wait for active jobs to finish.",
        )
    duplicate_job = _find_active_duplicate_job(
        job_type="scan_matrix",
        project_id=str(body.project_id),
        sandbox_root=str(body.sandbox_root),
    )
    if duplicate_job is not None:
        return _worker_job_error(
            "duplicate_job_active",
            "A scan matrix job is already active for this CUT project.",
            existing_job=duplicate_job,
        )
    job_store = get_cut_mcp_job_store()
    job = job_store.create_job(
        "scan_matrix",
        {
            "project_id": str(body.project_id),
            "sandbox_root": str(body.sandbox_root),
            "limit": int(body.limit),
            "run_stt": bool(body.run_stt),
            "task_type": "scan_matrix",
        },
    )
    thread = threading.Thread(target=_run_cut_scan_matrix_job, args=(str(job["job_id"]), body), daemon=True)
    thread.start()
    return {
        "success": True,
        "schema_version": "cut_mcp_job_v1",
        "job_id": str(job["job_id"]),
        "job": job,
    }


@worker_router.post("/worker/music-sync-async")
async def cut_music_sync_async(body: CutMusicSyncRequest = Body(...)) -> dict[str, Any]:
    """
    MARKER_171.WORKER.MUSIC_SYNC_V1
    MARKER_171.WORKER.BEAT_TRACK_PROXY
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _worker_job_error("project_not_found", "CUT project not found for music sync worker task.")
    if _count_active_background_jobs_for_sandbox(str(body.sandbox_root)) >= _SANDBOX_BACKGROUND_LIMIT:
        return _worker_job_error(
            "worker_backpressure_limit",
            "CUT worker queue is saturated for this sandbox. Wait for active jobs to finish.",
        )
    duplicate_job = _find_active_duplicate_job(
        job_type="music_sync",
        project_id=str(body.project_id),
        sandbox_root=str(body.sandbox_root),
    )
    if duplicate_job is not None:
        return _worker_job_error(
            "duplicate_job_active",
            "A music sync job is already active for this CUT project.",
            existing_job=duplicate_job,
        )
    job_store = get_cut_mcp_job_store()
    job = job_store.create_job(
        "music_sync",
        {
            "project_id": str(body.project_id),
            "sandbox_root": str(body.sandbox_root),
            "music_path": str(body.music_path or ""),
            "bpm_hint": body.bpm_hint,
            "max_analysis_sec": int(body.max_analysis_sec),
            "task_type": "music_sync",
        },
    )
    thread = threading.Thread(target=_run_cut_music_sync_job, args=(str(job["job_id"]), body), daemon=True)
    thread.start()
    return {
        "success": True,
        "schema_version": "cut_mcp_job_v1",
        "job_id": str(job["job_id"]),
        "job": job,
    }


@worker_router.post("/worker/pause-slice-async")
async def cut_pause_slice_async(body: CutPauseSliceRequest = Body(...)) -> dict[str, Any]:
    """
    MARKER_170.INTEL.SLICE_METHOD_BAKEOFF
    MARKER_170.INTEL.PAUSE_SLICE_V1
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _worker_job_error("project_not_found", "CUT project not found for pause slice worker task.")
    if _count_active_background_jobs_for_sandbox(str(body.sandbox_root)) >= _SANDBOX_BACKGROUND_LIMIT:
        return _worker_job_error(
            "worker_backpressure_limit",
            "CUT worker queue is saturated for this sandbox. Wait for active jobs to finish.",
        )
    duplicate_job = _find_active_duplicate_job(
        job_type="pause_slice",
        project_id=str(body.project_id),
        sandbox_root=str(body.sandbox_root),
    )
    if duplicate_job is not None:
        return _worker_job_error(
            "duplicate_job_active",
            "A pause slice job is already active for this CUT project.",
            existing_job=duplicate_job,
        )
    job_store = get_cut_mcp_job_store()
    job = job_store.create_job(
        "pause_slice",
        {
            "project_id": str(body.project_id),
            "sandbox_root": str(body.sandbox_root),
            "limit": int(body.limit),
            "sample_bytes": int(body.sample_bytes),
            "frame_ms": int(body.frame_ms),
            "silence_threshold": float(body.silence_threshold),
            "min_silence_ms": int(body.min_silence_ms),
            "keep_silence_ms": int(body.keep_silence_ms),
            "task_type": "pause_slice",
        },
    )
    thread = threading.Thread(target=_run_cut_pause_slice_job, args=(str(job["job_id"]), body), daemon=True)
    thread.start()
    return {
        "success": True,
        "schema_version": "cut_mcp_job_v1",
        "job_id": str(job["job_id"]),
        "job": job,
    }


@worker_router.post("/worker/timecode-sync-async")
async def cut_timecode_sync_async(body: CutTimecodeSyncRequest = Body(...)) -> dict[str, Any]:
    """
    MARKER_170.WORKER.TIMECODE_SYNC_V1
    MARKER_170.CONTRACT.MULTI_SYNC_ALIGNMENT_V1
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _worker_job_error("project_not_found", "CUT project not found for timecode sync worker task.")
    if _count_active_background_jobs_for_sandbox(str(body.sandbox_root)) >= _SANDBOX_BACKGROUND_LIMIT:
        return _worker_job_error(
            "worker_backpressure_limit",
            "CUT worker queue is saturated for this sandbox. Wait for active jobs to finish.",
        )
    duplicate_job = _find_active_duplicate_job(
        job_type="timecode_sync",
        project_id=str(body.project_id),
        sandbox_root=str(body.sandbox_root),
    )
    if duplicate_job is not None:
        return _worker_job_error(
            "duplicate_job_active",
            "A timecode sync job is already active for this CUT project.",
            existing_job=duplicate_job,
        )
    job_store = get_cut_mcp_job_store()
    job = job_store.create_job(
        "timecode_sync",
        {
            "project_id": str(body.project_id),
            "sandbox_root": str(body.sandbox_root),
            "limit": int(body.limit),
            "fps": int(body.fps),
            "task_type": "timecode_sync",
        },
    )
    thread = threading.Thread(target=_run_cut_timecode_sync_job, args=(str(job["job_id"]), body), daemon=True)
    thread.start()
    return {
        "success": True,
        "schema_version": "cut_mcp_job_v1",
        "job_id": str(job["job_id"]),
        "job": job,
    }


@worker_router.get("/job/{job_id}")
async def cut_job_status(job_id: str) -> dict[str, Any]:
    """
    MARKER_170.MCP.JOB_STATUS_V1 + B2.2 — ETA calculation.
    """
    store = get_cut_mcp_job_store()
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"CUT job not found: {job_id}")

    # MARKER_B2.2: Compute elapsed + ETA for running jobs
    started_at = job.get("started_at")
    progress = float(job.get("progress") or 0)
    if started_at and job.get("state") == "running" and progress > 0.01:
        try:
            from datetime import datetime as _dt, timezone as _tz
            start = _dt.fromisoformat(started_at)
            elapsed = (_dt.now(_tz.utc) - start).total_seconds()
            job["elapsed_sec"] = round(elapsed, 1)
            job["eta_sec"] = round(elapsed * (1.0 - progress) / progress, 1)
        except Exception:
            job["elapsed_sec"] = 0
            job["eta_sec"] = 0

    return {"success": True, "job": job}


@worker_router.post("/job/{job_id}/cancel")
async def cut_job_cancel(job_id: str) -> dict[str, Any]:
    """
    MARKER_170.WORKER.RETRY_CANCEL
    """
    store = get_cut_mcp_job_store()
    job = store.request_cancel(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"CUT job not found: {job_id}")
    return {"success": True, "schema_version": "cut_mcp_job_v1", "job_id": job_id, "job": job}


# Re-export for cut_routes.py cross-dependency
__all__ = ["worker_router", "_collect_project_jobs", "_worker_job_error",
           "_find_active_duplicate_job", "_count_active_background_jobs_for_sandbox",
           "_ACTIVE_JOB_STATES", "_SANDBOX_BACKGROUND_LIMIT"]
