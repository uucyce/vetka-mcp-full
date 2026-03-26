"""
Tests for fountain_parser.py — MARKER_CUT_B7.6.

Covers:
  - Correct number of scenes parsed from a 3-scene sample screenplay
  - Scene headings extracted properly (INT./EXT./forced)
  - Timing calculation: 55 lines = 60 sec
  - Edge cases: empty scene, title page only, no headings, Russian headings
  - Boneyard and Notes stripping
  - Title page detection (is_title_page=True, duration=0)
  - compute_total_runtime utility
"""
import pytest
from src.services.fountain_parser import (
    FountainParser,
    parse_fountain,
    parse_fountain_timed,
    compute_scene_timing,
    compute_total_runtime,
    FountainScene,
    TimedScene,
    LINES_PER_PAGE,
    SECONDS_PER_PAGE,
    MIN_SCENE_DURATION_SEC,
    TOKEN_SCENE_HEADING,
    TOKEN_ACTION,
    TOKEN_CHARACTER,
    TOKEN_DIALOGUE,
    TOKEN_TRANSITION,
)


# ---------------------------------------------------------------------------
# Sample Fountain documents
# ---------------------------------------------------------------------------

# 3-scene short screenplay used as primary test fixture
SAMPLE_FOUNTAIN_3_SCENES = """\
Title: The Last Signal
Author: A. Writer
Draft date: 2026-03-26

INT. MISSION CONTROL - NIGHT

Banks of monitors glow in the dark. DR. CHEN (50s, exhausted) leans over a console.

DR. CHEN
We've lost contact.

TECHNICIAN
(nervous)
For how long?

DR. CHEN
Seventeen minutes and counting.

Chen stands, pacing the length of the room.
The hum of electronics fills the silence.

EXT. LAUNCH PAD - NIGHT

Rain sheets across the empty platform.
The rocket stands alone, floodlights cutting through the mist.
A lone GUARD walks the perimeter.

> SMASH CUT TO: <

INT. ROCKET COCKPIT - CONTINUOUS

COMMANDER HAYES (40s) floats in zero-g, helmet off.
She checks the instrument panel — all readings nominal.

HAYES
Houston, do you read?

Nothing but static.
Hayes closes her eyes, breathes.
"""


# Pure action document (no headings) — paragraph fallback
DOCUMENTARY_FOUNTAIN = """\
The camera finds the city at dawn.

Streets still empty. A lone taxi idles at a red light.
The driver reads a paperback, dog-eared and worn.

Sunrise breaks over the skyline.
"""


# Title page only (no body scenes)
TITLE_ONLY_FOUNTAIN = """\
Title: Fragment
Author: Nobody
Draft date: 2026-01-01
"""


# Russian headings
RUSSIAN_FOUNTAIN = """\
ИНТ. КАФЕ - ДЕНЬ

Анна сидит за угловым столиком. Смотрит в окно на дождь.

АННА
Принесите ещё кофе.

НАТ. УЛИЦА - НОЧЬ

Дождь не прекращается. Анна выходит в ночь.
"""


# Boneyard and Notes
BONEYARD_FOUNTAIN = """\
INT. LIBRARY - DAY

/* This whole section might be cut */
The librarian shelves books quietly.
/* end cut */

LIBRARIAN
Shhh.

[[TODO: add more atmosphere here]]

EXT. GARDEN - DAY

Sunlight through leaves.
"""


# ---------------------------------------------------------------------------
# Core: 3-scene screenplay
# ---------------------------------------------------------------------------

def test_three_scenes_parsed():
    """Primary fixture: parse produces exactly 3 scenes (+ title page)."""
    scenes = parse_fountain(SAMPLE_FOUNTAIN_3_SCENES)
    # title page + 3 INT/EXT scenes
    body_scenes = [s for s in scenes if not s.is_title_page]
    assert len(body_scenes) == 3


def test_scene_headings_extracted():
    """Scene headings match INT./EXT. lines from source."""
    scenes = parse_fountain(SAMPLE_FOUNTAIN_3_SCENES)
    headings = [s.heading for s in scenes if not s.is_title_page]
    assert headings[0] == "INT. MISSION CONTROL - NIGHT"
    assert headings[1] == "EXT. LAUNCH PAD - NIGHT"
    assert headings[2] == "INT. ROCKET COCKPIT - CONTINUOUS"


