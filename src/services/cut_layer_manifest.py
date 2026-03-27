"""
MARKER_LAYERFX — CUT Layer Manifest Service.

Ingests explicit parallax layer manifests for CUT clips. A layer manifest
describes semantic scene layers (foreground_subject, secondary_subject,
mid_environment, background, special_clean) with their RGBA assets, masks,
depth maps, and z-ordering.

This complements (not replaces) the DaVinci-style single depth matte approach:
- **Depth effects** (depth_map, depth_blur, depth_fog, depth_grade) work with
  a single depth image and use luma-range masking. Great for continuous effects.
- **Layer manifests** provide explicit semantic decomposition with clean RGBA
  per layer. Required for parallax motion render and compositing operations
  that need per-object isolation (title-behind-subject, per-layer grading).

Both can coexist on the same clip — depth effects for continuous Z operations,
layer manifest for discrete semantic operations.

Supported input formats:
  1. `layer_space.json` — canonical VETKA layer space contract
  2. `plate_export_manifest.json` — parallax playground export format
  3. Manual layer pack — directory with named RGBA PNGs

@status: active
@phase: LAYERFX
@task: tb_1774609756_1
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Semantic layer roles (canonical)
# ---------------------------------------------------------------------------

LAYER_ROLES = [
    "foreground_subject",    # Primary subject (person, car, main object)
    "secondary_subject",     # Secondary subject (second person, pet, etc.)
    "mid_environment",       # Midground environment (furniture, trees, steam)
    "background",            # Background scene (sky, cityscape, wall)
    "special_clean",         # Clean plate (inpainted background, no subjects)
]

# Bridge: JSON/TS kebab-case roles → Python canonical underscore roles
_ROLE_NORMALIZE: dict[str, str] = {
    "foreground-subject": "foreground_subject",
    "secondary-subject": "secondary_subject",
    "environment-mid": "mid_environment",
    "background-far": "background",
    "special-clean": "special_clean",
}


def normalize_role(role: str) -> str:
    """Normalize a role string from any format to canonical underscore form."""
    return _ROLE_NORMALIZE.get(role, role)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SemanticLayer:
    """One semantic layer in a parallax scene decomposition."""
    layer_id: str = ""
    role: str = ""                   # One of LAYER_ROLES
    label: str = ""                  # Human-readable label
    order: int = 0                   # Compositing order (0 = back, higher = front)
    depth_priority: float = 0.0     # Depth priority 0-1 (from layout, NOT same as order)
    z: float = 1.0                   # Depth position in camera space
    visible: bool = True
    # Asset paths
    rgba_path: str = ""              # RGBA PNG with alpha isolation
    mask_path: str = ""              # Greyscale mask PNG
    depth_path: str = ""             # Per-layer depth map (optional)
    clean_path: str = ""             # Clean plate file path (from files.clean)
    clean_variant: str = ""          # Clean variant name (e.g. "no-vehicle") — semantic label
    # Layer properties
    coverage: float = 0.0           # Frame coverage fraction (0-1)
    parallax_strength: float = 1.0  # Motion amplitude multiplier
    motion_damping: float = 1.0     # Damping factor

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> SemanticLayer:
        # FIX-1: normalize role from kebab-case (JSON/TS) to underscore (Python)
        raw_role = str(d.get("role", ""))
        # FIX-2: depthPriority is float 0-1, order is int compositing index — separate fields
        raw_order = d.get("order") or d.get("index", 0)
        raw_depth_pri = float(d.get("depthPriority") or d.get("depth_priority", 0.0))
        # FIX-3: coverage field — try both "coverage" (manifest) and "plateCoverage" (layout risk)
        raw_coverage = d.get("coverage") or d.get("plateCoverage", 0.0)

        return SemanticLayer(
            layer_id=str(d.get("layer_id") or d.get("id", "")),
            role=normalize_role(raw_role),
            label=str(d.get("label", "")),
            order=int(raw_order),
            depth_priority=raw_depth_pri,
            z=float(d.get("z", 1.0)),
            visible=bool(d.get("visible", True)),
            rgba_path=str(d.get("rgba_path") or d.get("rgba", "")),
            mask_path=str(d.get("mask_path") or d.get("mask", "")),
            depth_path=str(d.get("depth_path") or d.get("depth", "")),
            clean_path=str(d.get("clean_path") or d.get("clean", "")),
            clean_variant=str(d.get("clean_variant") or d.get("cleanVariant", "") or ""),
            coverage=float(raw_coverage),
            parallax_strength=float(d.get("parallax_strength") or d.get("parallaxStrength", 1.0)),
            motion_damping=float(d.get("motion_damping") or d.get("motionDamping", 1.0)),
        )

    @property
    def has_rgba(self) -> bool:
        return bool(self.rgba_path) and Path(self.rgba_path).exists()

    @property
    def has_mask(self) -> bool:
        return bool(self.mask_path) and Path(self.mask_path).exists()


@dataclass
class CameraContract:
    """Camera geometry from layer manifest."""
    focal_length_mm: float = 50.0
    film_width_mm: float = 36.0
    z_near: float = 0.72
    z_far: float = 1.85
    motion_type: str = "orbit"
    duration_sec: float = 4.0
    travel_x_pct: float = 3.0
    travel_y_pct: float = 0.0
    zoom: float = 1.0
    overscan_pct: float = 20.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> CameraContract:
        return CameraContract(
            focal_length_mm=float(d.get("focalLengthMm") or d.get("focal_length_mm", 50.0)),
            film_width_mm=float(d.get("filmWidthMm") or d.get("film_width_mm", 36.0)),
            z_near=float(d.get("zNear") or d.get("z_near", 0.72)),
            z_far=float(d.get("zFar") or d.get("z_far", 1.85)),
            motion_type=str(d.get("motionType") or d.get("motion_type", "orbit")),
            duration_sec=float(d.get("durationSec") or d.get("duration_sec", 4.0)),
            travel_x_pct=float(d.get("travelXPct") or d.get("travel_x_pct", 3.0)),
            travel_y_pct=float(d.get("travelYPct") or d.get("travel_y_pct", 0.0)),
            zoom=float(d.get("zoom", 1.0)),
            overscan_pct=float(d.get("overscanPct") or d.get("overscan_pct", 20.0)),
        )


@dataclass
class LayerManifest:
    """Complete layer manifest for a parallax scene."""
    manifest_id: str = ""
    contract_version: str = "1.0.0"
    sample_id: str = ""
    source_path: str = ""               # Original source image
    source_width: int = 0
    source_height: int = 0
    layers: list[SemanticLayer] = field(default_factory=list)
    camera: CameraContract = field(default_factory=CameraContract)
    depth_path: str = ""                 # Global depth map (optional)
    background_rgba_path: str = ""       # Background RGBA (implicit layer)
    # Metadata
    format: str = ""                     # "layer_space" | "plate_export" | "manual"
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["layers"] = [l.to_dict() for l in self.layers]
        d["camera"] = self.camera.to_dict()
        return d

    @property
    def layer_count(self) -> int:
        return len(self.layers)

    @property
    def visible_layers(self) -> list[SemanticLayer]:
        return [l for l in self.layers if l.visible]

    def get_layer_by_role(self, role: str) -> SemanticLayer | None:
        """Find first layer with given role."""
        for l in self.layers:
            if l.role == role:
                return l
        return None

    @property
    def has_foreground(self) -> bool:
        return self.get_layer_by_role("foreground_subject") is not None

    @property
    def has_background(self) -> bool:
        return (self.get_layer_by_role("background") is not None
                or bool(self.background_rgba_path))


# ---------------------------------------------------------------------------
# Manifest ingestion — reads various formats
# ---------------------------------------------------------------------------

def ingest_layer_space(path: str | Path) -> LayerManifest:
    """
    Ingest canonical layer_space.json manifest.

    Expected format:
    {
      "contract_version": "1.0",
      "sampleId": "...",
      "source": {"path": "...", "width": N, "height": N},
      "layers": [{id, role, label, z, visible, rgba, mask, depth, ...}],
      "space": {camera settings},
      "provenance": {...}
    }
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    source = data.get("source", {})
    layers = []
    for ld in data.get("layers", []):
        layer = SemanticLayer.from_dict(ld)
        # Resolve relative paths
        base_dir = Path(path).parent
        if layer.rgba_path and not Path(layer.rgba_path).is_absolute():
            layer.rgba_path = str(base_dir / layer.rgba_path)
        if layer.mask_path and not Path(layer.mask_path).is_absolute():
            layer.mask_path = str(base_dir / layer.mask_path)
        if layer.depth_path and not Path(layer.depth_path).is_absolute():
            layer.depth_path = str(base_dir / layer.depth_path)
        layers.append(layer)

    camera = CameraContract.from_dict(data.get("space", data.get("camera", {})))

    return LayerManifest(
        manifest_id=str(data.get("sampleId", "")),
        contract_version=str(data.get("contract_version", "1.0")),
        sample_id=str(data.get("sampleId", "")),
        source_path=str(source.get("path", "")),
        source_width=int(source.get("width", 0)),
        source_height=int(source.get("height", 0)),
        layers=layers,
        camera=camera,
        depth_path=str(data.get("depth_path", "")),
        format="layer_space",
        provenance=data.get("provenance", {}),
    )


