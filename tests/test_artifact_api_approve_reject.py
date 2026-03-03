# MARKER_136.ARTIFACT_APPROVE_REJECT_TEST
import asyncio
import json
from types import SimpleNamespace

import src.services.artifact_scanner as scanner
from src.api.handlers.artifact_routes import (
    list_artifacts_for_panel,
    approve_artifact_for_panel,
    reject_artifact_for_panel,
)
from src.api.routes.artifact_routes import (
    ArtifactDecisionRequest,
    SaveSearchResultRequest,
    approve_artifact_endpoint,
    reject_artifact_endpoint,
    save_search_result_endpoint,
    media_startup,
    MediaStartupRequest,
    media_preview,
    MediaPreviewRequest,
    media_semantic_links,
    MediaSemanticLinksRequest,
    media_rhythm_assist,
    MediaRhythmAssistRequest,
    media_cam_overlay,
    MediaCamOverlayRequest,
    media_transcript_normalized,
    MediaTranscriptNormalizeRequest,
    media_export_premiere_xml,
    MediaExportPremiereXMLRequest,
    media_export_fcpxml,
    MediaExportFCPXMLRequest,
)


def _patch_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(scanner, "ARTIFACTS_DIR", tmp_path / "data" / "artifacts")
    monkeypatch.setattr(scanner, "VETKA_OUT_DIR", tmp_path / "src" / "vetka_out")
    monkeypatch.setattr(scanner, "STAGING_FILE", tmp_path / "data" / "staging.json")


def test_list_artifacts_includes_vetka_out(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    scanner.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    scanner.VETKA_OUT_DIR.mkdir(parents=True, exist_ok=True)

    (scanner.ARTIFACTS_DIR / "a.py").write_text("print('a')", encoding="utf-8")
    (scanner.VETKA_OUT_DIR / "b.md").write_text("# b", encoding="utf-8")

    payload = list_artifacts_for_panel()
    assert payload["success"] is True
    names = {a["name"] for a in payload["artifacts"]}
    assert names == {"a.py", "b.md"}


def test_approve_and_reject_update_staging(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    scanner.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    scanner.STAGING_FILE.parent.mkdir(parents=True, exist_ok=True)

    filename = "feature.py"
    (scanner.ARTIFACTS_DIR / filename).write_text("print('ok')", encoding="utf-8")

    artifact_id = scanner._generate_artifact_id(filename)

    approved = approve_artifact_for_panel(artifact_id, "looks good")
    assert approved["success"] is True
    assert approved["status"] == "approved"

    data = json.loads(scanner.STAGING_FILE.read_text(encoding="utf-8"))
    assert data["artifacts"][approved["artifact_id"]]["status"] == "approved"

    rejected = reject_artifact_for_panel(artifact_id, "needs tests")
    assert rejected["success"] is True
    assert rejected["status"] == "rejected"

    data = json.loads(scanner.STAGING_FILE.read_text(encoding="utf-8"))
    assert data["artifacts"][rejected["artifact_id"]]["feedback"] == "needs tests"


def test_artifact_route_endpoints(monkeypatch):
    monkeypatch.setattr(
        "src.api.routes.artifact_routes.approve_artifact_for_panel",
        lambda artifact_id, reason: {"success": True, "artifact_id": artifact_id, "reason": reason, "status": "approved"},
    )
    monkeypatch.setattr(
        "src.api.routes.artifact_routes.reject_artifact_for_panel",
        lambda artifact_id, reason: {"success": True, "artifact_id": artifact_id, "reason": reason, "status": "rejected"},
    )

    ok = asyncio.run(approve_artifact_endpoint("artifact_abc", ArtifactDecisionRequest(reason="ok")))
    bad = asyncio.run(reject_artifact_endpoint("artifact_abc", ArtifactDecisionRequest(reason="bad")))

    assert ok["status"] == "approved"
    assert bad["status"] == "rejected"


def test_save_search_result_endpoint_indexes_when_qdrant_available(monkeypatch, tmp_path):
    saved = tmp_path / "saved.md"
    saved.write_text("# ok", encoding="utf-8")

    async def _save_search_result_artifact_mock(**kwargs):
        return {
            "success": True,
            "file_path": str(saved),
            "title": "Saved",
        }

    monkeypatch.setattr(
        "src.api.routes.artifact_routes.save_search_result_artifact",
        _save_search_result_artifact_mock,
    )

    class _Updater:
        def update_file(self, path):
            return True

    monkeypatch.setattr(
        "src.api.routes.artifact_routes.get_qdrant_updater",
        lambda **kwargs: _Updater(),
    )

    req = SaveSearchResultRequest(source="web", url="https://example.com")
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=SimpleNamespace(client=object()))))
    result = asyncio.run(save_search_result_endpoint(req, request))
    assert result["success"] is True
    assert result["indexed"] is True


