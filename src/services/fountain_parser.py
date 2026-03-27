"""
MARKER_CUT_B7.6: fountain_parser.py — Fountain screenplay format parser.

Parses .fountain files per the Fountain spec (https://fountain.io/syntax)
into structured FountainScene objects with line counts. These feed into
screenplay_timing.py for NarrativeBPM / pulse_script_analyzer integration.

Fountain elements handled:
  - Title page: key: value pairs at start of doc (before first blank line)
  - Scene headings: INT./EXT./INT/EXT (forced with .) followed by location
  - Action: plain paragraphs
  - Character: ALL CAPS line preceding dialogue (optionally with ^)
  - Dialogue: line after Character (or after Parenthetical)
  - Parenthetical: (text) between Character and Dialogue
  - Transition: line ending with TO: (or forced with >)
  - Lyric: line starting with ~
  - Section: line(s) starting with # (H1), ## (H2), ### (H3)
  - Synopsis: line starting with =
  - Boneyard: /* ... */ block comments (stripped from output)
  - Notes: [[...]] inline notes (stripped from output)
  - Dual dialogue: character^ notation (parsed, flagged)
  - Centered text: > text < notation
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Fountain token types
# ---------------------------------------------------------------------------

TOKEN_TITLE_PAGE = "title_page"
TOKEN_SCENE_HEADING = "scene_heading"
TOKEN_ACTION = "action"
TOKEN_CHARACTER = "character"
TOKEN_DIALOGUE = "dialogue"
TOKEN_PARENTHETICAL = "parenthetical"
TOKEN_TRANSITION = "transition"
TOKEN_LYRIC = "lyric"
TOKEN_SECTION = "section"
TOKEN_SYNOPSIS = "synopsis"
TOKEN_CENTERED = "centered"
TOKEN_PAGE_BREAK = "page_break"

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Scene heading: INT./EXT./INT/EXT or forced with leading dot
_SCENE_HEADING_RE = re.compile(
    r"^(INT\.|EXT\.|INT/EXT\.|EXT/INT\.|I/E\.|E/I\.|ИНТ\.|НАТ\.|ИНТ/НАТ\.|НАТ/ИНТ\.|INT\b|EXT\b)",
    re.IGNORECASE,
)
_FORCED_HEADING_RE = re.compile(r"^\.")

# Transition: ends with TO: or forced with >
_TRANSITION_RE = re.compile(r"\bTO:$")
_FORCED_TRANSITION_RE = re.compile(r"^>(.+)$")

# Character: all caps, optional (V.O.)/(O.S.) etc., optional ^ for dual dialogue
_CHARACTER_RE = re.compile(r"^([A-ZА-ЯЁ][A-ZА-ЯЁ0-9 \t]*?)(\s*\^)?\s*(\(.*?\))?$")

# Parenthetical: enclosed in parens
_PARENTHETICAL_RE = re.compile(r"^\(.*\)$")

# Lyric: starts with ~
_LYRIC_RE = re.compile(r"^~(.*)$")

# Section: starts with # (H1, H2, H3)
_SECTION_RE = re.compile(r"^(#{1,3})\s+(.*)$")

# Synopsis: starts with =
_SYNOPSIS_RE = re.compile(r"^=\s*(.*)$")

# Centered text: > text <
_CENTERED_RE = re.compile(r"^>\s*(.*?)\s*<$")

# Page break: three or more === signs
_PAGE_BREAK_RE = re.compile(r"^={3,}$")

# Boneyard block: /* ... */
_BONEYARD_RE = re.compile(r"/\*.*?\*/", re.DOTALL)

# Notes: [[ ... ]]
_NOTES_RE = re.compile(r"\[\[.*?\]\]", re.DOTALL)

# Title page key: value
_TITLE_KEY_RE = re.compile(r"^([A-Za-z ]+):\s*(.*)$")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class FountainElement:
    """A single parsed Fountain element."""
    token_type: str         # one of TOKEN_* constants
    text: str               # cleaned text content
    raw: str                # original raw line(s)
    line_start: int         # 0-based line index in source
    line_end: int


@dataclass
class FountainScene:
    """
    A scene extracted from a Fountain screenplay.

    Produced by FountainParser.parse() and consumed by screenplay_timing.py
    via compute_scene_timing().

    Attributes:
        scene_id:    sequential ID, e.g. "sc_01"
        heading:     scene heading text, e.g. "INT. CAFE - DAY"
                     None for the title page pseudo-scene
        content:     full concatenated text of elements in the scene
        elements:    list of FountainElement objects
        line_count:  total lines in the scene (used for timing: 55 lines = 1 page)
        line_start:  0-based start line in source
        line_end:    0-based end line in source
        is_title_page: True for the title block (duration = 0)
    """
    scene_id: str
    heading: Optional[str]
    content: str
    elements: List[FountainElement] = field(default_factory=list)
    line_count: int = 0
    line_start: int = 0
    line_end: int = 0
    is_title_page: bool = False


# ---------------------------------------------------------------------------
# Timing integration types (mirrors screenplay_timing output for Fountain)
# ---------------------------------------------------------------------------

@dataclass
class TimedScene:
    """
    A FountainScene enriched with timing data.

    Produced by compute_scene_timing(). This is the primary output format
    expected by pulse_script_analyzer / NarrativeBPM pipeline.
    """
    scene_id: str
    heading: Optional[str]
    content: str
    line_count: int
    start_sec: float
    duration_sec: float
    page_number: float      # fractional page position at scene start
    is_title_page: bool = False


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class FountainParser:
    """
    Pure-Python Fountain screenplay parser.

    Usage:
        parser = FountainParser()
        scenes = parser.parse(fountain_text)
        # → List[FountainScene]

    Then feed into screenplay_timing:
        timed = compute_scene_timing(scenes)
        # → List[TimedScene]  with start_sec, duration_sec, page_number
    """

    def parse(self, text: str) -> List[FountainScene]:
        """
        Parse Fountain text into a list of FountainScene objects.

        Returns scenes in order. Title page (if present) is scene index 0
        with is_title_page=True and heading=None. Subsequent scenes correspond
        to INT./EXT. headings (or forced headings starting with '.').
        If no headings are found, the entire document is returned as a single
        scene with heading=None.
        """
        if not text or not text.strip():
            return []

        # 1. Strip boneyard and notes
        clean = _BONEYARD_RE.sub("", text)
        clean = _NOTES_RE.sub("", clean)

        # 2. Parse title page (everything before the first blank line IF
        #    the first non-empty block contains key: value pairs)
        title_meta, body_start_line, title_line_count = self._parse_title_page(clean)

        lines = clean.split("\n")
        body_lines = lines[body_start_line:]

        # 3. Tokenise body
        elements = self._tokenise(body_lines, line_offset=body_start_line)

        # 4. Group elements into scenes
        scenes = self._group_into_scenes(elements, title_meta, title_line_count, body_start_line)

        return scenes

    # --- Private ---

    def _parse_title_page(self, text: str) -> Tuple[Optional[dict], int, int]:
        """
        Detect and parse title page block.

        Returns (title_dict_or_None, body_start_line_index, title_line_count).
        title_dict maps keys to values, e.g. {"Title": "My Film", "Author": "..."}
        """
        lines = text.split("\n")
        # Title page ends at first double-blank or paragraph that isn't key:value
        title_dict: dict = {}
        i = 0

        # Skip leading blank lines
        while i < len(lines) and not lines[i].strip():
            i += 1

        first_content = i
        has_title_page = False

        # Check first non-blank block for key:value pairs
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                # Blank line — title page ends here
                i += 1
                break
            m = _TITLE_KEY_RE.match(line)
            if m:
                has_title_page = True
                key = m.group(1).strip()
                val = m.group(2).strip()
                # Handle multi-line value (indented continuation)
                j = i + 1
                while j < len(lines) and lines[j].startswith("   "):
                    val += " " + lines[j].strip()
                    j += 1
                title_dict[key] = val
                i = j
            else:
                # Not a key:value — no title page
                has_title_page = False
                break

        if not has_title_page:
            return None, 0, 0

        # Skip blank lines between title page and body
        while i < len(lines) and not lines[i].strip():
            i += 1

        title_line_count = i - first_content
        return title_dict, i, title_line_count

    def _tokenise(self, lines: List[str], line_offset: int = 0) -> List[FountainElement]:
        """Tokenise body lines into FountainElement objects."""
        elements: List[FountainElement] = []
        i = 0

        # State tracking for dialogue context
        in_dialogue = False  # True after Character element

        while i < len(lines):
            line = lines[i]
            abs_line = i + line_offset

            # --- Empty line ---
            if not line.strip():
                in_dialogue = False
                i += 1
                continue

            # --- Page break ===+ ---
            if _PAGE_BREAK_RE.match(line.strip()):
                elements.append(FountainElement(
                    token_type=TOKEN_PAGE_BREAK,
                    text="",
                    raw=line,
                    line_start=abs_line,
                    line_end=abs_line,
                ))
                in_dialogue = False
                i += 1
                continue

            # --- Section # ---
            m_section = _SECTION_RE.match(line.strip())
            if m_section:
                elements.append(FountainElement(
                    token_type=TOKEN_SECTION,
                    text=m_section.group(2).strip(),
                    raw=line,
                    line_start=abs_line,
                    line_end=abs_line,
                ))
                in_dialogue = False
                i += 1
                continue

            # --- Synopsis = ---
            m_synopsis = _SYNOPSIS_RE.match(line.strip())
            if m_synopsis:
                elements.append(FountainElement(
                    token_type=TOKEN_SYNOPSIS,
                    text=m_synopsis.group(1).strip(),
                    raw=line,
                    line_start=abs_line,
                    line_end=abs_line,
                ))
                in_dialogue = False
                i += 1
                continue

            # --- Lyric ~ ---
            m_lyric = _LYRIC_RE.match(line.strip())
            if m_lyric:
                elements.append(FountainElement(
                    token_type=TOKEN_LYRIC,
                    text=m_lyric.group(1).strip(),
                    raw=line,
                    line_start=abs_line,
                    line_end=abs_line,
                ))
                i += 1
                continue

            # --- Centered > text < ---
            m_centered = _CENTERED_RE.match(line.strip())
            if m_centered:
                elements.append(FountainElement(
                    token_type=TOKEN_CENTERED,
                    text=m_centered.group(1).strip(),
                    raw=line,
                    line_start=abs_line,
                    line_end=abs_line,
                ))
                i += 1
                continue

            stripped = line.strip()

            # --- Forced transition > (not centered) ---
            m_forced_trans = _FORCED_TRANSITION_RE.match(stripped)
            if m_forced_trans and not stripped.endswith("<"):
                elements.append(FountainElement(
                    token_type=TOKEN_TRANSITION,
                    text=m_forced_trans.group(1).strip(),
                    raw=line,
                    line_start=abs_line,
                    line_end=abs_line,
                ))
                in_dialogue = False
                i += 1
                continue

            # --- Natural transition (ends with TO:) ---
            if _TRANSITION_RE.search(stripped) and stripped == stripped.upper() and len(stripped) > 3:
                elements.append(FountainElement(
                    token_type=TOKEN_TRANSITION,
                    text=stripped,
                    raw=line,
                    line_start=abs_line,
                    line_end=abs_line,
                ))
                in_dialogue = False
                i += 1
                continue

            # --- Forced scene heading: starts with . but not .. ---
            if _FORCED_HEADING_RE.match(stripped) and not stripped.startswith(".."):
                heading_text = stripped[1:].strip()
                elements.append(FountainElement(
                    token_type=TOKEN_SCENE_HEADING,
                    text=heading_text,
                    raw=line,
                    line_start=abs_line,
                    line_end=abs_line,
                ))
                in_dialogue = False
                i += 1
                continue

            # --- Natural scene heading: INT./EXT. etc ---
            if _SCENE_HEADING_RE.match(stripped):
                elements.append(FountainElement(
                    token_type=TOKEN_SCENE_HEADING,
                    text=stripped,
                    raw=line,
                    line_start=abs_line,
                    line_end=abs_line,
                ))
                in_dialogue = False
                i += 1
                continue

            # --- Parenthetical (only valid in dialogue context) ---
            if in_dialogue and _PARENTHETICAL_RE.match(stripped):
                elements.append(FountainElement(
                    token_type=TOKEN_PARENTHETICAL,
                    text=stripped,
                    raw=line,
                    line_start=abs_line,
                    line_end=abs_line,
                ))
                # remains in_dialogue
                i += 1
                continue

            # --- Character: ALL CAPS line (not in dialogue) ---
            # Character must be preceded by a blank line (handled via in_dialogue=False reset)
            if not in_dialogue and self._is_character_cue(stripped, lines, i):
                elements.append(FountainElement(
                    token_type=TOKEN_CHARACTER,
                    text=stripped.rstrip("^").strip(),
                    raw=line,
                    line_start=abs_line,
                    line_end=abs_line,
                ))
                in_dialogue = True
                i += 1
                continue

            # --- Dialogue (after character or parenthetical) ---
            if in_dialogue:
                # Collect multi-line dialogue
                dlg_lines = [line]
                dlg_start = abs_line
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    if not next_line.strip():
                        break
                    # If next non-blank line is a character cue, stop
                    if self._is_character_cue(next_line.strip(), lines, j):
                        break
                    if _PARENTHETICAL_RE.match(next_line.strip()):
                        break
                    dlg_lines.append(next_line)
                    j += 1
                elements.append(FountainElement(
                    token_type=TOKEN_DIALOGUE,
                    text="\n".join(l.strip() for l in dlg_lines),
                    raw="\n".join(dlg_lines),
                    line_start=dlg_start,
                    line_end=dlg_start + len(dlg_lines) - 1,
                ))
                i = j
                continue

            # --- Action (fallback) ---
            # Collect until blank line
            action_lines = [line]
            action_start = abs_line
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                if not next_line.strip():
                    break
                # Stop if next line is a heading
                if _SCENE_HEADING_RE.match(next_line.strip()) or \
                   (_FORCED_HEADING_RE.match(next_line.strip()) and not next_line.strip().startswith("..")):
                    break
                action_lines.append(next_line)
                j += 1
            elements.append(FountainElement(
                token_type=TOKEN_ACTION,
                text="\n".join(l.strip() for l in action_lines),
                raw="\n".join(action_lines),
                line_start=action_start,
                line_end=action_start + len(action_lines) - 1,
            ))
            in_dialogue = False
            i = j

        return elements

    def _is_character_cue(self, stripped: str, lines: List[str], i: int) -> bool:
        """
        Determine if a line is a character cue:
          - Must be all-uppercase (letters, digits, spaces, parens for extensions)
          - Must not be empty
          - Must not look like a scene heading
          - Must not be a transition
          - Must have a non-empty next line (the dialogue)
        """
        if not stripped:
            return False
        # Remove dual-dialogue marker and extension for check
        candidate = re.sub(r"\^$", "", stripped).strip()
        candidate = re.sub(r"\s*\(.*?\)\s*$", "", candidate).strip()
        if not candidate:
            return False
        # Must be all uppercase letters/digits/spaces
        if not re.match(r"^[A-ZА-ЯЁ][A-ZА-ЯЁ0-9 \t]*$", candidate):
            return False
        # Must not look like a scene heading
        if _SCENE_HEADING_RE.match(stripped):
            return False
        # Must not be a transition
        if _TRANSITION_RE.search(stripped):
            return False
        # Next line must exist and be non-empty (the dialogue)
        next_idx = i + 1
        while next_idx < len(lines) and not lines[next_idx].strip():
            next_idx += 1
        # If no next line exists, it's not a character cue
        if next_idx >= len(lines):
            return False
        return True

    def _group_into_scenes(
        self,
        elements: List[FountainElement],
        title_meta: Optional[dict],
        title_line_count: int,
        body_start_line: int,
    ) -> List[FountainScene]:
        """Group parsed elements into FountainScene objects."""
        scenes: List[FountainScene] = []

        # Title page scene (zero-duration)
        if title_meta is not None:
            title_content_parts = [f"{k}: {v}" for k, v in title_meta.items()]
            scenes.append(FountainScene(
                scene_id="sc_00",
                heading=None,
                content="\n".join(title_content_parts),
                elements=[],
                line_count=title_line_count,
                line_start=0,
                line_end=body_start_line - 1,
                is_title_page=True,
            ))

        # Group body elements into scenes
        current_elements: List[FountainElement] = []
        current_heading: Optional[str] = None
        current_start: int = body_start_line
        scene_counter = 1

        def flush_scene():
            nonlocal current_elements, current_heading, current_start, scene_counter
            if not current_elements:
                return
            content_parts = []
            for el in current_elements:
                if el.token_type not in (TOKEN_PAGE_BREAK,):
                    content_parts.append(el.text)
            content = "\n".join(content_parts)
            if content.strip():
                line_count = sum(
                    el.line_end - el.line_start + 1
                    for el in current_elements
                )
                line_end = current_elements[-1].line_end if current_elements else current_start
                scenes.append(FountainScene(
                    scene_id=f"sc_{scene_counter:02d}",
                    heading=current_heading,
                    content=content,
                    elements=list(current_elements),
                    line_count=line_count,
                    line_start=current_start,
                    line_end=line_end,
                    is_title_page=False,
                ))
                scene_counter += 1
            current_elements = []
            current_heading = None

        for el in elements:
            if el.token_type == TOKEN_SCENE_HEADING:
                flush_scene()
                current_heading = el.text
                current_start = el.line_start
                current_elements = [el]
            else:
                if not current_elements and el.token_type != TOKEN_PAGE_BREAK:
                    current_start = el.line_start
                current_elements.append(el)

        flush_scene()

        # If no scenes created from body elements (no headings found),
        # treat all body elements as a single scene
        if not scenes or (len(scenes) == 1 and scenes[0].is_title_page):
            all_content_parts = [el.text for el in elements if el.token_type not in (TOKEN_PAGE_BREAK,)]
            content = "\n".join(all_content_parts)
            if content.strip():
                line_count = sum(el.line_end - el.line_start + 1 for el in elements)
                line_end = elements[-1].line_end if elements else body_start_line
                scenes.append(FountainScene(
                    scene_id=f"sc_{scene_counter:02d}",
                    heading=None,
                    content=content,
                    elements=list(elements),
                    line_count=line_count,
                    line_start=body_start_line,
                    line_end=line_end,
                    is_title_page=False,
                ))

        return scenes


# ---------------------------------------------------------------------------
# Timing integration
# ---------------------------------------------------------------------------

LINES_PER_PAGE: int = 55
SECONDS_PER_PAGE: float = 60.0
MIN_SCENE_DURATION_SEC: float = 5.0


def compute_scene_timing(scenes: List[FountainScene]) -> List[TimedScene]:
    """
    Enrich FountainScene list with start_sec, duration_sec, page_number.

    Industry rule: 55 lines = 1 page = 60 seconds.
    Title page scenes get duration_sec = 0.
    Very short scenes (< MIN_SCENE_DURATION_SEC) are clamped to minimum.

    Args:
        scenes: output of FountainParser.parse()

    Returns:
        List of TimedScene with chronological timing.
    """
    result: List[TimedScene] = []
    cumulative_sec = 0.0
    cumulative_pages = 0.0

    for sc in scenes:
        if sc.is_title_page:
            result.append(TimedScene(
                scene_id=sc.scene_id,
                heading=sc.heading,
                content=sc.content,
                line_count=sc.line_count,
                start_sec=0.0,
                duration_sec=0.0,
                page_number=0.0,
                is_title_page=True,
            ))
            continue

        # Compute duration from line count
        pages = max(sc.line_count / LINES_PER_PAGE, 0.01)
        duration_sec = max(pages * SECONDS_PER_PAGE, MIN_SCENE_DURATION_SEC)

        result.append(TimedScene(
            scene_id=sc.scene_id,
            heading=sc.heading,
            content=sc.content,
            line_count=sc.line_count,
            start_sec=cumulative_sec,
            duration_sec=duration_sec,
            page_number=cumulative_pages,
            is_title_page=False,
        ))

        cumulative_sec += duration_sec
        cumulative_pages += pages

    return result


def compute_total_runtime(scenes: List[FountainScene]) -> float:
    """
    Compute total estimated runtime in seconds from scene list.

    Convenience utility that sums durations across all non-title scenes.
    """
    timed = compute_scene_timing(scenes)
    if not timed:
        return 0.0
    non_title = [t for t in timed if not t.is_title_page]
    if not non_title:
        return 0.0
    last = non_title[-1]
    return last.start_sec + last.duration_sec


# ---------------------------------------------------------------------------
# Convenience API
# ---------------------------------------------------------------------------

def parse_fountain(text: str) -> List[FountainScene]:
    """Parse Fountain text into FountainScene list."""
    return FountainParser().parse(text)


def parse_fountain_timed(text: str) -> List[TimedScene]:
    """
    Parse Fountain text and return TimedScene list with full timing data.

    This is the primary integration point for pulse_script_analyzer /
    NarrativeBPM pipeline. Output format:
        {scene_id, heading, content, line_count, start_sec, duration_sec, page_number}
    """
    scenes = parse_fountain(text)
    return compute_scene_timing(scenes)