def ingest_plate_export(manifest_path: str | Path, layout_path: str | Path | None = None) -> LayerManifest:
    """
    Ingest parallax playground plate_export_manifest.json.

    Optionally reads plate_layout.json for camera geometry.

    Expected manifest format:
    {
      "exportedPlates": [
        {"id": "plate_00", "visible": true, "files": {"rgba": "...", "depth": "..."}},
        ...
      ]
    }
    """
    base_dir = Path(manifest_path).parent
    manifest_data = json.loads(Path(manifest_path).read_text(encoding="utf-8"))

    layout_data: dict[str, Any] = {}
    if layout_path and Path(layout_path).exists():
        layout_data = json.loads(Path(layout_path).read_text(encoding="utf-8"))

    layers = []
    for plate in manifest_data.get("exportedPlates", []):
        files = plate.get("files", {})
        # Merge files into plate dict for from_dict to pick up
        flat = dict(plate)
        flat["rgba"] = str(files.get("rgba", ""))
        flat["mask"] = str(files.get("mask", ""))
        flat["depth"] = str(files.get("depth", ""))
        flat["clean"] = str(files.get("clean", ""))  # file path → clean_path

        layer = SemanticLayer.from_dict(flat)
        # Resolve relative asset paths
        if layer.rgba_path and not Path(layer.rgba_path).is_absolute():
            layer.rgba_path = str(base_dir / layer.rgba_path) if layer.rgba_path else ""
        if layer.mask_path and not Path(layer.mask_path).is_absolute():
            layer.mask_path = str(base_dir / layer.mask_path) if layer.mask_path else ""
        if layer.depth_path and not Path(layer.depth_path).is_absolute():
            layer.depth_path = str(base_dir / layer.depth_path) if layer.depth_path else ""
        if layer.clean_path and not Path(layer.clean_path).is_absolute():
            layer.clean_path = str(base_dir / layer.clean_path) if layer.clean_path else ""
        # Use plate id as label fallback
        if not layer.label:
            layer.label = layer.layer_id
        layers.append(layer)

    # Camera from layout
    camera = CameraContract()
    source_info = layout_data.get("source", {})
    if layout_data.get("camera"):
        camera = CameraContract.from_dict(layout_data["camera"])

    # Background RGBA (top-level, not per-plate)
    bg_rgba = ""
    bg_file = base_dir / "background_rgba.png"
    if bg_file.exists():
        bg_rgba = str(bg_file)

    return LayerManifest(
        manifest_id=str(manifest_data.get("sampleId", base_dir.name)),
        sample_id=str(manifest_data.get("sampleId", base_dir.name)),
        source_path=str(source_info.get("path", "")),
        source_width=int(source_info.get("width", 0)),
        source_height=int(source_info.get("height", 0)),
        layers=layers,
        camera=camera,
        background_rgba_path=bg_rgba,
        format="plate_export",
        provenance={"manifest_path": str(manifest_path)},
    )


