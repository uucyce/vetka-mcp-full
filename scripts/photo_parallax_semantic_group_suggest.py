#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")
PLAYGROUND = ROOT / "photo_parallax_playground"
SAMPLES_DIR = PLAYGROUND / "public" / "samples"
HINTS_DIR = PLAYGROUND / "public" / "sample_hints"
PUBLIC_OUT_DIR = PLAYGROUND / "public" / "ai_assist_suggestions"
OUTPUT_DIR = PLAYGROUND / "output" / "ai_assist_suggestions"
OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen2.5vl:3b"


DEFAULT_FOCUS = {
    "cassette-closeup": {"x": 0.5, "y": 0.51, "width": 0.48, "height": 0.56, "feather": 0.16},
    "keyboard-hands": {"x": 0.51, "y": 0.58, "width": 0.6, "height": 0.52, "feather": 0.18},
    "drone-portrait": {"x": 0.5, "y": 0.44, "width": 0.42, "height": 0.72, "feather": 0.18},
    "hover-politsia": {"x": 0.53, "y": 0.46, "width": 0.46, "height": 0.48, "feather": 0.14},
}


@dataclass
class Sample:
    id: str
    title: str
    file_name: str
    width: int
    height: int
    scenario: str
    notes: str


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="append", dest="samples", default=[])
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout", type=int, default=180)
    return parser.parse_args()


def load_samples() -> list[Sample]:
    manifest = json.loads((SAMPLES_DIR / "manifest.json").read_text())
    return [Sample(**item) for item in manifest["samples"]]


def encode_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def strip_json_fence(text: str) -> str:
    stripped = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, re.DOTALL)
    if match:
        return match.group(1).strip()
    first = stripped.find("{")
    last = stripped.rfind("}")
    if first >= 0 and last > first:
        return stripped[first : last + 1]
    return stripped


def expand_focus_box(sample_id: str, scale_x: float = 1.18, scale_y: float = 1.14) -> dict[str, float]:
    focus = DEFAULT_FOCUS[sample_id]
    width = clamp(focus["width"] * scale_x, 0.16, 0.88)
    height = clamp(focus["height"] * scale_y, 0.18, 0.9)
    x = clamp(focus["x"] - width / 2, 0.0, 1.0 - width)
    y = clamp(focus["y"] - height / 2, 0.0, 1.0 - height)
    return {
        "x": round(x, 4),
        "y": round(y, 4),
        "width": round(width, 4),
        "height": round(height, 4),
    }


def sanitize_box(raw: dict[str, Any]) -> dict[str, Any] | None:
    try:
        x = clamp(float(raw.get("x", 0)), 0.0, 1.0)
        y = clamp(float(raw.get("y", 0)), 0.0, 1.0)
        width = clamp(float(raw.get("width", 0)), 0.0, 1.0)
        height = clamp(float(raw.get("height", 0)), 0.0, 1.0)
    except (TypeError, ValueError):
        return None

    width = min(width, 1.0 - x)
    height = min(height, 1.0 - y)
    area = width * height
    if width < 0.06 or height < 0.06 or area < 0.015:
        return None
    if width > 0.92 or height > 0.92 or area > 0.72:
        return None
    if area > 0.18 and ((x < 0.02 and y < 0.02) or (x + width > 0.98 and y < 0.02) or (x < 0.02 and y + height > 0.98) or (x + width > 0.98 and y + height > 0.98)):
        return None
    return {
        "label": str(raw.get("label", "group")).strip() or "group",
        "x": round(x, 4),
        "y": round(y, 4),
        "width": round(width, 4),
        "height": round(height, 4),
        "reason": str(raw.get("reason", "")).strip(),
        "area": round(area, 4),
    }




def intersection_over_union(a: dict[str, Any], b: dict[str, Any]) -> float:
    left = max(a["x"], b["x"])
    top = max(a["y"], b["y"])
    right = min(a["x"] + a["width"], b["x"] + b["width"])
    bottom = min(a["y"] + a["height"], b["y"] + b["height"])
    if right <= left or bottom <= top:
        return 0.0
    intersection = (right - left) * (bottom - top)
    union = a["area"] + b["area"] - intersection
    if union <= 0:
        return 0.0
    return intersection / union

def fallback_foreground(sample: Sample, reasons: list[str]) -> list[dict[str, Any]]:
    box = expand_focus_box(sample.id)
    reasons.append("fallback_focus_box")
    return [
        {
            "label": "focus fallback",
            **box,
            "reason": "Safe fallback around the default focus region because the model response was missing or too broad.",
            "area": round(box["width"] * box["height"], 4),
        }
    ]


def build_prompt(sample: Sample) -> str:
    focus = DEFAULT_FOCUS[sample.id]
    return f"""
You analyze a single still image for a 2.5D parallax tool.
Return ONLY valid JSON.

Image 1 is the source photo.
Image 2 is a color hint overlay for the same photo:
- red means likely closer / foreground
- blue means likely farther
- green means protect detail

Scene id: {sample.id}
Title: {sample.title}
Scenario: {sample.scenario}
Notes: {sample.notes}
Default focus guess: {json.dumps(focus)}

Goal:
- detect semantic groups that should stay together in one layer
- avoid wrong left/right depth splits
- prefer one shared foreground box when hands hold one object

Schema:
{{
  "scene_summary": "short string",
  "primary_subject": "short string",
  "foreground_groups": [
    {{"label": "string", "x": 0.0, "y": 0.0, "width": 0.0, "height": 0.0, "reason": "string"}}
  ],
  "midground_groups": [
    {{"label": "string", "x": 0.0, "y": 0.0, "width": 0.0, "height": 0.0, "reason": "string"}}
  ],
  "background_note": "short string",
  "warnings": ["string"]
}}

Rules:
- coordinates normalized 0..1
- use coarse boxes around whole semantic groups, not tiny details
- no full-frame boxes
- if uncertain, return an empty array instead of a giant box
- max 2 foreground_groups and max 2 midground_groups
- no markdown
""".strip()


