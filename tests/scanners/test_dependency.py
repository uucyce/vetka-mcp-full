# ========================================
# MARKER: Phase 72.1 Foundation
# Created: 2026-01-19
# File: tests/scanners/test_dependency.py
# Purpose: Unit tests for Dependency dataclass
# ========================================
"""
Unit tests for Dependency dataclass.

Tests cover:
    - Basic creation and validation
    - Enum conversion
    - Serialization roundtrip
    - Edge cases and error handling
"""

import pytest
from datetime import datetime, timedelta

from src.scanners.dependency import Dependency, DependencyType
from src.scanners.exceptions import DependencyValidationError


class TestDependencyType:
    """Tests for DependencyType enum."""

    def test_all_types_have_string_values(self):
        """All enum members should have string values."""
        for dtype in DependencyType:
            assert isinstance(dtype.value, str)
            assert len(dtype.value) > 0

    def test_code_types_exist(self):
        """Code-related types should exist."""
        assert DependencyType.IMPORT.value == "import"
        assert DependencyType.REQUIRE.value == "require"

    def test_document_types_exist(self):
        """Document-related types should exist."""
        assert DependencyType.REFERENCE.value == "reference"
        assert DependencyType.CITATION.value == "citation"

    def test_semantic_types_exist(self):
        """Semantic/computed types should exist."""
        assert DependencyType.TEMPORAL_SEMANTIC.value == "temporal_semantic"
        assert DependencyType.PREREQUISITE.value == "prerequisite"


class TestDependencyCreation:
    """Tests for Dependency creation and validation."""

    def test_basic_creation(self):
        """Basic dependency creation with required fields."""
        dep = Dependency(
            target="main.py",
            source="utils.py",
            dependency_type=DependencyType.IMPORT,
            confidence=1.0
        )

        assert dep.target == "main.py"
        assert dep.source == "utils.py"
        assert dep.dependency_type == DependencyType.IMPORT
        assert dep.confidence == 1.0
        assert dep.line_number is None
        assert dep.context is None
        assert isinstance(dep.created_at, datetime)
        assert dep.metadata == {}

    def test_creation_with_all_fields(self):
        """Creation with all optional fields."""
        now = datetime.now()
        dep = Dependency(
            target="main.py",
            source="utils.py",
            dependency_type=DependencyType.IMPORT,
            confidence=0.95,
            line_number=42,
            context="from utils import helper",
            created_at=now,
            metadata={"author": "test", "version": 1}
        )

        assert dep.line_number == 42
        assert dep.context == "from utils import helper"
        assert dep.created_at == now
        assert dep.metadata == {"author": "test", "version": 1}

    def test_string_to_enum_conversion(self):
        """String dependency_type should auto-convert to enum."""
        dep = Dependency(
            target="doc.md",
            source="ref.txt",
            dependency_type="reference",
            confidence=0.8
        )

        assert isinstance(dep.dependency_type, DependencyType)
        assert dep.dependency_type == DependencyType.REFERENCE

    def test_invalid_enum_string(self):
        """Invalid string should raise DependencyValidationError."""
        with pytest.raises(DependencyValidationError, match="Invalid dependency type"):
            Dependency(
                target="a.py",
                source="b.py",
                dependency_type="invalid_type",
                confidence=1.0
            )


class TestDependencyValidation:
    """Tests for Dependency validation."""

    def test_confidence_valid_range(self):
        """Confidence values 0.0-1.0 should be accepted."""
        # Boundary values
        Dependency("a", "b", DependencyType.IMPORT, 0.0)
        Dependency("a", "b", DependencyType.IMPORT, 0.5)
        Dependency("a", "b", DependencyType.IMPORT, 1.0)

        # Integer 0 and 1 should work
        Dependency("a", "b", DependencyType.IMPORT, 0)
        Dependency("a", "b", DependencyType.IMPORT, 1)

    def test_confidence_below_range(self):
        """Confidence below 0.0 should raise error."""
        with pytest.raises(DependencyValidationError, match="must be 0.0-1.0"):
            Dependency("a", "b", DependencyType.IMPORT, -0.1)

    def test_confidence_above_range(self):
        """Confidence above 1.0 should raise error."""
        with pytest.raises(DependencyValidationError, match="must be 0.0-1.0"):
            Dependency("a", "b", DependencyType.IMPORT, 1.1)

    def test_confidence_not_a_number(self):
        """Non-numeric confidence should raise error."""
        with pytest.raises(DependencyValidationError, match="must be a number"):
            Dependency("a", "b", DependencyType.IMPORT, "high")  # type: ignore

    def test_empty_target(self):
        """Empty target path should raise error."""
        with pytest.raises(DependencyValidationError, match="Target path cannot be empty"):
            Dependency("", "source.py", DependencyType.IMPORT, 1.0)

    def test_empty_source(self):
        """Empty source path should raise error."""
        with pytest.raises(DependencyValidationError, match="Source path cannot be empty"):
            Dependency("target.py", "", DependencyType.IMPORT, 1.0)

    def test_none_target(self):
        """None target should raise error."""
        with pytest.raises(DependencyValidationError):
            Dependency(None, "source.py", DependencyType.IMPORT, 1.0)  # type: ignore

    def test_none_source(self):
        """None source should raise error."""
        with pytest.raises(DependencyValidationError):
            Dependency("target.py", None, DependencyType.IMPORT, 1.0)  # type: ignore

    def test_line_number_valid(self):
        """Valid line numbers should be accepted."""
        dep = Dependency("a", "b", DependencyType.IMPORT, 1.0, line_number=1)
        assert dep.line_number == 1

        dep = Dependency("a", "b", DependencyType.IMPORT, 1.0, line_number=9999)
        assert dep.line_number == 9999

    def test_line_number_zero(self):
        """Line number 0 should raise error (1-indexed)."""
        with pytest.raises(DependencyValidationError, match="positive integer"):
            Dependency("a", "b", DependencyType.IMPORT, 1.0, line_number=0)

    def test_line_number_negative(self):
        """Negative line number should raise error."""
        with pytest.raises(DependencyValidationError, match="positive integer"):
            Dependency("a", "b", DependencyType.IMPORT, 1.0, line_number=-1)


