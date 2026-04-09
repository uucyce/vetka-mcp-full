"""
Unified MIME/extension policy for ingest routes.

MARKER_153.IMPL.G01_MIME_POLICY
"""

from pathlib import Path
from typing import Dict, Optional, Tuple
import mimetypes

# Explicitly denied executable/binary package formats for ingest safety.
DENY_EXTENSIONS = {
    ".exe", ".dll", ".so", ".dylib", ".msi", ".pkg", ".bat", ".cmd", ".app", ".apk", ".ipa",
}

# Extension to ingest category.
EXTENSION_CATEGORIES: Dict[str, str] = {
    # text/code/docs/data
    ".py": "code", ".js": "code", ".ts": "code", ".tsx": "code", ".jsx": "code",
    ".go": "code", ".rs": "code", ".java": "code", ".cpp": "code", ".c": "code",
    ".md": "document", ".txt": "document", ".rst": "document", ".adoc": "document",
    ".json": "data", ".yaml": "data", ".yml": "data", ".toml": "data", ".csv": "data",
    ".html": "document", ".css": "document", ".xml": "data",
    # image/pdf
    ".pdf": "pdf", ".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image",
    ".bmp": "image", ".webp": "image", ".tiff": "image", ".svg": "image",
    # audio/video
    ".mp3": "audio", ".wav": "audio", ".m4a": "audio", ".aac": "audio", ".flac": "audio", ".ogg": "audio",
    ".mp4": "video", ".mov": "video", ".mkv": "video", ".avi": "video", ".webm": "video",
}

# Size limits by category (bytes).
MAX_SIZE_BY_CATEGORY: Dict[str, int] = {
    "code": 10 * 1024 * 1024,
    "document": 10 * 1024 * 1024,
    "data": 10 * 1024 * 1024,
    "pdf": 20 * 1024 * 1024,
    "image": 20 * 1024 * 1024,
    "audio": 100 * 1024 * 1024,
    "video": 300 * 1024 * 1024,
    "unknown": 1 * 1024 * 1024,
}


def classify_extension(path_or_name: str) -> Tuple[str, str]:
    ext = Path(path_or_name).suffix.lower()
    category = EXTENSION_CATEGORIES.get(ext, "unknown")
    return ext, category


def normalize_mime(path_or_name: str, fallback: str = "application/octet-stream") -> str:
    mime_type, _ = mimetypes.guess_type(path_or_name)
    return mime_type or fallback


def validate_ingest_target(path_or_name: str, size_bytes: int, mime_type: Optional[str] = None) -> Tuple[bool, Dict[str, str]]:
    ext, category = classify_extension(path_or_name)
    mime = mime_type or normalize_mime(path_or_name)

    if ext in DENY_EXTENSIONS:
        return False, {
            "code": "DENY_EXTENSION",
            "message": f"Blocked extension: {ext}",
            "extension": ext,
            "category": category,
            "mime_type": mime,
        }

    if category == "unknown":
        return False, {
            "code": "UNKNOWN_EXTENSION",
            "message": f"Unknown extension: {ext or '(none)'}",
            "extension": ext or "",
            "category": category,
            "mime_type": mime,
        }

    max_size = MAX_SIZE_BY_CATEGORY.get(category, MAX_SIZE_BY_CATEGORY["unknown"])
    if size_bytes > max_size:
        return False, {
            "code": "FILE_TOO_LARGE",
            "message": f"File exceeds limit for {category}: {size_bytes}>{max_size}",
            "extension": ext,
            "category": category,
            "mime_type": mime,
        }

    return True, {
        "code": "OK",
        "message": "allowed",
        "extension": ext,
        "category": category,
        "mime_type": mime,
    }