def ingest_manifest(path: str | Path) -> LayerManifest:
    """
    Auto-detect manifest format and ingest.

    Looks at the JSON structure to determine if it's layer_space or plate_export.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")

    data = json.loads(p.read_text(encoding="utf-8"))

    # Detect format
    if "contract_version" in data and "layers" in data:
        return ingest_layer_space(path)
    elif "exportedPlates" in data:
        # Look for sibling plate_layout.json
        layout_path = p.parent / "plate_layout.json"
        return ingest_plate_export(path, layout_path if layout_path.exists() else None)
    else:
        raise ValueError(f"Unknown manifest format in {path}")


# ---------------------------------------------------------------------------
# Clip metadata integration
# ---------------------------------------------------------------------------

@dataclass
class LayerManifestMeta:
    """Layer manifest metadata stored on a clip."""
    manifest_path: str = ""
    format: str = ""                    # "layer_space" | "plate_export" | "manual"
    layer_count: int = 0
    has_foreground: bool = False
    has_background: bool = False
    sample_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> LayerManifestMeta:
        return LayerManifestMeta(**{k: d[k] for k in d if k in LayerManifestMeta.__dataclass_fields__})

    @staticmethod
    def from_manifest(manifest: LayerManifest, manifest_path: str) -> LayerManifestMeta:
        return LayerManifestMeta(
            manifest_path=manifest_path,
            format=manifest.format,
            layer_count=manifest.layer_count,
            has_foreground=manifest.has_foreground,
            has_background=manifest.has_background,
            sample_id=manifest.sample_id,
        )
