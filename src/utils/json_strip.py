"""
GEMMA-211: JSON Strip Helper for Gemma 4 Markdown Wrap Fix
===========================================================

Gemma 4 wraps JSON responses in markdown code blocks:
    ```json
    {"priority": 1, ...}
    ```

This module provides extraction utilities.
Benchmark proven: strict prompt gives 9.5x speedup (6.9s → 0.73s).

@file json_strip.py
@status active
@phase 211
@used_by model_router.py, llm_call_tool.py
"""

import json
import re
from typing import Any, Dict, Optional, Tuple


# Strict prompt for Gemma 4 — proven 9.5x speedup in benchmark
STRICT_JSON_PROMPT = (
    "Return ONLY valid JSON. No markdown, no code blocks, no explanation. "
    "Start your response with { and end with }."
)


def extract_json(response: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from LLM response, handling Gemma 4 markdown wrap.

    Strategy (in order):
    1. Try direct json.loads (works for clean responses)
    2. Strip ```json ... ``` markdown blocks
    3. Find first { and last } in response
    4. Return None if all fail

    Args:
        response: Raw LLM response string

    Returns:
        Parsed dict or None if extraction fails
    """
    if not response or not response.strip():
        return None

    text = response.strip()

    # Strategy 1: Direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 2: Strip markdown code blocks
    # Matches: ```json {...} ``` or ``` {...} ```
    md_pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
    md_match = re.search(md_pattern, text, re.DOTALL)
    if md_match:
        try:
            return json.loads(md_match.group(1).strip())
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 3: Find first { and last }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_str = text[first_brace : last_brace + 1]
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 4: Try line-by-line for multi-line JSON without braces wrap
    # (rare edge case: model outputs JSON lines)
    lines = text.split("\n")
    json_lines = []
    in_json = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("{"):
            in_json = True
        if in_json:
            json_lines.append(stripped)
        if in_json and stripped.endswith("}"):
            break

    if json_lines:
        try:
            return json.loads("\n".join(json_lines))
        except (json.JSONDecodeError, ValueError):
            pass

    return None


def extract_json_or_raise(response: str) -> Dict[str, Any]:
    """
    Same as extract_json but raises ValueError on failure.

    Args:
        response: Raw LLM response string

    Returns:
        Parsed dict

    Raises:
        ValueError: If JSON cannot be extracted
    """
    result = extract_json(response)
    if result is None:
        raise ValueError(f"Failed to extract JSON from response: {response[:200]}...")
    return result


def validate_json_schema(
    data: Dict[str, Any], required_fields: list
) -> Tuple[bool, str]:
    """
    Validate extracted JSON has required fields.

    Args:
        data: Parsed JSON dict
        required_fields: List of field names that must be present

    Returns:
        (is_valid, error_message)
    """
    missing = [f for f in required_fields if f not in data]
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"
    return True, ""


def gemma_json_response(prompt: str, model: str = "gemma4:e4b") -> str:
    """
    Build a prompt with strict JSON instructions for Gemma 4.

    This is the proven fix: appending STRICT_JSON_PROMPT reduces
    response time from 6.9s to 0.73s (9.5x speedup).

    Args:
        prompt: User's actual prompt
        model: Target model (default: gemma4:e4b)

    Returns:
        Full prompt with strict JSON instructions appended
    """
    return f"{prompt}\n\n{STRICT_JSON_PROMPT}"
