"""
MARKER_158.TEST.WATCHER_MULTIMEDIA_EXTENSIONS

Regression guard: watcher extension gate must include multimedia extensions,
otherwise file system events for media never enter ingest pipeline.
"""

from src.scanners.file_watcher import SUPPORTED_EXTENSIONS


def test_watcher_includes_pdf_and_image_extensions():
    required = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}
    assert required.issubset(SUPPORTED_EXTENSIONS)


def test_watcher_includes_audio_and_video_extensions():
    required = {
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
    assert required.issubset(SUPPORTED_EXTENSIONS)
