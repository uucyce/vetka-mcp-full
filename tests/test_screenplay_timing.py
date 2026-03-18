"""
Tests for screenplay_timing.py — CUT-1.1 Script Spine foundation.
"""
import pytest
from src.services.screenplay_timing import (
    parse_screenplay,
    get_total_duration,
    get_total_pages,
    SceneChunk,
    LINES_PER_PAGE,
    SECONDS_PER_PAGE,
)


# ─── Screenplay with scene headings ───

SCREENPLAY_TEXT = """INT. CAFE - DAY

Anna sits at a corner table, stirring her coffee.
She watches the rain through the window.
The waiter approaches.

WAITER
Can I get you anything else?

ANNA
No, thank you.

EXT. STREET - NIGHT

Rain pours down. Anna walks quickly,
her coat pulled tight against the cold.
She stops at a crosswalk, looking both ways.

INT. ANNA'S APARTMENT - NIGHT

Anna enters, drops her keys on the table.
She sits on the couch, staring at the ceiling.
"""


def test_screenplay_splits_by_headings():
    chunks = parse_screenplay(SCREENPLAY_TEXT)
    assert len(chunks) == 3
    assert chunks[0].scene_heading == "INT. CAFE - DAY"
    assert chunks[1].scene_heading == "EXT. STREET - NIGHT"
    assert chunks[2].scene_heading == "INT. ANNA'S APARTMENT - NIGHT"


def test_screenplay_chunk_type_is_scene():
    chunks = parse_screenplay(SCREENPLAY_TEXT)
    for c in chunks:
        assert c.chunk_type == "scene"


def test_screenplay_chunk_ids_sequential():
    chunks = parse_screenplay(SCREENPLAY_TEXT)
    assert chunks[0].chunk_id == "SCN_01"
    assert chunks[1].chunk_id == "SCN_02"
    assert chunks[2].chunk_id == "SCN_03"


def test_screenplay_timing_cumulative():
    chunks = parse_screenplay(SCREENPLAY_TEXT)
    # Each chunk starts where the previous ended
    assert chunks[0].start_sec == 0.0
    assert chunks[1].start_sec == pytest.approx(chunks[0].duration_sec, abs=0.01)
    assert chunks[2].start_sec == pytest.approx(
        chunks[0].duration_sec + chunks[1].duration_sec, abs=0.01
    )


def test_screenplay_line_numbers():
    chunks = parse_screenplay(SCREENPLAY_TEXT)
    # First chunk starts at line 0 (or 1 depending on leading newline)
    assert chunks[0].line_start >= 0
    # Each subsequent chunk starts after previous ends
    for i in range(1, len(chunks)):
        assert chunks[i].line_start > chunks[i - 1].line_end


# ─── Documentary / no headings — paragraph fallback ───

DOCUMENTARY_TEXT = """The camera pans across the vast desert.
Sand dunes stretch to the horizon.
A single figure walks in the distance.

The figure stops, kneels down.
He picks up a handful of sand, lets it fall.
The wind carries it away.

Back in the city, traffic flows endlessly.
People rush past without looking up.
The sky is grey, heavy with smog."""


def test_documentary_splits_by_paragraphs():
    chunks = parse_screenplay(DOCUMENTARY_TEXT)
    assert len(chunks) == 3
    for c in chunks:
        assert c.chunk_type == "paragraph"
        assert c.scene_heading is None


def test_documentary_chunk_ids():
    chunks = parse_screenplay(DOCUMENTARY_TEXT)
    assert chunks[0].chunk_id == "SCN_01"
    assert chunks[1].chunk_id == "SCN_02"
    assert chunks[2].chunk_id == "SCN_03"


# ─── Empty input ───

def test_empty_text():
    assert parse_screenplay("") == []
    assert parse_screenplay("   ") == []
    assert parse_screenplay("\n\n\n") == []


# ─── Timing: 55 lines = 1 page = 60 sec ───

def test_timing_55_lines_equals_60_sec():
    # 55 non-empty lines = exactly 1 page
    text = "\n".join(f"Line {i}" for i in range(LINES_PER_PAGE))
    chunks = parse_screenplay(text)
    assert len(chunks) == 1
    assert chunks[0].page_count == pytest.approx(1.0, abs=0.1)
    assert chunks[0].duration_sec == pytest.approx(SECONDS_PER_PAGE, abs=5.0)


# ─── Russian headings ───

RUSSIAN_SCREENPLAY = """ИНТ. КАФЕ - ДЕНЬ

Анна сидит за столиком в углу.
Она смотрит на дождь за окном.

НАТ. УЛИЦА - НОЧЬ

Дождь льёт. Анна идёт быстро.
"""


def test_russian_headings():
    chunks = parse_screenplay(RUSSIAN_SCREENPLAY)
    assert len(chunks) == 2
    assert chunks[0].scene_heading == "ИНТ. КАФЕ - ДЕНЬ"
    assert chunks[1].scene_heading == "НАТ. УЛИЦА - НОЧЬ"


# ─── Helper functions ───

def test_total_duration():
    chunks = parse_screenplay(SCREENPLAY_TEXT)
    total = get_total_duration(chunks)
    assert total > 0
    last = chunks[-1]
    assert total == pytest.approx(last.start_sec + last.duration_sec, abs=0.01)


def test_total_pages():
    chunks = parse_screenplay(SCREENPLAY_TEXT)
    total = get_total_pages(chunks)
    assert total > 0
    assert total == pytest.approx(sum(c.page_count for c in chunks), abs=0.01)


def test_total_duration_empty():
    assert get_total_duration([]) == 0.0
    assert get_total_pages([]) == 0.0
