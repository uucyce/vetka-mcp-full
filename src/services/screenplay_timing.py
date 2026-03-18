"""
MARKER_CUT_1.1: screenplay_timing.py — Screenplay-aware chunker + page-timer.

Foundation of CUT Script Spine. Converts plain text (screenplay or any text)
into structured SceneChunk objects with chronological timing.

Algorithm:
  1. Detect scene headings via regex (INT./EXT./ИНТ./НАТ./SCENE/СЦЕНА)
  2. If headings found → split by them (hard scene boundaries)
  3. If no headings → fallback: split by blank lines (paragraphs)
  4. For each chunk: 55 lines = 1 page OR ~1800 chars = 1 page (whichever first)
  5. 1 page = 60 seconds (Courier 12pt standard)

Ref: docs/190_ph_CUT_WORKFLOW_ARCH/ROADMAP_CUT_FULL.md §Phase 1
     docs/190_ph_CUT_WORKFLOW_ARCH/CUT_TARGET_ARCHITECTURE.md §1
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

# ─── Constants ───

LINES_PER_PAGE = 55
CHARS_PER_PAGE = 1800
SECONDS_PER_PAGE = 60.0

# Scene heading regex (matches INT./EXT. and Russian equivalents)
SCENE_HEADING_RE = re.compile(
    r"^(INT\.|EXT\.|INT/EXT\.|ИНТ\.|НАТ\.|ИНТ/НАТ\.|SCENE|СЦЕНА|#{1,3}\s|\d+\.\s)",
    re.IGNORECASE,
)


# ─── Data model ───

@dataclass
class SceneChunk:
    """A chunk of script text with chronological timing."""
    chunk_id: str           # "SCN_01", "SCN_02", ...
    scene_heading: str | None  # "INT. CAFE - DAY" or None
    chunk_type: str         # "scene" | "paragraph"
    text: str
    start_sec: float
    duration_sec: float
    line_start: int         # first line in source text (0-based)
    line_end: int           # last line in source text (0-based)
    page_count: float       # how many pages this chunk spans


# ─── Timing ───

def _estimate_pages(text: str) -> float:
    """Estimate page count from text. Whichever metric yields more pages wins."""
    lines = text.split("\n")
    by_lines = len(lines) / LINES_PER_PAGE
    by_chars = len(text) / CHARS_PER_PAGE
    return max(by_lines, by_chars, 0.01)  # min 0.01 to avoid zero-duration chunks


# ─── Splitting ───

def _split_by_headings(lines: list[str]) -> list[tuple[str | None, int, int, str]]:
    """Split lines by scene headings. Returns [(heading, start, end, text), ...]."""
    segments: list[tuple[str | None, int, int, str]] = []
    current_lines: list[str] = []
    current_heading: str | None = None
    start_line = 0

    for i, line in enumerate(lines):
        if SCENE_HEADING_RE.match(line.strip()) and current_lines:
            # Flush previous segment
            segments.append((
                current_heading,
                start_line,
                i - 1,
                "\n".join(current_lines),
            ))
            current_lines = [line]
            current_heading = line.strip()
            start_line = i
        else:
            if not current_lines and line.strip():
                current_heading = line.strip() if SCENE_HEADING_RE.match(line.strip()) else None
            current_lines.append(line)

    # Flush last segment
    if current_lines:
        segments.append((
            current_heading,
            start_line,
            len(lines) - 1,
            "\n".join(current_lines),
        ))

    return segments


def _split_by_paragraphs(lines: list[str]) -> list[tuple[str | None, int, int, str]]:
    """Split lines by blank lines (paragraph breaks). Returns [(None, start, end, text), ...]."""
    segments: list[tuple[str | None, int, int, str]] = []
    current_lines: list[str] = []
    start_line = 0

    for i, line in enumerate(lines):
        if not line.strip():
            if current_lines:
                segments.append((
                    None,
                    start_line,
                    i - 1,
                    "\n".join(current_lines),
                ))
                current_lines = []
            start_line = i + 1
        else:
            if not current_lines:
                start_line = i
            current_lines.append(line)

    # Flush last segment
    if current_lines:
        segments.append((
            None,
            start_line,
            len(lines) - 1,
            "\n".join(current_lines),
        ))

    return segments


# ─── Main API ───

def parse_screenplay(text: str) -> list[SceneChunk]:
    """
    Parse screenplay text into SceneChunk objects with chronological timing.

    If scene headings (INT./EXT./ИНТ./НАТ.) are found, splits by them.
    Otherwise falls back to paragraph splitting.

    Returns list of SceneChunk with cumulative timing (1 page = 60 sec).
    """
    if not text or not text.strip():
        return []

    lines = text.split("\n")

    # Detect if text has scene headings
    has_headings = any(SCENE_HEADING_RE.match(line.strip()) for line in lines if line.strip())

    if has_headings:
        segments = _split_by_headings(lines)
        chunk_type = "scene"
    else:
        segments = _split_by_paragraphs(lines)
        chunk_type = "paragraph"

    # Build SceneChunks with cumulative timing
    chunks: list[SceneChunk] = []
    cumulative_sec = 0.0

    for idx, (heading, start, end, segment_text) in enumerate(segments):
        if not segment_text.strip():
            continue

        page_count = _estimate_pages(segment_text)
        duration_sec = page_count * SECONDS_PER_PAGE

        chunks.append(SceneChunk(
            chunk_id=f"SCN_{idx + 1:02d}",
            scene_heading=heading,
            chunk_type=chunk_type,
            text=segment_text,
            start_sec=cumulative_sec,
            duration_sec=duration_sec,
            line_start=start,
            line_end=end,
            page_count=page_count,
        ))

        cumulative_sec += duration_sec

    return chunks


def get_total_duration(chunks: list[SceneChunk]) -> float:
    """Total estimated duration in seconds."""
    if not chunks:
        return 0.0
    last = chunks[-1]
    return last.start_sec + last.duration_sec


def get_total_pages(chunks: list[SceneChunk]) -> float:
    """Total estimated page count."""
    return sum(c.page_count for c in chunks)
