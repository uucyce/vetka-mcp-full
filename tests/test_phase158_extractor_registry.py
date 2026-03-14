from pathlib import Path

from src.scanners.extractor_registry import MediaExtractorRegistry


def test_extractor_registry_text_route(tmp_path):
    registry = MediaExtractorRegistry()
    fpath = tmp_path / "note.md"
    fpath.write_text("# hello\nworld", encoding="utf-8")

    result = registry.extract_file(fpath, rel_path="note.md")
    assert result.extractor_id == "text_reader"
    assert "hello" in result.text
    assert result.metadata.get("extraction_route") == "text"


def test_extractor_registry_dispatches_ocr(monkeypatch, tmp_path):
    registry = MediaExtractorRegistry()
    fpath = tmp_path / "frame.png"
    fpath.write_bytes(b"\x89PNG\r\n\x1a\n")

    called = {"ocr": False}

    def _fake_ocr(**kwargs):
        called["ocr"] = True
        from src.scanners.extractor_registry import ExtractionResult

        return ExtractionResult(
            text="ocr text",
            metadata={"extraction_route": "ocr"},
            extractor_id="ocr_processor",
        )

    monkeypatch.setattr(registry, "_extract_ocr", _fake_ocr)
    result = registry.extract_file(fpath, rel_path="frame.png")

    assert called["ocr"] is True
    assert result.extractor_id == "ocr_processor"
    assert result.text == "ocr text"


def test_extractor_registry_dispatches_media(monkeypatch, tmp_path):
    registry = MediaExtractorRegistry()
    fpath = tmp_path / "clip.mp4"
    fpath.write_bytes(b"\x00\x00\x00\x18ftypmp42")

    called = {"av": False}

    def _fake_av(**kwargs):
        called["av"] = True
        from src.scanners.extractor_registry import ExtractionResult

        return ExtractionResult(
            text="transcript",
            media_chunks=[{"start_sec": 0.0, "end_sec": 1.0, "text": "hello"}],
            metadata={"extraction_route": "stt"},
            extractor_id="whisper_stt",
        )

    monkeypatch.setattr(registry, "_extract_av", _fake_av)
    result = registry.extract_file(fpath, rel_path="clip.mp4")

    assert called["av"] is True
    assert result.extractor_id == "whisper_stt"
    assert len(result.media_chunks) == 1


def test_extractor_registry_optional_enrichment_success(monkeypatch, tmp_path):
    registry = MediaExtractorRegistry()
    fpath = tmp_path / "clip.mp4"
    fpath.write_bytes(b"\x00\x00\x00\x18ftypmp42")

    def _fake_av(**kwargs):
        from src.scanners.extractor_registry import ExtractionResult

        return ExtractionResult(
            text="transcript",
            media_chunks=[{"start_sec": 0.0, "end_sec": 1.0, "text": "hello"}],
            metadata={"extraction_route": "stt"},
            extractor_id="whisper_stt",
        )

    def _hook(**kwargs):
        return {"vector_dim": 768}

    monkeypatch.setattr(registry, "_extract_av", _fake_av)
    monkeypatch.setattr(
        registry,
        "_get_optional_enrichers",
        lambda **kwargs: [("jepa", _hook, 50.0)],
    )

    result = registry.extract_file(fpath, rel_path="clip.mp4")
    enrich = result.metadata.get("optional_enrichments", {})
    assert "jepa" in enrich
    assert enrich["jepa"]["status"] == "ok"
    assert enrich["jepa"]["payload"]["vector_dim"] == 768


def test_extractor_registry_optional_enrichment_error_is_graceful(monkeypatch, tmp_path):
    registry = MediaExtractorRegistry()
    fpath = tmp_path / "clip.mp4"
    fpath.write_bytes(b"\x00\x00\x00\x18ftypmp42")

    def _fake_av(**kwargs):
        from src.scanners.extractor_registry import ExtractionResult

        return ExtractionResult(
            text="transcript",
            media_chunks=[],
            metadata={"extraction_route": "stt"},
            extractor_id="whisper_stt",
        )

    def _hook_fail(**kwargs):
        raise RuntimeError("jepa_unavailable")

    monkeypatch.setattr(registry, "_extract_av", _fake_av)
    monkeypatch.setattr(
        registry,
        "_get_optional_enrichers",
        lambda **kwargs: [("jepa", _hook_fail, 50.0)],
    )

    result = registry.extract_file(fpath, rel_path="clip.mp4")
    enrich = result.metadata.get("optional_enrichments", {})
    assert "jepa" in enrich
    assert enrich["jepa"]["status"] == "error"
    assert "jepa_unavailable" in enrich["jepa"]["error"]
    assert result.extractor_id == "whisper_stt"


def test_extractor_registry_optional_enrichment_marks_over_budget(monkeypatch, tmp_path):
    registry = MediaExtractorRegistry()
    fpath = tmp_path / "clip.mp4"
    fpath.write_bytes(b"\x00\x00\x00\x18ftypmp42")

    def _fake_av(**kwargs):
        from src.scanners.extractor_registry import ExtractionResult

        return ExtractionResult(
            text="transcript",
            media_chunks=[],
            metadata={"extraction_route": "stt"},
            extractor_id="whisper_stt",
        )

    def _hook(**kwargs):
        return {"ok": True}

    ticks = iter([10.0, 10.08])  # 80ms
    monkeypatch.setattr("src.scanners.extractor_registry.time.perf_counter", lambda: next(ticks))
    monkeypatch.setattr(registry, "_extract_av", _fake_av)
    monkeypatch.setattr(
        registry,
        "_get_optional_enrichers",
        lambda **kwargs: [("pulse", _hook, 20.0)],
    )

    result = registry.extract_file(fpath, rel_path="clip.mp4")
    enrich = result.metadata.get("optional_enrichments", {})
    assert enrich["pulse"]["status"] == "over_budget"
    assert enrich["pulse"]["latency_ms"] >= 80.0


