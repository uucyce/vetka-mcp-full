from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/media/build_myco_motion_assets.py")


def load_module():
    spec = importlib.util.spec_from_file_location("build_myco_motion_assets", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_default_specs_cover_expected_roles():
    module = load_module()
    specs = module.default_specs(Path("/tmp/fake_team_a"))
    roles = [(spec.role, spec.variant, spec.assembled) for spec in specs]
    assert ("architect", "primary", True) in roles
    assert ("coder", "coder1", False) in roles
    assert ("coder", "coder2", False) in roles
    assert ("researcher", "primary", False) in roles
    assert ("scout", "scout1", False) in roles
    assert ("scout", "scout2", False) in roles
    assert ("scout", "scout3", False) in roles
    assert ("verifier", "primary", False) in roles


def test_build_manifest_dry_run_uses_baseline_and_architect_master(tmp_path):
    module = load_module()
    source_dir = tmp_path / "team_A_mp4"
    source_dir.mkdir()
    output_root = tmp_path / "out"
    preset = {"mode": "luma", "fps": 8.0, "luma_threshold": 52.0, "alpha_blur": 0.8}

    manifest = module.build_manifest(source_dir, output_root, preset, dry_run=True)

    assert manifest["marker"] == "MARKER_168.MYCO.MOTION.BATCH_BUILD.V1"
    assert manifest["dry_run"] is True
    assert manifest["preset"] == preset
    assert manifest["architect_assembly"]["status"] == "planned"
    assert manifest["architect_assembly"]["output_mp4"].endswith("architect_master.mp4")
    assert len(manifest["assets"]) == 8

    architect = next(asset for asset in manifest["assets"] if asset["role"] == "architect")
    assert architect["assembled"] is True
    assert architect["source_mp4"].endswith("architect_master.mp4")
    assert architect["status"] == "planned"