def test_save_search_result_endpoint_marks_index_error_without_qdrant(monkeypatch, tmp_path):
    saved = tmp_path / "saved.md"
    saved.write_text("# ok", encoding="utf-8")

    async def _save_search_result_artifact_mock(**kwargs):
        return {
            "success": True,
            "file_path": str(saved),
            "title": "Saved",
        }

    monkeypatch.setattr(
        "src.api.routes.artifact_routes.save_search_result_artifact",
        _save_search_result_artifact_mock,
    )

    req = SaveSearchResultRequest(source="file", path="README.md")
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=None)))
    result = asyncio.run(save_search_result_endpoint(req, request))
    assert result["success"] is True
    assert result["indexed"] is False
    assert result["index_error"] == "qdrant_client_not_available"


def test_save_search_result_endpoint_returns_policy_block(monkeypatch, tmp_path):
    blocked = tmp_path / "blocked.exe"
    blocked.write_bytes(b"binary")

    async def _save_search_result_artifact_mock(**kwargs):
        return {
            "success": True,
            "file_path": str(blocked),
            "title": "Saved",
        }

    monkeypatch.setattr(
        "src.api.routes.artifact_routes.save_search_result_artifact",
        _save_search_result_artifact_mock,
    )

    req = SaveSearchResultRequest(source="file", path="README.md")
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=SimpleNamespace(client=object()))))
    result = asyncio.run(save_search_result_endpoint(req, request))
    assert result["success"] is True
    assert result["indexed"] is False
    assert result["index_error"] == "ingest_policy_blocked"
    assert result["index_policy"]["code"] in ("DENY_EXTENSION", "UNKNOWN_EXTENSION", "FILE_TOO_LARGE")


def test_save_search_result_endpoint_wires_artifact_batch_queue(monkeypatch, tmp_path):
    saved = tmp_path / "saved.md"
    saved.write_text("# ok\nartifact body", encoding="utf-8")

    async def _save_search_result_artifact_mock(**kwargs):
        return {
            "success": True,
            "file_path": str(saved),
            "title": "Saved",
            "artifact_id": "art-1",
        }

    monkeypatch.setattr(
        "src.api.routes.artifact_routes.save_search_result_artifact",
        _save_search_result_artifact_mock,
    )

    class _Updater:
        def update_file(self, path):
            return True

    class _Registry:
        def extract_file(self, file_path, rel_path=None, max_text_chars=5000):
            from src.scanners.extractor_registry import ExtractionResult

            return ExtractionResult(
                text="artifact text",
                metadata={"extraction_route": "text"},
                extractor_id="text_reader",
            )

    captured = {"queued": False, "flushed": False}

    class _BatchMgr:
        async def queue_artifact(self, **kwargs):
            captured["queued"] = True

        async def force_flush(self):
            captured["flushed"] = True

    monkeypatch.setattr(
        "src.api.routes.artifact_routes.get_qdrant_updater",
        lambda **kwargs: _Updater(),
    )
    monkeypatch.setattr(
        "src.api.routes.artifact_routes.get_media_extractor_registry",
        lambda: _Registry(),
    )
    monkeypatch.setattr(
        "src.memory.qdrant_batch_manager.get_batch_manager",
        lambda: _BatchMgr(),
    )

    req = SaveSearchResultRequest(source="web", url="https://example.com")
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=SimpleNamespace(client=object()))))
    result = asyncio.run(save_search_result_endpoint(req, request))
    assert result["success"] is True
    assert result["indexed"] is True
    assert result["artifact_batch_queued"] is True
    assert captured["queued"] is True
    assert captured["flushed"] is True