def test_extractor_registry_builtin_jepa_hook_enabled(monkeypatch, tmp_path):
    registry = MediaExtractorRegistry()
    fpath = tmp_path / "clip.mp4"
    fpath.write_bytes(b"\x00\x00\x00\x18ftypmp42")

    def _fake_av(**kwargs):
        from src.scanners.extractor_registry import ExtractionResult

        return ExtractionResult(
            text="scene transcript",
            media_chunks=[{"start_sec": 0.0, "end_sec": 1.1, "text": "character turns"}],
            metadata={"extraction_route": "stt"},
            extractor_id="whisper_stt",
        )

    monkeypatch.setattr(registry, "_extract_av", _fake_av)
    monkeypatch.setenv("VETKA_EXTRACTOR_JEPA_ENABLE", "true")
    monkeypatch.setenv("VETKA_EXTRACTOR_JEPA_TARGET_DIM", "64")

    class _Res:
        provider_mode = "jepa_runtime_module"
        detail = "src.services.jepa_runtime|jepa_http_runtime"
        vectors = [[0.1] * 64, [0.2] * 64]

    def _fake_embed(texts, **kwargs):
        assert texts
        assert kwargs.get("target_dim") == 64
        return _Res()

    monkeypatch.setattr("src.services.mcc_jepa_adapter.embed_texts_for_overlay", _fake_embed)

    result = registry.extract_file(fpath, rel_path="clip.mp4")
    enrich = result.metadata.get("optional_enrichments", {})
    assert "jepa" in enrich
    assert enrich["jepa"]["status"] == "ok"
    assert enrich["jepa"]["payload"]["provider_mode"] == "jepa_runtime_module"
    assert enrich["jepa"]["payload"]["vector_dim"] == 64
    assert enrich["jepa"]["payload"]["vector_count"] == 2


def test_extractor_registry_builtin_jepa_hook_disabled(monkeypatch, tmp_path):
    registry = MediaExtractorRegistry()
    fpath = tmp_path / "clip.mp4"
    fpath.write_bytes(b"\x00\x00\x00\x18ftypmp42")

    def _fake_av(**kwargs):
        from src.scanners.extractor_registry import ExtractionResult

        return ExtractionResult(
            text="transcript",
            media_chunks=[],
            metadata={"extraction_route": "stt"},
            extractor_id="whisper_stt",
        )

    monkeypatch.setattr(registry, "_extract_av", _fake_av)
    monkeypatch.setenv("VETKA_EXTRACTOR_JEPA_ENABLE", "false")
    monkeypatch.setenv("VETKA_EXTRACTOR_PULSE_ENABLE", "false")

    result = registry.extract_file(fpath, rel_path="clip.mp4")
    assert "optional_enrichments" not in (result.metadata or {})


def test_extractor_registry_builtin_pulse_hook_enabled(monkeypatch, tmp_path):
    registry = MediaExtractorRegistry()
    fpath = tmp_path / "track.wav"
    fpath.write_bytes(b"RIFF....WAVEfmt ")

    def _fake_av(**kwargs):
        from src.scanners.extractor_registry import ExtractionResult

        return ExtractionResult(
            text="beat transcript",
            media_chunks=[
                {"start_sec": 0.0, "end_sec": 0.2, "text": "k"},
                {"start_sec": 0.5, "end_sec": 0.7, "text": "s"},
                {"start_sec": 1.0, "end_sec": 1.2, "text": "k"},
                {"start_sec": 1.5, "end_sec": 1.7, "text": "s"},
            ],
            metadata={"extraction_route": "stt"},
            extractor_id="whisper_stt",
        )

    monkeypatch.setattr(registry, "_extract_av", _fake_av)
    monkeypatch.setenv("VETKA_EXTRACTOR_JEPA_ENABLE", "false")
    monkeypatch.setenv("VETKA_EXTRACTOR_PULSE_ENABLE", "true")

    result = registry.extract_file(fpath, rel_path="track.wav")
    enrich = result.metadata.get("optional_enrichments", {})
    assert "pulse" in enrich
    assert enrich["pulse"]["status"] == "ok"
    payload = enrich["pulse"]["payload"]
    assert payload["mode"] == "segment_cadence_v1"
    assert payload["estimated_bpm"] > 0.0
    assert payload["chunks_count"] == 4


def test_extractor_registry_builtin_pulse_hook_degraded_when_segments_missing(monkeypatch, tmp_path):
    registry = MediaExtractorRegistry()
    fpath = tmp_path / "track.wav"
    fpath.write_bytes(b"RIFF....WAVEfmt ")

    def _fake_av(**kwargs):
        from src.scanners.extractor_registry import ExtractionResult

        return ExtractionResult(
            text="short",
            media_chunks=[{"start_sec": 0.0, "end_sec": 0.4, "text": "intro"}],
            metadata={"extraction_route": "stt"},
            extractor_id="whisper_stt",
        )

    monkeypatch.setattr(registry, "_extract_av", _fake_av)
    monkeypatch.setenv("VETKA_EXTRACTOR_JEPA_ENABLE", "false")
    monkeypatch.setenv("VETKA_EXTRACTOR_PULSE_ENABLE", "true")

    result = registry.extract_file(fpath, rel_path="track.wav")
    enrich = result.metadata.get("optional_enrichments", {})
    payload = enrich["pulse"]["payload"]
    assert payload["mode"] == "metadata_proxy_v1"
    assert payload["estimated_bpm"] == 0.0
    assert payload["degraded_reason"] == "insufficient_segments"
