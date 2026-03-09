"""
MARKER_153.1A: Project Configuration — persistence between restarts.
MARKER_153.2A: Sandbox utilities — quota check, disk usage, status.

Stores project source, sandbox path, quota, and Qdrant collection.
Single project per instance (Phase 153). Multi-project registry is planned.

MARKER_161.7.MULTIPROJECT.REGISTRY.RECON.V1:
Current file is single-project source of truth and migration anchor for project-registry.

@phase 153
@wave 1-2
@status active
"""

import json
import os
import subprocess
import uuid
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# Default config file location
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
CONFIG_PATH = os.path.join(DATA_DIR, "project_config.json")
SESSION_STATE_PATH = os.path.join(DATA_DIR, "session_state.json")
# MARKER_161.7.MULTIPROJECT.REGISTRY.PATHS.V1:
# Future registry layout: projects/<project_id>/{project_config,session_state}.json + active_project pointer.


def _normalize_display_name(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text[:80]


def _slug_from_name(raw: str) -> str:
    text = str(raw or "").strip().lower()
    text = re.sub(r"[^a-z0-9._-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("._-")
    return text or "project"


@dataclass
class ProjectConfig:
    """Project configuration — survives server restarts."""

    project_id: str = ""
    source_type: str = "local"          # "local" | "git"
    source_path: str = ""               # absolute path or git URL
    sandbox_path: str = ""              # /data/playgrounds/{project_id}/
    quota_gb: int = 10
    created_at: str = ""
    qdrant_collection: str = ""
    # MARKER_161.9.MULTIPROJECT.NAMING.CONFIG_PERSIST.V1
    display_name: str = ""

    @classmethod
    def load(cls, path: Optional[str] = None) -> Optional['ProjectConfig']:
        """Load from data/project_config.json. Returns None if no config."""
        path = path or CONFIG_PATH
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        except (json.JSONDecodeError, TypeError, KeyError):
            return None

    def save(self, path: Optional[str] = None) -> bool:
        """Save to data/project_config.json."""
        path = path or CONFIG_PATH
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                json.dump(asdict(self), f, indent=2)
            return True
        except OSError:
            return False

    @classmethod
    def create_new(
        cls,
        source_type: str,
        source_path: str,
        quota_gb: int = 10,
        sandbox_path: str = "",
        project_name: str = "",
    ) -> 'ProjectConfig':
        """Create a new project config from source."""
        display_name = _normalize_display_name(project_name)
        if display_name:
            name = display_name
        elif source_type == "git":
            name = source_path.rstrip("/").split("/")[-1].replace(".git", "")
        else:
            name = os.path.basename(source_path.rstrip("/"))

        slug = _slug_from_name(name)
        project_id = f"{slug}_{uuid.uuid4().hex[:8]}"
        resolved_sandbox = os.path.abspath(os.path.expanduser(sandbox_path.strip())) if str(sandbox_path or "").strip() else ""
        sandbox_path_final = resolved_sandbox or os.path.join(DATA_DIR, "playgrounds", project_id)
        if not display_name:
            display_name = _normalize_display_name(os.path.basename(sandbox_path_final.rstrip("/")) or slug)

        return cls(
            project_id=project_id,
            source_type=source_type,
            source_path=source_path,
            sandbox_path=sandbox_path_final,
            quota_gb=quota_gb,
            created_at=datetime.now(timezone.utc).isoformat(),
            qdrant_collection=project_id,
            display_name=display_name,
        )

    def validate(self) -> list[str]:
        """Validate config. Returns list of errors (empty = valid)."""
        errors = []
        if not self.project_id:
            errors.append("project_id is required")
        if self.source_type not in ("local", "git"):
            errors.append(f"Invalid source_type: {self.source_type}")
        if not self.source_path:
            errors.append("source_path is required")
        if self.source_type == "local" and not os.path.isabs(self.source_path):
            errors.append("source_path must be absolute for local projects")
        if self.sandbox_path and not os.path.isabs(self.sandbox_path):
            errors.append("sandbox_path must be absolute")
        if self.quota_gb < 1 or self.quota_gb > 100:
            errors.append(f"quota_gb must be 1-100, got {self.quota_gb}")
        return errors

    # ── MARKER_153.2A: Sandbox utilities ──

    def sandbox_exists(self) -> bool:
        """Check if sandbox directory exists on disk."""
        return bool(self.sandbox_path) and os.path.isdir(self.sandbox_path)

    def get_disk_usage_bytes(self) -> int:
        """Get sandbox disk usage in bytes. Returns 0 if sandbox doesn't exist."""
        if not self.sandbox_exists():
            return 0
        try:
            timeout_sec = max(
                1,
                int(str(os.getenv("VETKA_SANDBOX_DU_TIMEOUT_SEC", "5")).strip() or "5"),
            )
            result = subprocess.run(
                ["du", "-sk", self.sandbox_path],
                capture_output=True, text=True, timeout=timeout_sec,
            )
            if result.returncode == 0 and result.stdout.strip():
                kb = int(result.stdout.split()[0])
                return kb * 1024
        except (subprocess.TimeoutExpired, ValueError, OSError):
            pass
        return 0

    def get_disk_usage_gb(self) -> float:
        """Get sandbox disk usage in GB (rounded to 2 decimals)."""
        return round(self.get_disk_usage_bytes() / (1024 ** 3), 2)

    def check_quota(self) -> dict:
        """Check sandbox disk usage against quota."""
        used_gb = self.get_disk_usage_gb()
        quota_gb = self.quota_gb
        percent = round((used_gb / quota_gb) * 100, 1) if quota_gb > 0 else 0
        return {
            "used_gb": used_gb,
            "quota_gb": quota_gb,
            "percent": percent,
            "warning": percent >= 80,
            "exceeded": percent >= 100,
        }

    def get_sandbox_status(self) -> dict:
        """Full sandbox status for REST API / UI."""
        exists = self.sandbox_exists()
        quota = self.check_quota() if exists else {
            "used_gb": 0, "quota_gb": self.quota_gb,
            "percent": 0, "warning": False, "exceeded": False,
        }
        file_count = 0
        include_file_count = str(os.getenv("VETKA_SANDBOX_COUNT_FILES", "0")).strip().lower() in {"1", "true", "yes", "on"}
        if exists and include_file_count:
            try:
                result = subprocess.run(
                    ["find", self.sandbox_path, "-type", "f"],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode == 0:
                    file_count = len(result.stdout.strip().splitlines())
            except (subprocess.TimeoutExpired, OSError):
                pass
        return {
            "exists": exists,
            "sandbox_path": self.sandbox_path,
            "file_count": file_count,
            **quota,
        }


@dataclass
class SessionState:
    """MCC session state — navigation level, selections, zoom."""

    level: str = "roadmap"              # roadmap | tasks | workflow | running | results
    roadmap_node_id: str = ""           # selected module in roadmap
    task_id: str = ""                   # selected task
    selected_key: Optional[Dict[str, Any]] = None  # selected API key {provider, key_masked}
    history: list = field(default_factory=list)  # navigation history for back
    last_updated: str = ""

    @classmethod
    def load(cls, path: Optional[str] = None) -> 'SessionState':
        """Load session state. Returns default if no file."""
        path = path or SESSION_STATE_PATH
        if not os.path.exists(path):
            return cls()
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        except (json.JSONDecodeError, TypeError, KeyError):
            return cls()

    def save(self, path: Optional[str] = None) -> bool:
        """Save session state to disk."""
        path = path or SESSION_STATE_PATH
        try:
            self.last_updated = datetime.now(timezone.utc).isoformat()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                json.dump(asdict(self), f, indent=2)
            return True
        except OSError:
            return False
