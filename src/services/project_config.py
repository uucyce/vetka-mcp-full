"""
MARKER_153.1A: Project Configuration — persistence between restarts.

Stores project source, sandbox path, quota, and Qdrant collection.
Single project per instance (Phase 153). Multi-project = Phase 154.

@phase 153
@wave 1
@status active
"""

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

# Default config file location
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
CONFIG_PATH = os.path.join(DATA_DIR, "project_config.json")
SESSION_STATE_PATH = os.path.join(DATA_DIR, "session_state.json")


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
    def create_new(cls, source_type: str, source_path: str, quota_gb: int = 10) -> 'ProjectConfig':
        """Create a new project config from source."""
        # Derive project_id from path
        if source_type == "git":
            # git@github.com:user/repo.git -> repo
            name = source_path.rstrip("/").split("/")[-1].replace(".git", "")
        else:
            # /Users/user/my-project -> my-project
            name = os.path.basename(source_path.rstrip("/"))

        project_id = f"{name}_{uuid.uuid4().hex[:8]}"
        sandbox_path = os.path.join(DATA_DIR, "playgrounds", project_id)

        return cls(
            project_id=project_id,
            source_type=source_type,
            source_path=source_path,
            sandbox_path=sandbox_path,
            quota_gb=quota_gb,
            created_at=datetime.now(timezone.utc).isoformat(),
            qdrant_collection=project_id,
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
        if self.quota_gb < 1 or self.quota_gb > 100:
            errors.append(f"quota_gb must be 1-100, got {self.quota_gb}")
        return errors


@dataclass
class SessionState:
    """MCC session state — navigation level, selections, zoom."""

    level: str = "roadmap"              # roadmap | tasks | workflow | running | results
    roadmap_node_id: str = ""           # selected module in roadmap
    task_id: str = ""                   # selected task
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
