#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def _load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_paths(manifest: dict, groups: list[str] | None) -> list[tuple[str, str]]:
    selected = []
    requested = set(groups or [])
    for group in manifest.get("groups", []):
        name = str(group.get("name", "")).strip()
        if requested and name not in requested:
            continue
        for rel in group.get("paths", []):
            selected.append((name, str(rel)))
    return selected


def sync_core_mirror(source_root: Path, sandbox_root: Path, manifest_path: Path, groups: list[str] | None, dry_run: bool) -> int:
    manifest = _load_manifest(manifest_path)
    mirror_root = sandbox_root / "core_mirror"
    mirror_root.mkdir(parents=True, exist_ok=True)

    copied = 0
    missing = 0
    for group_name, rel_path in _iter_paths(manifest, groups):
        src = source_root / rel_path
        dst = mirror_root / rel_path
        if not src.exists():
            missing += 1
            print(f"[WARN] missing source ({group_name}): {src}")
            continue
        print(f"[SYNC] {group_name}: {src} -> {dst}")
        if dry_run:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1

    print(f"[MARKER_170.SANDBOX.SYNC_SCRIPT] copied={copied} missing={missing} dry_run={dry_run}")
    return 0 if missing == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync mirrored VETKA core files into a CUT sandbox.")
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--sandbox-root", type=Path, required=True)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Defaults to <sandbox-root>/config/cut_core_mirror_manifest.json if present, else repo example manifest.",
    )
    parser.add_argument("--group", action="append", dest="groups", help="Optional manifest group(s) to sync.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned copies without writing files.")
    args = parser.parse_args()

    sandbox_root = args.sandbox_root.resolve()
    default_manifest = sandbox_root / "config" / "cut_core_mirror_manifest.json"
    fallback_manifest = Path(__file__).resolve().parents[2] / "config" / "cut" / "cut_core_mirror_manifest.example.json"
    manifest_path = (args.manifest.resolve() if args.manifest else (default_manifest if default_manifest.exists() else fallback_manifest))

    return sync_core_mirror(
        source_root=args.source_root.resolve(),
        sandbox_root=sandbox_root,
        manifest_path=manifest_path,
        groups=args.groups,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
