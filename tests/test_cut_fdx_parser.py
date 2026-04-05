"""
MARKER_FDX_PARSER — Tests for Final Draft .fdx screenplay parser.

Tests cover:
  - XML parsing and element classification
  - Scene grouping and heading detection
  - SceneChunk output with timing
  - Metadata extraction (title, author)
  - Edge cases (empty, no headings, malformed)
  - Plain text conversion
  - File I/O

@task: tb_1774436431_1
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from src.services.cut_fdx_parser import (
    FDXElement,
    FDXMetadata,
    FDXScene,
    _classify_paragraph,
    _extract_text,
    fdx_to_plain_text,
    parse_fdx,
    parse_fdx_elements,
    parse_fdx_file,
    parse_fdx_scenes,
)
from src.services.screenplay_timing import SECONDS_PER_PAGE, SceneChunk


# ---------------------------------------------------------------------------
# Test FDX fixtures
# ---------------------------------------------------------------------------

MINIMAL_FDX = """<?xml version="1.0" encoding="UTF-8"?>
<FinalDraft DocumentType="Script" Template="No" Version="4">
  <Content>
    <Paragraph Type="Scene Heading"><Text>INT. CAFE - DAY</Text></Paragraph>
    <Paragraph Type="Action"><Text>A busy cafe in downtown Moscow.</Text></Paragraph>
    <Paragraph Type="Character"><Text>JOHN</Text></Paragraph>
    <Paragraph Type="Dialogue"><Text>Hello there.</Text></Paragraph>
  </Content>
</FinalDraft>"""

TWO_SCENES_FDX = """<?xml version="1.0" encoding="UTF-8"?>
<FinalDraft DocumentType="Script" Template="No" Version="4">
  <Content>
    <Paragraph Type="Scene Heading"><Text>INT. CAFE - DAY</Text></Paragraph>
    <Paragraph Type="Action"><Text>A busy cafe in downtown Moscow.</Text></Paragraph>
    <Paragraph Type="Character"><Text>JOHN</Text></Paragraph>
    <Paragraph Type="Dialogue"><Text>Hello there.</Text></Paragraph>
    <Paragraph Type="Scene Heading"><Text>EXT. STREET - NIGHT</Text></Paragraph>
    <Paragraph Type="Action"><Text>Rain pours down on empty streets.</Text></Paragraph>
    <Paragraph Type="Transition"><Text>CUT TO:</Text></Paragraph>
  </Content>
</FinalDraft>"""

RICH_FDX = """<?xml version="1.0" encoding="UTF-8"?>
<FinalDraft DocumentType="Script" Template="No" Version="4">
  <Content>
    <Paragraph Type="Scene Heading"><Text>INT. OFFICE - DAY</Text></Paragraph>
    <Paragraph Type="Action"><Text>The office is quiet. Papers scattered on desks.</Text></Paragraph>
    <Paragraph Type="Character"><Text>SARAH</Text></Paragraph>
    <Paragraph Type="Parenthetical"><Text>whispering</Text></Paragraph>
    <Paragraph Type="Dialogue"><Text>Did you hear about the merger?</Text></Paragraph>
    <Paragraph Type="Character" DualDialogue="Start"><Text>MIKE</Text></Paragraph>
    <Paragraph Type="Dialogue"><Text>Everyone has.</Text></Paragraph>
    <Paragraph Type="Transition"><Text>DISSOLVE TO:</Text></Paragraph>
    <Paragraph Type="Scene Heading"><Text>EXT. PARKING LOT - NIGHT</Text></Paragraph>
    <Paragraph Type="Action"><Text>Sarah walks to her car alone.</Text></Paragraph>
    <Paragraph Type="Shot"><Text>CLOSE UP on Sarah's face</Text></Paragraph>
  </Content>