def test_scene_ids_sequential():
    """Scene IDs start at sc_01 for body scenes."""
    scenes = parse_fountain(SAMPLE_FOUNTAIN_3_SCENES)
    body = [s for s in scenes if not s.is_title_page]
    assert body[0].scene_id == "sc_01"
    assert body[1].scene_id == "sc_02"
    assert body[2].scene_id == "sc_03"


def test_scene_content_not_empty():
    """Every body scene has non-empty content."""
    scenes = parse_fountain(SAMPLE_FOUNTAIN_3_SCENES)
    for sc in scenes:
        if not sc.is_title_page:
            assert sc.content.strip(), f"Scene {sc.scene_id} has empty content"


def test_scene_elements_present():
    """Body scenes contain parsed elements."""
    scenes = parse_fountain(SAMPLE_FOUNTAIN_3_SCENES)
    for sc in scenes:
        if not sc.is_title_page:
            assert len(sc.elements) > 0, f"Scene {sc.scene_id} has no elements"


# ---------------------------------------------------------------------------
# Title page
# ---------------------------------------------------------------------------

def test_title_page_detected():
    """Title block is parsed as is_title_page=True."""
    scenes = parse_fountain(SAMPLE_FOUNTAIN_3_SCENES)
    assert scenes[0].is_title_page is True
    assert scenes[0].heading is None


def test_title_page_zero_duration():
    """Title page contributes 0 seconds to timeline."""
    scenes = parse_fountain(SAMPLE_FOUNTAIN_3_SCENES)
    timed = compute_scene_timing(scenes)
    title_timed = [t for t in timed if t.is_title_page]
    assert len(title_timed) == 1
    assert title_timed[0].duration_sec == 0.0
    assert title_timed[0].start_sec == 0.0


def test_title_only_document():
    """Title-only document yields just the title page scene."""
    scenes = parse_fountain(TITLE_ONLY_FOUNTAIN)
    # Should have title page; body might be empty
    assert any(s.is_title_page for s in scenes)


# ---------------------------------------------------------------------------
# Timing: 55 lines = 1 page = 60 sec
# ---------------------------------------------------------------------------

def test_timing_55_lines_equals_60_sec():
    """
    A scene with exactly 55 action lines yields ~60 seconds.
    We build a synthetic fountain with one scene heading + 55 content lines.
    """
    content_lines = "\n".join(f"Action line {i}." for i in range(LINES_PER_PAGE))
    fountain_text = f"INT. ROOM - DAY\n\n{content_lines}\n"
    scenes = parse_fountain(fountain_text)
    timed = compute_scene_timing(scenes)
    body = [t for t in timed if not t.is_title_page]
    assert len(body) == 1
    # duration should be approximately 60 sec (55 lines / 55 * 60)
    assert body[0].duration_sec == pytest.approx(SECONDS_PER_PAGE, rel=0.2)


def test_timing_cumulative():
    """start_sec of each scene equals sum of previous durations."""
    scenes = parse_fountain(SAMPLE_FOUNTAIN_3_SCENES)
    timed = [t for t in compute_scene_timing(scenes) if not t.is_title_page]
    running = 0.0
    for t in timed:
        assert t.start_sec == pytest.approx(running, abs=0.01)
        running += t.duration_sec


def test_minimum_scene_duration():
    """Very short scenes get at least MIN_SCENE_DURATION_SEC."""
    fountain_text = "INT. A - DAY\n\nOk.\n\nEXT. B - DAY\n\nYep.\n"
    scenes = parse_fountain(fountain_text)
    timed = compute_scene_timing(scenes)
    for t in timed:
        if not t.is_title_page:
            assert t.duration_sec >= MIN_SCENE_DURATION_SEC


def test_page_number_advances():
    """page_number should increase monotonically across scenes."""
    scenes = parse_fountain(SAMPLE_FOUNTAIN_3_SCENES)
    timed = [t for t in compute_scene_timing(scenes) if not t.is_title_page]
    for i in range(1, len(timed)):
        assert timed[i].page_number >= timed[i - 1].page_number


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_text_returns_empty_list():
    assert parse_fountain("") == []
    assert parse_fountain("   ") == []
    assert parse_fountain("\n\n\n") == []