def test_media_preview_returns_waveform_for_wav(monkeypatch, tmp_path):
    import wave
    import struct

    wav_path = tmp_path / "tone.wav"
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(8000)
        frames = b"".join(struct.pack("<h", int(12000 * (1 if i % 2 == 0 else -1))) for i in range(1600))
        wf.writeframes(frames)

    monkeypatch.setattr(
        "src.api.routes.artifact_routes._probe_media_duration",
        lambda path: 0.2,
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=None)))
    payload = MediaPreviewRequest(path=str(wav_path), waveform_bins=32, preview_segments_limit=8)
    result = asyncio.run(media_preview(payload, request))
    assert result["success"] is True
    assert result["modality"] == "audio"
    assert isinstance(result["waveform_bins"], list)
    assert len(result["waveform_bins"]) > 0


def test_media_preview_not_found(tmp_path):
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=None)))
    payload = MediaPreviewRequest(path=str(tmp_path / "missing.mp4"), waveform_bins=32, preview_segments_limit=8)
    try:
        asyncio.run(media_preview(payload, request))
        assert False, "Expected HTTPException for missing media file"
    except Exception as exc:
        from fastapi import HTTPException

        assert isinstance(exc, HTTPException)
        assert exc.status_code == 404


def test_media_startup_collects_scope_stats(tmp_path):
    media_dir = tmp_path / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    (media_dir / "a.wav").write_bytes(b"RIFFxxxxWAVEfmt ")
    (media_dir / "b.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    (media_dir / "note.txt").write_text("hello", encoding="utf-8")

    result = asyncio.run(media_startup(MediaStartupRequest(scope_path=str(media_dir), quick_scan_limit=1000)))
    assert result["success"] is True
    assert result["scope_path"] == str(media_dir)
    assert result["stats"]["media_files"] == 2
    assert result["stats"]["audio_files"] == 1
    assert result["stats"]["video_files"] == 1
    assert result["degraded_mode"] is False
    assert result["missing_inputs"]["script_or_treatment"] is True
    assert result["missing_inputs"]["montage_sheet"] is True
    assert result["missing_inputs"]["transcript_or_timecodes"] is True
    assert isinstance(result["fallback_questions"], list)
    assert len(result["fallback_questions"]) >= 1


def test_media_startup_falls_back_when_scope_missing(tmp_path):
    missing = tmp_path / "nope"
    result = asyncio.run(media_startup(MediaStartupRequest(scope_path=str(missing), quick_scan_limit=1000)))
    assert result["success"] is True
    assert result["degraded_mode"] is True
    assert result["degraded_reason"] == "scope_not_found_fallback_to_cwd"


def test_media_startup_detects_existing_pipeline_inputs(tmp_path):
    media_dir = tmp_path / "media_ready"
    media_dir.mkdir(parents=True, exist_ok=True)
    (media_dir / "scene_01.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    (media_dir / "film_script_treatment.md").write_text("scene plan", encoding="utf-8")
    (media_dir / "montage_sheet_v1.csv").write_text("scene,take,timecode\n1,A,00:00:10", encoding="utf-8")
    (media_dir / "dialog_transcript.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nhello\n", encoding="utf-8")

    result = asyncio.run(media_startup(MediaStartupRequest(scope_path=str(media_dir), quick_scan_limit=1000)))
    assert result["success"] is True
    assert result["missing_inputs"]["script_or_treatment"] is False
    assert result["missing_inputs"]["montage_sheet"] is False
    assert result["missing_inputs"]["transcript_or_timecodes"] is False
    assert result["fallback_questions"] == []


def test_media_preview_enriches_timeline_lanes(tmp_path, monkeypatch):
    mp4_path = tmp_path / "clip.mp4"
    mp4_path.write_bytes(b"\x00\x00\x00\x18ftypmp42")
    monkeypatch.setattr(
        "src.api.routes.artifact_routes._probe_media_duration",
        lambda path: 10.0,
    )

    class _Result:
        def __init__(self, payload):
            self.payload = payload

    class _Updater:
        collection_name = "vetka_tree"

        def _get_point_id(self, path):
            return "pt1"

    class _Client:
        def retrieve(self, **kwargs):
            return [
                _Result(
                    {
                        "media_chunks_v1": [
                            {"start_sec": 0.0, "end_sec": 6.0, "text": "main"},
                            {"start_sec": 1.0, "end_sec": 2.0, "text": "alt"},
                        ]
                    }
                )
            ]

    monkeypatch.setattr(
        "src.api.routes.artifact_routes.get_qdrant_updater",
        lambda **kwargs: _Updater(),
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=SimpleNamespace(client=_Client()))))
    payload = MediaPreviewRequest(path=str(mp4_path), waveform_bins=32, preview_segments_limit=8)
    result = asyncio.run(media_preview(payload, request))
    assert result["success"] is True
    assert len(result["timeline_segments"]) == 2
    assert result["timeline_segments"][0]["timeline_lane"] == "video_main"
    assert result["timeline_segments"][1]["timeline_lane"] == "take_alt_y"


