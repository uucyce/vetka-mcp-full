"""
PULSE Script Rhythm Analyzer — extracts narrative BPM from script/brief text.

Parses text into scenes, determines dramatic_function and pendulum_position
for each. When no LLM available, uses keyword heuristics.

MARKER_179.4_SCRIPT_ANALYZER
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.services.pulse_cinema_matrix import get_cinema_matrix, CinemaMatrixRow
from src.services.pulse_conductor import NarrativeBPM


# ---------------------------------------------------------------------------
# Keyword-based dramatic function detection
# ---------------------------------------------------------------------------

_FUNCTION_KEYWORDS: Dict[str, Dict[str, Any]] = {
    "victory": {
        "keywords": ["победа", "victory", "triumph", "win", "celebrates", "hero",
                      "celebration", "выиграл", "победил", "торжество"],
        "pendulum": 0.8,
        "energy": 0.9,
        "scale_hint": "Ionian",
    },
    "wonder": {
        "keywords": ["чудо", "wonder", "miracle", "dream", "magic", "fly", "flying",
                      "мечта", "полёт", "волшебство", "magic", "fantasy"],
        "pendulum": 0.8,
        "energy": 0.7,
        "scale_hint": "Lydian",
    },
    "adventure": {
        "keywords": ["погоня", "chase", "run", "escape", "road", "journey", "drive",
                      "бежит", "гонится", "дорога", "путешествие", "heist", "action"],
        "pendulum": 0.6,
        "energy": 0.85,
        "scale_hint": "Mixolydian",
    },
    "mystery": {
        "keywords": ["тайна", "mystery", "detective", "clue", "noir", "shadow",
                      "ночь", "night", "investigate", "secret", "загадка", "тень"],
        "pendulum": -0.4,
        "energy": 0.4,
        "scale_hint": "Dorian",
    },
    "loss": {
        "keywords": ["потеря", "loss", "grief", "death", "farewell", "goodbye",
                      "прощание", "горе", "смерть", "плачет", "cry", "tears", "funeral"],
        "pendulum": -0.7,
        "energy": 0.3,
        "scale_hint": "Aeolian",
    },
    "menace": {
        "keywords": ["угроза", "threat", "ritual", "evil", "horror", "monster",
                      "ужас", "ритуал", "зло", "dark", "blood", "curse", "demon"],
        "pendulum": -0.9,
        "energy": 0.6,
        "scale_hint": "Phrygian",
    },
    "madness": {
        "keywords": ["безумие", "madness", "chaos", "insane", "collapse", "breakdown",
                      "хаос", "развал", "сумасшествие", "crazy", "psycho", "shatter"],
        "pendulum": -1.0,
        "energy": 0.8,
        "scale_hint": "Locrian",
    },
    "passion": {
        "keywords": ["страсть", "passion", "love", "obsession", "fatal", "desire",
                      "любовь", "влечение", "роковой", "flame", "seduce"],
        "pendulum": -0.4,
        "energy": 0.7,
        "scale_hint": "Harmonic Minor",
    },
    "dream": {
        "keywords": ["сон", "dream", "surreal", "hallucination", "underwater",
                      "галлюцинация", "подводный", "otherworldly", "float"],
        "pendulum": -0.2,
        "energy": 0.3,
        "scale_hint": "Whole Tone",
    },
    "tension": {
        "keywords": ["нарастание", "escalation", "buildup", "panic", "countdown",
                      "таймер", "bomb", "ticking", "давление", "pressure"],
        "pendulum": 0.0,
        "energy": 0.9,
        "scale_hint": "Chromatic",
    },
    "epic": {
        "keywords": ["эпос", "epic", "battle", "army", "hero journey", "boss fight",
                      "битва", "герой", "легенда", "legend", "warrior"],
        "pendulum": 0.6,
        "energy": 0.95,
        "scale_hint": "Major Pentatonic",
    },
}


@dataclass
class SceneSegment:
    """A segment of script identified as a scene."""
    text: str
    scene_id: str
    start_line: int
    end_line: int
    heading: str = ""


class PulseScriptAnalyzer:
    """
    Analyzes script/brief text and extracts NarrativeBPM for each scene.

    Usage:
        analyzer = PulseScriptAnalyzer()
        scenes = analyzer.analyze("INT. DARK ALLEY - NIGHT\\nThe detective...")
        # → [NarrativeBPM(scene_id="sc_0", dramatic_function="Mystery", ...)]
    """

    def __init__(self):
        self._matrix = get_cinema_matrix()

    def analyze(self, text: str) -> List[NarrativeBPM]:
        """
        Analyze script text and return NarrativeBPM for each detected scene.

        Uses keyword heuristics (no LLM required).
        """
        segments = self._split_into_scenes(text)
        results = []

        for seg in segments:
            nbpm = self._analyze_segment(seg)
            results.append(nbpm)

        # Post-process: check pendulum oscillation
        results = self._enforce_pendulum_movement(results)

        return results

    def analyze_single(self, text: str, scene_id: str = "sc_0") -> NarrativeBPM:
        """Analyze a single scene description."""
        seg = SceneSegment(text=text, scene_id=scene_id, start_line=0, end_line=0)
        return self._analyze_segment(seg)

    # --- Private ---

    def _split_into_scenes(self, text: str) -> List[SceneSegment]:
        """Split script text into scene segments."""
        lines = text.strip().split("\n")
        segments: List[SceneSegment] = []
        current_lines: List[str] = []
        current_heading = ""
        start_line = 0

        # Scene heading patterns (screenwriting convention)
        scene_heading_re = re.compile(
            r"^(INT\.|EXT\.|ИНТ\.|НАТ\.|SCENE|СЦЕНА|#{1,3}\s|\d+\.\s)",
            re.IGNORECASE,
        )

        for i, line in enumerate(lines):
            if scene_heading_re.match(line.strip()) and current_lines:
                # Flush previous scene
                segments.append(SceneSegment(
                    text="\n".join(current_lines),
                    scene_id=f"sc_{len(segments)}",
                    start_line=start_line,
                    end_line=i - 1,
                    heading=current_heading,
                ))
                current_lines = [line]
                current_heading = line.strip()
                start_line = i
            else:
                if not current_lines and line.strip():
                    current_heading = line.strip()
                current_lines.append(line)

        # Flush last segment
        if current_lines:
            segments.append(SceneSegment(
                text="\n".join(current_lines),
                scene_id=f"sc_{len(segments)}",
                start_line=start_line,
                end_line=len(lines) - 1,
                heading=current_heading,
            ))

        # If no scenes detected, treat entire text as one scene
        if not segments:
            segments.append(SceneSegment(
                text=text,
                scene_id="sc_0",
                start_line=0,
                end_line=len(lines) - 1,
            ))

        return segments

    def _analyze_segment(self, seg: SceneSegment) -> NarrativeBPM:
        """Analyze a single scene segment using keyword matching."""
        text_lower = seg.text.lower()
        best_function = ""
        best_score = 0.0
        best_config: Dict[str, Any] = {}
        matched_keywords: List[str] = []

        for func_name, config in _FUNCTION_KEYWORDS.items():
            score = 0.0
            found_kw: List[str] = []
            for kw in config["keywords"]:
                if kw.lower() in text_lower:
                    score += 1.0
                    found_kw.append(kw)
            if score > best_score:
                best_score = score
                best_function = func_name
                best_config = config
                matched_keywords = found_kw

        if not best_function:
            # No keywords matched — return neutral
            return NarrativeBPM(
                scene_id=seg.scene_id,
                dramatic_function="Neutral",
                pendulum_position=0.0,
                estimated_energy=0.5,
                keywords=[],
                suggested_scale="Ionian",
                confidence=0.2,
            )

        # Confidence based on keyword density
        word_count = max(len(text_lower.split()), 1)
        keyword_density = min(best_score / word_count * 10, 1.0)
        confidence = min(0.3 + keyword_density * 0.5 + best_score * 0.1, 0.9)

        return NarrativeBPM(
            scene_id=seg.scene_id,
            dramatic_function=best_function.replace("_", " ").title(),
            pendulum_position=best_config.get("pendulum", 0.0),
            estimated_energy=best_config.get("energy", 0.5),
            keywords=matched_keywords,
            suggested_scale=best_config.get("scale_hint", ""),
            confidence=round(confidence, 3),
        )

    def _enforce_pendulum_movement(
        self, scenes: List[NarrativeBPM]
    ) -> List[NarrativeBPM]:
        """
        McKee's pendulum: scenes should oscillate between positive and negative.

        If 3+ consecutive scenes have same sign, reduce confidence
        to signal monotonous pacing.
        """
        if len(scenes) < 3:
            return scenes

        for i in range(2, len(scenes)):
            signs = [
                1 if scenes[j].pendulum_position >= 0 else -1
                for j in range(i - 2, i + 1)
            ]
            if signs[0] == signs[1] == signs[2]:
                # Three consecutive same-sign — reduce confidence
                scenes[i].confidence = max(scenes[i].confidence - 0.1, 0.1)

        return scenes


# Singleton
_analyzer_instance: Optional[PulseScriptAnalyzer] = None


def get_script_analyzer() -> PulseScriptAnalyzer:
    """Get or create singleton script analyzer."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = PulseScriptAnalyzer()
    return _analyzer_instance
