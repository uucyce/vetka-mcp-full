"""
Tests for POST /api/cut/script/parse endpoint — CUT-1.2.
Tests the endpoint logic directly (no server needed).
"""
import pytest
from dataclasses import asdict
from src.services.screenplay_timing import parse_screenplay, get_total_duration, get_total_pages


SCREENPLAY = """INT. CAFE - DAY

Anna sits at a corner table.

EXT. STREET - NIGHT

Rain pours down.

INT. APARTMENT - NIGHT

Anna enters.
"""


def test_parse_returns_chunks():
    chunks = parse_screenplay(SCREENPLAY)
    result = {
        "success": True,
        "chunks": [asdict(c) for c in chunks],
        "total_duration_sec": get_total_duration(chunks),
        "page_count": get_total_pages(chunks),
    }
    assert result["success"] is True
    assert len(result["chunks"]) == 3
    assert result["total_duration_sec"] > 0
    assert result["page_count"] > 0


def test_parse_chunk_fields():
    chunks = parse_screenplay(SCREENPLAY)
    data = [asdict(c) for c in chunks]
    first = data[0]
    assert "chunk_id" in first
    assert "scene_heading" in first
    assert "chunk_type" in first
    assert "text" in first
    assert "start_sec" in first
    assert "duration_sec" in first
    assert "line_start" in first
    assert "line_end" in first
    assert "page_count" in first
    assert first["chunk_id"] == "SCN_01"
    assert first["scene_heading"] == "INT. CAFE - DAY"


def test_parse_empty_text():
    chunks = parse_screenplay("")
    result = {
        "success": True,
        "chunks": [asdict(c) for c in chunks],
        "total_duration_sec": get_total_duration(chunks),
        "page_count": get_total_pages(chunks),
    }
    assert result["chunks"] == []
    assert result["total_duration_sec"] == 0.0
    assert result["page_count"] == 0.0
