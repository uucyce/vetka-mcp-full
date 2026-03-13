from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.services.cut_scene_graph_taxonomy import SCENE_GRAPH_EDGE_TYPE_SET, SCENE_GRAPH_NODE_TYPE_SET


CUT_VIDEO_EXT = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}
CUT_AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
CUT_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff", ".avif"}
CUT_DOC_EXT = {".pdf", ".doc", ".docx", ".md", ".txt", ".rtf", ".fdx"}
CUT_PROJECT_EXT = {".prproj", ".aep", ".fcpxml", ".xml", ".edl", ".prin"}
CUT_SCRIPT_TOKENS = ("script", "scenario", "treatment", "screenplay")
CUT_MONTAGE_TOKENS = ("montage", "edit_sheet", "shotlist", "shot_list", "edl", "fcpxml", "xml")
CUT_TIMECODE_TOKENS = ("transcript", "timecode", "subtitles", "captions", ".srt", ".vtt", ".json")
CUT_MUSIC_TOKENS = ("punch", "music", "song", "track", "score", "ost")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_abs(path: str) -> str:
    return os.path.realpath(os.path.abspath(os.path.expanduser(str(path or "").strip())))


def _slug_from_name(raw: str) -> str:
    text = str(raw or "").strip().lower()
    text = re.sub(r"[^a-z0-9._-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("._-")
    return text or "cut_project"


def _classify_cut_asset_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in CUT_VIDEO_EXT:
        return "video"
    if ext in CUT_AUDIO_EXT:
        return "audio"
    if ext in CUT_IMAGE_EXT:
        return "image"
    if ext in CUT_DOC_EXT:
        return "document"
    if ext in CUT_PROJECT_EXT:
        return "project"
    return "other"


@dataclass(frozen=True)
class CutProjectPaths:
    sandbox_root: str

    @property
    def config_dir(self) -> str:
        return os.path.join(self.sandbox_root, "config")

    @property
    def runtime_dir(self) -> str:
        return os.path.join(self.sandbox_root, "cut_runtime")

    @property
    def runtime_state_dir(self) -> str:
        return os.path.join(self.runtime_dir, "state")

    @property
    def storage_dir(self) -> str:
        return os.path.join(self.sandbox_root, "cut_storage")

    @property
    def core_mirror_root(self) -> str:
        return os.path.join(self.sandbox_root, "core_mirror")

    @property
    def manifest_path(self) -> str:
        return os.path.join(self.config_dir, "cut_core_mirror_manifest.json")

    @property
    def project_path(self) -> str:
        return os.path.join(self.config_dir, "cut_project.json")

    @property
    def bootstrap_state_path(self) -> str:
        return os.path.join(self.config_dir, "cut_bootstrap_state.json")

    @property
    def timeline_state_path(self) -> str:
        return os.path.join(self.runtime_state_dir, "timeline_state.latest.json")

    @property
    def scene_graph_path(self) -> str:
        return os.path.join(self.runtime_state_dir, "scene_graph.latest.json")

    @property
    def timeline_edit_log_path(self) -> str:
        return os.path.join(self.runtime_state_dir, "timeline_edit_log.jsonl")

    @property
    def scene_graph_edit_log_path(self) -> str:
        return os.path.join(self.runtime_state_dir, "scene_graph_edit_log.jsonl")

    @property
    def waveform_bundle_path(self) -> str:
        return os.path.join(self.runtime_state_dir, "waveform_bundle.latest.json")

    @property
    def transcript_bundle_path(self) -> str:
        return os.path.join(self.runtime_state_dir, "transcript_bundle.latest.json")

    @property
    def thumbnail_bundle_path(self) -> str:
        return os.path.join(self.runtime_state_dir, "thumbnail_bundle.latest.json")

    @property
    def audio_sync_result_path(self) -> str:
        return os.path.join(self.runtime_state_dir, "audio_sync_result.latest.json")

    @property
    def slice_bundle_path(self) -> str:
        return os.path.join(self.runtime_state_dir, "slice_bundle.latest.json")

    @property
    def timecode_sync_result_path(self) -> str:
        return os.path.join(self.runtime_state_dir, "timecode_sync_result.latest.json")

    @property
    def music_sync_result_path(self) -> str:
        return os.path.join(self.runtime_state_dir, "music_sync_result.latest.json")

    @property
    def time_marker_bundle_path(self) -> str:
        return os.path.join(self.runtime_state_dir, "time_marker_bundle.latest.json")

    @property
    def time_marker_edit_log_path(self) -> str:
        return os.path.join(self.runtime_state_dir, "time_marker_edit_log.jsonl")


class CutProjectStore:
    """
    MARKER_170.STORE.CUT_PROJECT_STORE_V1

    File-backed persistence for standalone CUT sandbox bootstrap state.
    """

    def __init__(self, sandbox_root: str) -> None:
        self.sandbox_root = _norm_abs(sandbox_root)
        self.paths = CutProjectPaths(self.sandbox_root)

    def load_project(self) -> dict[str, Any] | None:
        payload = self._load_json(self.paths.project_path, expected_schema="cut_project_v1")
        if payload is None or not self._validate_project_payload(payload):
            return None
        return payload

    def save_project(self, project: dict[str, Any]) -> None:
        payload = dict(project or {})
        payload["sandbox_root"] = self.sandbox_root
        payload["last_opened_at"] = _utc_now_iso()
        if not self._validate_project_payload(payload):
            raise ValueError("Invalid cut_project_v1 payload")
        self._atomic_write_json(self.paths.project_path, payload)

    def load_bootstrap_state(self) -> dict[str, Any] | None:
        payload = self._load_json(self.paths.bootstrap_state_path, expected_schema="cut_bootstrap_state_v1")
        if payload is None or not self._validate_bootstrap_state_payload(payload):
            return None
        return payload

    def save_bootstrap_state(self, state: dict[str, Any]) -> None:
        payload = dict(state or {})
        if not self._validate_bootstrap_state_payload(payload):
            raise ValueError("Invalid cut_bootstrap_state_v1 payload")
        self._atomic_write_json(self.paths.bootstrap_state_path, payload)

    def load_timeline_state(self) -> dict[str, Any] | None:
        payload = self._load_json(self.paths.timeline_state_path, expected_schema="cut_timeline_state_v1")
        if payload is None or not self._validate_timeline_state_payload(payload):
            return None
        return payload

    def save_timeline_state(self, state: dict[str, Any]) -> None:
        payload = dict(state or {})
        if not self._validate_timeline_state_payload(payload):
            raise ValueError("Invalid cut_timeline_state_v1 payload")
        self._atomic_write_json(self.paths.timeline_state_path, payload)

    def load_scene_graph(self) -> dict[str, Any] | None:
        payload = self._load_json(self.paths.scene_graph_path, expected_schema="cut_scene_graph_v1")
        if payload is None or not self._validate_scene_graph_payload(payload):
            return None
        return payload

    def save_scene_graph(self, graph: dict[str, Any]) -> None:
        payload = dict(graph or {})
        if not self._validate_scene_graph_payload(payload):
            raise ValueError("Invalid cut_scene_graph_v1 payload")
        self._atomic_write_json(self.paths.scene_graph_path, payload)

    def append_timeline_edit_event(self, event: dict[str, Any]) -> None:
        payload = dict(event or {})
        os.makedirs(os.path.dirname(self.paths.timeline_edit_log_path), exist_ok=True)
        with open(self.paths.timeline_edit_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False))
            f.write("\n")

    def append_scene_graph_edit_event(self, event: dict[str, Any]) -> None:
        payload = dict(event or {})
        os.makedirs(os.path.dirname(self.paths.scene_graph_edit_log_path), exist_ok=True)
        with open(self.paths.scene_graph_edit_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False))
            f.write("\n")

    def load_waveform_bundle(self) -> dict[str, Any] | None:
        payload = self._load_json(self.paths.waveform_bundle_path, expected_schema="cut_waveform_bundle_v1")
        if payload is None or not self._validate_waveform_bundle_payload(payload):
            return None
        return payload

    def save_waveform_bundle(self, bundle: dict[str, Any]) -> None:
        payload = dict(bundle or {})
        if not self._validate_waveform_bundle_payload(payload):
            raise ValueError("Invalid cut_waveform_bundle_v1 payload")
        self._atomic_write_json(self.paths.waveform_bundle_path, payload)

    def load_transcript_bundle(self) -> dict[str, Any] | None:
        payload = self._load_json(self.paths.transcript_bundle_path, expected_schema="cut_transcript_bundle_v1")
        if payload is None or not self._validate_transcript_bundle_payload(payload):
            return None
        return payload

    def save_transcript_bundle(self, bundle: dict[str, Any]) -> None:
        payload = dict(bundle or {})
        if not self._validate_transcript_bundle_payload(payload):
            raise ValueError("Invalid cut_transcript_bundle_v1 payload")
        self._atomic_write_json(self.paths.transcript_bundle_path, payload)

    def load_thumbnail_bundle(self) -> dict[str, Any] | None:
        payload = self._load_json(self.paths.thumbnail_bundle_path, expected_schema="cut_thumbnail_bundle_v1")
        if payload is None or not self._validate_thumbnail_bundle_payload(payload):
            return None
        return payload

    def save_thumbnail_bundle(self, bundle: dict[str, Any]) -> None:
        payload = dict(bundle or {})
        if not self._validate_thumbnail_bundle_payload(payload):
            raise ValueError("Invalid cut_thumbnail_bundle_v1 payload")
        self._atomic_write_json(self.paths.thumbnail_bundle_path, payload)

    def load_audio_sync_result(self) -> dict[str, Any] | None:
        payload = self._load_json(self.paths.audio_sync_result_path, expected_schema="cut_audio_sync_result_v1")
        if payload is None or not self._validate_audio_sync_result_payload(payload):
            return None
        return payload

    def save_audio_sync_result(self, result: dict[str, Any]) -> None:
        payload = dict(result or {})
        if not self._validate_audio_sync_result_payload(payload):
            raise ValueError("Invalid cut_audio_sync_result_v1 payload")
        self._atomic_write_json(self.paths.audio_sync_result_path, payload)

    def load_slice_bundle(self) -> dict[str, Any] | None:
        payload = self._load_json(self.paths.slice_bundle_path, expected_schema="cut_slice_bundle_v1")
        if payload is None or not self._validate_slice_bundle_payload(payload):
            return None
        return payload

    def save_slice_bundle(self, bundle: dict[str, Any]) -> None:
        payload = dict(bundle or {})
        if not self._validate_slice_bundle_payload(payload):
            raise ValueError("Invalid cut_slice_bundle_v1 payload")
        self._atomic_write_json(self.paths.slice_bundle_path, payload)

    def load_timecode_sync_result(self) -> dict[str, Any] | None:
        payload = self._load_json(self.paths.timecode_sync_result_path, expected_schema="cut_timecode_sync_result_v1")
        if payload is None or not self._validate_timecode_sync_result_payload(payload):
            return None
        return payload

    def save_timecode_sync_result(self, result: dict[str, Any]) -> None:
        payload = dict(result or {})
        if not self._validate_timecode_sync_result_payload(payload):
            raise ValueError("Invalid cut_timecode_sync_result_v1 payload")
        self._atomic_write_json(self.paths.timecode_sync_result_path, payload)

    def load_music_sync_result(self) -> dict[str, Any] | None:
        payload = self._load_json(self.paths.music_sync_result_path, expected_schema="cut_music_sync_result_v1")
        if payload is None or not self._validate_music_sync_result_payload(payload):
            return None
        return payload

    def save_music_sync_result(self, result: dict[str, Any]) -> None:
        payload = dict(result or {})
        if not self._validate_music_sync_result_payload(payload):
            raise ValueError("Invalid cut_music_sync_result_v1 payload")
        self._atomic_write_json(self.paths.music_sync_result_path, payload)

    def load_time_marker_bundle(self) -> dict[str, Any] | None:
        payload = self._load_json(self.paths.time_marker_bundle_path, expected_schema="cut_time_marker_bundle_v1")
        if payload is None or not self._validate_time_marker_bundle_payload(payload):
            return None
        return payload

    def save_time_marker_bundle(self, bundle: dict[str, Any]) -> None:
        payload = dict(bundle or {})
        if not self._validate_time_marker_bundle_payload(payload):
            raise ValueError("Invalid cut_time_marker_bundle_v1 payload")
        self._atomic_write_json(self.paths.time_marker_bundle_path, payload)

    def append_time_marker_edit_event(self, event: dict[str, Any]) -> None:
        payload = dict(event or {})
        os.makedirs(os.path.dirname(self.paths.time_marker_edit_log_path), exist_ok=True)
        with open(self.paths.time_marker_edit_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False))
            f.write("\n")

    def resolve_create_or_open(self, source_path: str) -> tuple[str, dict[str, Any] | None]:
        project = self.load_project()
        if not project:
            return ("create", None)
        persisted_source = _norm_abs(str(project.get("source_path") or ""))
        persisted_sandbox = _norm_abs(str(project.get("sandbox_root") or ""))
        if persisted_source == _norm_abs(source_path) and persisted_sandbox == self.sandbox_root:
            return ("open", project)
        return ("create", None)

    def create_project(
        self,
        *,
        source_path: str,
        display_name: str,
        bootstrap_profile: str,
        use_core_mirror: bool,
        source_type: str = "local",
    ) -> dict[str, Any]:
        source_abs = _norm_abs(source_path)
        label = str(display_name or "").strip() or os.path.basename(source_abs.rstrip(os.sep)) or "VETKA CUT Project"
        slug = _slug_from_name(label)
        project_id = f"cut_{slug}_{uuid.uuid4().hex[:8]}"
        now = _utc_now_iso()
        return {
            "schema_version": "cut_project_v1",
            "project_id": project_id,
            "display_name": label,
            "source_type": source_type,
            "source_path": source_abs,
            "sandbox_root": self.sandbox_root,
            "core_mirror_root": self.paths.core_mirror_root,
            "runtime_root": self.paths.runtime_dir,
            "storage_root": self.paths.storage_dir,
            "qdrant_namespace": project_id,
            "bootstrap_profile": str(bootstrap_profile or "default"),
            "edit_mode_target": "standalone",
            "state": "bootstrapping",
            "contracts": {
                "media_chunks": "media_chunks_v1",
                "montage_sheet": "vetka_montage_sheet_v1",
                "bootstrap": "cut_bootstrap_v1",
            },
            "memory_policy": {
                "engram_enabled": True,
                "cam_enabled": True,
                "elision_enabled": True,
                "namespace_mode": "sandbox_project",
            },
            "worker_topology": {
                "cut_mcp": "enabled",
                "media_worker_mcp": "enabled",
            },
            "import_defaults": {
                "quick_scan_limit": 5000,
                "use_core_mirror": bool(use_core_mirror),
            },
            "created_at": now,
            "last_opened_at": now,
            "notes": "",
        }

    def sandbox_layout_status(self) -> dict[str, Any]:
        expected_dirs = [
            self.paths.config_dir,
            self.paths.runtime_dir,
            self.paths.storage_dir,
        ]
        missing_dirs = [path for path in expected_dirs if not os.path.isdir(path)]
        return {
            "sandbox_exists": os.path.isdir(self.sandbox_root),
            "missing_dirs": missing_dirs,
            "core_mirror_exists": os.path.isdir(self.paths.core_mirror_root),
            "manifest_exists": os.path.isfile(self.paths.manifest_path),
        }

    def _load_json(self, path: str, expected_schema: str | None = None) -> dict[str, Any] | None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except FileNotFoundError:
            return None
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        if expected_schema and str(payload.get("schema_version") or "") != expected_schema:
            return None
        return payload

    def _validate_project_payload(self, payload: dict[str, Any]) -> bool:
        required = [
            "schema_version",
            "project_id",
            "display_name",
            "source_path",
            "sandbox_root",
            "core_mirror_root",
            "runtime_root",
            "storage_root",
            "qdrant_namespace",
            "created_at",
            "bootstrap_profile",
            "state",
        ]
        if any(not str(payload.get(key) or "").strip() for key in required):
            return False
        if str(payload.get("schema_version")) != "cut_project_v1":
            return False
        if _norm_abs(str(payload.get("sandbox_root") or "")) != self.sandbox_root:
            return False
        abs_fields = ("source_path", "sandbox_root", "core_mirror_root", "runtime_root", "storage_root")
        if any(not os.path.isabs(str(payload.get(key) or "")) for key in abs_fields):
            return False
        return True

    def _validate_bootstrap_state_payload(self, payload: dict[str, Any]) -> bool:
        required = [
            "schema_version",
            "project_id",
            "last_bootstrap_mode",
            "last_source_path",
            "last_stats",
            "last_degraded_reason",
            "last_job_id",
            "updated_at",
        ]
        if any(key not in payload for key in required):
            return False
        if str(payload.get("schema_version")) != "cut_bootstrap_state_v1":
            return False
        if str(payload.get("last_bootstrap_mode")) not in {"create_or_open", "open_existing", "create_new"}:
            return False
        if not os.path.isabs(str(payload.get("last_source_path") or "")):
            return False
        if not isinstance(payload.get("last_stats"), dict):
            return False
        return True

    def _validate_timeline_state_payload(self, payload: dict[str, Any]) -> bool:
        required = [
            "schema_version",
            "project_id",
            "timeline_id",
            "revision",
            "fps",
            "lanes",
            "selection",
            "view",
            "updated_at",
        ]
        if any(key not in payload for key in required):
            return False
        if str(payload.get("schema_version")) != "cut_timeline_state_v1":
            return False
        if not isinstance(payload.get("lanes"), list):
            return False
        if not isinstance(payload.get("selection"), dict):
            return False
        if not isinstance(payload.get("view"), dict):
            return False
        return True

    def _validate_scene_graph_payload(self, payload: dict[str, Any]) -> bool:
        required = [
            "schema_version",
            "project_id",
            "graph_id",
            "revision",
            "nodes",
            "edges",
            "updated_at",
        ]
        if any(key not in payload for key in required):
            return False
        if str(payload.get("schema_version")) != "cut_scene_graph_v1":
            return False

        project_id = payload.get("project_id")
        graph_id = payload.get("graph_id")
        revision = payload.get("revision")
        updated_at = payload.get("updated_at")
        nodes = payload.get("nodes")
        edges = payload.get("edges")

        if not isinstance(project_id, str) or not project_id.strip():
            return False
        if not isinstance(graph_id, str) or not graph_id.strip():
            return False
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            return False
        if not isinstance(updated_at, str) or not self._is_iso_datetime(updated_at):
            return False
        if not isinstance(nodes, list):
            return False
        if not isinstance(edges, list):
            return False

        node_ids: set[str] = set()
        for node in nodes:
            if not isinstance(node, dict):
                return False
            if set(node.keys()) != {"node_id", "node_type", "label", "record_ref", "metadata"}:
                return False
            node_id = node.get("node_id")
            node_type = node.get("node_type")
            label = node.get("label")
            record_ref = node.get("record_ref")
            metadata = node.get("metadata")
            if not isinstance(node_id, str) or not node_id.strip() or node_id in node_ids:
                return False
            if not isinstance(node_type, str) or node_type not in SCENE_GRAPH_NODE_TYPE_SET:
                return False
            if not isinstance(label, str) or not label.strip():
                return False
            if record_ref is not None and not isinstance(record_ref, str):
                return False
            if not isinstance(metadata, dict):
                return False
            node_ids.add(node_id)

        edge_ids: set[str] = set()
        for edge in edges:
            if not isinstance(edge, dict):
                return False
            if set(edge.keys()) != {"edge_id", "edge_type", "source", "target", "weight"}:
                return False
            edge_id = edge.get("edge_id")
            edge_type = edge.get("edge_type")
            source = edge.get("source")
            target = edge.get("target")
            weight = edge.get("weight")
            if not isinstance(edge_id, str) or not edge_id.strip() or edge_id in edge_ids:
                return False
            if not isinstance(edge_type, str) or edge_type not in SCENE_GRAPH_EDGE_TYPE_SET:
                return False
            if not isinstance(source, str) or not source.strip() or source not in node_ids:
                return False
            if not isinstance(target, str) or not target.strip() or target not in node_ids:
                return False
            if not isinstance(weight, (int, float)) or isinstance(weight, bool) or weight < 0 or weight > 1:
                return False
            edge_ids.add(edge_id)

        return True

    def _is_iso_datetime(self, raw: str) -> bool:
        try:
            datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return False
        return True

    def _validate_waveform_bundle_payload(self, payload: dict[str, Any]) -> bool:
        required = [
            "schema_version",
            "project_id",
            "revision",
            "items",
            "generated_at",
        ]
        if any(key not in payload for key in required):
            return False
        if str(payload.get("schema_version")) != "cut_waveform_bundle_v1":
            return False
        if not isinstance(payload.get("items"), list):
            return False
        return True

    def _validate_transcript_bundle_payload(self, payload: dict[str, Any]) -> bool:
        required = [
            "schema_version",
            "project_id",
            "revision",
            "items",
            "generated_at",
        ]
        if any(key not in payload for key in required):
            return False
        if str(payload.get("schema_version")) != "cut_transcript_bundle_v1":
            return False
        if not isinstance(payload.get("items"), list):
            return False
        return True

    def _validate_thumbnail_bundle_payload(self, payload: dict[str, Any]) -> bool:
        required = [
            "schema_version",
            "project_id",
            "revision",
            "items",
            "generated_at",
        ]
        if any(key not in payload for key in required):
            return False
        if str(payload.get("schema_version")) != "cut_thumbnail_bundle_v1":
            return False
        if not isinstance(payload.get("items"), list):
            return False
        return True

    def _validate_audio_sync_result_payload(self, payload: dict[str, Any]) -> bool:
        required = [
            "schema_version",
            "project_id",
            "revision",
            "items",
            "generated_at",
        ]
        if any(key not in payload for key in required):
            return False
        if str(payload.get("schema_version")) != "cut_audio_sync_result_v1":
            return False
        if not isinstance(payload.get("items"), list):
            return False
        for item in payload.get("items", []):
            if not isinstance(item, dict):
                return False
            item_required = [
                "item_id",
                "reference_path",
                "source_path",
                "detected_offset_sec",
                "confidence",
                "method",
                "refinement_steps",
                "peak_value",
                "degraded_mode",
                "degraded_reason",
            ]
            if any(key not in item for key in item_required):
                return False
        return True

    def _validate_slice_bundle_payload(self, payload: dict[str, Any]) -> bool:
        required = [
            "schema_version",
            "project_id",
            "revision",
            "items",
            "generated_at",
        ]
        if any(key not in payload for key in required):
            return False
        if str(payload.get("schema_version")) != "cut_slice_bundle_v1":
            return False
        if not isinstance(payload.get("items"), list):
            return False
        for item in payload.get("items", []):
            if not isinstance(item, dict):
                return False
            item_required = [
                "item_id",
                "source_path",
                "method",
                "windows",
                "degraded_mode",
                "degraded_reason",
            ]
            if any(key not in item for key in item_required):
                return False
            if not isinstance(item.get("windows"), list):
                return False
        return True

    def _validate_timecode_sync_result_payload(self, payload: dict[str, Any]) -> bool:
        required = [
            "schema_version",
            "project_id",
            "revision",
            "items",
            "generated_at",
        ]
        if any(key not in payload for key in required):
            return False
        if str(payload.get("schema_version")) != "cut_timecode_sync_result_v1":
            return False
        if not isinstance(payload.get("items"), list):
            return False
        for item in payload.get("items", []):
            if not isinstance(item, dict):
                return False
            item_required = [
                "item_id",
                "reference_path",
                "source_path",
                "reference_timecode",
                "source_timecode",
                "fps",
                "detected_offset_sec",
                "confidence",
                "method",
                "degraded_mode",
                "degraded_reason",
            ]
            if any(key not in item for key in item_required):
                return False
        return True

    def _validate_music_sync_result_payload(self, payload: dict[str, Any]) -> bool:
        required = ["schema_version", "project_id", "music_path", "tempo",
                     "downbeats", "phrases", "cue_points", "derived_from", "generated_at"]
        if any(key not in payload for key in required):
            return False
        if str(payload.get("schema_version")) != "cut_music_sync_result_v1":
            return False
        tempo = payload.get("tempo")
        if not isinstance(tempo, dict) or "bpm" not in tempo or "confidence" not in tempo:
            return False
        if not isinstance(payload.get("downbeats"), list):
            return False
        if not isinstance(payload.get("phrases"), list):
            return False
        for phrase in payload.get("phrases", []):
            if not isinstance(phrase, dict):
                return False
            if any(k not in phrase for k in ("phrase_id", "start_sec", "end_sec", "energy", "label")):
                return False
        if not isinstance(payload.get("cue_points"), list):
            return False
        for cue in payload.get("cue_points", []):
            if not isinstance(cue, dict):
                return False
            if any(k not in cue for k in ("cue_id", "time_sec", "kind", "strength")):
                return False
        return True

    def _validate_time_marker_bundle_payload(self, payload: dict[str, Any]) -> bool:
        required = [
            "schema_version",
            "project_id",
            "timeline_id",
            "revision",
            "items",
            "generated_at",
        ]
        if any(key not in payload for key in required):
            return False
        if str(payload.get("schema_version")) != "cut_time_marker_bundle_v1":
            return False
        if not isinstance(payload.get("items"), list):
            return False
        for item in payload.get("items", []):
            if not self._validate_time_marker_payload(item):
                return False
        return True

    def _validate_time_marker_payload(self, payload: dict[str, Any]) -> bool:
        required = [
            "marker_id",
            "schema_version",
            "project_id",
            "timeline_id",
            "media_path",
            "kind",
            "start_sec",
            "end_sec",
            "score",
            "created_at",
            "updated_at",
        ]
        if any(key not in payload for key in required):
            return False
        if str(payload.get("schema_version")) != "cut_time_marker_v1":
            return False
        if str(payload.get("kind") or "") not in {"favorite", "comment", "cam", "insight", "chat", "music_sync"}:
            return False
        start_sec = float(payload.get("start_sec") or 0.0)
        end_sec = float(payload.get("end_sec") or 0.0)
        if start_sec < 0 or end_sec < 0 or end_sec < start_sec:
            return False
        score = float(payload.get("score") or 0.0)
        if score < 0 or score > 1:
            return False
        status = str(payload.get("status") or "active")
        if status not in {"active", "archived"}:
            return False
        if not str(payload.get("project_id") or "").strip():
            return False
        if not str(payload.get("timeline_id") or "").strip():
            return False
        if not str(payload.get("media_path") or "").strip():
            return False
        return True

    def _atomic_write_json(self, path: str, payload: dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix=".cut_tmp_", dir=os.path.dirname(path))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
                f.write("\n")
            os.replace(tmp_path, path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


def quick_scan_cut_source(source_path: str, limit: int = 5000) -> dict[str, Any]:
    source = Path(_norm_abs(source_path))
    stats = {
        "media_files": 0,
        "video_files": 0,
        "audio_files": 0,
        "image_files": 0,
        "doc_files": 0,
        "scanned_entries": 0,
    }
    signals = {
        "has_script_or_treatment": False,
        "has_montage_sheet": False,
        "has_transcript_or_timecodes": False,
    }

    def visit_file(path: Path) -> None:
        name = path.name.lower()
        asset_type = _classify_cut_asset_type(path)
        stats["scanned_entries"] += 1
        if asset_type == "video":
            stats["video_files"] += 1
            stats["media_files"] += 1
        elif asset_type == "audio":
            stats["audio_files"] += 1
            stats["media_files"] += 1
        elif asset_type == "image":
            stats["image_files"] += 1
            stats["media_files"] += 1
        elif asset_type == "document":
            stats["doc_files"] += 1

        if any(token in name for token in CUT_SCRIPT_TOKENS):
            signals["has_script_or_treatment"] = True
        if any(token in name for token in CUT_MONTAGE_TOKENS):
            signals["has_montage_sheet"] = True
        if any(token in name for token in CUT_TIMECODE_TOKENS):
            signals["has_transcript_or_timecodes"] = True

    if source.is_file():
        visit_file(source)
    elif source.is_dir():
        for idx, path in enumerate(source.rglob("*")):
            if idx >= max(1, int(limit or 1)):
                break
            if path.is_file():
                visit_file(path)

    return {"stats": stats, "signals": signals}


def build_cut_source_manifest(source_path: str, limit: int = 5000) -> dict[str, Any]:
    source = Path(_norm_abs(source_path))
    limit_value = max(1, int(limit or 1))
    totals = {"video": 0, "audio": 0, "image": 0, "document": 0, "project": 0, "other": 0}
    bucket_map: dict[str, dict[str, Any]] = {}
    key_docs: list[str] = []
    project_files: list[str] = []
    music_tracks: list[dict[str, Any]] = []
    scanned_entries = 0

    def ensure_bucket(name: str) -> dict[str, Any]:
        bucket = bucket_map.get(name)
        if bucket is None:
            bucket = {
                "bucket": name,
                "total_files": 0,
                "asset_totals": {"video": 0, "audio": 0, "image": 0, "document": 0, "project": 0, "other": 0},
                "extensions": {},
                "sample_paths": [],
            }
            bucket_map[name] = bucket
        return bucket

    def visit_file(path: Path) -> None:
        nonlocal scanned_entries
        scanned_entries += 1
        asset_type = _classify_cut_asset_type(path)
        totals[asset_type] += 1
        rel = path.relative_to(source) if source.is_dir() else Path(path.name)
        bucket_name = rel.parts[0] if len(rel.parts) > 1 else "."
        bucket = ensure_bucket(bucket_name)
        bucket["total_files"] += 1
        bucket["asset_totals"][asset_type] += 1
        ext = path.suffix.lower() or "<none>"
        bucket["extensions"][ext] = int(bucket["extensions"].get(ext, 0)) + 1
        rel_str = str(rel)
        if len(bucket["sample_paths"]) < 6:
            bucket["sample_paths"].append(rel_str)

        name = path.name.lower()
        if asset_type == "document" and (
            any(token in name for token in CUT_SCRIPT_TOKENS)
            or any(token in name for token in CUT_MONTAGE_TOKENS)
            or any(token in name for token in CUT_TIMECODE_TOKENS)
        ):
            if len(key_docs) < 10:
                key_docs.append(rel_str)
        if asset_type == "project" and len(project_files) < 10:
            project_files.append(rel_str)
        if asset_type == "audio":
            priority = 2 if any(token in name for token in CUT_MUSIC_TOKENS) else 1
            music_tracks.append(
                {
                    "path": str(path),
                    "relative_path": rel_str,
                    "label": "punch_track" if "punch" in name else "audio_track",
                    "priority": priority,
                }
            )

    if source.is_file():
        visit_file(source)
    elif source.is_dir():
        for idx, path in enumerate(source.rglob("*")):
            if idx >= limit_value:
                break
            if path.is_file():
                visit_file(path)

    bucket_summaries = sorted(
        bucket_map.values(),
        key=lambda item: (-int(item["total_files"]), str(item["bucket"])),
    )
    for bucket in bucket_summaries:
        bucket["extensions"] = dict(
            sorted(bucket["extensions"].items(), key=lambda item: (-int(item[1]), item[0]))[:8]
        )

    music_tracks.sort(key=lambda item: (-int(item["priority"]), item["relative_path"]))
    primary_music_track = music_tracks[0] if music_tracks else None
    return {
        "schema_version": "cut_source_manifest_v1",
        "source_root": str(source),
        "source_kind": "file" if source.is_file() else "directory" if source.is_dir() else "missing",
        "limit": limit_value,
        "scanned_entries": scanned_entries,
        "asset_totals": totals,
        "bucket_summaries": bucket_summaries[:12],
        "key_docs": key_docs,
        "project_files": project_files,
        "audio_tracks": music_tracks[:8],
        "primary_music_track": primary_music_track,
    }


def build_cut_bootstrap_profile(source_path: str, bootstrap_profile: str, *, limit: int = 5000) -> dict[str, Any]:
    profile_name = str(bootstrap_profile or "default").strip() or "default"
    profile_payload: dict[str, Any] = {"profile_name": profile_name}
    if profile_name != "berlin_fixture_v1":
        return profile_payload

    manifest = build_cut_source_manifest(source_path, limit=limit)
    profile_payload.update(
        {
            "source_label": "berlin_sample",
            "sandbox_hint": "codex54_cut_fixture_sandbox",
            "reserved_port": 3211,
            "launch_protocol_doc": "docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_LAUNCH_AND_PORT_PROTOCOL_2026-03-13.md",
            "fixture_manifest": manifest,
            "music_track": manifest.get("primary_music_track"),
        }
    )
    return profile_payload


def build_cut_fallback_questions(signals: dict[str, Any], stats: dict[str, Any]) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    if int(stats.get("media_files", 0) or 0) > 0 and not bool(signals.get("has_script_or_treatment")):
        questions.append(
            {
                "id": "missing_script_or_treatment",
                "priority": 2,
                "question": "No script or treatment detected. Build initial scene grouping from filenames, time, and semantics?",
                "prefill": "VETKA CUT, infer a first scene structure from media metadata and semantic clustering.",
            }
        )
    if int(stats.get("media_files", 0) or 0) > 0 and not bool(signals.get("has_montage_sheet")):
        questions.append(
            {
                "id": "missing_montage_sheet",
                "priority": 3,
                "question": "No montage sheet detected. Create a first-pass montage sheet from available clips and takes?",
                "prefill": "VETKA CUT, generate a first-pass montage sheet from discovered media records.",
            }
        )
    if int(stats.get("audio_files", 0) or 0) > 0 and not bool(signals.get("has_transcript_or_timecodes")):
        questions.append(
            {
                "id": "missing_transcript_timecodes",
                "priority": 1,
                "question": "No transcript or timecodes detected. Queue transcript and timecode generation for audio/video?",
                "prefill": "VETKA CUT, start transcript and timecode generation for the current source scope.",
            }
        )
    return questions