def test_media_semantic_links_groups_relations(tmp_path, monkeypatch):
    media_path = tmp_path / "scene.mp4"
    media_path.write_bytes(b"\x00\x00\x00\x18ftypmp42")

    class _TW:
        def search_media_chunks(self, **kwargs):
            return [
                {
                    "score": 0.91,
                    "parent_file_path": str(media_path),
                    "start_sec": 5.0,
                    "end_sec": 6.0,
                    "text": "John runs through the city street",
                },
                {
                    "score": 0.75,
                    "parent_file_path": str(media_path),
                    "start_sec": 8.0,
                    "end_sec": 9.0,
                    "text": "The theme of sacrifice becomes clear",
                },
            ]

    monkeypatch.setattr(
        "src.orchestration.triple_write_manager.get_triple_write_manager",
        lambda: _TW(),
    )

    payload = MediaSemanticLinksRequest(
        path=str(media_path),
        query_text="John enters the street quickly",
        start_sec=1.0,
        end_sec=2.0,
        limit=8,
    )
    result = asyncio.run(media_semantic_links(payload))
    assert result["success"] is True
    assert len(result["links"]) >= 1
    relation_types = {item["relation_type"] for item in result["links"]}
    assert "hero" in relation_types or "location" in relation_types


def test_media_semantic_links_empty_query_returns_degraded(tmp_path):
    media_path = tmp_path / "scene.mp4"
    media_path.write_bytes(b"\x00\x00\x00\x18ftypmp42")

    payload = MediaSemanticLinksRequest(path=str(media_path), query_text="", limit=8)
    result = asyncio.run(media_semantic_links(payload))
    assert result["success"] is True
    assert result["degraded_mode"] is True
    assert result["degraded_reason"] == "empty_query_text"
    assert result["links"] == []


