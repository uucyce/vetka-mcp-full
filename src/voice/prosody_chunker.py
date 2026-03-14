from __future__ import annotations

import re
from typing import List, Tuple

_SPACE_RE = re.compile(r"\s+")
_SENTENCE_BOUNDARY_RE = re.compile(r"[.!?…]+(?:[\"')\]]+)?\s+")
_CLAUSE_BOUNDARY_RE = re.compile(r"[,;:—–-]\s+")


def _normalize(text: str) -> str:
    return _SPACE_RE.sub(" ", (text or "").strip())


def _word_count(text: str) -> int:
    return len(text.split())


def _cut_by_words(text: str, max_words: int) -> tuple[str, str]:
    words = text.split()
    if len(words) <= max_words:
        return text.strip(), ""
    head = " ".join(words[:max_words]).strip()
    tail = " ".join(words[max_words:]).strip()
    return head, tail


def extract_ready_chunks(
    buffer_text: str,
    *,
    min_words: int = 8,
    min_chars: int = 48,
    max_words: int = 16,
) -> Tuple[List[str], str]:
    """
    Split stream buffer into prosody-safe chunks.

    Priority:
    1) sentence boundaries (. ! ? …)
    2) clause boundaries (, ; : —)
    3) emergency cut by whole words (never by syllables/chars)
    """
    text = _normalize(buffer_text)
    if not text:
        return [], ""

    out: list[str] = []
    remaining = text

    while remaining:
        sent = [(m.end(), 2) for m in _SENTENCE_BOUNDARY_RE.finditer(remaining)]
        clause = [(m.end(), 1) for m in _CLAUSE_BOUNDARY_RE.finditer(remaining)]
        boundaries = sorted(sent + clause, key=lambda x: x[0])

        chosen_idx: int | None = None
        oversized_idx: int | None = None

        for idx, prio in boundaries:
            candidate = remaining[:idx].strip()
            words = _word_count(candidate)
            # Sentence-ending punctuation can be emitted with softer thresholds
            # to avoid waiting too long on short natural phrases.
            local_min_words = 2 if prio >= 2 else max(3, min_words)
            local_min_chars = 8 if prio >= 2 else max(24, min_chars)
            if words < local_min_words or len(candidate) < local_min_chars:
                continue
            if words <= max(max_words, min_words):
                chosen_idx = idx
                break
            if oversized_idx is None:
                oversized_idx = idx

        if chosen_idx is None and oversized_idx is not None:
            chosen_idx = oversized_idx

        if chosen_idx is not None:
            chunk = remaining[:chosen_idx].strip()
            remaining = remaining[chosen_idx:].strip()
            if chunk:
                out.append(chunk)
            continue

        words_total = _word_count(remaining)
        if words_total >= max(3, min_words) and len(remaining) >= max(24, min_chars):
            chunk, tail = _cut_by_words(remaining, max(3, min_words))
            if chunk:
                out.append(chunk)
            remaining = tail
            continue

        break

    return out, remaining