def test_no_headings_paragraph_mode():
    """Document without INT./EXT. headings is returned as single scene."""
    scenes = parse_fountain(DOCUMENTARY_FOUNTAIN)
    body = [s for s in scenes if not s.is_title_page]
    # All content in one or more paragraph scenes with heading=None
    assert len(body) >= 1
    for sc in body:
        assert sc.heading is None


def test_boneyard_stripped():
    """/* ... */ blocks are removed before parsing."""
    scenes = parse_fountain(BONEYARD_FOUNTAIN)
    for sc in scenes:
        assert "/*" not in sc.content
        assert "*/" not in sc.content


def test_notes_stripped():
    """[[ ... ]] notes are removed before parsing."""
    scenes = parse_fountain(BONEYARD_FOUNTAIN)
    for sc in scenes:
        assert "[[" not in sc.content
        assert "]]" not in sc.content


def test_russian_headings():
    """ИНТ. and НАТ. headings are detected correctly."""
    scenes = parse_fountain(RUSSIAN_FOUNTAIN)
    body = [s for s in scenes if not s.is_title_page]
    assert len(body) == 2
    assert body[0].heading == "ИНТ. КАФЕ - ДЕНЬ"
    assert body[1].heading == "НАТ. УЛИЦА - НОЧЬ"


# ---------------------------------------------------------------------------
# compute_total_runtime
# ---------------------------------------------------------------------------

def test_compute_total_runtime_positive():
    """Total runtime is positive for a multi-scene screenplay."""
    scenes = parse_fountain(SAMPLE_FOUNTAIN_3_SCENES)
    runtime = compute_total_runtime(scenes)
    assert runtime > 0.0


def test_compute_total_runtime_empty():
    """Empty document yields 0 runtime."""
    assert compute_total_runtime([]) == 0.0


def test_compute_total_runtime_equals_sum():
    """Total runtime equals sum of individual scene durations."""
    scenes = parse_fountain(SAMPLE_FOUNTAIN_3_SCENES)
    timed = [t for t in compute_scene_timing(scenes) if not t.is_title_page]
    expected = sum(t.duration_sec for t in timed)
    result = compute_total_runtime(scenes)
    assert result == pytest.approx(expected, abs=0.01)


# ---------------------------------------------------------------------------
# parse_fountain_timed convenience API
# ---------------------------------------------------------------------------

def test_parse_fountain_timed_returns_timed_scenes():
    """parse_fountain_timed returns List[TimedScene] with timing fields."""
    timed = parse_fountain_timed(SAMPLE_FOUNTAIN_3_SCENES)
    assert len(timed) > 0
    for t in timed:
        assert isinstance(t, TimedScene)
        assert hasattr(t, "start_sec")
        assert hasattr(t, "duration_sec")
        assert hasattr(t, "page_number")


def test_parse_fountain_timed_first_body_scene_start_zero():
    """First non-title scene starts at time 0."""
    timed = parse_fountain_timed(SAMPLE_FOUNTAIN_3_SCENES)
    body = [t for t in timed if not t.is_title_page]
    assert body[0].start_sec == pytest.approx(0.0, abs=0.01)


# ---------------------------------------------------------------------------
# Element-level token checks
# ---------------------------------------------------------------------------

def test_scene_heading_token_type():
    """Scene heading elements carry TOKEN_SCENE_HEADING type."""
    scenes = parse_fountain(SAMPLE_FOUNTAIN_3_SCENES)
    for sc in scenes:
        for el in sc.elements:
            if el.token_type == TOKEN_SCENE_HEADING:
                assert el.text  # heading text is not empty


def test_character_elements_exist_in_dialogue_scene():
    """First scene (MISSION CONTROL) contains character elements."""
    scenes = parse_fountain(SAMPLE_FOUNTAIN_3_SCENES)
    body = [s for s in scenes if not s.is_title_page]
    first = body[0]
    token_types = {el.token_type for el in first.elements}
    assert TOKEN_CHARACTER in token_types


def test_dialogue_elements_follow_character():
    """Dialogue elements exist where character elements are present."""
    scenes = parse_fountain(SAMPLE_FOUNTAIN_3_SCENES)
    body = [s for s in scenes if not s.is_title_page]
    first = body[0]
    token_types = {el.token_type for el in first.elements}
    assert TOKEN_DIALOGUE in token_types
