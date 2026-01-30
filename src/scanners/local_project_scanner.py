# src/scanners/local_project_scanner.py
"""
Scan local project directories to create Phase 9 format data.
FIXED: Limits + symlinks protection (Haiku bug #6)

@status: active
@phase: 96
@depends: config.design_system
@used_by: tree_routes, visualization
"""

import os
import hashlib
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.design_system import SCANNER_LIMITS


class LocalProjectScanner:
    """Scans local project and creates Phase 9 compatible data."""

    IGNORE_PATTERNS = [
        '.git', '__pycache__', 'node_modules', '.env',
        '.DS_Store', '*.pyc', 'build', 'dist', 'venv', '.venv',
        '.idea', '.vscode', 'target', '.gradle', 'Pods'
    ]

    LANG_MAP = {
        '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
        '.jsx': 'jsx', '.tsx': 'tsx', '.java': 'java',
        '.cpp': 'cpp', '.c': 'c', '.go': 'go', '.rs': 'rust',
        '.rb': 'ruby', '.php': 'php', '.sql': 'sql',
        '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml',
        '.md': 'markdown', '.txt': 'text', '.html': 'html',
        '.css': 'css', '.scss': 'scss', '.swift': 'swift',
        '.kt': 'kotlin', '.scala': 'scala'
    }

    def scan(self, directory: str) -> dict:
        """Scan directory and return Phase 9 format data."""
        root = Path(directory)
        if not root.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        # Collect files with limits
        files = []
        for item in self._walk_safe(root):
            if item.is_file() and len(files) < SCANNER_LIMITS["max_files"]:
                files.append({
                    "name": item.name,
                    "path": str(item.relative_to(root)),
                    "language": self._detect_lang(item),
                    "size_bytes": item.stat().st_size
                })

        # Create workflow ID
        workflow_id = f"scan_{root.name}_{hashlib.md5(str(root).encode()).hexdigest()[:8]}"

        # Find tests
        test_files = [f["name"] for f in files if self._is_test(f["name"])]

        return {
            "workflow_id": workflow_id,
            "timestamp": datetime.now().isoformat(),
            "source": "local_scan",
            "scanned_path": str(root.absolute()),

            "pm_result": {
                "plan": f"Local project: {root.name}",
                "description": f"Scanned {len(files)} files",
                "eval_score": 0.75
            },

            "architect_result": {
                "description": f"Project structure of {root.name}",
                "directories": list(set(str(Path(f["path"]).parent) for f in files))[:20],
                "eval_score": 0.70
            },

            "dev_result": {
                "files": files,
                "total_files": len(files),
                "eval_score": 0.80
            },

            "qa_result": {
                "tests": test_files,
                "passed": len(test_files),
                "failed": 0,
                "coverage": 0,
                "eval_score": 0.60 if test_files else 0.30
            },

            "arc_suggestions": [
                {"transformation": "Add documentation", "success": 0.85}
            ] if not any(f["language"] == "markdown" for f in files) else [],

            "metrics": {
                "total_files": len(files),
                "scan_time_ms": 0
            }
        }

    def _walk_safe(self, root: Path, current_depth: int = 0, visited: set = None):
        """
        Walk directory with protection against:
        - Infinite loops (symlinks)
        - Too many directories
        - Too deep nesting
        FIXED: Haiku bug #6
        """
        if visited is None:
            visited = set()

        # Check depth limit
        if current_depth > SCANNER_LIMITS["max_depth"]:
            return

        # Prevent infinite loops (symlinks)
        try:
            real_path = root.resolve()
        except OSError:
            return

        if real_path in visited:
            return
        visited.add(real_path)

        # Check total directories limit
        if len(visited) > SCANNER_LIMITS["max_directories"]:
            return

        try:
            items = sorted(root.iterdir())[:SCANNER_LIMITS["max_items_per_dir"]]
            for item in items:
                if self._should_ignore(item):
                    continue

                yield item

                # Recurse into directories (but not symlinks)
                if item.is_dir() and not item.is_symlink():
                    yield from self._walk_safe(item, current_depth + 1, visited)

        except (PermissionError, OSError):
            pass

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored."""
        name = path.name
        for pattern in self.IGNORE_PATTERNS:
            if pattern.startswith('*'):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern or name.startswith(pattern):
                return True
        return False

    def _detect_lang(self, path: Path) -> str:
        """Detect language from extension."""
        return self.LANG_MAP.get(path.suffix.lower(), 'unknown')

    def _is_test(self, filename: str) -> bool:
        """Check if file is a test."""
        name_lower = filename.lower()
        return any(p in name_lower for p in ['test_', '_test.', '.spec.', '.test.'])
