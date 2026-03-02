"""
Canonical Qwen voice catalog and normalization helpers.
"""

from __future__ import annotations

import re
from typing import Optional

QWEN_VOICE_POOL = [
    "serena",
    "vivian",
    "uncle_fu",
    "ryan",
    "aiden",
    "ono_anna",
    "sohee",
    "eric",
    "dylan",
]

QWEN_LEGACY_ALIASES = {
    "alloy": "eric",
    "echo": "aiden",
    "fable": "uncle_fu",
    "onyx": "dylan",
    "nova": "vivian",
    "sage": "serena",
    "verse": "dylan",
}

_VOICE_SET = set(QWEN_VOICE_POOL)


def normalize_qwen_voice_id(voice_id: Optional[str], default: str = "ryan") -> str:
    """
    Normalize external voice id to canonical Qwen voice id.
    Unknown ids map deterministically to known pool.
    """
    raw = (voice_id or "").strip()
    if not raw:
        return default

    normalized = re.sub(r"[\s\-]+", "_", raw.lower())
    normalized = QWEN_LEGACY_ALIASES.get(normalized, normalized)
    if normalized in _VOICE_SET:
        return normalized
    return QWEN_VOICE_POOL[hash(normalized) % len(QWEN_VOICE_POOL)]