def test_media_rhythm_assist_returns_metrics(tmp_path, monkeypatch):
    media_path = tmp_path / "scene.mp4"
    media_path.write_bytes(b"\x00\x00\x00\x18ftypmp42")
    monkeypatch.setattr(
        "src.api.routes.artifact_routes._probe_media_duration",
        lambda path: 12.0,
    )

    class _Result:
        def __init__(self, payload):
            self.payload = payload

    class _Updater:
        collection_name = "vetka_tree"

        def _get_point_id(self, path):
            return "pt1"

    class _Client:
        def retrieve(self, **kwargs):
            return [
                _Result(
                    {
                        "media_chunks_v1": [
                            {"start_sec": 0.0, "end_sec": 2.0, "text": "John enters room", "confidence": 0.8},
                            {"start_sec": 2.0, "end_sec": 3.2, "text": "Camera turns quickly", "confidence": 0.9},
                            {"start_sec": 3.2, "end_sec": 4.1, "text": "Cut to street", "confidence": 0.7},
                        ]
                    }
                )
            ]

    monkeypatch.setattr(
        "src.api.routes.artifact_routes.get_qdrant_updater",
        lambda **kwargs: _Updater(),
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=SimpleNamespace(client=_Client()))))
    payload = MediaRhythmAssistRequest(path=str(media_path), bins=48, segments_limit=64)
    result = asyncio.run(media_rhythm_assist(payload, request))
    assert result["success"] is True
    assert "rhythm_features" in result
    assert result["rhythm_features"]["cut_density"]["per_min"] >= 0.0
    assert 0.0 <= result["rhythm_features"]["motion_volatility"] <= 1.0
    assert isinstance(result.get("energy_track"), list)
    assert len(result["energy_track"]) == 48
    assert "pulse_bridge" in result
    assert "mode" in result["pulse_bridge"]
    assert len(result["recommendations"]) >= 1


def test_media_rhythm_assist_degraded_when_no_segments(tmp_path, monkeypatch):
    media_path = tmp_path / "empty.mp4"
    media_path.write_bytes(b"\x00\x00\x00\x18ftypmp42")
    monkeypatch.setattr(
        "src.api.routes.artifact_routes._probe_media_duration",
        lambda path: 8.0,
    )

    class _Updater:
        collection_name = "vetka_tree"

        def _get_point_id(self, path):
            return "pt-empty"

    class _Client:
        def retrieve(self, **kwargs):
            return []

    monkeypatch.setattr(
        "src.api.routes.artifact_routes.get_qdrant_updater",
        lambda **kwargs: _Updater(),
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=SimpleNamespace(client=_Client()))))
    payload = MediaRhythmAssistRequest(path=str(media_path), bins=32, segments_limit=16)
    result = asyncio.run(media_rhythm_assist(payload, request))
    assert result["success"] is True
    assert result["degraded_mode"] is True
    assert result["degraded_reason"] == "no_media_segments_v1"


def test_media_routes_playback_metadata_contract_smoke(tmp_path, monkeypatch):
    media_path = tmp_path / "scene.mp4"
    media_path.write_bytes(b"\x00\x00\x00\x18ftypmp42")
    monkeypatch.setattr(
        "src.api.routes.artifact_routes._probe_media_duration",
        lambda path: 10.0,
    )

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=None)))

    preview = asyncio.run(
        media_preview(
            MediaPreviewRequest(path=str(media_path), waveform_bins=24, preview_segments_limit=16),
            request,
        )
    )
    assert isinstance(preview.get("playback_metadata"), dict)
    assert preview["playback_metadata"]["modality"] == "video"
    assert preview["playback_metadata"]["duration_sec"] == 10.0
    assert "has_waveform" in preview["playback_metadata"]
    assert "has_timeline_segments" in preview["playback_metadata"]

    semantic = asyncio.run(
        media_semantic_links(
            MediaSemanticLinksRequest(path=str(media_path), query_text="hero action", limit=5)
        )
    )
    assert isinstance(semantic.get("playback_metadata"), dict)
    assert semantic["playback_metadata"]["query_text"] == "hero action"
    assert semantic["playback_metadata"]["links_count"] == len(semantic["links"])

    rhythm = asyncio.run(
        media_rhythm_assist(
            MediaRhythmAssistRequest(path=str(media_path), bins=32, segments_limit=16),
            request,
        )
    )
    assert isinstance(rhythm.get("playback_metadata"), dict)
    assert rhythm["playback_metadata"]["duration_sec"] == 10.0
    assert rhythm["playback_metadata"]["target_bpm"] == rhythm["music_binding"]["target_bpm"]
    assert rhythm["playback_metadata"]["phase_markers_count"] == len(rhythm["rhythm_features"]["phase_markers"])


