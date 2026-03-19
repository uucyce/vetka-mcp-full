#!/usr/bin/env python3
"""Build a visual acceptance pack that separates product truth from technical export readiness."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


DEFAULT_CHECKS = [
    {
        "id": "depth_truth_readable",
        "question": "Depth-first truth is readable and not a proxy/oval artifact.",
    },
    {
        "id": "export_preserves_depth_truth",
        "question": "Exported plate/depth artifacts preserve the same scene separation seen in depth-first preview.",
    },
    {
        "id": "parallax_planes_separable",
        "question": "Rendered result shows separable foreground, midground, and background motion.",
    },
    {
        "id": "no_oval_proxy_cutout",
        "question": "Rendered/exported result does not collapse into oval/focus cutout look.",
    },
    {
        "id": "no_flat_one_plane_motion",
        "question": "Rendered result does not look like a single flat image panning as one plane.",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build visual acceptance pack for parallax canonical outputs.")
    parser.add_argument(
        "--compare-summary",
        required=True,
        help="Path to render_compare_qwen_multiplate_summary.json",
    )
    parser.add_argument(
        "--render-summary",
        required=True,
        help="Path to render_preview_multiplate_summary.json",
    )
    parser.add_argument(
        "--review-root",
        required=True,
        help="Directory with depth/composite review artifacts",
    )
    parser.add_argument(
        "--export-root",
        required=True,
        help="Directory with exported plate assets",
    )
    parser.add_argument(
        "--outdir",
        required=True,
        help="Directory where visual acceptance files will be written",
    )
    parser.add_argument("--sample", action="append", dest="samples")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def maybe_path(path: Path) -> str | None:
    return str(path) if path.exists() else None


def collect_review_evidence(review_root: Path, sample_id: str) -> dict[str, str | None]:
    return {
        "depth_compare_path": maybe_path(review_root / f"{sample_id}-depth-compare.png"),
        "depth_raw_path": maybe_path(review_root / f"{sample_id}-depth-raw.png"),
        "depth_edited_path": maybe_path(review_root / f"{sample_id}-depth-edited.png"),
        "composite_compare_path": maybe_path(review_root / f"{sample_id}-composite-compare.png"),
        "composite_raw_path": maybe_path(review_root / f"{sample_id}-composite-raw.png"),
        "composite_edited_path": maybe_path(review_root / f"{sample_id}-composite-edited.png"),
    }


def collect_export_evidence(export_root: Path, sample_id: str) -> dict[str, str | None]:
    sample_root = export_root / sample_id
    manifest_path = sample_root / "plate_export_manifest.json"
    manifest = load_json(manifest_path) if manifest_path.exists() else {}

    exported_plates = manifest.get("exportedPlates") or []
    plate_files: list[dict[str, Any]] = []
    for plate in exported_plates:
        files = plate.get("files") or {}
        plate_files.append(
            {
                "id": plate.get("id"),
                "role": plate.get("role"),
                "coverage": plate.get("coverage"),
                "rgba_path": str(sample_root / files["rgba"]) if files.get("rgba") else None,
                "mask_path": str(sample_root / files["mask"]) if files.get("mask") else None,
                "depth_path": str(sample_root / files["depth"]) if files.get("depth") else None,
                "clean_path": str(sample_root / files["clean"]) if files.get("clean") else None,
            }
        )

    return {
        "manifest_path": maybe_path(manifest_path),
        "plate_layout_path": maybe_path(sample_root / "plate_layout.json"),
        "global_depth_path": maybe_path(sample_root / "global_depth_bw.png"),
        "background_rgba_path": maybe_path(sample_root / "background_rgba.png"),
        "background_mask_path": maybe_path(sample_root / "background_mask.png"),
        "export_depth_screenshot_path": maybe_path(sample_root / "plate_export_depth.png"),
        "export_composite_screenshot_path": maybe_path(sample_root / "plate_export_composite.png"),
        "readiness_path": maybe_path(sample_root / "plate_export_readiness_diagnostics.json"),
        "plates": plate_files,
    }


def build_entry(
    sample_id: str,
    compare_entry: dict[str, Any] | None,
    render_entry: dict[str, Any] | None,
    review_root: Path,
    export_root: Path,
) -> dict[str, Any]:
    return {
        "sample": sample_id,
        "status": "needs_review",
        "product_truth": {
            "source_of_truth": "depth-first preview",
            "checks": [
                {
                    **check,
                    "status": "needs_review",
                    "notes": "",
                }
                for check in DEFAULT_CHECKS
            ],
            "known_failure_patterns": [
                "oval-focus surrogate look",
                "flat one-plane motion",
                "missing foreground/mid/background separation",
            ],
        },
        "review_evidence": collect_review_evidence(review_root, sample_id),
        "export_evidence": collect_export_evidence(export_root, sample_id),
        "render_evidence": {
            "render_summary_entry": render_entry,
            "compare_summary_entry": compare_entry,
            "render_preview_path": render_entry.get("preview_path") if render_entry else None,
            "render_poster_path": render_entry.get("poster_path") if render_entry else None,
            "compare_sheet_path": compare_entry.get("sheet_path") if compare_entry else None,
            "compare_video_path": compare_entry.get("compare_video_path") if compare_entry else None,
        },
        "decision_rule": {
            "pass_requires": [
                "all checks marked pass",
                "no known failure pattern observed",
            ],
            "fail_if_any": [
                "oval-focus surrogate look is present",
                "render behaves like flat one-plane motion",
                "depth-first separation is not preserved in export/render",
            ],
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Parallax Visual Acceptance Checklist",
        "",
        f"Дата: `{payload['created_at']}`",
        "",
        "Правило:",
        "",
        "- `export works` и `batch pass` не означают product readiness;",
        "- source of truth здесь это `depth-first preview`;",
        "- negative checks: `oval-focus surrogate look`, `flat one-plane motion`, `missing separable foreground/mid/background`.",
        "",
    ]

    for entry in payload["entries"]:
        lines.extend(
            [
                f"## {entry['sample']}",
                "",
                f"- status: `{entry['status']}`",
                f"- review depth compare: `{entry['review_evidence']['depth_compare_path']}`",
                f"- review composite compare: `{entry['review_evidence']['composite_compare_path']}`",
                f"- export depth screenshot: `{entry['export_evidence']['export_depth_screenshot_path']}`",
                f"- export composite screenshot: `{entry['export_evidence']['export_composite_screenshot_path']}`",
                f"- render poster: `{entry['render_evidence']['render_poster_path']}`",
                f"- render video: `{entry['render_evidence']['render_preview_path']}`",
                f"- compare sheet: `{entry['render_evidence']['compare_sheet_path']}`",
                "",
                "Checks:",
                "",
            ]
        )
        for check in entry["product_truth"]["checks"]:
            lines.append(f"- [{ ' ' }] {check['id']}: {check['question']}")
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    compare_summary_path = Path(args.compare_summary).expanduser().resolve()
    render_summary_path = Path(args.render_summary).expanduser().resolve()
    review_root = Path(args.review_root).expanduser().resolve()
    export_root = Path(args.export_root).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    allowed = set(args.samples or [])

    compare_summary = load_json(compare_summary_path)
    render_summary = load_json(render_summary_path)
    compare_by_sample = {entry["sample"]: entry for entry in compare_summary.get("entries", [])}
    render_by_sample = {entry["sample"]: entry for entry in render_summary.get("entries", [])}
    sample_ids = sorted(set(compare_by_sample) | set(render_by_sample))
    if allowed:
        sample_ids = [sample_id for sample_id in sample_ids if sample_id in allowed]

    entries = [
        build_entry(
            sample_id=sample_id,
            compare_entry=compare_by_sample.get(sample_id),
            render_entry=render_by_sample.get(sample_id),
            review_root=review_root,
            export_root=export_root,
        )
        for sample_id in sample_ids
    ]

    payload = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "compare_summary_path": str(compare_summary_path),
        "render_summary_path": str(render_summary_path),
        "review_root": str(review_root),
        "export_root": str(export_root),
        "entries": entries,
        "count": len(entries),
        "overall_status": "needs_review" if entries else "empty",
    }

    json_path = outdir / "visual_acceptance_summary.json"
    md_path = outdir / "visual_acceptance_checklist.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    print(f"MARKER_180.PARALLAX.VISUAL_ACCEPTANCE.SUMMARY={json_path}")
    print(f"MARKER_180.PARALLAX.VISUAL_ACCEPTANCE.CHECKLIST={md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
