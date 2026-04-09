# ========================================
# MARKER: Phase 72.1 Foundation
# Created: 2026-01-19
# File: src/scanners/base_scanner.py
# Purpose: Abstract base class for all dependency scanners
# ========================================
"""
Abstract base class for VETKA dependency scanners.

Extensible architecture supporting the "Periodic Table" of content types:
- CodeScanner (Python, JS, TS) -> Phase 72.3
- DocumentScanner (MD, TXT, RST) -> Future
- VideoScanner (MP4, chapters) -> Future
- AudioScanner (podcasts, segments) -> Future
- BookScanner (chapters, citations) -> Future

Each scanner implements:
1. supported_extensions - what files it can scan
2. extract_dependencies - how to extract dependencies from content

@status: active
@phase: 96
@depends: abc, pathlib, dependency, exceptions
@used_by: python_scanner
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Set

from .dependency import Dependency
from .exceptions import UnsupportedFileTypeError


class BaseScanner(ABC):
    """
    Abstract base class for all dependency scanners.

    Subclasses must implement:
        - supported_extensions: Set of file extensions this scanner handles
        - extract_dependencies: Extract dependencies from file content

    Example implementation:
        class PythonScanner(BaseScanner):
            @property
            def supported_extensions(self) -> Set[str]:
                return {'.py', '.pyi'}

            def extract_dependencies(self, file_path: str, content: str) -> List[Dependency]:
                # Parse Python imports using AST
                ...
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> Set[str]:
        """
        Set of file extensions this scanner supports.

        Extensions should be lowercase with leading dot.

        Returns:
            Set of extensions, e.g., {'.py', '.pyi'}

        Example:
            {'.py', '.pyi'}           # Python
            {'.js', '.jsx', '.ts'}    # JavaScript/TypeScript
            {'.md', '.txt', '.rst'}   # Documents
        """
        pass

    @abstractmethod
    def extract_dependencies(
        self,
        file_path: str,
        content: str
    ) -> List[Dependency]:
        """
        Extract dependencies from file content.

        Args:
            file_path: Full path to the file being scanned
            content: File content as string

        Returns:
            List of Dependency objects found in the content.
            Empty list if no dependencies found.

        Raises:
            ParseError: If content cannot be parsed
            UnsupportedFileTypeError: If file type not supported

        Note:
            This method should NOT read the file itself - content is provided.
            This allows for testing and caching.
        """
        pass

    def can_scan(self, file_path: str) -> bool:
        """
        Check if this scanner can handle the given file.

        Args:
            file_path: Path to file (can be relative or absolute)

        Returns:
            True if file extension is in supported_extensions
        """
        ext = Path(file_path).suffix.lower()
        return ext in self.supported_extensions

    def validate_content(self, content: str) -> bool:
        """
        Validate that content is suitable for scanning.

        Override in subclasses for specific validation logic.

        Args:
            content: File content to validate

        Returns:
            True if content is valid for scanning
        """
        # Default: any non-empty content is valid
        return bool(content and content.strip())

    def scan_file(self, file_path: str, content: str) -> List[Dependency]:
        """
        High-level method to scan a file with validation.

        Args:
            file_path: Path to the file
            content: File content

        Returns:
            List of dependencies

        Raises:
            UnsupportedFileTypeError: If file type not supported
            ParseError: If content cannot be parsed
        """
        if not self.can_scan(file_path):
            raise UnsupportedFileTypeError(
                f"Scanner {self.__class__.__name__} does not support "
                f"file type: {Path(file_path).suffix}"
            )

        if not self.validate_content(content):
            return []  # Empty/invalid content = no dependencies

        return self.extract_dependencies(file_path, content)

    @property
    def scanner_name(self) -> str:
        """
        Human-readable name of this scanner.

        Returns:
            Class name by default, override for custom name
        """
        return self.__class__.__name__

    def __repr__(self) -> str:
        """String representation including supported extensions."""
        extensions = ', '.join(sorted(self.supported_extensions))
        return f"{self.scanner_name}(extensions=[{extensions}])"
