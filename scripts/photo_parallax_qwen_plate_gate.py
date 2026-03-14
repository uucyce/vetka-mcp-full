#!/usr/bin/env python3
"""Gate Qwen plate proposals into keep/enrich/replace decisions."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from photo_parallax_subject_plate_bakeoff import save_json


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")
PLAYGROUND = ROOT / "photo_parallax_playground"
MANUAL_EXPORT_ROOT = PLAYGROUND / "output" / "plate_exports"
QWEN_EXPORT_ROOT = PLAYGROUND / "output" / "plate_exports_qwen"
QWEN_PLAN_ROOT = PLAYGROUND / "output" / "qwen_plate_plans"
OUT_ROOT = PLAYGROUND / "output" / "qwen_plate_gates"
PUBLIC_ROOT = PLAYGROUND / "public" / "qwen_plate_gates"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="append", dest="samples", default=[])
    parser.add_argument("--manual-export-root", default=str(MANUAL_EXPORT_ROOT))
    parser.add_argument("--qwen-export-root", default=str(QWEN_EXPORT_ROOT))
    parser.add_argument("--qwen-plan-root", default=str(QWEN_PLAN_ROOT))
    parser.add_argument("--outdir", default=str(OUT_ROOT))
    parser.add_argument("--public-outdir", default=str(PUBLIC_ROOT))
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def slugify(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def is_visible_renderable(plate: dict[str, Any]) -> bool:
    return bool(plate.get("visible")) and plate.get("role") != "special-clean"


def is_special_clean(plate: dict[str, Any]) -> bool:
    return plate.get("role") == "special-clean"


def next_plate_id(plates: list[dict[str, Any]]) -> str:
    highest = 0
    for plate in plates:
        match = re.match(r"plate_(\d+)$", str(plate.get("id", "")))
        if match:
            highest = max(highest, int(match.group(1)))
    return f"plate_{highest + 1:02d}"


def build_enriched_stack(
    manual_stack: dict[str, Any],
    qwen_stack: dict[str, Any],
) -> dict[str, Any]:
    manual_plates = [dict(plate) for plate in manual_stack["plates"]]
    manual_visible_by_slug = {
        slugify(plate["label"]): plate
        for plate in manual_plates
        if is_visible_renderable(plate)
    }
    manual_clean_variants = {
        slugify(plate.get("cleanVariant"))
        for plate in manual_plates
        if is_special_clean(plate) and plate.get("cleanVariant")
    }
    qwen_visible_by_id = {
        plate["id"]: plate
        for plate in qwen_stack["plates"]
        if is_visible_renderable(plate)
    }
    qwen_special = [plate for plate in qwen_stack["plates"] if is_special_clean(plate)]

    for qplate in qwen_stack["plates"]:
        if not is_visible_renderable(qplate):
            continue
        target = manual_visible_by_slug.get(slugify(qplate["label"]))
        clean_variant = qplate.get("cleanVariant")
        if target and clean_variant and not target.get("cleanVariant"):
            target["cleanVariant"] = clean_variant

    for clean in qwen_special:
        clean_variant = slugify(clean.get("cleanVariant"))
        if not clean_variant or clean_variant in manual_clean_variants:
            continue
        qwen_target = qwen_visible_by_id.get(clean.get("targetPlate"))
        if not qwen_target:
            continue
        manual_target = manual_visible_by_slug.get(slugify(qwen_target.get("label")))
        if not manual_target:
            continue
        if not manual_target.get("cleanVariant"):
            manual_target["cleanVariant"] = clean.get("cleanVariant")
        new_plate = dict(clean)
        new_plate["id"] = next_plate_id(manual_plates)
        new_plate["targetPlate"] = manual_target["id"]
        new_plate["visible"] = False
        manual_plates.append(new_plate)
        manual_clean_variants.add(clean_variant)

    return {"sampleId": manual_stack["sampleId"], "plates": manual_plates}


def gate_case(sample_id: str, manual_stack: dict[str, Any], qwen_stack: dict[str, Any], qwen_plan: dict[str, Any]) -> dict[str, Any]:
    manual_visible = [plate for plate in manual_stack["plates"] if is_visible_renderable(plate)]
    qwen_visible = [plate for plate in qwen_stack["plates"] if is_visible_renderable(plate)]
    manual_special = [plate for plate in manual_stack["plates"] if is_special_clean(plate)]
    qwen_special = [plate for plate in qwen_stack["plates"] if is_special_clean(plate)]

    manual_visible_slugs = {slugify(plate["label"]) for plate in manual_visible}
    qwen_visible_slugs = {slugify(plate["label"]) for plate in qwen_visible}
    visible_overlap = sorted(manual_visible_slugs & qwen_visible_slugs)
    overlap_ratio = len(visible_overlap) / max(1, min(len(manual_visible_slugs), len(qwen_visible_slugs)))

    manual_special_variants = {slugify(plate.get("cleanVariant")) for plate in manual_special if plate.get("cleanVariant")}
    qwen_special_variants = {slugify(plate.get("cleanVariant")) for plate in qwen_special if plate.get("cleanVariant")}
    added_special_variants = sorted(variant for variant in qwen_special_variants if variant and variant not in manual_special_variants)

    confidence = float(qwen_plan.get("confidence", 0.0) or 0.0)
    reasons: list[str] = []
    decision = "keep-current-stack"

    if confidence < 0.6:
        decision = "keep-current-stack"
        reasons.append("Qwen confidence is below the safe threshold for structural changes.")
    elif added_special_variants and overlap_ratio >= 0.67:
        decision = "enrich-current-stack"
        reasons.append("Qwen preserves the visible scene structure and adds useful special-clean variants.")
    elif len(qwen_visible) > len(manual_visible) and overlap_ratio >= 0.75 and confidence >= 0.85:
        decision = "replace-current-stack"
        reasons.append("Qwen proposes a richer visible stack with high confidence and strong semantic overlap.")
    else:
        decision = "keep-current-stack"
        reasons.append("Qwen does not add enough reliable structure beyond the current manual/default stack.")

    if decision == "replace-current-stack":
        gated_stack = qwen_stack
    elif decision == "enrich-current-stack":
        gated_stack = build_enriched_stack(manual_stack, qwen_stack)
    else:
        gated_stack = manual_stack

    return {
        "sample_id": sample_id,
        "decision": decision,
        "confidence": round(confidence, 3),
        "metrics": {
            "manual_visible_count": len(manual_visible),
            "qwen_visible_count": len(qwen_visible),
            "manual_special_clean_count": len(manual_special),
            "qwen_special_clean_count": len(qwen_special),
            "visible_overlap_ratio": round(overlap_ratio, 3),
        },
        "added_special_clean_variants": added_special_variants,
        "visible_overlap_labels": visible_overlap,
        "reasons": reasons,
        "gated_plate_stack": gated_stack,
    }


def main() -> int:
    args = parse_args()
    manual_root = Path(args.manual_export_root)
    qwen_root = Path(args.qwen_export_root)
    qwen_plan_root = Path(args.qwen_plan_root)
    outdir = Path(args.outdir)
    public_outdir = Path(args.public_outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    public_outdir.mkdir(parents=True, exist_ok=True)

    requested = set(args.samples)
    sample_ids = sorted(
        sample_dir.name for sample_dir in qwen_root.iterdir() if sample_dir.is_dir() and (not requested or sample_dir.name in requested)
    )

    entries: list[dict[str, Any]] = []
    for sample_id in sample_ids:
        manual_stack_path = manual_root / sample_id / "plate_stack.json"
        qwen_stack_path = qwen_root / sample_id / "plate_stack.json"
        qwen_plan_path = qwen_plan_root / f"{sample_id}.json"
        if not manual_stack_path.exists() or not qwen_stack_path.exists() or not qwen_plan_path.exists():
            continue
        manual_stack = load_json(manual_stack_path)
        qwen_stack = load_json(qwen_stack_path)
        qwen_plan = load_json(qwen_plan_path)
        result = gate_case(sample_id, manual_stack, qwen_stack, qwen_plan)
        result["created_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        save_json(outdir / f"{sample_id}.json", result)
        save_json(public_outdir / f"{sample_id}.json", result)
        entries.append(
            {
                "sample_id": sample_id,
                "decision": result["decision"],
                "confidence": result["confidence"],
                "added_special_clean_variants": result["added_special_clean_variants"],
                "path": f"/qwen_plate_gates/{sample_id}.json",
            }
        )

    manifest = {"created_at": dt.datetime.now(dt.timezone.utc).isoformat(), "entries": entries}
    save_json(outdir / "manifest.json", manifest)
    save_json(public_outdir / "manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
