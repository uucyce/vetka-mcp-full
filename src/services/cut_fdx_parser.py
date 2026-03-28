"""
MARKER_FDX_PARSER — Final Draft .fdx screenplay parser.

Parses Final Draft 8+ XML (.fdx) files into SceneChunk objects compatible
with the existing CUT screenplay pipeline (screenplay_timing.py, PULSE
conductor, script routes).

FDX XML structure (simplified):
  <FinalDraft DocumentType="Script" ...>
    <Content>
      <Paragraph Type="Scene Heading"><Text>INT. CAFE - DAY</Text></Paragraph>
      <Paragraph Type="Action"><Text>A busy cafe...</Text></Paragraph>
      <Paragraph Type="Character"><Text>JOHN</Text></Paragraph>
      <Paragraph Type="Dialogue"><Text>Hello there.</Text></Paragraph>
      <Paragraph Type="Parenthetical"><Text>(smiling)</Text></Paragraph>
      <Paragraph Type="Transition"><Text>CUT TO:</Text></Paragraph>
    </Content>
  </FinalDraft>

Paragraph types in FDX:
  Scene Heading, Action, Character, Dialogue, Parenthetical,
  Transition, Shot, General, Cast List

Timing: same industry standard as fountain_parser / screenplay_timing:
  55 lines = 1 page = 60 seconds (Courier 12pt)

@status: active
@phase: W8
@task: tb_1774436431_1
@depends: xml.etree.ElementTree (stdlib)
@used_by: cut_routes.py (POST /cut/script/parse), pulse_script_analyzer
"""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.services.screenplay_timing import (
    CHARS_PER_PAGE,
    LINES_PER_PAGE,
    SECONDS_PER_PAGE,
    SceneChunk,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# FDX element types → canonical mapping
# ---------------------------------------------------------------------------

# FDX Paragraph Type attribute values (case varies across FD versions)
_FDX_SCENE_HEADING = {"scene heading", "slug line"}
_FDX_ACTION = {"action", "general"}
_FDX_CHARACTER = {"character"}
_FDX_DIALOGUE = {"dialogue", "dialog"}
_FDX_PARENTHETICAL = {"parenthetical"}
_FDX_TRANSITION = {"transition"}
_FDX_SHOT = {"shot"}
_FDX_CAST_LIST = {"cast list"}


@dataclass
class FDXElement:
    """One parsed element from an FDX paragraph."""
    element_type: str   # scene_heading, action, character, dialogue, parenthetical, transition, shot
    text: str
    dual_dialogue: bool = False


@dataclass
class FDXScene:
    """A scene extracted from FDX — group of elements under one heading."""
    scene_id: str                           # "SCN_01", etc.
    heading: str = ""                       # "INT. CAFE - DAY"
    elements: list[FDXElement] = field(default_factory=list)
    line_start: int = 0                     # Paragraph index in source XML
    line_end: int = 0

    @property
    def text(self) -> str:
        """Reconstruct plain text from elements."""
        parts = []
        for el in self.elements:
            if el.element_type == "scene_heading":
                parts.append(el.text.upper())
            elif el.element_type == "character":
                parts.append(el.text.upper())
            elif el.element_type == "parenthetical":
                parts.append(f"({el.text})")
            elif el.element_type == "dialogue":
                parts.append(el.text)
            elif el.element_type == "transition":
                parts.append(el.text)
            else:
                parts.append(el.text)
        return "\n".join(parts).strip()

    @property
    def line_count(self) -> int:
        return self.text.count("\n") + 1


@dataclass
class FDXMetadata:
    """Metadata extracted from FDX header."""
    title: str = ""
    author: str = ""
    draft: str = ""
    copyright: str = ""
    contact: str = ""


# ---------------------------------------------------------------------------
# XML parsing
# ---------------------------------------------------------------------------

def _extract_text(paragraph: ET.Element) -> str:
    """
    Extract full text from a <Paragraph> element.
    FDX stores text in <Text> children, potentially split across
    multiple <Text> elements with style attributes.
    """
    parts = []
    for text_el in paragraph.iter("Text"):
        if text_el.text:
            parts.append(text_el.text)
        if text_el.tail:
            parts.append(text_el.tail)
    return "".join(parts).strip()


def _classify_paragraph(para_type: str) -> str:
    """Map FDX Paragraph Type → canonical element type."""
    pt = para_type.lower().strip()
    if pt in _FDX_SCENE_HEADING:
        return "scene_heading"
    if pt in _FDX_ACTION:
        return "action"
    if pt in _FDX_CHARACTER:
        return "character"
    if pt in _FDX_DIALOGUE:
        return "dialogue"
    if pt in _FDX_PARENTHETICAL:
        return "parenthetical"
    if pt in _FDX_TRANSITION:
        return "transition"
    if pt in _FDX_SHOT:
        return "shot"
    if pt in _FDX_CAST_LIST:
        return "action"  # treat as general text
    return "action"  # default unknown → action


def _parse_metadata(root: ET.Element) -> FDXMetadata:
    """Extract metadata from FDX TitlePage or HeaderAndFooter."""
    meta = FDXMetadata()

    # Try TitlePage element
    title_page = root.find(".//TitlePage")
    if title_page is not None:
        for content in title_page.findall(".//Content/Paragraph"):
            text = _extract_text(content)
            if not text:
                continue
            # Heuristic: first non-empty line = title, "written by" line → author
            if not meta.title and not any(
                kw in text.lower() for kw in ("written", "draft", "copyright", "©")
            ):
                meta.title = text
            elif "written by" in text.lower() or "by" == text.lower().strip():
                continue  # skip "written by" label
            elif not meta.author and meta.title:
                meta.author = text

    # Try SmartType / ScriptNotes for title
    for el in root.findall(".//SmartType"):
        if el.get("Type") == "Title" and el.text:
            meta.title = el.text.strip()

    return meta


def parse_fdx_elements(xml_text: str) -> tuple[list[FDXElement], FDXMetadata]:
    """
    Parse raw FDX XML into a flat list of FDXElements + metadata.

    Args:
        xml_text: Full .fdx file content as string.

    Returns:
        (elements, metadata) tuple.

    Raises:
        ET.ParseError: If XML is malformed.
        ValueError: If not a valid FDX document.
    """
    root = ET.fromstring(xml_text)

    # Validate it's an FDX file
    if root.tag != "FinalDraft":
        raise ValueError(f"Not a Final Draft file: root element is <{root.tag}>")

    metadata = _parse_metadata(root)
    elements: list[FDXElement] = []

    # Find Content element (contains all paragraphs)
    content = root.find("Content")
    if content is None:
        return elements, metadata

    for para in content.findall("Paragraph"):
        para_type = para.get("Type", "Action")
        text = _extract_text(para)

        if not text:
            continue

        el_type = _classify_paragraph(para_type)
        dual = para.get("DualDialogue") == "Start"

        elements.append(FDXElement(
            element_type=el_type,
            text=text,
            dual_dialogue=dual,
        ))

    return elements, metadata


def parse_fdx_scenes(xml_text: str) -> list[FDXScene]:
    """
    Parse FDX XML into grouped scenes.

    Splits elements at scene headings. Elements before the first heading
    become scene "SCN_00" (title page / preamble).
    """
    elements, metadata = parse_fdx_elements(xml_text)

    scenes: list[FDXScene] = []
    current_elements: list[FDXElement] = []
    current_heading = ""
    scene_idx = 0
    para_start = 0

    for i, el in enumerate(elements):
        if el.element_type == "scene_heading":
            # Flush previous scene
            if current_elements:
                scenes.append(FDXScene(
                    scene_id=f"SCN_{scene_idx:02d}",
                    heading=current_heading,
                    elements=list(current_elements),
                    line_start=para_start,
                    line_end=i - 1,
                ))
                scene_idx += 1

            current_elements = [el]
            current_heading = el.text
            para_start = i
        else:
            current_elements.append(el)

    # Flush last scene
    if current_elements:
        scenes.append(FDXScene(
            scene_id=f"SCN_{scene_idx:02d}",
            heading=current_heading,
            elements=list(current_elements),
            line_start=para_start,
            line_end=len(elements) - 1,
        ))

    return scenes


# ---------------------------------------------------------------------------
# SceneChunk output (route-compatible)
# ---------------------------------------------------------------------------

def _estimate_pages(text: str) -> float:
    """Estimate page count. Same algorithm as screenplay_timing.py."""
    lines = text.split("\n")
    by_lines = len(lines) / LINES_PER_PAGE
    by_chars = len(text) / CHARS_PER_PAGE
    return max(by_lines, by_chars, 0.01)


def parse_fdx(xml_text: str) -> list[SceneChunk]:
    """
    Parse FDX XML into SceneChunk objects with chronological timing.

    This is the primary integration point — output matches
    screenplay_timing.parse_screenplay() for route compatibility.

    Args:
        xml_text: Full .fdx file content as string.

    Returns:
        List of SceneChunk with cumulative timing.
    """
    scenes = parse_fdx_scenes(xml_text)

    chunks: list[SceneChunk] = []
    cursor_sec = 0.0

    for scene in scenes:
        text = scene.text
        pages = _estimate_pages(text)
        duration = pages * SECONDS_PER_PAGE

        chunks.append(SceneChunk(
            chunk_id=scene.scene_id,
            scene_heading=scene.heading or None,
            chunk_type="scene" if scene.heading else "paragraph",
            text=text,
            start_sec=cursor_sec,
            duration_sec=round(duration, 2),
            line_start=scene.line_start,
            line_end=scene.line_end,
            page_count=round(pages, 3),
        ))

        cursor_sec += duration

    return chunks


def parse_fdx_file(path: str | Path) -> list[SceneChunk]:
    """
    Parse an .fdx file from disk into SceneChunk objects.

    Args:
        path: Path to .fdx file.

    Returns:
        List of SceneChunk with chronological timing.

    Raises:
        FileNotFoundError: If file doesn't exist.
        ET.ParseError: If XML is malformed.
        ValueError: If not a valid FDX document.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"FDX file not found: {path}")

    xml_text = p.read_text(encoding="utf-8")
    return parse_fdx(xml_text)


def fdx_to_plain_text(xml_text: str) -> str:
    """
    Convert FDX XML to plain screenplay text.

    Useful for feeding into PulseScriptAnalyzer which operates on raw text.
    """
    scenes = parse_fdx_scenes(xml_text)
    return "\n\n".join(s.text for s in scenes if s.text)
