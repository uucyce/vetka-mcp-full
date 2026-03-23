"""
MARKER_B47 — Conform/Relink service (FCP7 Ch.44).

Detects missing/moved source files in a CUT project and provides
relink suggestions via fuzzy matching (filename + duration).

Flow:
  1. check_project_media() → list of {path, status: online|offline, suggestions[]}
  2. relink_media() → apply path remaps across all timeline clips + scene graph

@status: active
@phase: B47
@task: tb_1774248197_6
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MediaStatus:
    """Status of a single source file in the project."""
    source_path: str
    status: str = "online"      # online | offline | moved
    file_size: int = 0
    clip_ids: list[str] = field(default_factory=list)
    suggestions: list[dict[str, Any]] = field(default_factory=list)  # [{path, score, reason}]


def _collect_source_paths(timeline: dict[str, Any]) -> dict[str, list[str]]:
    """Extract unique source paths from timeline → {path: [clip_ids]}."""
    paths: dict[str, list[str]] = {}
    for lane in timeline.get("lanes", []):
        for clip in lane.get("clips", []):
            sp = clip.get("source_path", "")
            if sp:
                paths.setdefault(sp, []).append(clip.get("clip_id", ""))
    return paths


def _probe_duration_fast(path: str) -> float | None:
    """Quick duration probe via ffprobe (timeout 3s)."""
    import subprocess
    import shutil
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    try:
        cmd = [
            ffprobe, "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception:
        pass
    return None


def _fuzzy_match_score(
    original_name: str,
    original_size: int,
    candidate_path: str,
) -> tuple[float, str]:
    """Score a candidate file as a potential relink target.

    Returns (score 0-1, reason string).
    Matching criteria:
      - Exact filename: 0.6
      - Stem match (ignore extension): 0.4
      - Size within 5%: +0.2
      - Same extension: +0.1
    """
    cand = Path(candidate_path)
    orig = Path(original_name)
    score = 0.0
    reasons: list[str] = []

    # Filename match
    if cand.name == orig.name:
        score += 0.6
        reasons.append("exact_name")
    elif cand.stem == orig.stem:
        score += 0.4
        reasons.append("stem_match")
    else:
        return 0.0, ""  # No name similarity → skip

    # Extension match
    if cand.suffix.lower() == orig.suffix.lower():
        score += 0.1
        reasons.append("same_ext")

    # Size match (within 5%)
    if original_size > 0:
        try:
            cand_size = os.path.getsize(candidate_path)
            ratio = cand_size / original_size if original_size > 0 else 0
            if 0.95 <= ratio <= 1.05:
                score += 0.2
                reasons.append("size_match")
        except OSError:
            pass

    return min(1.0, score), "+".join(reasons)


def check_project_media(
    timeline: dict[str, Any],
    *,
    search_roots: list[str] | None = None,
    max_suggestions: int = 3,
) -> list[MediaStatus]:
    """Check all source files in timeline for online/offline status.

    For offline files, optionally search search_roots for fuzzy matches.

    Args:
        timeline: Timeline state dict with lanes/clips.
        search_roots: Directories to search for moved files (optional).
        max_suggestions: Max relink suggestions per offline file.

    Returns:
        List of MediaStatus for each unique source path.
    """
    source_map = _collect_source_paths(timeline)
    results: list[MediaStatus] = []

    for source_path, clip_ids in source_map.items():
        ms = MediaStatus(source_path=source_path, clip_ids=clip_ids)
        p = Path(source_path)

        if p.is_file():
            ms.status = "online"
            try:
                ms.file_size = p.stat().st_size
            except OSError:
                pass
        else:
            ms.status = "offline"
            # Try to find in search roots
            if search_roots:
                candidates: list[tuple[float, str, str]] = []
                original_name = p.name
                # Try to get original size from metadata (best effort)
                original_size = 0

                for root in search_roots:
                    if not os.path.isdir(root):
                        continue
                    for dirpath, _dirs, files in os.walk(root):
                        for fname in files:
                            if Path(fname).stem != p.stem:
                                continue  # Quick filter: stem must match
                            cand_path = os.path.join(dirpath, fname)
                            score, reason = _fuzzy_match_score(original_name, original_size, cand_path)
                            if score > 0.3:
                                candidates.append((score, cand_path, reason))

                # Sort by score descending
                candidates.sort(key=lambda x: -x[0])
                ms.suggestions = [
                    {"path": c[1], "score": round(c[0], 2), "reason": c[2]}
                    for c in candidates[:max_suggestions]
                ]
                if ms.suggestions and ms.suggestions[0]["score"] >= 0.7:
                    ms.status = "moved"  # High confidence — likely just moved

        results.append(ms)

    return results


def relink_media(
    timeline: dict[str, Any],
    remap: dict[str, str],
) -> dict[str, Any]:
    """Apply source path remapping across all timeline clips.

    Args:
        timeline: Timeline state dict (modified in place).
        remap: Dict of {old_path: new_path}.

    Returns:
        Summary: {remapped_count, clip_ids_affected, not_found}.
    """
    remapped_count = 0
    affected_clips: list[str] = []
    not_found: list[str] = []

    for old_path, new_path in remap.items():
        if not os.path.isfile(new_path):
            not_found.append(new_path)
            continue

        found = False
        for lane in timeline.get("lanes", []):
            for clip in lane.get("clips", []):
                if clip.get("source_path") == old_path:
                    clip["source_path"] = new_path
                    remapped_count += 1
                    affected_clips.append(clip.get("clip_id", ""))
                    found = True
        if not found:
            not_found.append(old_path)

    return {
        "remapped_count": remapped_count,
        "clip_ids_affected": affected_clips,
        "not_found": not_found,
    }