def run_ollama_request(model: str, prompt: str, images: list[str], timeout: int) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "images": images,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 1200,
        },
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def call_ollama(model: str, sample: Sample, timeout: int) -> dict[str, Any]:
    sample_path = SAMPLES_DIR / sample.file_name
    hint_path = HINTS_DIR / f"{sample.id}.png"
    prompt = build_prompt(sample)
    image_payloads = [
        [encode_image(sample_path), encode_image(hint_path)],
        [encode_image(sample_path)],
    ]
    last_error = None
    for images in image_payloads:
        body = run_ollama_request(model, prompt, images, timeout)
        raw_text = body.get("response", "")
        cleaned = strip_json_fence(raw_text)
        if not cleaned:
            last_error = ValueError("Empty response")
            continue
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
        parsed["_raw_response"] = raw_text
        parsed["_image_count"] = len(images)
        return parsed
    if last_error:
        raise last_error
    raise ValueError("No response from model")


def build_result(model: str, sample: Sample, parsed: dict[str, Any] | None, error: str | None) -> dict[str, Any]:
    sanitation_flags: list[str] = []
    accepted_fg: list[dict[str, Any]] = []
    accepted_mid: list[dict[str, Any]] = []
    raw_fg = []
    raw_mid = []
    if parsed:
        raw_fg = list(parsed.get("foreground_groups") or [])
        raw_mid = list(parsed.get("midground_groups") or [])
        for item in raw_fg[:2]:
            box = sanitize_box(item)
            if box:
                accepted_fg.append(box)
            else:
                sanitation_flags.append("rejected_fg_box")
        for item in raw_mid[:2]:
            box = sanitize_box(item)
            if box:
                accepted_mid.append(box)
            else:
                sanitation_flags.append("rejected_mid_box")

    if not accepted_fg:
        accepted_fg = fallback_foreground(sample, sanitation_flags)

    deduped_mid: list[dict[str, Any]] = []
    for candidate in accepted_mid:
        if any(intersection_over_union(candidate, fg) > 0.68 for fg in accepted_fg):
            sanitation_flags.append("rejected_mid_overlap_fg")
            continue
        deduped_mid.append(candidate)
    accepted_mid = deduped_mid

    if not accepted_mid and sample.id in {"keyboard-hands", "hover-politsia"}:
        focus_box = expand_focus_box(sample.id, 1.28, 1.24)
        mid_width = clamp(focus_box["width"] * 0.9, 0.1, 0.9)
        mid_height = clamp(focus_box["height"] * 0.42, 0.08, 0.7)
        accepted_mid = [
            {
                "label": "midground fallback",
                "x": round(clamp(focus_box["x"] - 0.05, 0.0, 1.0), 4),
                "y": round(clamp(focus_box["y"] + focus_box["height"] * 0.55, 0.0, 1.0), 4),
                "width": round(mid_width, 4),
                "height": round(mid_height, 4),
                "reason": "Fallback midground band derived from focus region for layered layouts.",
                "area": round(mid_width * mid_height, 4),
            }
        ]
        sanitation_flags.append("fallback_midground_box")

    confidence = 0.42
    if parsed and not error:
        confidence += 0.18
    if accepted_fg:
        confidence += 0.16
    if accepted_mid:
        confidence += 0.1
    confidence -= min(0.22, 0.06 * len(sanitation_flags))
    confidence = round(clamp(confidence, 0.1, 0.92), 3)

    return {
        "sample_id": sample.id,
        "title": sample.title,
        "model": model,
        "scene_summary": (parsed or {}).get("scene_summary", ""),
        "primary_subject": (parsed or {}).get("primary_subject", ""),
        "background_note": (parsed or {}).get("background_note", ""),
        "warnings": list((parsed or {}).get("warnings") or []),
        "accepted_foreground_groups": accepted_fg,
        "accepted_midground_groups": accepted_mid,
        "raw_foreground_groups": raw_fg,
        "raw_midground_groups": raw_mid,
        "sanitation_flags": sanitation_flags,
        "confidence": confidence,
        "error": error,
        "raw_response": (parsed or {}).get("_raw_response", ""),
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    args = parse_args()
    samples = load_samples()
    selected = {sample.id for sample in samples if not args.samples or sample.id in args.samples}
    if not selected:
        print("No samples selected", file=sys.stderr)
        return 1

    PUBLIC_OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, Any]] = []
    for sample in samples:
        if sample.id not in selected:
            continue
        parsed = None
        error = None
        try:
            parsed = call_ollama(args.model, sample, args.timeout)
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        result = build_result(args.model, sample, parsed, error)
        write_json(PUBLIC_OUT_DIR / f"{sample.id}.json", result)
        write_json(OUTPUT_DIR / f"{sample.id}.json", result)
        manifest.append(
            {
                "sample_id": sample.id,
                "title": sample.title,
                "path": f"/ai_assist_suggestions/{sample.id}.json",
                "confidence": result["confidence"],
                "flags": result["sanitation_flags"],
                "error": result["error"],
            }
        )
        print(f"AI assist: {sample.id} confidence={result['confidence']} flags={','.join(result['sanitation_flags']) or 'none'}")

    write_json(PUBLIC_OUT_DIR / "manifest.json", {"model": args.model, "suggestions": manifest})
    write_json(OUTPUT_DIR / "manifest.json", {"model": args.model, "suggestions": manifest})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
