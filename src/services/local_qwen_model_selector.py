"""
Local Ollama Qwen selector helpers.

MARKER_177.REFLEX.LOCAL_QWEN_SELECTOR.V1

Provides a stable way to inspect local Ollama models and choose the
strongest available text-oriented Qwen family model for tool-capable tasks.
Uses the Ollama HTTP API instead of `ollama list`, which can be unstable on
some local MLX/Metal setups.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List
from urllib.request import urlopen


OLLAMA_URL = "http://127.0.0.1:11434"


def fetch_ollama_models(ollama_url: str = OLLAMA_URL, timeout: float = 3.0) -> List[Dict[str, Any]]:
    """Fetch local Ollama tags from the HTTP API."""
    target = f"{str(ollama_url).rstrip('/')}/api/tags"
    with urlopen(target, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    rows = payload.get("models", []) if isinstance(payload, dict) else []
    return [row for row in rows if isinstance(row, dict)]


def choose_best_local_qwen(models: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Pick the strongest local Qwen model for general tool-capable local use."""
    candidates: List[Dict[str, Any]] = []
    for row in models:
        name = str(row.get("name") or row.get("model") or "").strip()
        lowered = name.lower()
        if "qwen" not in lowered:
            continue
        if "tts" in lowered or "embed" in lowered:
            continue

        details = row.get("details") if isinstance(row.get("details"), dict) else {}
        family = str(details.get("family", "")).lower()
        parameter_size = _parse_parameter_billions(str(details.get("parameter_size", "")) or name)
        score = _score_qwen_candidate(name=lowered, family=family, parameter_size=parameter_size)

        candidates.append(
            {
                "name": name,
                "family": family,
                "parameter_size_b": parameter_size,
                "quantization": str(details.get("quantization_level", "")),
                "score": round(score, 4),
                "reason": _describe_candidate(name=lowered, family=family, parameter_size=parameter_size),
            }
        )

    candidates.sort(key=lambda row: (row["score"], row["parameter_size_b"], row["name"]), reverse=True)
    best = candidates[0] if candidates else None
    return {
        "best_model": best["name"] if best else "",
        "best": best,
        "candidates": candidates,
        "count": len(candidates),
    }


def get_best_local_qwen_model(ollama_url: str = OLLAMA_URL, timeout: float = 3.0) -> Dict[str, Any]:
    """Fetch local Ollama models and return the strongest available Qwen choice."""
    models = fetch_ollama_models(ollama_url=ollama_url, timeout=timeout)
    selection = choose_best_local_qwen(models)
    selection["ollama_url"] = ollama_url
    selection["total_models"] = len(models)
    return selection


def _score_qwen_candidate(name: str, family: str, parameter_size: float) -> float:
    generation_score = 0.0
    if "qwen3.5" in name or family == "qwen35":
        generation_score = 4.0
    elif "qwen3" in name or family == "qwen3":
        generation_score = 3.0
    elif "qwen2.5" in name or family == "qwen25vl" or "qwen25" in family:
        generation_score = 2.0
    elif "qwen2" in name or family == "qwen2":
        generation_score = 1.0

    vision_penalty = 0.75 if "vl" in name or "vl" in family else 0.0
    latest_bonus = 0.05 if ":latest" in name else 0.0
    return generation_score + parameter_size - vision_penalty + latest_bonus


def _describe_candidate(name: str, family: str, parameter_size: float) -> str:
    segments = []
    if family:
        segments.append(f"family={family}")
    if parameter_size > 0:
        segments.append(f"params={parameter_size:.1f}B")
    if "vl" in name or "vl" in family:
        segments.append("vision_penalty")
    return ", ".join(segments) if segments else "qwen_candidate"


def _parse_parameter_billions(raw_value: str) -> float:
    value = str(raw_value or "").strip().upper()
    if not value:
        return _parse_size_from_name(raw_value)
    if value.endswith("B"):
        try:
            return float(value[:-1])
        except ValueError:
            return 0.0
    if value.endswith("M"):
        try:
            return float(value[:-1]) / 1000.0
        except ValueError:
            return 0.0
    return _parse_size_from_name(raw_value)


def _parse_size_from_name(raw_value: str) -> float:
    text = str(raw_value or "").lower()
    for token in text.replace("-", ":").split(":"):
        if token.endswith("b"):
            try:
                return float(token[:-1])
            except ValueError:
                continue
    return 0.0
