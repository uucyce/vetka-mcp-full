#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import io
import json
import re
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")
PLAYGROUND = ROOT / "photo_parallax_playground"
SAMPLES_DIR = PLAYGROUND / "public" / "samples"
PLATE_EXPORT_ROOT = PLAYGROUND / "output" / "plate_exports"
PUBLIC_OUT_DIR = PLAYGROUND / "public" / "qwen_plate_plans"
OUTPUT_DIR = PLAYGROUND / "output" / "qwen_plate_plans"
OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen2.5vl:3b"

ALLOWED_ROLES = {
    "foreground-subject",
    "secondary-subject",
    "environment-mid",
    "background-far",
    "special-clean",
}


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "plate"


def normalize_clean_variant(value: str | None) -> str | None:
    if not value:
        return None
    return slugify(value)


def normalize_target_key(value: str | None) -> str | None:
    if not value:
        return None
    return slugify(value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="append", dest="samples", default=[])
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout", type=int, default=180)
    return parser.parse_args()


def load_samples() -> list[dict[str, Any]]:
    return json.loads((SAMPLES_DIR / "manifest.json").read_text(encoding="utf-8"))["samples"]


def encode_image(path: Path, max_side: int = 1280) -> str:
    image = Image.open(path).convert("RGB")
    if max(image.size) > max_side:
        image.thumbnail((max_side, max_side))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=92)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


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


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def sanitize_box(raw: dict[str, Any] | None) -> dict[str, float]:
    raw = raw or {}
    try:
        x = clamp(float(raw.get("x", 0.02)), 0.0, 1.0)
        y = clamp(float(raw.get("y", 0.02)), 0.0, 1.0)
        width = clamp(float(raw.get("width", 0.4)), 0.02, 1.0)
        height = clamp(float(raw.get("height", 0.4)), 0.02, 1.0)
    except (TypeError, ValueError):
        x, y, width, height = 0.02, 0.02, 0.4, 0.4
    width = min(width, 1.0 - x)
    height = min(height, 1.0 - y)
    area = width * height
    if area < 0.015:
        width = max(width, 0.18)
        height = max(height, 0.18)
        width = min(width, 1.0 - x)
        height = min(height, 1.0 - y)
    return {
        "x": round(x, 4),
        "y": round(y, 4),
        "width": round(width, 4),
        "height": round(height, 4),
    }