</FinalDraft>"""

METADATA_FDX = """<?xml version="1.0" encoding="UTF-8"?>
<FinalDraft DocumentType="Script" Template="No" Version="4">
  <TitlePage>
    <Content>
      <Paragraph Type="Title Page"><Text>MY GREAT SCREENPLAY</Text></Paragraph>
      <Paragraph Type="Title Page"><Text>Written by</Text></Paragraph>
      <Paragraph Type="Title Page"><Text>Jane Author</Text></Paragraph>
    </Content>
  </TitlePage>
  <Content>
    <Paragraph Type="Scene Heading"><Text>INT. ROOM - DAY</Text></Paragraph>
    <Paragraph Type="Action"><Text>Empty room.</Text></Paragraph>
  </Content>
</FinalDraft>"""

NO_HEADINGS_FDX = """<?xml version="1.0" encoding="UTF-8"?>
<FinalDraft DocumentType="Script" Template="No" Version="4">
  <Content>
    <Paragraph Type="Action"><Text>First paragraph of action.</Text></Paragraph>
    <Paragraph Type="Character"><Text>VOICE</Text></Paragraph>
    <Paragraph Type="Dialogue"><Text>Hello from nowhere.</Text></Paragraph>
  </Content>
</FinalDraft>"""

EMPTY_CONTENT_FDX = """<?xml version="1.0" encoding="UTF-8"?>
<FinalDraft DocumentType="Script" Template="No" Version="4">
  <Content>
  </Content>
</FinalDraft>"""

SPLIT_TEXT_FDX = """<?xml version="1.0" encoding="UTF-8"?>
<FinalDraft DocumentType="Script" Template="No" Version="4">
  <Content>
    <Paragraph Type="Scene Heading"><Text>INT. LAB - </Text><Text Style="Bold">NIGHT</Text></Paragraph>
    <Paragraph Type="Action"><Text>Machines </Text><Text Style="Italic">hum</Text><Text> softly.</Text></Paragraph>
  </Content>