def test_media_cam_overlay_returns_contract(tmp_path, monkeypatch):
    media_path = tmp_path / "scene.mp4"
    media_path.write_bytes(b"\x00\x00\x00\x18ftypmp42")
    monkeypatch.setattr(
        "src.api.routes.artifact_routes._probe_media_duration",
        lambda path: 12.0,
    )

    class _Result:
        def __init__(self, payload):
            self.payload = payload

    class _Updater:
        collection_name = "vetka_tree"

        def _get_point_id(self, path):
            return "pt-cam"

    class _Client:
        def retrieve(self, **kwargs):
            return [
                _Result(
                    {
                        "media_chunks_v1": [
                            {"start_sec": 0.0, "end_sec": 1.5, "text": "calm shot", "confidence": 0.5},
                            {"start_sec": 1.5, "end_sec": 2.1, "text": "action burst", "confidence": 0.9},
                            {"start_sec": 2.1, "end_sec": 3.6, "text": "reaction", "confidence": 0.7},
                        ]
                    }
                )
            ]

    monkeypatch.setattr(
        "src.api.routes.artifact_routes.get_qdrant_updater",
        lambda **kwargs: _Updater(),
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=SimpleNamespace(client=_Client()))))
    payload = MediaCamOverlayRequest(path=str(media_path), bins=36, segments_limit=64)
    result = asyncio.run(media_cam_overlay(payload, request))
    assert result["success"] is True
    assert result["modality"] == "video"
    assert len(result["cam_features"]["uniqueness_track"]) == 36
    assert len(result["cam_features"]["memorability_track"]) == 36
    assert isinstance(result["cam_features"]["top_moments"], list)
    assert isinstance(result["cam_bridge"], dict)
    assert "mode" in result["cam_bridge"]
    assert isinstance(result["playback_metadata"], dict)
    assert result["playback_metadata"]["cam_bins"] == 36


def test_media_cam_overlay_degraded_when_no_segments(tmp_path, monkeypatch):
    media_path = tmp_path / "scene.mp4"
    media_path.write_bytes(b"\x00\x00\x00\x18ftypmp42")
    monkeypatch.setattr(
        "src.api.routes.artifact_routes._probe_media_duration",
        lambda path: 9.0,
    )

    class _Updater:
        collection_name = "vetka_tree"

        def _get_point_id(self, path):
            return "pt-empty-cam"

    class _Client:
        def retrieve(self, **kwargs):
            return []

    monkeypatch.setattr(
        "src.api.routes.artifact_routes.get_qdrant_updater",
        lambda **kwargs: _Updater(),
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=SimpleNamespace(client=_Client()))))
    payload = MediaCamOverlayRequest(path=str(media_path), bins=24, segments_limit=16)
    result = asyncio.run(media_cam_overlay(payload, request))
    assert result["success"] is True
    segment_source = result.get("playback_metadata", {}).get("segment_source")
    if segment_source == "ffmpeg_scene_detect":
        assert result["degraded_mode"] is False
        assert result["degraded_reason"] == ""
    else:
        assert result["degraded_mode"] is True
        assert result["degraded_reason"] == "no_media_segments_v1"


def test_media_transcript_normalized_success_contract(tmp_path, monkeypatch):
    media_path = tmp_path / "voice.m4a"
    media_path.write_bytes(b"\x00\x00\x00\x18ftypM4A ")
    monkeypatch.setattr("src.api.routes.artifact_routes._probe_media_duration", lambda path: 14.0)
    monkeypatch.setattr(
        "src.api.routes.artifact_routes._transcribe_media_whisper",
        lambda target, duration_sec, max_transcribe_sec=None, clip_for_testing_only=False: {
            "text": "hello world",
            "segments": [
                {"start": 0.0, "end": 0.7, "text": "hello", "confidence": 0.9},
                {"start": 0.7, "end": 1.2, "text": "world", "confidence": 0.8},
            ],
            "language": "en",
            "source_engine": "mlx_whisper",
            "clipped": False,
        },
    )

    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=None)))
    payload = MediaTranscriptNormalizeRequest(path=str(media_path), segments_limit=64)
    result = asyncio.run(media_transcript_normalized(payload, req))
    assert result["success"] is True
    assert result["degraded_mode"] is False
    tx = result["transcript_normalized_json"]
    assert tx["schema_version"] == "vetka_transcript_v1"
    assert tx["language"] == "en"
    assert tx["text"] == "hello world"
    assert len(tx["segments"]) == 2
    assert result["playback_metadata"]["segments_count"] == 2