class TestDependencySerialization:
    """Tests for Dependency serialization."""

    def test_to_dict_basic(self):
        """to_dict should return proper dict structure."""
        dep = Dependency(
            target="main.py",
            source="utils.py",
            dependency_type=DependencyType.IMPORT,
            confidence=0.95
        )

        data = dep.to_dict()

        assert isinstance(data, dict)
        assert data['target'] == "main.py"
        assert data['source'] == "utils.py"
        assert data['dependency_type'] == "import"  # String, not enum
        assert data['confidence'] == 0.95
        assert isinstance(data['created_at'], str)  # ISO format

    def test_to_dict_with_metadata(self):
        """to_dict should include all optional fields."""
        dep = Dependency(
            target="main.py",
            source="utils.py",
            dependency_type=DependencyType.IMPORT,
            confidence=0.95,
            line_number=42,
            context="import utils",
            metadata={"key": "value"}
        )

        data = dep.to_dict()

        assert data['line_number'] == 42
        assert data['context'] == "import utils"
        assert data['metadata'] == {"key": "value"}

    def test_from_dict_basic(self):
        """from_dict should recreate Dependency."""
        data = {
            'target': 'main.py',
            'source': 'utils.py',
            'dependency_type': 'import',
            'confidence': 0.95,
            'line_number': None,
            'context': None,
            'created_at': '2026-01-19T12:00:00',
            'metadata': {}
        }

        dep = Dependency.from_dict(data)

        assert dep.target == 'main.py'
        assert dep.source == 'utils.py'
        assert dep.dependency_type == DependencyType.IMPORT
        assert dep.confidence == 0.95

    def test_roundtrip_serialization(self):
        """to_dict -> from_dict should preserve data."""
        original = Dependency(
            target="main.py",
            source="utils.py",
            dependency_type=DependencyType.IMPORT,
            confidence=0.95,
            line_number=42,
            context="from utils import helper",
            metadata={"author": "test"}
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = Dependency.from_dict(data)

        assert restored.target == original.target
        assert restored.source == original.source
        assert restored.dependency_type == original.dependency_type
        assert restored.confidence == original.confidence
        assert restored.line_number == original.line_number
        assert restored.context == original.context
        assert restored.metadata == original.metadata


class TestDependencyMethods:
    """Tests for Dependency helper methods."""

    def test_is_explicit_import(self):
        """IMPORT type should be explicit."""
        dep = Dependency("a", "b", DependencyType.IMPORT, 1.0)
        assert dep.is_explicit() is True
        assert dep.is_inferred() is False

    def test_is_explicit_reference(self):
        """REFERENCE type should be explicit."""
        dep = Dependency("a", "b", DependencyType.REFERENCE, 1.0)
        assert dep.is_explicit() is True

    def test_is_inferred_temporal_semantic(self):
        """TEMPORAL_SEMANTIC type should be inferred."""
        dep = Dependency("a", "b", DependencyType.TEMPORAL_SEMANTIC, 0.7)
        assert dep.is_inferred() is True
        assert dep.is_explicit() is False

    def test_is_inferred_prerequisite(self):
        """PREREQUISITE type should be inferred."""
        dep = Dependency("a", "b", DependencyType.PREREQUISITE, 0.6)
        assert dep.is_inferred() is True

    def test_repr_format(self):
        """__repr__ should be human-readable."""
        dep = Dependency(
            target="main.py",
            source="utils.py",
            dependency_type=DependencyType.IMPORT,
            confidence=0.95
        )

        repr_str = repr(dep)

        assert "utils.py" in repr_str
        assert "main.py" in repr_str
        assert "import" in repr_str
        assert "0.95" in repr_str

    def test_equality(self):
        """Dependencies with same target/source/type should be equal."""
        dep1 = Dependency("a", "b", DependencyType.IMPORT, 1.0)
        dep2 = Dependency("a", "b", DependencyType.IMPORT, 0.5)  # Different confidence

        assert dep1 == dep2  # Same target/source/type

    def test_inequality_different_target(self):
        """Dependencies with different targets should not be equal."""
        dep1 = Dependency("a", "b", DependencyType.IMPORT, 1.0)
        dep2 = Dependency("c", "b", DependencyType.IMPORT, 1.0)

        assert dep1 != dep2

    def test_inequality_different_type(self):
        """Dependencies with different types should not be equal."""
        dep1 = Dependency("a", "b", DependencyType.IMPORT, 1.0)
        dep2 = Dependency("a", "b", DependencyType.REFERENCE, 1.0)

        assert dep1 != dep2

    def test_hash_for_sets(self):
        """Dependencies should be usable in sets."""
        dep1 = Dependency("a", "b", DependencyType.IMPORT, 1.0)
        dep2 = Dependency("a", "b", DependencyType.IMPORT, 0.5)  # Same key
        dep3 = Dependency("c", "d", DependencyType.IMPORT, 1.0)

        deps_set = {dep1, dep2, dep3}

        assert len(deps_set) == 2  # dep1 and dep2 are equal
