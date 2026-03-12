#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


DEFAULT_SANDBOX_NAME = "VETKA_CUT_SANDBOX"


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def bootstrap_sandbox(sandbox_root: Path, manifest_src: Path, source_root: Path) -> None:
    sandbox_root.mkdir(parents=True, exist_ok=True)

    dirs = [
        sandbox_root / "core_mirror",
        sandbox_root / "cut_runtime" / "configs",
        sandbox_root / "cut_runtime" / "jobs",
        sandbox_root / "cut_runtime" / "logs",
        sandbox_root / "cut_runtime" / "cache",
        sandbox_root / "cut_runtime" / "preview_cache",
        sandbox_root / "cut_storage" / "imports",
        sandbox_root / "cut_storage" / "artifacts",
        sandbox_root / "cut_storage" / "exports",
        sandbox_root / "cut_storage" / "temp",
        sandbox_root / "docs",
        sandbox_root / "reports",
        sandbox_root / "config",
    ]
    for item in dirs:
        item.mkdir(parents=True, exist_ok=True)

    manifest_dst = sandbox_root / "config" / "cut_core_mirror_manifest.json"
    if not manifest_dst.exists():
        manifest_dst.write_text(manifest_src.read_text(encoding="utf-8"), encoding="utf-8")

    env_example = "\n".join([
        f"VETKA_CUT_SANDBOX_ROOT={sandbox_root}",
        f"VETKA_CUT_CORE_MIRROR_ROOT={sandbox_root / 'core_mirror'}",
        f"VETKA_CUT_RUNTIME_ROOT={sandbox_root / 'cut_runtime'}",
        f"VETKA_CUT_STORAGE_ROOT={sandbox_root / 'cut_storage'}",
        "VETKA_CUT_QDRANT_PREFIX=cut_dev",
        "VETKA_CUT_PROFILE=dev",
        "VETKA_CUT_API_PORT=8837",
        "VETKA_CUT_MCP_PORT=8838",
        "VETKA_CUT_WORKER_PORT=8839",
        ""
    ])
    _write_text(sandbox_root / "config" / "cut.env.example", env_example)

    metadata = {
        "schema_version": "cut_sandbox_bootstrap_v1",
        "sandbox_root": str(sandbox_root),
        "source_root": str(source_root),
        "manifest": str(manifest_dst),
        "core_mirror_root": str(sandbox_root / "core_mirror"),
    }
    _write_text(
        sandbox_root / "config" / "cut_sandbox_bootstrap.json",
        json.dumps(metadata, indent=2, ensure_ascii=True) + "\n",
    )

    readme = "\n".join([
        "# VETKA CUT Sandbox",
        "",
        "This sandbox is a standalone bootstrap area for VETKA CUT.",
        "",
        "Layout:",
        "- core_mirror/: mirrored upstream VETKA core files",
        "- cut_runtime/: CUT runtime configs, logs, jobs, cache",
        "- cut_storage/: imports, artifacts, exports, temp",
        "- config/: local env example + mirror manifest",
        "",
        "Recommended next step:",
        f"python3 {source_root / 'scripts' / 'cut' / 'sync_cut_core_mirror.py'} --source-root {source_root} --sandbox-root {sandbox_root}",
        ""
    ])
    _write_text(sandbox_root / "README.md", readme)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap a standalone VETKA CUT sandbox.")
    parser.add_argument("--sandbox-root", type=Path, default=Path.home() / "Documents" / DEFAULT_SANDBOX_NAME)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "config" / "cut" / "cut_core_mirror_manifest.example.json",
    )
    args = parser.parse_args()

    bootstrap_sandbox(args.sandbox_root.resolve(), args.manifest.resolve(), args.source_root.resolve())
    print(f"[MARKER_170.SANDBOX.CREATE] Bootstrapped sandbox at {args.sandbox_root.resolve()}")
    print(f"[MARKER_170.SANDBOX.ENV_ISOLATION] Wrote config/cut.env.example")
    print(f"[MARKER_170.SANDBOX.CORE_MIRROR_MANIFEST] Wrote config/cut_core_mirror_manifest.json")
    print(f"[MARKER_170.SANDBOX.STORAGE_NAMESPACE] Created isolated runtime/storage directories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
