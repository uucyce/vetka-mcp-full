"""
MARKER_173.6 — Clip Proxy Generation Worker.

Generates lightweight proxy files for faster timeline scrubbing.
Proxies are 720p H.264 at low bitrate — good enough for editing preview,
small enough for instant seeking.

Architecture:
- ProxySpec: resolution, bitrate, codec config
- generate_proxy(): FFmpeg transcode with progress tracking
- ProxyWorker: batch generator with status tracking
- Proxy files stored in: {sandbox}/cut_runtime/proxies/

Requirements:
- FFmpeg must be available
- Source must be a valid video file
- Generates only if proxy doesn't exist or is stale

Usage:
    from src.services.cut_proxy_worker import ProxyWorker

    worker = ProxyWorker(sandbox_root="/path/to/project")
    result = worker.generate(source_path="/media/raw.mp4")
    # result = ProxyResult(proxy_path="...720p.mp4", ...)

    batch = worker.generate_batch(["/media/a.mp4", "/media/b.mp4"])
"""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.services.cut_ffmpeg_waveform import HAS_FFMPEG, FFMPEG

logger = logging.getLogger("cut.proxy_worker")


# ── Proxy presets ─────────────────────────────────────────

@dataclass
class ProxySpec:
    """Proxy transcode settings."""
    width: int = 1280       # 720p width
    height: int = 720       # 720p height
    video_bitrate: str = "2M"   # 2 Mbps
    audio_bitrate: str = "128k"
    codec: str = "libx264"
    preset: str = "ultrafast"
    crf: int = 28           # quality (higher = smaller file, lower quality)
    suffix: str = "_proxy_720p"
    extension: str = ".mp4"


PROXY_720P = ProxySpec()
PROXY_480P = ProxySpec(width=854, height=480, video_bitrate="1M", crf=30, suffix="_proxy_480p")
PROXY_360P = ProxySpec(width=640, height=360, video_bitrate="500k", crf=32, suffix="_proxy_360p")


# ── MARKER_B2: Auto-select proxy spec via ProbeResult ─────

@dataclass
class AutoProxyDecision:
    """Result of auto proxy spec selection."""
    needs_proxy: bool = False
    spec: ProxySpec | None = None
    reason: str = ""           # human-readable reason for decision
    playback_class: str = ""   # from ProbeResult
    source_resolution: str = "" # e.g. "4K", "1080p"


def auto_select_proxy_spec(probe_result: Any) -> AutoProxyDecision:
    """
    MARKER_B2 — Intelligently select proxy spec based on ProbeResult.

    Decision matrix:
      transcode_required + any resolution → 480p (heavy source, small proxy)
      proxy_recommended + ≥4K             → 480p
      proxy_recommended + ≥1080p          → 720p
      proxy_recommended + <1080p          → skip (already small)
      native + ≥4K                        → 720p (4K native is heavy for scrubbing)
      native + <4K                        → skip
      audio_only                          → skip

    Args:
        probe_result: ProbeResult from cut_codec_probe.probe_file()

    Returns:
        AutoProxyDecision with spec selection and reasoning.
    """
    decision = AutoProxyDecision()

    if not hasattr(probe_result, "ok") or not probe_result.ok:
        decision.reason = "probe_failed"
        return decision

    pc = getattr(probe_result, "playback_class", "") or ""
    height = getattr(probe_result, "height", 0) or 0
    codec_family = getattr(probe_result, "codec_family", "") or ""
    resolution_label = getattr(probe_result, "resolution_label", "") or ""

    decision.playback_class = pc
    decision.source_resolution = resolution_label

    # Audio-only: no proxy needed
    if codec_family == "audio_only":
        decision.reason = "audio_only"
        return decision

    # Transcode required (RAW, exotic codecs) → always proxy, small
    if pc == "transcode_required":
        decision.needs_proxy = True
        decision.spec = PROXY_480P
        decision.reason = f"transcode_required ({resolution_label}): heavy codec needs small proxy"
        return decision

    # Proxy recommended (production codecs, HEVC 10-bit, broadcast MXF)
    if pc == "proxy_recommended":
        if height >= 2160:  # 4K+
            decision.needs_proxy = True
            decision.spec = PROXY_480P
            decision.reason = f"proxy_recommended + {resolution_label}: 4K+ heavy → 480p proxy"
        elif height >= 1080:
            decision.needs_proxy = True
            decision.spec = PROXY_720P
            decision.reason = f"proxy_recommended + {resolution_label}: heavy codec → 720p proxy"
        else:
            decision.reason = f"proxy_recommended + {resolution_label}: small enough, skip"
        return decision

    # Native playback (H.264/VP9/AV1 in native container)
    if pc == "native":
        if height >= 2160:  # 4K native is still heavy for timeline scrubbing
            decision.needs_proxy = True
            decision.spec = PROXY_720P
            decision.reason = f"native + {resolution_label}: 4K+ too heavy for scrubbing → 720p"
        else:
            decision.reason = f"native + {resolution_label}: lightweight, no proxy needed"
        return decision

    # Unknown or unsupported → proxy to be safe
    if pc == "unsupported":
        decision.needs_proxy = True
        decision.spec = PROXY_480P
        decision.reason = f"unsupported codec: transcode to 480p proxy"
        return decision

    decision.reason = f"unknown playback_class '{pc}': skip"
    return decision