def test_media_transcript_normalized_degraded_when_stt_unavailable(tmp_path, monkeypatch):
    media_path = tmp_path / "voice.m4a"
    media_path.write_bytes(b"\x00\x00\x00\x18ftypM4A ")
    monkeypatch.setattr("src.api.routes.artifact_routes._probe_media_duration", lambda path: 10.0)

    def _boom(*args, **kwargs):
        raise RuntimeError("whisper_model_missing")

    monkeypatch.setattr("src.api.routes.artifact_routes._transcribe_media_whisper", _boom)
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=None)))
    payload = MediaTranscriptNormalizeRequest(path=str(media_path), segments_limit=64)
    result = asyncio.run(media_transcript_normalized(payload, req))
    assert result["success"] is True
    assert result["degraded_mode"] is True
    assert str(result["degraded_reason"]).startswith("stt_unavailable:")
    tx = result["transcript_normalized_json"]
    assert tx["segments"] == []


def test_media_export_premiere_xml_contract(tmp_path, monkeypatch):
    media_path = tmp_path / "scene.mp4"
    media_path.write_bytes(b"\x00\x00\x00\x18ftypmp42")
    monkeypatch.setattr("src.api.routes.artifact_routes._probe_media_duration", lambda path: 12.0)
    monkeypatch.setattr(
        "src.api.routes.artifact_routes._transcribe_media_whisper",
        lambda target, duration_sec, max_transcribe_sec=None, clip_for_testing_only=False: {
            "text": "hello world",
            "segments": [
                {"start": 0.5, "end": 1.2, "text": "hello"},
                {"start": 2.0, "end": 2.9, "text": "world"},
            ],
            "language": "en",
            "source_engine": "mlx_whisper",
            "clipped": False,
        },
    )
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=None)))
    payload = MediaExportPremiereXMLRequest(path=str(media_path), sequence_name="SeqA", fps=30.0)
    result = asyncio.run(media_export_premiere_xml(payload, req))
    assert result["success"] is True
    assert result["format"] == "premiere_xml"
    assert result["xml_root"] == "xmeml"
    assert "<xmeml version=\"5\"" in result["xml_content"]


def test_media_export_fcpxml_contract(tmp_path, monkeypatch):
    media_path = tmp_path / "scene.mp4"
    media_path.write_bytes(b"\x00\x00\x00\x18ftypmp42")
    monkeypatch.setattr("src.api.routes.artifact_routes._probe_media_duration", lambda path: 12.0)
    monkeypatch.setattr(
        "src.api.routes.artifact_routes._transcribe_media_whisper",
        lambda target, duration_sec, max_transcribe_sec=None, clip_for_testing_only=False: {
            "text": "hello world",
            "segments": [
                {"start": 0.5, "end": 1.2, "text": "hello"},
                {"start": 2.0, "end": 2.9, "text": "world"},
            ],
            "language": "en",
            "source_engine": "mlx_whisper",
            "clipped": False,
        },
    )
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=None)))
    payload = MediaExportFCPXMLRequest(path=str(media_path), sequence_name="SeqF", fps=30.0)
    result = asyncio.run(media_export_fcpxml(payload, req))
    assert result["success"] is True
    assert result["format"] == "fcpxml"
    assert result["xml_root"] == "fcpxml"
    assert "<fcpxml version=" in result["xml_content"]