</FinalDraft>"""


# ---------------------------------------------------------------------------
# Element classification tests
# ---------------------------------------------------------------------------


class TestClassifyParagraph:
    def test_scene_heading(self):
        assert _classify_paragraph("Scene Heading") == "scene_heading"

    def test_scene_heading_case_insensitive(self):
        assert _classify_paragraph("SCENE HEADING") == "scene_heading"

    def test_slug_line(self):
        assert _classify_paragraph("Slug Line") == "scene_heading"

    def test_action(self):
        assert _classify_paragraph("Action") == "action"

    def test_general(self):
        assert _classify_paragraph("General") == "action"

    def test_character(self):
        assert _classify_paragraph("Character") == "character"

    def test_dialogue(self):
        assert _classify_paragraph("Dialogue") == "dialogue"

    def test_dialog_variant(self):
        assert _classify_paragraph("Dialog") == "dialogue"

    def test_parenthetical(self):
        assert _classify_paragraph("Parenthetical") == "parenthetical"

    def test_transition(self):
        assert _classify_paragraph("Transition") == "transition"

    def test_shot(self):
        assert _classify_paragraph("Shot") == "shot"

    def test_unknown_defaults_to_action(self):
        assert _classify_paragraph("SomeWeirdType") == "action"


# ---------------------------------------------------------------------------
# Text extraction tests
# ---------------------------------------------------------------------------


class TestExtractText:
    def test_simple_text(self):
        para = ET.fromstring('<Paragraph Type="Action"><Text>Hello world</Text></Paragraph>')
        assert _extract_text(para) == "Hello world"

    def test_multi_text_elements(self):
        para = ET.fromstring(
            '<Paragraph Type="Action">'
            '<Text>Hello </Text><Text>world</Text>'
            '</Paragraph>'
        )
        assert _extract_text(para) == "Hello world"

    def test_styled_text(self):
        para = ET.fromstring(
            '<Paragraph Type="Action">'
            '<Text>Normal </Text><Text Style="Bold">bold</Text><Text> end</Text>'
            '</Paragraph>'
        )
        assert _extract_text(para) == "Normal bold end"

    def test_empty_paragraph(self):
        para = ET.fromstring('<Paragraph Type="Action"></Paragraph>')
        assert _extract_text(para) == ""


# ---------------------------------------------------------------------------
# Element parsing tests
# ---------------------------------------------------------------------------


class TestParseElements:
    def test_minimal_fdx(self):
        elements, meta = parse_fdx_elements(MINIMAL_FDX)
        assert len(elements) == 4
        assert elements[0].element_type == "scene_heading"
        assert elements[0].text == "INT. CAFE - DAY"
        assert elements[1].element_type == "action"
        assert elements[2].element_type == "character"
        assert elements[3].element_type == "dialogue"

    def test_not_final_draft(self):
        with pytest.raises(ValueError, match="Not a Final Draft"):
            parse_fdx_elements("<SomeOtherFormat/>")

    def test_malformed_xml(self):
        with pytest.raises(ET.ParseError):
            parse_fdx_elements("not xml at all <<<>>>")

    def test_empty_content(self):
        elements, meta = parse_fdx_elements(EMPTY_CONTENT_FDX)
        assert len(elements) == 0

    def test_dual_dialogue_flag(self):
        elements, _ = parse_fdx_elements(RICH_FDX)
        dual = [e for e in elements if e.dual_dialogue]
        assert len(dual) == 1
        assert dual[0].text == "MIKE"

    def test_split_text_concatenated(self):
        elements, _ = parse_fdx_elements(SPLIT_TEXT_FDX)
        assert elements[0].text == "INT. LAB - NIGHT"
        assert elements[1].text == "Machines hum softly."


# ---------------------------------------------------------------------------
# Metadata tests
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_title_extraction(self):
        _, meta = parse_fdx_elements(METADATA_FDX)
        assert meta.title == "MY GREAT SCREENPLAY"

    def test_author_extraction(self):
        _, meta = parse_fdx_elements(METADATA_FDX)
        assert meta.author == "Jane Author"

    def test_no_metadata(self):
        _, meta = parse_fdx_elements(MINIMAL_FDX)
        assert meta.title == ""
        assert meta.author == ""


# ---------------------------------------------------------------------------
# Scene grouping tests
# ---------------------------------------------------------------------------


class TestParseScenes:
    def test_two_scenes(self):
        scenes = parse_fdx_scenes(TWO_SCENES_FDX)
        assert len(scenes) == 2
        assert scenes[0].scene_id == "SCN_00"
        assert scenes[0].heading == "INT. CAFE - DAY"
        assert scenes[1].scene_id == "SCN_01"
        assert scenes[1].heading == "EXT. STREET - NIGHT"

    def test_scene_elements_grouped(self):
        scenes = parse_fdx_scenes(TWO_SCENES_FDX)
        # First scene: heading + action + character + dialogue = 4
        assert len(scenes[0].elements) == 4
        # Second scene: heading + action + transition = 3
        assert len(scenes[1].elements) == 3

    def test_no_headings_single_scene(self):
        scenes = parse_fdx_scenes(NO_HEADINGS_FDX)
        assert len(scenes) == 1
        assert scenes[0].heading == ""
        assert scenes[0].scene_id == "SCN_00"

    def test_scene_text_reconstruction(self):
        scenes = parse_fdx_scenes(MINIMAL_FDX)
        text = scenes[0].text
        assert "INT. CAFE - DAY" in text
        assert "A busy cafe" in text
        assert "JOHN" in text
        assert "Hello there" in text

    def test_scene_line_count(self):
        scenes = parse_fdx_scenes(MINIMAL_FDX)
        assert scenes[0].line_count > 0

    def test_rich_fdx_three_items(self):
        scenes = parse_fdx_scenes(RICH_FDX)
        assert len(scenes) == 2
        assert scenes[0].heading == "INT. OFFICE - DAY"
        assert scenes[1].heading == "EXT. PARKING LOT - NIGHT"


# ---------------------------------------------------------------------------
# SceneChunk output tests
# ---------------------------------------------------------------------------


class TestParseFdx:
    def test_returns_scene_chunks(self):
        chunks = parse_fdx(TWO_SCENES_FDX)
        assert len(chunks) == 2
        assert all(isinstance(c, SceneChunk) for c in chunks)

    def test_chunk_ids(self):
        chunks = parse_fdx(TWO_SCENES_FDX)
        assert chunks[0].chunk_id == "SCN_00"
        assert chunks[1].chunk_id == "SCN_01"

    def test_chunk_headings(self):
        chunks = parse_fdx(TWO_SCENES_FDX)
        assert chunks[0].scene_heading == "INT. CAFE - DAY"
        assert chunks[1].scene_heading == "EXT. STREET - NIGHT"

    def test_chunk_type_scene(self):
        chunks = parse_fdx(TWO_SCENES_FDX)
        assert chunks[0].chunk_type == "scene"

    def test_chunk_type_paragraph_no_heading(self):
        chunks = parse_fdx(NO_HEADINGS_FDX)
        assert chunks[0].chunk_type == "paragraph"
        assert chunks[0].scene_heading is None

    def test_cumulative_timing(self):
        chunks = parse_fdx(TWO_SCENES_FDX)
        assert chunks[0].start_sec == 0.0
        assert chunks[1].start_sec == pytest.approx(chunks[0].duration_sec, abs=0.01)

    def test_duration_positive(self):
        chunks = parse_fdx(TWO_SCENES_FDX)
        for c in chunks:
            assert c.duration_sec > 0

    def test_page_count_positive(self):
        chunks = parse_fdx(TWO_SCENES_FDX)
        for c in chunks:
            assert c.page_count > 0

    def test_text_not_empty(self):
        chunks = parse_fdx(TWO_SCENES_FDX)
        for c in chunks:
            assert len(c.text) > 0

    def test_empty_fdx_returns_empty(self):
        chunks = parse_fdx(EMPTY_CONTENT_FDX)
        assert chunks == []


# ---------------------------------------------------------------------------
# File I/O tests
# ---------------------------------------------------------------------------


class TestParseFdxFile:
    def test_parse_file(self, tmp_path):
        f = tmp_path / "test.fdx"
        f.write_text(MINIMAL_FDX, encoding="utf-8")
        chunks = parse_fdx_file(f)
        assert len(chunks) == 1
        assert chunks[0].scene_heading == "INT. CAFE - DAY"

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_fdx_file("/nonexistent/path/script.fdx")


# ---------------------------------------------------------------------------
# Plain text conversion tests
# ---------------------------------------------------------------------------


class TestFdxToPlainText:
    def test_plain_text_contains_all_scenes(self):
        text = fdx_to_plain_text(TWO_SCENES_FDX)
        assert "INT. CAFE - DAY" in text
        assert "EXT. STREET - NIGHT" in text
        assert "Hello there" in text
        assert "Rain pours" in text

    def test_plain_text_has_scene_breaks(self):
        text = fdx_to_plain_text(TWO_SCENES_FDX)
        # Scenes separated by double newline
        assert "\n\n" in text

    def test_empty_returns_empty(self):
        text = fdx_to_plain_text(EMPTY_CONTENT_FDX)
        assert text == ""


# ---------------------------------------------------------------------------
# Timing accuracy tests
# ---------------------------------------------------------------------------


class TestTimingAccuracy:
    def test_timing_uses_page_formula(self):
        """Verify timing follows 55 lines = 1 page = 60 sec."""
        # Build an FDX with ~55 lines of action (1 page ≈ 60 sec)
        lines = "\n".join(f"Line {i}: Action description here." for i in range(55))
        fdx = f'''<?xml version="1.0" encoding="UTF-8"?>
<FinalDraft DocumentType="Script" Template="No" Version="4">
  <Content>
    <Paragraph Type="Scene Heading"><Text>INT. TEST - DAY</Text></Paragraph>
    <Paragraph Type="Action"><Text>{lines}</Text></Paragraph>
  </Content>
</FinalDraft>'''
        chunks = parse_fdx(fdx)
        assert len(chunks) == 1
        # Should be approximately 60 seconds (1 page)
        assert chunks[0].duration_sec == pytest.approx(SECONDS_PER_PAGE, rel=0.3)

    def test_total_duration_increases_with_scenes(self):
        """More scenes = more total duration."""
        one = parse_fdx(MINIMAL_FDX)
        two = parse_fdx(TWO_SCENES_FDX)
        total_one = sum(c.duration_sec for c in one)
        total_two = sum(c.duration_sec for c in two)
        assert total_two > total_one


# ---------------------------------------------------------------------------
# Route auto-detect integration tests (_parse_script_auto)
# ---------------------------------------------------------------------------


try:
    from src.api.routes.cut_routes import _parse_script_auto
    _HAS_ROUTES = True
except ImportError:
    _HAS_ROUTES = False


@pytest.mark.skipif(not _HAS_ROUTES, reason="fastapi not installed")
class TestParseScriptAutoDetect:
    """Test the _parse_script_auto function from cut_routes.py."""

    def _auto(self, text, fmt_hint="auto"):
        return _parse_script_auto(text, fmt_hint)

    def test_fdx_auto_detected(self):
        chunks, detected = self._auto(MINIMAL_FDX)
        assert detected == "fdx"
        assert len(chunks) >= 1
        assert chunks[0].scene_heading == "INT. CAFE - DAY"

    def test_fdx_explicit_hint(self):
        chunks, detected = self._auto(MINIMAL_FDX, "fdx")
        assert detected == "fdx"

    def test_plain_text_fallback(self):
        text = "Some random text\nwith no special formatting.\nJust paragraphs."
        chunks, detected = self._auto(text)
        assert detected == "plain"
        assert len(chunks) >= 1

    def test_plain_text_explicit_hint(self):
        text = "INT. CAFE - DAY\nSome action."
        chunks, detected = self._auto(text, "plain")
        assert detected == "plain"

    def test_fountain_auto_detected(self):
        fountain = (
            "INT. COFFEE SHOP - MORNING\n\n"
            "SARAH enters, looking around nervously.\n\n"
            "SARAH\n"
            "Is anyone here?\n\n"
            "EXT. PARKING LOT - NIGHT\n\n"
            "Rain pours down.\n\n"
            "CUT TO:\n"
        )
        chunks, detected = self._auto(fountain)
        assert detected == "fountain"
        assert len(chunks) >= 1

    def test_fountain_explicit_hint(self):
        fountain = (
            "INT. OFFICE - DAY\n\n"
            "Quiet.\n\n"
            "EXT. STREET - NIGHT\n\n"
            "Loud.\n"
        )
        chunks, detected = self._auto(fountain, "fountain")
        assert detected == "fountain"

    def test_empty_text(self):
        """Empty text should not crash — handled by route before calling auto."""
        from src.services.screenplay_timing import parse_screenplay
        chunks = parse_screenplay("")
        assert chunks == []

    def test_fdx_without_xml_declaration(self):
        """FDX starting with <FinalDraft (no <?xml> prolog)."""
        fdx_no_prolog = (
            '<FinalDraft DocumentType="Script" Template="No" Version="4">'
            '<Content>'
            '<Paragraph Type="Scene Heading"><Text>INT. LAB - NIGHT</Text></Paragraph>'
            '<Paragraph Type="Action"><Text>Silence.</Text></Paragraph>'
            '</Content>'
            '</FinalDraft>'
        )
        chunks, detected = self._auto(fdx_no_prolog)
        assert detected == "fdx"
        assert chunks[0].scene_heading == "INT. LAB - NIGHT"

    def test_detected_format_in_response(self):
        """Chunks from all formats have the same SceneChunk structure."""
        from dataclasses import fields
        from src.services.screenplay_timing import SceneChunk

        expected_fields = {f.name for f in fields(SceneChunk)}

        # FDX
        fdx_chunks, _ = self._auto(MINIMAL_FDX)
        for c in fdx_chunks:
            assert set(vars(c).keys()) == expected_fields

        # Plain
        plain_chunks, _ = self._auto("Some text.", "plain")
        for c in plain_chunks:
            assert set(vars(c).keys()) == expected_fields
