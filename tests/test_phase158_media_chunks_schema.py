from src.scanners.multimodal_contracts import (
    MEDIA_CHUNKS_SCHEMA_VERSION,
    EXTRACTION_VERSION,
    normalize_media_chunks,
    build_multimodal_payload,
)


def test_normalize_media_chunks_v1_shape():
    chunks = normalize_media_chunks(
        [{"start_sec": 1.0, "end_sec": 2.5, "text": "hello", "confidence": 0.9}],
        parent_file_path="media/a.mp4",
        modality="video",
        extractor_id="whisper_stt",
    )
    assert len(chunks) == 1
    c = chunks[0]
    assert c["schema_version"] == MEDIA_CHUNKS_SCHEMA_VERSION
    assert c["chunk_index"] == 0
    assert c["chunk_id"] == "media/a.mp4#chunk:0"
    assert c["duration_sec"] == 1.5
    assert c["extractor_id"] == "whisper_stt"
    assert c["timeline_lane"] == "video_main"
    assert c["lane_index"] == 0


def test_normalize_media_chunks_sorts_by_start_and_reindexes():
    chunks = normalize_media_chunks(
        [
            {"start_sec": 6.0, "end_sec": 7.0, "text": "third", "confidence": 0.4},
            {"start_sec": 1.0, "end_sec": 2.0, "text": "first", "confidence": 0.8},
            {"start_sec": 3.0, "end_sec": 4.0, "text": "second", "confidence": 0.7},
        ],
        parent_file_path="media/sort.mp4",
        modality="video",
        extractor_id="whisper_stt",
    )
    assert [c["text"] for c in chunks] == ["first", "second", "third"]
    assert [c["chunk_index"] for c in chunks] == [0, 1, 2]
    assert [c["chunk_id"] for c in chunks] == [
        "media/sort.mp4#chunk:0",
        "media/sort.mp4#chunk:1",
        "media/sort.mp4#chunk:2",
    ]


def test_normalize_media_chunks_clamps_bounds_and_coerces_types():
    chunks = normalize_media_chunks(
        [
            {"start_sec": "-2.2", "end_sec": "-1.0", "text": None, "confidence": "2.7"},
            {"start_sec": "bad", "end_sec": "also_bad", "text": "ok", "confidence": "bad"},
        ],
        parent_file_path="media/coerce.wav",
        modality="audio",
        extractor_id="whisper_stt",
    )
    assert len(chunks) == 2
    assert chunks[0]["start_sec"] == 0.0
    assert chunks[0]["end_sec"] == 0.0
    assert chunks[0]["duration_sec"] == 0.0
    assert chunks[0]["text"] == ""
    assert chunks[0]["confidence"] == 1.0
    assert chunks[0]["timeline_lane"] == "audio_sync"

    assert chunks[1]["start_sec"] == 0.0
    assert chunks[1]["end_sec"] == 0.0
    assert chunks[1]["confidence"] == 0.0


def test_build_multimodal_payload_contains_v1_fields():
    payload = build_multimodal_payload(
        extension=".mp4",
        mime_type="video/mp4",
        modality="video",
        ingest_mode="multimodal",
        extractor_id="whisper_stt",
        extraction_route="stt",
        media_chunks_v1=[{"chunk_index": 0, "text": "hello"}],
        extra={"foo": "bar"},
    )
    assert payload["media_chunks_schema"] == MEDIA_CHUNKS_SCHEMA_VERSION
    assert payload["extraction_version"] == EXTRACTION_VERSION
    assert "media_chunks_v1" in payload
    assert payload["media_chunks"] == payload["media_chunks_v1"][:32]
    assert payload["foo"] == "bar"


def test_build_multimodal_payload_marks_non_degraded_for_stt():
    payload = build_multimodal_payload(
        extension=".mp4",
        mime_type="video/mp4",
        modality="video",
        ingest_mode="multimodal",
        extractor_id="whisper_stt",
        extraction_route="stt",
        media_chunks_v1=[{"chunk_index": 0, "text": "hello"}],
    )
    assert payload["degraded_mode"] is False
    assert payload["degraded_reason"] == ""


def test_build_multimodal_payload_marks_degraded_for_summary_fallback():
    payload = build_multimodal_payload(
        extension=".mp4",
        mime_type="video/mp4",
        modality="video",
        ingest_mode="multimodal",
        extractor_id="summary_fallback",
        extraction_route="summary_fallback",
        media_chunks_v1=[],
    )
    assert payload["degraded_mode"] is True
    assert payload["degraded_reason"] == "summary_fallback"


def test_build_multimodal_payload_marks_degraded_for_ocr_error():
    payload = build_multimodal_payload(
        extension=".png",
        mime_type="image/png",
        modality="image",
        ingest_mode="multimodal",
        extractor_id="ocr_processor",
        extraction_route="ocr_error",
        media_chunks_v1=[],
    )
    assert payload["degraded_mode"] is True
    assert payload["degraded_reason"] == "ocr_error"
