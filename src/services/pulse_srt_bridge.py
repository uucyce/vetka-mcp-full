"""
PULSE SRT Bridge — converts SRT/VTT subtitle files to NarrativeBPM scenes.

Parses subtitle blocks, groups them into narrative scenes by gap detection,
then runs each scene through PulseScriptAnalyzer for dramatic function analysis.

Flow:
  .srt / .vtt file → parse blocks → group into scenes → analyze → NarrativeBPM[]

MARKER_179.15_SRT_NARRATIVE_BRIDGE
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.services.pulse_conductor import NarrativeBPM
from src.services.pulse_script_analyzer import get_script_analyzer


# ---------------------------------------------------------------------------
# SRT / VTT parsing
# ---------------------------------------------------------------------------

@dataclass
class SubtitleBlock:
    """A single subtitle entry with timing and text."""
    index: int
    start_sec: float
    end_sec: float
    text: str

    @property
    def duration_sec(self) -> float:
        return self.end_sec - self.start_sec


def parse_timestamp(ts: str) -> float:
    """Parse SRT/VTT timestamp → seconds. Handles both ',' and '.' separators."""
    ts = ts.strip().replace(",", ".")
    parts = ts.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(ts)


def parse_srt(content: str) -> List[SubtitleBlock]:
    """Parse SRT format subtitle content."""
    blocks: List[SubtitleBlock] = []
    # Split on blank lines
    raw_blocks = re.split(r"\n\s*\n", content.strip())

    for raw in raw_blocks:
        lines = raw.strip().split("\n")
        if len(lines) < 2:
            continue

        # Find the timing line (contains -->)
        timing_idx = -1
        for i, line in enumerate(lines):
            if "-->" in line:
                timing_idx = i
                break

        if timing_idx < 0:
            continue

        # Parse timing
        timing_parts = lines[timing_idx].split("-->")
        if len(timing_parts) != 2:
            continue

        try:
            start = parse_timestamp(timing_parts[0])
            end = parse_timestamp(timing_parts[1])
        except (ValueError, IndexError):
            continue

        # Text is everything after timing line
        text_lines = lines[timing_idx + 1:]
        text = " ".join(line.strip() for line in text_lines if line.strip())
        # Strip HTML tags (common in SRT)
        text = re.sub(r"<[^>]+>", "", text)

        # Index: try to parse from line before timing, else sequential
        try:
            idx = int(lines[timing_idx - 1].strip()) if timing_idx > 0 else len(blocks)
        except ValueError:
            idx = len(blocks)

        if text:
            blocks.append(SubtitleBlock(
                index=idx,
                start_sec=start,
                end_sec=end,
                text=text,
            ))

    return blocks


def parse_vtt(content: str) -> List[SubtitleBlock]:
    """Parse WebVTT format. Similar to SRT but with WEBVTT header."""
    # Remove WEBVTT header and any metadata
    content = re.sub(r"^WEBVTT[^\n]*\n", "", content.strip())
    content = re.sub(r"^NOTE[^\n]*\n(?:[^\n]+\n)*\n", "", content, flags=re.MULTILINE)
    # VTT uses same format as SRT after header
    return parse_srt(content)


def parse_subtitles(content: str) -> List[SubtitleBlock]:
    """Auto-detect SRT vs VTT and parse."""
    stripped = content.strip()
    if stripped.startswith("WEBVTT"):
        return parse_vtt(content)
    return parse_srt(content)


# ---------------------------------------------------------------------------
# Scene grouping — group subtitle blocks into narrative scenes
# ---------------------------------------------------------------------------

@dataclass
class SubtitleScene:
    """A group of subtitle blocks forming a narrative scene."""
    scene_id: str
    blocks: List[SubtitleBlock]
    start_sec: float
    end_sec: float
    combined_text: str

    @property
    def duration_sec(self) -> float:
        return self.end_sec - self.start_sec


def group_into_scenes(
    blocks: List[SubtitleBlock],
    gap_threshold_sec: float = 3.0,
    max_scene_duration_sec: float = 120.0,
) -> List[SubtitleScene]:
    """
    Group subtitle blocks into scenes based on timing gaps.

    A new scene starts when:
    - Gap between blocks exceeds gap_threshold_sec
    - Current scene exceeds max_scene_duration_sec
    """
    if not blocks:
        return []

    scenes: List[SubtitleScene] = []
    current_blocks: List[SubtitleBlock] = [blocks[0]]

    for i in range(1, len(blocks)):
        gap = blocks[i].start_sec - blocks[i - 1].end_sec
        current_duration = blocks[i].end_sec - current_blocks[0].start_sec

        if gap > gap_threshold_sec or current_duration > max_scene_duration_sec:
            # Flush current scene
            scenes.append(_make_scene(current_blocks, len(scenes)))
            current_blocks = [blocks[i]]
        else:
            current_blocks.append(blocks[i])

    # Flush last scene
    if current_blocks:
        scenes.append(_make_scene(current_blocks, len(scenes)))

    return scenes


def _make_scene(blocks: List[SubtitleBlock], index: int) -> SubtitleScene:
    """Create a SubtitleScene from a list of blocks."""
    combined = " ".join(b.text for b in blocks)
    return SubtitleScene(
        scene_id=f"srt_sc_{index}",
        blocks=blocks,
        start_sec=blocks[0].start_sec,
        end_sec=blocks[-1].end_sec,
        combined_text=combined,
    )


# ---------------------------------------------------------------------------
# SRT → NarrativeBPM conversion
# ---------------------------------------------------------------------------

def srt_to_narrative_bpm(
    content: str,
    gap_threshold_sec: float = 3.0,
    max_scene_duration_sec: float = 120.0,
) -> List[NarrativeBPM]:
    """
    Parse SRT/VTT content and convert to NarrativeBPM scenes.

    1. Parse subtitle blocks
    2. Group into scenes by timing gaps
    3. Run each scene through PulseScriptAnalyzer
    4. Return NarrativeBPM list with timing metadata
    """
    blocks = parse_subtitles(content)
    if not blocks:
        return []

    scenes = group_into_scenes(
        blocks,
        gap_threshold_sec=gap_threshold_sec,
        max_scene_duration_sec=max_scene_duration_sec,
    )

    analyzer = get_script_analyzer()
    results: List[NarrativeBPM] = []

    for scene in scenes:
        nbpm = analyzer.analyze_single(scene.combined_text, scene_id=scene.scene_id)
        # Override scene_id to include timing info
        nbpm.scene_id = scene.scene_id
        results.append(nbpm)

    return results


def srt_to_narrative_bpm_with_timing(
    content: str,
    gap_threshold_sec: float = 3.0,
    max_scene_duration_sec: float = 120.0,
) -> List[Dict[str, Any]]:
    """
    Same as srt_to_narrative_bpm but returns dicts with timing metadata.

    Each entry includes start_sec, end_sec, duration_sec alongside NarrativeBPM fields.
    This is what the REST API returns.
    """
    blocks = parse_subtitles(content)
    if not blocks:
        return []

    scenes = group_into_scenes(
        blocks,
        gap_threshold_sec=gap_threshold_sec,
        max_scene_duration_sec=max_scene_duration_sec,
    )

    analyzer = get_script_analyzer()
    results: List[Dict[str, Any]] = []

    for scene in scenes:
        nbpm = analyzer.analyze_single(scene.combined_text, scene_id=scene.scene_id)

        results.append({
            "scene_id": scene.scene_id,
            "start_sec": round(scene.start_sec, 3),
            "end_sec": round(scene.end_sec, 3),
            "duration_sec": round(scene.duration_sec, 3),
            "subtitle_count": len(scene.blocks),
            "combined_text": scene.combined_text,
            "dramatic_function": nbpm.dramatic_function,
            "pendulum_position": nbpm.pendulum_position,
            "estimated_energy": nbpm.estimated_energy,
            "suggested_scale": nbpm.suggested_scale,
            "keywords": nbpm.keywords,
            "confidence": nbpm.confidence,
        })

    return results
