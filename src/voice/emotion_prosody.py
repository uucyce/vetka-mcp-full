"""
Local emotion -> prosody mapping for voice responses.

S6.4 goals:
- no LLM/token usage
- deterministic heuristic inference
- bounded/smoothed prosody changes between turns
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from typing import Dict, Any


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


_POSITIVE_WORDS = {
    "great", "awesome", "good", "nice", "perfect", "excellent", "thanks", "thank you",
    "хорошо", "отлично", "супер", "спасибо", "класс",
}
_NEGATIVE_WORDS = {
    "error", "fail", "failed", "problem", "bad", "wrong", "critical",
    "ошибка", "плохо", "проблема", "неверно", "критично",
}
_URGENT_WORDS = {
    "urgent", "asap", "now", "immediately", "critical", "blocker",
    "срочно", "немедленно", "быстро", "критично",
}
_HEDGE_WORDS = {
    "maybe", "perhaps", "probably", "i think", "might",
    "возможно", "кажется", "наверное", "может быть",
}
_POLITE_WORDS = {
    "please", "could you", "would you", "kindly",
    "пожалуйста", "будьте добры", "не могли бы",
}


@dataclass
class EmotionState:
    sentiment: float
    arousal: float
    urgency: float
    confidence: float
    politeness: float


@dataclass
class ProsodyState:
    speed: float
    pitch: int
    energy: float
    pause_profile: str


_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
_LATIN_RE = re.compile(r"[A-Za-z]")
_URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
_CODE_RE = re.compile(r"`{1,3}|<[^>]+>|[{()}\\[\\]]")


def _score_by_lexicon(text_lc: str, lexicon: set[str]) -> float:
    if not text_lc.strip():
        return 0.0
    hits = 0
    for word in lexicon:
        if word in text_lc:
            hits += 1
    return hits / max(1.0, len(text_lc.split()) * 0.35)


def infer_emotion_state(text: str) -> EmotionState:
    t = (text or "").strip()
    tl = t.lower()

    pos = _score_by_lexicon(tl, _POSITIVE_WORDS)
    neg = _score_by_lexicon(tl, _NEGATIVE_WORDS)
    urgent = _score_by_lexicon(tl, _URGENT_WORDS)
    hedge = _score_by_lexicon(tl, _HEDGE_WORDS)
    polite = _score_by_lexicon(tl, _POLITE_WORDS)

    exclaims = t.count("!")
    questions = t.count("?")
    caps_ratio = 0.0
    letters = [c for c in t if c.isalpha()]
    if letters:
        caps_ratio = sum(1 for c in letters if c.isupper()) / len(letters)

    arousal = _clamp(0.28 + urgent * 0.8 + exclaims * 0.05 + caps_ratio * 0.55, 0.08, 0.98)
    urgency = _clamp(0.16 + urgent * 0.95 + exclaims * 0.06 + questions * 0.02, 0.05, 0.99)
    sentiment = _clamp(0.5 + pos * 0.8 - neg * 1.0, 0.02, 0.98)
    confidence = _clamp(0.64 + (1.0 - hedge) * 0.22 - questions * 0.02, 0.05, 0.98)
    politeness = _clamp(0.3 + polite * 0.95, 0.05, 0.98)

    return EmotionState(
        sentiment=round(sentiment, 4),
        arousal=round(arousal, 4),
        urgency=round(urgency, 4),
        confidence=round(confidence, 4),
        politeness=round(politeness, 4),
    )


def map_emotion_to_prosody(emotion: EmotionState) -> ProsodyState:
    speed = 0.9 + (emotion.urgency * 0.22) + (emotion.arousal * 0.12) - (emotion.politeness * 0.07)
    pitch = int(round(-1.0 + (emotion.arousal - 0.5) * 4.5 + (emotion.sentiment - 0.5) * 2.0))
    energy = 0.38 + emotion.arousal * 0.43 + emotion.urgency * 0.16

    speed = _clamp(speed, 0.85, 1.18)
    pitch = int(max(-3, min(3, pitch)))
    energy = _clamp(energy, 0.32, 0.94)

    if emotion.urgency >= 0.72:
        pause_profile = "short"
    elif emotion.politeness >= 0.66 and emotion.arousal < 0.45:
        pause_profile = "calm"
    else:
        pause_profile = "balanced"

    return ProsodyState(
        speed=round(speed, 3),
        pitch=pitch,
        energy=round(energy, 3),
        pause_profile=pause_profile,
    )


def smooth_prosody(current: ProsodyState, previous: ProsodyState | None) -> ProsodyState:
    if previous is None:
        return current

    alpha = 0.35
    max_delta_speed = 0.08
    max_delta_pitch = 1
    max_delta_energy = 0.12

    blended_speed = previous.speed + (current.speed - previous.speed) * alpha
    blended_energy = previous.energy + (current.energy - previous.energy) * alpha
    blended_pitch_raw = previous.pitch + (current.pitch - previous.pitch) * alpha
    blended_pitch = int(round(blended_pitch_raw))

    speed_delta = _clamp(blended_speed - previous.speed, -max_delta_speed, max_delta_speed)
    energy_delta = _clamp(blended_energy - previous.energy, -max_delta_energy, max_delta_energy)
    pitch_delta = int(max(-max_delta_pitch, min(max_delta_pitch, blended_pitch - previous.pitch)))

    return ProsodyState(
        speed=round(previous.speed + speed_delta, 3),
        pitch=int(previous.pitch + pitch_delta),
        energy=round(previous.energy + energy_delta, 3),
        pause_profile=current.pause_profile if current.pause_profile == previous.pause_profile else "balanced",
    )


def _is_stability_sensitive_text(text: str) -> bool:
    """Detect text patterns where aggressive post-prosody often degrades Qwen quality."""
    t = (text or "").strip()
    if not t:
        return False
    if len(t) >= 280:
        return True
    if _URL_RE.search(t) or _CODE_RE.search(t):
        return True
    has_cyr = bool(_CYRILLIC_RE.search(t))
    has_lat = bool(_LATIN_RE.search(t))
    if has_cyr and has_lat:
        return True
    return False


def _stability_guard(prosody: ProsodyState, text: str) -> ProsodyState:
    """
    Keep prosody in a conservative band to avoid warbling/crying artifacts and truncation.
    """
    if _is_stability_sensitive_text(text):
        return ProsodyState(speed=1.0, pitch=0, energy=0.55, pause_profile="balanced")

    guarded_speed = _clamp(float(prosody.speed), 0.94, 1.06)
    guarded_pitch = int(max(-1, min(1, int(prosody.pitch))))
    guarded_energy = _clamp(float(prosody.energy), 0.45, 0.72)
    guarded_pause = prosody.pause_profile if prosody.pause_profile in {"balanced", "calm"} else "balanced"
    return ProsodyState(
        speed=round(guarded_speed, 3),
        pitch=guarded_pitch,
        energy=round(guarded_energy, 3),
        pause_profile=guarded_pause,
    )


def infer_and_map_prosody(
    text: str,
    previous_prosody: Dict[str, Any] | None = None,
) -> Dict[str, Dict[str, Any]]:
    emotion = infer_emotion_state(text)
    mapped = map_emotion_to_prosody(emotion)
    prev = None
    if isinstance(previous_prosody, dict):
        try:
            prev = ProsodyState(
                speed=float(previous_prosody.get("speed", 1.0)),
                pitch=int(previous_prosody.get("pitch", 0)),
                energy=float(previous_prosody.get("energy", 0.5)),
                pause_profile=str(previous_prosody.get("pause_profile", "balanced")),
            )
        except Exception:
            prev = None
    smooth = smooth_prosody(mapped, prev)
    guarded = _stability_guard(smooth, text)
    return {
        "emotion": asdict(emotion),
        "prosody": asdict(guarded),
    }