@dataclass
class ProxyResult:
    """Result of proxy generation."""
    source_path: str = ""
    proxy_path: str = ""
    success: bool = False
    skipped: bool = False      # True if proxy already exists and is fresh
    error: str = ""
    duration_sec: float = 0.0  # transcode time
    source_size_bytes: int = 0
    proxy_size_bytes: int = 0
    spec: str = "720p"


class ProxyWorker:
    """
    Batch proxy generator using FFmpeg.

    Stores proxies in {sandbox_root}/cut_runtime/proxies/
    with content-hash-based filenames to avoid duplicates.
    """

    def __init__(
        self,
        sandbox_root: str,
        spec: ProxySpec | None = None,
        force: bool = False,
    ) -> None:
        self.sandbox_root = Path(sandbox_root)
        self.spec = spec or PROXY_720P
        self.force = force
        self._proxy_dir = self.sandbox_root / "cut_runtime" / "proxies"

    @property
    def proxy_dir(self) -> Path:
        return self._proxy_dir

    def _content_hash(self, source_path: str) -> str:
        """Quick hash from file path + size + mtime (not full content)."""
        try:
            stat = os.stat(source_path)
            data = f"{source_path}:{stat.st_size}:{stat.st_mtime_ns}"
            return hashlib.sha256(data.encode()).hexdigest()[:16]
        except (OSError, FileNotFoundError):
            return hashlib.sha256(source_path.encode()).hexdigest()[:16]

    def _proxy_path_for(self, source_path: str) -> Path:
        """Compute proxy file path from source."""
        content_hash = self._content_hash(source_path)
        stem = Path(source_path).stem
        # Sanitize stem for filesystem
        safe_stem = "".join(c if c.isalnum() or c in "-_" else "_" for c in stem)[:60]
        filename = f"{safe_stem}_{content_hash}{self.spec.suffix}{self.spec.extension}"
        return self._proxy_dir / filename

    def _is_proxy_fresh(self, source_path: str, proxy_path: Path) -> bool:
        """Check if proxy exists and is newer than source."""
        if not proxy_path.is_file():
            return False
        if self.force:
            return False
        try:
            src_mtime = os.path.getmtime(source_path)
            prx_mtime = os.path.getmtime(str(proxy_path))
            return prx_mtime >= src_mtime
        except OSError:
            return False

    def generate(self, source_path: str) -> ProxyResult:
        """
        Generate a proxy for a single source file.

        Returns ProxyResult with success/skipped/error status.
        """
        result = ProxyResult(source_path=source_path, spec=f"{self.spec.width}x{self.spec.height}")

        # Validate
        if not HAS_FFMPEG:
            result.error = "ffmpeg_not_available"
            return result

        if not os.path.isfile(source_path):
            result.error = f"source_not_found: {source_path}"
            return result

        result.source_size_bytes = os.path.getsize(source_path)

        proxy_path = self._proxy_path_for(source_path)
        result.proxy_path = str(proxy_path)

        # Check if fresh proxy exists
        if self._is_proxy_fresh(source_path, proxy_path):
            result.success = True
            result.skipped = True
            try:
                result.proxy_size_bytes = os.path.getsize(str(proxy_path))
            except OSError:
                pass
            return result

        # Create proxy directory
        self._proxy_dir.mkdir(parents=True, exist_ok=True)

        # Build FFmpeg command
        tmp_path = proxy_path.with_suffix(".tmp.mp4")
        cmd = [
            FFMPEG,
            "-y",                         # overwrite
            "-i", source_path,
            "-vf", f"scale={self.spec.width}:{self.spec.height}:force_original_aspect_ratio=decrease,pad={self.spec.width}:{self.spec.height}:(ow-iw)/2:(oh-ih)/2",
            "-c:v", self.spec.codec,
            "-preset", self.spec.preset,
            "-crf", str(self.spec.crf),
            "-b:v", self.spec.video_bitrate,
            "-c:a", "aac",
            "-b:a", self.spec.audio_bitrate,
            "-movflags", "+faststart",    # web-friendly seeking
            "-threads", "2",
            str(tmp_path),
        ]

        t0 = time.time()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=600,  # 10min max
            )
            result.duration_sec = round(time.time() - t0, 2)

            if proc.returncode != 0:
                stderr = proc.stderr.decode("utf-8", errors="replace")[:500]
                result.error = f"ffmpeg_error: {stderr}"
                # Cleanup temp file
                if tmp_path.is_file():
                    tmp_path.unlink(missing_ok=True)
                return result

            # Atomic rename
            tmp_path.replace(proxy_path)
            result.success = True
            try:
                result.proxy_size_bytes = os.path.getsize(str(proxy_path))
            except OSError:
                pass

        except subprocess.TimeoutExpired:
            result.error = "ffmpeg_timeout"
            result.duration_sec = round(time.time() - t0, 2)
            if tmp_path.is_file():
                tmp_path.unlink(missing_ok=True)
        except (FileNotFoundError, OSError) as exc:
            result.error = f"ffmpeg_not_found: {exc}"
            result.duration_sec = round(time.time() - t0, 2)

        return result

    def generate_batch(
        self,
        source_paths: list[str],
        *,
        on_progress: Any = None,
    ) -> list[ProxyResult]:
        """
        Generate proxies for multiple source files.

        Args:
            source_paths: List of media file paths
            on_progress: Optional callback(index, total, result)

        Returns:
            List of ProxyResult for each source
        """
        results: list[ProxyResult] = []
        total = len(source_paths)

        for i, sp in enumerate(source_paths):
            result = self.generate(sp)
            results.append(result)

            if on_progress is not None:
                try:
                    on_progress(i, total, result)
                except Exception:
                    pass

            if result.success:
                logger.info(
                    "Proxy [%d/%d] %s → %s (%.1fs, %s→%s)",
                    i + 1, total,
                    "SKIP" if result.skipped else "OK",
                    os.path.basename(result.proxy_path),
                    result.duration_sec,
                    _human_size(result.source_size_bytes),
                    _human_size(result.proxy_size_bytes),
                )
            else:
                logger.warning("Proxy [%d/%d] FAIL %s: %s", i + 1, total, sp, result.error)

        return results

    def generate_auto(
        self,
        source_paths: list[str],
        *,
        on_progress: Any = None,
    ) -> list[dict[str, Any]]:
        """
        MARKER_B2 — Auto-proxy: probe each file, decide spec, generate if needed.

        Returns list of dicts with proxy result + probe metadata + decision info.
        """
        from src.services.cut_codec_probe import probe_file

        results: list[dict[str, Any]] = []
        total = len(source_paths)

        for i, sp in enumerate(source_paths):
            probe_result = probe_file(sp)
            decision = auto_select_proxy_spec(probe_result)

            entry: dict[str, Any] = {
                "source_path": sp,
                "needs_proxy": decision.needs_proxy,
                "reason": decision.reason,
                "playback_class": decision.playback_class,
                "source_resolution": decision.source_resolution,
                "codec_family": probe_result.codec_family if probe_result.ok else "",
                "video_codec": probe_result.video_codec if probe_result.ok else "",
            }

            if decision.needs_proxy and decision.spec:
                # Temporarily switch spec for this file
                orig_spec = self.spec
                self.spec = decision.spec
                proxy_result = self.generate(sp)
                self.spec = orig_spec

                entry.update({
                    "proxy_path": proxy_result.proxy_path,
                    "proxy_success": proxy_result.success,
                    "proxy_skipped": proxy_result.skipped,
                    "proxy_error": proxy_result.error,
                    "proxy_duration_sec": proxy_result.duration_sec,
                    "source_size_bytes": proxy_result.source_size_bytes,
                    "proxy_size_bytes": proxy_result.proxy_size_bytes,
                    "proxy_spec": f"{decision.spec.width}x{decision.spec.height}",
                })
            else:
                entry.update({
                    "proxy_path": None,
                    "proxy_success": False,
                    "proxy_skipped": True,
                    "proxy_error": "",
                    "proxy_duration_sec": 0.0,
                    "source_size_bytes": probe_result.file_size_bytes if probe_result.ok else 0,
                    "proxy_size_bytes": 0,
                    "proxy_spec": "none",
                })

            results.append(entry)

            if on_progress is not None:
                try:
                    on_progress(i, total, entry)
                except Exception:
                    pass

            logger.info(
                "AutoProxy [%d/%d] %s → %s (%s)",
                i + 1, total,
                "PROXY" if decision.needs_proxy else "SKIP",
                os.path.basename(sp),
                decision.reason,
            )

        return results

    def get_proxy_path(self, source_path: str) -> str | None:
        """Get existing proxy path for a source, or None if not generated."""
        proxy_path = self._proxy_path_for(source_path)
        if proxy_path.is_file():
            return str(proxy_path)
        return None

    def list_proxies(self) -> list[dict[str, Any]]:
        """List all generated proxy files."""
        if not self._proxy_dir.is_dir():
            return []
        proxies = []
        for f in sorted(self._proxy_dir.iterdir()):
            if f.is_file() and f.suffix == self.spec.extension:
                proxies.append({
                    "filename": f.name,
                    "path": str(f),
                    "size_bytes": f.stat().st_size,
                    "mtime": f.stat().st_mtime,
                })
        return proxies

    def cleanup_stale(self, valid_sources: list[str]) -> int:
        """Remove proxies for sources no longer in the project. Returns count removed."""
        if not self._proxy_dir.is_dir():
            return 0
        valid_hashes = {self._content_hash(sp) for sp in valid_sources}
        removed = 0
        for f in list(self._proxy_dir.iterdir()):
            if f.is_file() and f.suffix == self.spec.extension:
                # Extract hash from filename: stem_HASH_proxy_720p.mp4
                parts = f.stem.split("_")
                file_hash = ""
                for p in parts:
                    if len(p) == 16 and all(c in "0123456789abcdef" for c in p):
                        file_hash = p
                        break
                if file_hash and file_hash not in valid_hashes:
                    f.unlink(missing_ok=True)
                    removed += 1
        return removed


def _human_size(size_bytes: int) -> str:
    """Convert bytes to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f}MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"
