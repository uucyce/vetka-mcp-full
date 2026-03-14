"""
MARKER_180.21: project.vetka-cut.json Schema — defines the CUT project file format.

Architecture doc §10:
"Every CUT project saves to project.vetka-cut.json:
 - Project metadata (name, version, created_at)
 - Timeline versions (array of {id, label, version, mode, parentId})
 - Panel layout (dock positions, grid sizes, floating positions)
 - PULSE settings (triangle position, active scale, BPM config)
 - Marker bundle reference
 - Asset manifest"

This module provides:
1. Pydantic models for validation
2. Default schema factory
3. Load/save helpers
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("vetka_cut.schema")

# ─── Schema version ───
SCHEMA_VERSION = "vetka-cut-project-v1"


# ─── Sub-models ───

class TimelineVersionEntry(BaseModel):
    """One timeline version in the project."""
    id: str
    label: str
    version: int = 0
    mode: str = "manual"           # favorites | script | music | manual
    parent_id: Optional[str] = None
    created_at: float = 0.0        # epoch seconds
    clip_count: int = 0


class PanelLayoutConfig(BaseModel):
    """Saved panel layout state."""
    left_width: int = 220
    right_width: int = 280
    bottom_height: int = 180
    right_split: float = 0.5       # 0-1, split between source_monitor and inspector
    # Floating panels
    floating_panels: List[Dict[str, Any]] = Field(default_factory=list)
    # Tab state: which panels share left column
    left_tabs: List[str] = Field(default_factory=lambda: ["script", "dag_project"])
    active_left_tab: str = "script"


class PulseConfig(BaseModel):
    """PULSE analysis configuration for the project."""
    # McKee triangle position
    triangle_arch: float = 0.5
    triangle_mini: float = 0.3
    triangle_anti: float = 0.2
    # Active scale
    active_scale: str = ""         # e.g. "standard_drama"
    # BPM config
    sync_tolerance_sec: float = 0.083  # ±2 frames at 24fps
    # Camelot
    reference_key: str = ""        # project's reference Camelot key


class AssetEntry(BaseModel):
    """One asset in the project manifest."""
    asset_id: str
    source_path: str
    media_type: str = "unknown"    # video | audio | image | subtitle
    duration_sec: float = 0.0
    camelot_key: str = ""
    energy: float = 0.5
    cluster: str = "other"         # character | location | take | dub | music | sfx | graphics | other


# ─── Main project schema ───

class VetkaCutProject(BaseModel):
    """
    Complete VETKA CUT project file schema.
    Saved as project.vetka-cut.json in the project sandbox.
    """
    schema_version: str = SCHEMA_VERSION
    project_name: str = "untitled"
    project_id: str = ""
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    # Timeline versions (§7.1: NEVER overwrite, always new)
    timelines: List[TimelineVersionEntry] = Field(
        default_factory=lambda: [
            TimelineVersionEntry(id="main", label="Main", version=0, mode="manual")
        ]
    )
    active_timeline_id: str = "main"
    next_version: int = 1

    # Panel layout
    layout: PanelLayoutConfig = Field(default_factory=PanelLayoutConfig)

    # PULSE settings
    pulse: PulseConfig = Field(default_factory=PulseConfig)

    # Asset manifest
    assets: List[AssetEntry] = Field(default_factory=list)

    # Marker bundle reference (path relative to sandbox)
    marker_bundle_path: str = "markers/time_marker_bundle.json"

    # Metadata
    description: str = ""
    tags: List[str] = Field(default_factory=list)


# ─── Factory ───

def create_default_project(name: str = "untitled", project_id: str = "") -> VetkaCutProject:
    """Create a new project with sensible defaults."""
    return VetkaCutProject(
        project_name=name,
        project_id=project_id or f"cut_{int(time.time())}",
    )


# ─── Load / Save ───

def load_project(path: str | Path) -> VetkaCutProject:
    """Load project from JSON file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Project file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return VetkaCutProject(**data)


def save_project(project: VetkaCutProject, path: str | Path) -> None:
    """Save project to JSON file."""
    path = Path(path)
    project.updated_at = time.time()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        project.model_dump_json(indent=2),
        encoding="utf-8",
    )
    logger.info(f"Saved project to {path}")


# ─── Convenience: add timeline version ───

def add_timeline_version(
    project: VetkaCutProject,
    mode: str = "manual",
    parent_id: str | None = None,
) -> TimelineVersionEntry:
    """
    Add a new timeline version. NEVER overwrites (§7.1 safety).
    Returns the new entry.
    """
    version = project.next_version
    version_str = str(version).zfill(2)
    label = f"{project.project_name}_cut-{version_str}"
    entry = TimelineVersionEntry(
        id=f"tl_{label}_{int(time.time())}",
        label=label,
        version=version,
        mode=mode,
        parent_id=parent_id or project.active_timeline_id,
        created_at=time.time(),
    )
    project.timelines.append(entry)
    project.active_timeline_id = entry.id
    project.next_version = version + 1
    return entry
