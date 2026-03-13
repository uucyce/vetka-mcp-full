#!/usr/bin/env python3
"""
Seed a small MCC project fixture and print a browser URL that opens MCC
with the seeded project activated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any
from urllib import error, parse, request


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "mcc" / "fixtures" / "playwright_mcc_graph_repo"
DEFAULT_API_BASE = "http://127.0.0.1:5001/api/mcc"
DEFAULT_BROWSER_BASE = "http://127.0.0.1:3002/"
FIXTURE_NAME = "mcc_playwright_graph_fixture"


def _get_json(url: str) -> dict[str, Any]:
    with request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _find_existing_project(api_base: str, fixture_path: str) -> str:
    payload = _get_json(f"{api_base}/projects/list")
    for row in payload.get("projects") or []:
        if str((row or {}).get("source_path", "")) == fixture_path:
            return str((row or {}).get("project_id", "")).strip()
    return ""


def _activate_project(api_base: str, project_id: str) -> None:
    _post_json(f"{api_base}/projects/activate", {"project_id": project_id})


def _create_fixture_project(api_base: str, fixture_path: str) -> str:
    sandbox_name = f"mcc_playwright_fixture_{hashlib.sha1(fixture_path.encode('utf-8')).hexdigest()[:8]}"
    sandbox_path = str(Path(tempfile.gettempdir()) / sandbox_name)
    payload = _post_json(
        f"{api_base}/project/init",
        {
            "source_type": "local",
            "source_path": fixture_path,
            "sandbox_path": sandbox_path,
            "quota_gb": 1,
            "project_name": FIXTURE_NAME,
        },
    )
    if not payload.get("success"):
        raise RuntimeError(f"fixture project init failed: {payload}")
    return str(payload.get("project_id", "")).strip()


def seed_fixture(api_base: str, fixture_path: str) -> str:
    project_id = _find_existing_project(api_base, fixture_path)
    if project_id:
        _activate_project(api_base, project_id)
        return project_id
    return _create_fixture_project(api_base, fixture_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--browser-base", default=DEFAULT_BROWSER_BASE)
    parser.add_argument("--fixture-path", default=str(FIXTURE_ROOT))
    args = parser.parse_args()

    fixture_path = str(Path(args.fixture_path).resolve())
    if not Path(fixture_path).is_dir():
        raise SystemExit(f"fixture path not found: {fixture_path}")

    try:
        project_id = seed_fixture(args.api_base.rstrip("/"), fixture_path)
    except error.URLError as exc:
        raise SystemExit(f"failed to reach MCC backend: {exc}") from exc

    params = parse.urlencode({"project_id": project_id})
    browser_url = f"{args.browser_base.rstrip('/')}/?{params}"
    print(
        json.dumps(
            {
                "project_id": project_id,
                "fixture_path": fixture_path,
                "browser_url": browser_url,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
