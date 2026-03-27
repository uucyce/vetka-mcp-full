"""
CUT project sandbox fixture for store-level and API tests.

Replaces the duplicated sandbox creation in test_cut_multi_timeline_store.py,
phase173/test_cut_undo_redo.py, and ~30 phase170 bootstrap tests.

Usage as pytest fixture (via conftest or direct import):
    from tests.fixtures.cut_sandbox import create_sandbox

    def test_something(tmp_path):
        sandbox = create_sandbox(tmp_path)
        # sandbox has .cut_config/cut_project.json + cut_runtime/state/

Or as a pytest fixture (register in conftest.py):
    @pytest.fixture
    def sandbox(tmp_path):
        return create_sandbox(tmp_path)
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional


def create_sandbox(
    base_path: Path,
    project_id: str = "test-project",
    source_path: str = "/tmp/cut/source.mov",
    display_name: Optional[str] = None,
    extra_config: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Create a minimal CUT project sandbox directory structure.

    Creates:
        base_path/
        ├── .cut_config/
        │   └── cut_project.json    (cut_project_v1 schema)
        └── cut_runtime/
            └── state/              (empty, for timeline state files)

    Args:
        base_path: Root directory for the sandbox (typically tmp_path).
        project_id: Project identifier written to config.
        source_path: Source media path written to config.
        display_name: Human-readable name. Defaults to "Test <project_id>".
        extra_config: Additional fields merged into cut_project.json.

    Returns:
        base_path (same as input, for chaining).
    """
    # Create directory structure
    config_dir = base_path / ".cut_config"
    config_dir.mkdir(parents=True, exist_ok=True)

    state_dir = base_path / "cut_runtime" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    # Write project config
    config = {
        "schema_version": "cut_project_v1",
        "project_id": project_id,
        "display_name": display_name or f"Test {project_id}",
        "source_path": source_path,
        "sandbox_root": str(base_path),
        "state": "ready",
        "created_at": time.time(),
    }
    if extra_config:
        config.update(extra_config)

    config_file = config_dir / "cut_project.json"
    config_file.write_text(json.dumps(config, indent=2))

    return base_path


def create_sandbox_with_timeline(
    base_path: Path,
    timeline_state: Dict[str, Any],
    project_id: str = "test-project",
    **sandbox_kwargs: Any,
) -> Path:
    """
    Create sandbox and pre-populate it with a timeline state file.

    Args:
        base_path: Root directory for the sandbox.
        timeline_state: A cut_timeline_state_v1 dict
                        (use cut_timeline_factory.make_timeline_state).
        project_id: Project identifier.
        **sandbox_kwargs: Passed to create_sandbox().

    Returns:
        base_path.
    """
    sandbox = create_sandbox(base_path, project_id=project_id, **sandbox_kwargs)

    state_dir = sandbox / "cut_runtime" / "state"
    timeline_id = timeline_state.get("timeline_id", "main")
    state_file = state_dir / f"{timeline_id}.json"
    state_file.write_text(json.dumps(timeline_state, indent=2))

    return sandbox