def build_prompt(sample: dict[str, Any], current_plate_stack: dict[str, Any]) -> str:
    return f"""
Analyze a still image and its black-and-white depth map for a 2.5D parallax tool.
Depth convention: white = closer, black = farther.

You are helping create a multi-plate decomposition like an experienced After Effects compositor.

Scene:
- sample_id: {sample["id"]}
- title: {sample["title"]}
- scenario: {sample["scenario"]}
- notes: {sample["notes"]}

Current plate stack draft:
{json.dumps(current_plate_stack, ensure_ascii=False)}

Goal:
- propose the optimal multi-plate decomposition for a 2.5D parallax shot
- keep semantically linked objects together
- avoid naive left/right splits
- suggest special clean plates like no-people, no-vehicle, no-hands when useful

Return ONLY valid JSON.

Schema:
{{
  "scene_summary": "string",
  "recommended_plate_count": 0,
  "plates": [
    {{
      "name": "string",
      "role": "foreground-subject | secondary-subject | environment-mid | background-far | special-clean",
      "depth_order": 1,
      "objects": ["string"],
      "reason": "string",
      "box": {{"x": 0.0, "y": 0.0, "width": 0.0, "height": 0.0}},
      "needs_clean_plate": false,
      "suggested_clean_variant": null
    }}
  ],
  "special_clean_plates": [
    {{
      "name": "string",
      "target_plate": "string",
      "reason": "string"
    }}
  ],
  "notes": ["string"],
  "confidence": 0.0
}}

Rules:
- prefer 3 to 5 plates unless the scene clearly needs more
- boxes must be coarse semantic groups, not pixel-accurate masks
- no full-frame foreground boxes
- at most 6 normal plates and 3 special clean plates
- special-clean plates should usually not have their own visible box
- if uncertain, still return your best structured proposal
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
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def build_plate_stack_proposal(sample_id: str, sanitized: dict[str, Any]) -> dict[str, Any]:
    normal_plates = [plate for plate in sanitized["plates"] if plate["role"] != "special-clean"]
    special_clean = sanitized["special_clean_plates"]
    total_depth = max(1, len(normal_plates))
    proposal = []
    for index, plate in enumerate(normal_plates, start=1):
        depth_rank = total_depth - (index - 1)
        z = 28 - (index - 1) * 16
        depth_priority = clamp(0.88 - (index - 1) * 0.18, 0.08, 0.92)
        proposal.append(
            {
                "id": f"plate_{index:02d}",
                "label": plate["name"],
                "role": plate["role"],
                "source": "qwen-plan",
                **plate["box"],
                "z": round(z, 2),
                "depthPriority": round(depth_priority, 3),
                "visible": plate["role"] != "special-clean",
                "depthOrder": depth_rank,
                "cleanVariant": normalize_clean_variant(plate.get("suggested_clean_variant")),
            }
        )

    proposal_by_id = {plate["id"]: plate for plate in proposal}
    proposal_by_label = {normalize_target_key(plate["label"]): plate for plate in proposal}
    deduped_special_clean = []
    seen_special_keys: set[str] = set()
    for clean in special_clean:
        clean_variant = normalize_clean_variant(clean.get("name"))
        target_raw = clean.get("target_plate")
        target_plate = None
        if target_raw and target_raw in proposal_by_id:
            target_plate = target_raw
        else:
            target_plate = proposal_by_label.get(normalize_target_key(target_raw) or "", {}).get("id")
        dedupe_key = f"{target_plate or 'none'}::{clean_variant or 'none'}"
        if dedupe_key in seen_special_keys:
            continue
        seen_special_keys.add(dedupe_key)
        deduped_special_clean.append(
            {
                "name": clean.get("name"),
                "cleanVariant": clean_variant,
                "targetPlate": target_plate,
                "reason": clean.get("reason", ""),
            }
        )
        if target_plate and clean_variant and target_plate in proposal_by_id:
            proposal_by_id[target_plate]["cleanVariant"] = clean_variant

    if deduped_special_clean:
        for plate in proposal:
            plate["cleanVariant"] = None
        for clean in deduped_special_clean:
            target_plate = clean.get("targetPlate")
            clean_variant = clean.get("cleanVariant")
            if target_plate and clean_variant and target_plate in proposal_by_id:
                proposal_by_id[target_plate]["cleanVariant"] = clean_variant

    base_index = len(proposal) + 1
    for offset, clean in enumerate(deduped_special_clean, start=0):
        proposal.append(
            {
                "id": f"plate_{base_index + offset:02d}",
                "label": clean["name"],
                "role": "special-clean",
                "source": "qwen-plan",
                "x": 0.02,
                "y": 0.02,
                "width": 0.96,
                "height": 0.96,
                "z": -30 - offset * 4,
                "depthPriority": 0.08,
                "visible": False,
                "depthOrder": 99,
                "cleanVariant": clean["cleanVariant"],
                "targetPlate": clean.get("targetPlate"),
            }
        )

    return {"sampleId": sample_id, "plates": proposal}


def sanitize_plan(sample: dict[str, Any], parsed: dict[str, Any], current_plate_stack: dict[str, Any]) -> dict[str, Any]:
    plates = []
    for index, raw in enumerate(list(parsed.get("plates") or [])[:6], start=1):
        role = str(raw.get("role", "environment-mid")).strip()
        if role not in ALLOWED_ROLES:
            role = "environment-mid"
        name = str(raw.get("name", f"plate {index}")).strip() or f"plate {index}"
        depth_order = index
        try:
            depth_order = max(1, min(8, int(raw.get("depth_order", index))))
        except (TypeError, ValueError):
            depth_order = index
        objects = [str(item).strip() for item in list(raw.get("objects") or [])[:6] if str(item).strip()]
        plates.append(
            {
                "id": f"proposal_plate_{index:02d}",
                "name": name,
                "role": role,
                "depth_order": depth_order,
                "objects": objects,
                "reason": str(raw.get("reason", "")).strip(),
                "box": sanitize_box(raw.get("box")),
                "needs_clean_plate": bool(raw.get("needs_clean_plate", False)),
                "suggested_clean_variant": normalize_clean_variant(str(raw.get("suggested_clean_variant")).strip()) if raw.get("suggested_clean_variant") else None,
            }
        )
    if not plates:
        plates = [
            {
                "id": "proposal_plate_01",
                "name": current_plate_stack["plates"][0]["label"],
                "role": current_plate_stack["plates"][0]["role"],
                "depth_order": 1,
                "objects": [current_plate_stack["plates"][0]["label"]],
                "reason": "Fallback to the current lead plate because Qwen returned no usable plate list.",
                "box": sanitize_box(current_plate_stack["plates"][0]),
                "needs_clean_plate": False,
                "suggested_clean_variant": normalize_clean_variant(current_plate_stack["plates"][0].get("cleanVariant")),
            }
        ]

    special_clean: list[dict[str, Any]] = []
    seen_special_clean: set[str] = set()
    for index, raw in enumerate(list(parsed.get("special_clean_plates") or [])[:3], start=1):
        name = str(raw.get("name", f"special_clean_{index}")).strip() or f"special_clean_{index}"
        clean_variant = normalize_clean_variant(name)
        target_plate = str(raw.get("target_plate", "")).strip() or None
        dedupe_key = f"{normalize_target_key(target_plate) or 'none'}::{clean_variant or 'none'}"
        if dedupe_key in seen_special_clean:
            continue
        seen_special_clean.add(dedupe_key)
        special_clean.append(
            {
                "name": name,
                "target_plate": target_plate,
                "clean_variant": clean_variant,
                "reason": str(raw.get("reason", "")).strip(),
            }
        )

    if not special_clean:
        normal_plate_names = {normalize_target_key(plate["name"]) for plate in plates if plate["role"] != "special-clean"}
        for plate in plates:
            if plate["role"] != "special-clean":
                continue
            clean_variant = plate.get("suggested_clean_variant") or normalize_clean_variant(plate["name"])
            target_plate = None
            for obj in plate.get("objects", []):
                if normalize_target_key(obj) in normal_plate_names:
                    target_plate = obj
                    break
            dedupe_key = f"{normalize_target_key(target_plate) or 'none'}::{clean_variant or 'none'}"
            if dedupe_key in seen_special_clean:
                continue
            seen_special_clean.add(dedupe_key)
            special_clean.append(
                {
                    "name": plate["name"],
                    "target_plate": target_plate,
                    "clean_variant": clean_variant,
                    "reason": plate["reason"],
                }
            )

    recommended_plate_count = max(2, min(6, int(parsed.get("recommended_plate_count", len(plates)))))
    confidence = clamp(float(parsed.get("confidence", 0.5)), 0.0, 1.0)
    notes = [str(item).strip() for item in list(parsed.get("notes") or [])[:8] if str(item).strip()]

    sanitized = {
        "sample_id": sample["id"],
        "title": sample["title"],
        "model": DEFAULT_MODEL,
        "scene_summary": str(parsed.get("scene_summary", "")).strip(),
        "recommended_plate_count": recommended_plate_count,
        "plates": sorted(plates, key=lambda item: item["depth_order"]),
        "special_clean_plates": special_clean,
        "notes": notes,
        "confidence": round(confidence, 3),
    }
    sanitized["plate_stack_proposal"] = build_plate_stack_proposal(sample["id"], sanitized)
    return sanitized


def main() -> int:
    args = parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_OUT_DIR.mkdir(parents=True, exist_ok=True)

    requested = set(args.samples)
    entries = []
    for sample in load_samples():
        if requested and sample["id"] not in requested:
            continue
        export_dir = PLATE_EXPORT_ROOT / sample["id"]
        if not export_dir.exists():
            continue
        depth_path = export_dir / "global_depth_bw.png"
        plate_stack_path = export_dir / "plate_stack.json"
        if not depth_path.exists() or not plate_stack_path.exists():
            continue
        current_plate_stack = json.loads(plate_stack_path.read_text(encoding="utf-8"))
        prompt = build_prompt(sample, current_plate_stack)
        source_path = SAMPLES_DIR / sample["file_name"]

        raw_text = ""
        error = None
        parsed = None
        image_batches = [
            [encode_image(source_path, max_side=1280), encode_image(depth_path, max_side=1280)],
            [encode_image(source_path, max_side=1024)],
        ]
        for images in image_batches:
            try:
                payload = run_ollama_request(args.model, prompt, images, args.timeout)
                raw_text = payload.get("response", "")
                parsed = json.loads(strip_json_fence(raw_text))
                break
            except Exception as exc:  # noqa: BLE001
                error = str(exc)
                parsed = None
        if parsed is None:
            result = {
                "sample_id": sample["id"],
                "title": sample["title"],
                "model": args.model,
                "scene_summary": "",
                "recommended_plate_count": 0,
                "plates": [],
                "special_clean_plates": [],
                "notes": [],
                "confidence": 0.0,
                "error": error,
                "plate_stack_proposal": current_plate_stack,
            }
        else:
            result = sanitize_plan(sample, parsed, current_plate_stack)
            result["raw_response"] = raw_text
            result["error"] = None

        out_path = OUTPUT_DIR / f"{sample['id']}.json"
        public_path = PUBLIC_OUT_DIR / f"{sample['id']}.json"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        public_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        entries.append(
            {
                "sample_id": sample["id"],
                "title": sample["title"],
                "path": f"/qwen_plate_plans/{sample['id']}.json",
                "recommended_plate_count": result["recommended_plate_count"],
                "confidence": result["confidence"],
                "error": result.get("error"),
            }
        )

    manifest = {"model": args.model, "plans": entries}
    (OUTPUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (PUBLIC_OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
