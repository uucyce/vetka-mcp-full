"""
VETKA Phase 12: Local File Scanner

Walks directory tree and extracts file metadata + content for indexing.

@status: active
@phase: 96
@depends: pathlib, hashlib, dataclasses
@used_by: embedding_pipeline, file_watcher
"""

import os
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Generator, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ScannedFile:
    """Represents a scanned file with metadata and content."""
    path: str
    name: str
    extension: str
    size_bytes: int
    modified_time: float
    created_time: float
    content: str
    content_hash: str
    parent_folder: str
    depth: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LocalScanner:
    """
    Scans local directories for files and extracts content.

    Supports: .md, .txt, .py, .js, .ts, .json, .yaml, .yml, .html, .css
    """

    SUPPORTED_EXTENSIONS = {
        '.md', '.txt', '.py', '.js', '.ts', '.jsx', '.tsx',
        '.json', '.yaml', '.yml', '.html', '.css', '.scss',
        '.sh', '.bash', '.zsh', '.sql', '.graphql',
        '.xml', '.csv', '.ini', '.cfg', '.conf', '.env',
        '.rst', '.org', '.wiki'
    }

    SKIP_DIRS = {
        '.git', '.svn', '.hg', 'node_modules', '__pycache__',
        '.venv', 'venv', 'env', '.env', 'dist', 'build',
        '.idea', '.vscode', '.DS_Store', 'vendor', 'target'
    }

    MAX_FILE_SIZE = 1024 * 1024  # 1MB max per file

    def __init__(self, root_path: str, max_files: int = 10000):
        self.root_path = Path(root_path).expanduser().resolve()
        self.max_files = max_files
        self.scanned_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.total_bytes = 0

    def scan(self) -> Generator[ScannedFile, None, None]:
        """
        Generator that yields ScannedFile objects.

        Usage:
            scanner = LocalScanner('/path/to/docs')
            for file in scanner.scan():
                print(file.path, file.size_bytes)
        """
        if not self.root_path.exists():
            raise ValueError(f"Path does not exist: {self.root_path}")

        if not self.root_path.is_dir():
            raise ValueError(f"Path is not a directory: {self.root_path}")

        root_depth = len(self.root_path.parts)

        for dirpath, dirnames, filenames in os.walk(self.root_path):
            # Skip hidden and excluded directories
            dirnames[:] = [d for d in dirnames if d not in self.SKIP_DIRS and not d.startswith('.')]

            current_path = Path(dirpath)
            depth = len(current_path.parts) - root_depth

            for filename in filenames:
                if self.scanned_count >= self.max_files:
                    return

                file_path = current_path / filename

                try:
                    scanned = self._scan_file(file_path, depth)
                    if scanned:
                        self.scanned_count += 1
                        self.total_bytes += scanned.size_bytes
                        yield scanned
                    else:
                        self.skipped_count += 1
                except Exception as e:
                    self.error_count += 1
                    print(f"[Scanner] Error scanning {file_path}: {e}")

    def _scan_file(self, file_path: Path, depth: int) -> Optional[ScannedFile]:
        """Scan a single file and return ScannedFile or None if skipped."""

        # Check extension
        ext = file_path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            return None

        # Check file size
        try:
            stat = file_path.stat()
            if stat.st_size > self.MAX_FILE_SIZE:
                return None
            if stat.st_size == 0:
                return None
        except OSError:
            return None

        # Read content
        content = self._read_content(file_path)
        if not content:
            return None

        # Compute content hash
        content_hash = hashlib.md5(content.encode('utf-8', errors='ignore')).hexdigest()

        # Get REAL file creation time (st_birthtime on macOS, fallback to ctime)
        try:
            # macOS/BSD has st_birthtime for true creation date
            created_time = stat.st_birthtime
        except AttributeError:
            # Linux/Windows fallback to ctime (which may be metadata change time)
            created_time = stat.st_ctime

        return ScannedFile(
            path=str(file_path),
            name=file_path.name,
            extension=ext,
            size_bytes=stat.st_size,
            modified_time=stat.st_mtime,
            created_time=created_time,
            content=content,
            content_hash=content_hash,
            parent_folder=str(file_path.parent),
            depth=depth
        )

    def _read_content(self, file_path: Path) -> Optional[str]:
        """Read file content as text."""
        encodings = ['utf-8', 'latin-1', 'cp1252']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
            except Exception:
                return None

        return None

    def get_stats(self) -> Dict[str, Any]:
        """Return scanning statistics."""
        return {
            'root_path': str(self.root_path),
            'scanned_count': self.scanned_count,
            'skipped_count': self.skipped_count,
            'error_count': self.error_count,
            'total_bytes': self.total_bytes,
            'total_mb': round(self.total_bytes / (1024 * 1024), 2)
        }


def scan_directory(path: str, max_files: int = 10000) -> List[Dict[str, Any]]:
    """
    Convenience function to scan a directory and return list of file dicts.

    Args:
        path: Directory path to scan
        max_files: Maximum number of files to scan

    Returns:
        List of file dictionaries with metadata and content
    """
    scanner = LocalScanner(path, max_files=max_files)
    files = [f.to_dict() for f in scanner.scan()]

    stats = scanner.get_stats()
    print(f"[Scanner] Scanned {stats['scanned_count']} files ({stats['total_mb']} MB)")
    print(f"[Scanner] Skipped {stats['skipped_count']}, Errors {stats['error_count']}")

    return files
