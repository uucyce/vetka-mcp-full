#!/usr/bin/env python3
"""Copy selected research fixtures into the photo parallax playground."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")
TARGET_DIR = ROOT / "photo_parallax_playground" / "public" / "samples"

SAMPLES = [
    {
        "id": "cassette-closeup",
        "file_name": "cassette-closeup.png",
        "source": Path("/Users/danilagulin/work/teletape_temp/berlin/Img_gen_unsorted/1801260f-b8a4-4fd2-aef3-5e2c1e7ba28b.png"),
        "title": "Cassette close-up",
        "scenario": "large foreground object, soft background lights",
        "notes": "Good for disocclusion checks around hands and transparent cassette edges.",
    },
    {
        "id": "keyboard-hands",
        "file_name": "keyboard-hands.png",
        "source": Path("/Users/danilagulin/work/teletape_temp/berlin/Img_gen_unsorted/2f2ecd1d-c8a4-4059-9e30-49e0efbcdf02.png"),
        "title": "Keyboard hands",
        "scenario": "multi-depth mid-shot with fingers, keyboard, monitors",
        "notes": "Useful for layer split and mask edge tests with multiple near surfaces.",
    },
    {
        "id": "hover-politsia",
        "file_name": "hover-politsia.jpg",
        "source": Path("/Users/danilagulin/work/teletape_temp/berlin/Img_gen_unsorted/fe7b0bc2-6d14-41af-aa99-27608110108a.jpg"),
        "title": "Hover Politsia street",
        "scenario": "wide scene with separate foreground actors and deep background",
        "notes": "Good for background plate and overscan planning.",
    },
    {
        "id": "drone-portrait",
        "file_name": "drone-portrait.webp",
        "source": Path("/Users/danilagulin/work/teletape_temp/berlin/Img_gen_unsorted/max_flux1_claud1.webp"),
        "title": "Drone portrait",
        "scenario": "portrait with strong subject isolation and bokeh",
        "notes": "Good for foreground/background separation and safe camera travel presets.",
    },
    {
        "id": "punk-rooftop",
        "file_name": "punk-rooftop.png",
        "source": Path("/Users/danilagulin/work/teletape_temp/berlin/Img_gen_unsorted/005fd181-71cf-4683-8592-ebf8b6cfb3c7.png"),
        "title": "Punk rooftop",
        "scenario": "single seated figure on rooftop with deep urban background",
        "notes": "Good for foreground human grouping against a complex wide city backdrop.",
    },
    {
        "id": "truck-driver",
        "file_name": "truck-driver.png",
        "source": Path("/Users/danilagulin/work/teletape_temp/berlin/Img_gen_unsorted/00e88d67-3670-401a-adfb-88a9ffa0f192.png"),
        "title": "Truck driver",
        "scenario": "subject inside a vehicle cabin framed by window geometry",
        "notes": "Good for testing object grouping inside hard frame boundaries.",
    },
]


def main() -> int:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []

    for sample in SAMPLES:
        src = sample["source"]
        dst = TARGET_DIR / sample["file_name"]
        shutil.copy2(src, dst)
        completed = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "json",
                str(dst),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        stream = json.loads(completed.stdout)["streams"][0]
        width = int(stream["width"])
        height = int(stream["height"])
        manifest.append(
            {
                "id": sample["id"],
                "title": sample["title"],
                "file_name": sample["file_name"],
                "width": width,
                "height": height,
                "scenario": sample["scenario"],
                "notes": sample["notes"],
            }
        )

    (TARGET_DIR / "manifest.json").write_text(
        json.dumps({"samples": manifest}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(manifest)} samples to {TARGET_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
