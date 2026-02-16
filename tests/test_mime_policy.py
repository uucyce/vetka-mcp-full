from src.scanners.mime_policy import validate_ingest_target


def test_validate_ingest_target_allows_known_small_file():
    ok, info = validate_ingest_target("notes.md", 1024, "text/markdown")
    assert ok is True
    assert info["code"] == "OK"
    assert info["category"] == "document"


def test_validate_ingest_target_blocks_denied_extension():
    ok, info = validate_ingest_target("payload.exe", 2048, "application/x-msdownload")
    assert ok is False
    assert info["code"] == "DENY_EXTENSION"


def test_validate_ingest_target_blocks_unknown_extension():
    ok, info = validate_ingest_target("mystery.zzz", 100)
    assert ok is False
    assert info["code"] == "UNKNOWN_EXTENSION"


def test_validate_ingest_target_blocks_oversize_video():
    # 300MB limit + 1 byte
    ok, info = validate_ingest_target("clip.mp4", (300 * 1024 * 1024) + 1, "video/mp4")
    assert ok is False
    assert info["code"] == "FILE_TOO_LARGE"
