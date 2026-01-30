# ========================================
# MARKER: Phase 72.1 Foundation
# Created: 2026-01-19
# File: src/scanners/dependency.py
# Purpose: Universal dependency structure for all content types
# ========================================
"""
Universal dependency structure for VETKA.

Supports all content types in the "Periodic Table":
- Code: imports, requires
- Documents: references, citations
- Media: temporal sequences, remixes
- Books: chapters, footnotes
- Videos: timestamps, continuations

@status: active
@phase: 96
@depends: dataclasses, datetime, enum, exceptions
@used_by: python_scanner, dependency_calculator, base_scanner
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from .exceptions import DependencyValidationError


class DependencyType(Enum):
    """
    Types of dependencies between content.

    Extensible for future content types (video chapters, audio segments, etc.)
    """
    # Code dependencies
    IMPORT = "import"                        # Explicit import (Python, JS, etc.)
    REQUIRE = "require"                      # CommonJS require()

    # Document dependencies
    REFERENCE = "reference"                  # Explicit reference (URL, path)
    CITATION = "citation"                    # Academic citation
    FOOTNOTE = "footnote"                    # Footnote reference

    # Semantic dependencies (computed)
    TEMPORAL_SEMANTIC = "temporal_semantic"  # Time + semantic similarity
    PREREQUISITE = "prerequisite"            # Logical prerequisite

    # Media dependencies (future)
    DERIVED = "derived"                      # Derived work (remix, fork)
    CONTINUATION = "continuation"            # Sequel, next part
    CHAPTER = "chapter"                      # Chapter reference


@dataclass
class Dependency:
    """
    Universal dependency structure: A -> B means B depends on A.

    Examples:
        Code: main.py imports utils.py
              -> Dependency(target="main.py", source="utils.py", type=IMPORT)

        Doc:  report.md references data.csv
              -> Dependency(target="report.md", source="data.csv", type=REFERENCE)

        Video: tutorial_02.mp4 continues tutorial_01.mp4
               -> Dependency(target="tutorial_02.mp4", source="tutorial_01.mp4",
                             type=CONTINUATION)

    Attributes:
        target: File that depends on source (consumer)
        source: File being depended upon (provider)
        dependency_type: Type of dependency relationship
        confidence: Score 0.0-1.0 (1.0 = explicit import, lower = inferred)
        line_number: For code - line where import occurs
        context: Context string (e.g., "from utils import helper")
        created_at: When this dependency was detected
        metadata: Additional scanner-specific data
    """
    target: str                              # File that depends (consumer)
    source: str                              # File depended upon (provider)
    dependency_type: DependencyType          # Type of dependency
    confidence: float                        # Score 0.0-1.0

    # Optional metadata
    line_number: Optional[int] = None        # Line number in source code
    context: Optional[str] = None            # Context of the dependency
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate dependency after creation."""
        # Convert string to enum if needed
        if isinstance(self.dependency_type, str):
            try:
                self.dependency_type = DependencyType(self.dependency_type)
            except ValueError as e:
                raise DependencyValidationError(
                    f"Invalid dependency type: {self.dependency_type}. "
                    f"Valid types: {[t.value for t in DependencyType]}"
                ) from e

        # Validate confidence range
        if not isinstance(self.confidence, (int, float)):
            raise DependencyValidationError(
                f"Confidence must be a number, got {type(self.confidence).__name__}"
            )
        if not 0.0 <= self.confidence <= 1.0:
            raise DependencyValidationError(
                f"Confidence must be 0.0-1.0, got {self.confidence}"
            )

        # Validate paths not empty
        if not self.target or not isinstance(self.target, str):
            raise DependencyValidationError(
                "Target path cannot be empty and must be a string"
            )
        if not self.source or not isinstance(self.source, str):
            raise DependencyValidationError(
                "Source path cannot be empty and must be a string"
            )

        # Validate line_number if provided
        if self.line_number is not None:
            if not isinstance(self.line_number, int) or self.line_number < 1:
                raise DependencyValidationError(
                    f"Line number must be a positive integer, got {self.line_number}"
                )

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dict for JSON/storage.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            'target': self.target,
            'source': self.source,
            'dependency_type': self.dependency_type.value,
            'confidence': self.confidence,
            'line_number': self.line_number,
            'context': self.context,
            'created_at': self.created_at.isoformat(),
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Dependency':
        """
        Deserialize from dict.

        Args:
            data: Dictionary with dependency fields

        Returns:
            New Dependency instance

        Raises:
            DependencyValidationError: If data is invalid
        """
        data = data.copy()

        # Convert dependency_type string to enum
        if 'dependency_type' in data and isinstance(data['dependency_type'], str):
            data['dependency_type'] = DependencyType(data['dependency_type'])

        # Convert created_at string to datetime
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])

        return cls(**data)

    def is_explicit(self) -> bool:
        """
        Check if this is an explicit (high-confidence) dependency.

        Explicit dependencies come from direct code analysis (imports, requires)
        rather than inference (semantic similarity).

        Returns:
            True if dependency is explicit (import, require, reference)
        """
        explicit_types = {
            DependencyType.IMPORT,
            DependencyType.REQUIRE,
            DependencyType.REFERENCE,
            DependencyType.CITATION,
            DependencyType.FOOTNOTE,
        }
        return self.dependency_type in explicit_types

    def is_inferred(self) -> bool:
        """
        Check if this is an inferred (computed) dependency.

        Inferred dependencies are calculated from semantic similarity
        and temporal relationships.

        Returns:
            True if dependency is inferred
        """
        return not self.is_explicit()

    def __repr__(self) -> str:
        """Human-readable representation."""
        return (
            f"Dependency({self.source} -> {self.target}, "
            f"type={self.dependency_type.value}, conf={self.confidence:.2f})"
        )

    def __eq__(self, other: object) -> bool:
        """Check equality based on target, source, and type."""
        if not isinstance(other, Dependency):
            return NotImplemented
        return (
            self.target == other.target and
            self.source == other.source and
            self.dependency_type == other.dependency_type
        )

    def __hash__(self) -> int:
        """Hash based on target, source, and type for use in sets."""
        return hash((self.target, self.source, self.dependency_type))
