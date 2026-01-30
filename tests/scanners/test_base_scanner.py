# ========================================
# MARKER: Phase 72.1 Foundation
# Created: 2026-01-19
# File: tests/scanners/test_base_scanner.py
# Purpose: Unit tests + Contract tests for BaseScanner ABC
# ========================================
"""
Unit tests and Contract tests for BaseScanner ABC.

Tests cover:
    - Abstract class behavior
    - Default implementations (can_scan, validate_content)
    - Contract tests for any scanner implementation

Contract tests ensure any future scanner (Video, Audio, Document)
automatically validates against the BaseScanner interface.
"""

import pytest
from typing import List, Set

from src.scanners.base_scanner import BaseScanner
from src.scanners.dependency import Dependency, DependencyType
from src.scanners.exceptions import UnsupportedFileTypeError


# =============================================================================
# Mock Implementations for Testing
# =============================================================================

class MockPythonScanner(BaseScanner):
    """Mock scanner for Python files."""

    @property
    def supported_extensions(self) -> Set[str]:
        return {'.py', '.pyi'}

    def extract_dependencies(self, file_path: str, content: str) -> List[Dependency]:
        """Simple mock: return one dependency if 'import' found."""
        dependencies = []
        if 'import' in content:
            dependencies.append(
                Dependency(
                    target=file_path,
                    source="mock_module.py",
                    dependency_type=DependencyType.IMPORT,
                    confidence=1.0,
                    context="mock import"
                )
            )
        return dependencies


class MockEmptyScanner(BaseScanner):
    """Scanner that always returns empty results."""

    @property
    def supported_extensions(self) -> Set[str]:
        return {'.empty'}

    def extract_dependencies(self, file_path: str, content: str) -> List[Dependency]:
        return []


class MockMultiExtensionScanner(BaseScanner):
    """Scanner supporting multiple extensions."""

    @property
    def supported_extensions(self) -> Set[str]:
        return {'.js', '.jsx', '.ts', '.tsx', '.mjs'}

    def extract_dependencies(self, file_path: str, content: str) -> List[Dependency]:
        return []


# =============================================================================
# Unit Tests for BaseScanner
# =============================================================================

class TestBaseScannerAbstract:
    """Tests for BaseScanner abstract behavior."""

    def test_cannot_instantiate_directly(self):
        """BaseScanner should not be instantiable."""
        with pytest.raises(TypeError, match="abstract"):
            BaseScanner()  # type: ignore

    def test_must_implement_supported_extensions(self):
        """Subclass without supported_extensions should fail."""

        class IncompleteScanner(BaseScanner):
            def extract_dependencies(self, file_path: str, content: str) -> List[Dependency]:
                return []

        with pytest.raises(TypeError):
            IncompleteScanner()  # type: ignore

    def test_must_implement_extract_dependencies(self):
        """Subclass without extract_dependencies should fail."""

        class IncompleteScanner(BaseScanner):
            @property
            def supported_extensions(self) -> Set[str]:
                return {'.py'}

        with pytest.raises(TypeError):
            IncompleteScanner()  # type: ignore


class TestBaseScannerCanScan:
    """Tests for can_scan method."""

    def test_can_scan_supported_extension(self):
        """can_scan returns True for supported extensions."""
        scanner = MockPythonScanner()

        assert scanner.can_scan("test.py") is True
        assert scanner.can_scan("module.pyi") is True
        assert scanner.can_scan("/path/to/deep/file.py") is True

    def test_can_scan_unsupported_extension(self):
        """can_scan returns False for unsupported extensions."""
        scanner = MockPythonScanner()

        assert scanner.can_scan("test.js") is False
        assert scanner.can_scan("document.txt") is False
        assert scanner.can_scan("video.mp4") is False

    def test_can_scan_case_insensitive(self):
        """can_scan should be case-insensitive."""
        scanner = MockPythonScanner()

        assert scanner.can_scan("test.PY") is True
        assert scanner.can_scan("test.Py") is True
        assert scanner.can_scan("test.pYi") is True

    def test_can_scan_no_extension(self):
        """Files without extension should not match."""
        scanner = MockPythonScanner()

        assert scanner.can_scan("Makefile") is False
        assert scanner.can_scan("README") is False

    def test_can_scan_hidden_files(self):
        """Hidden files should be checked by extension."""
        scanner = MockPythonScanner()

        assert scanner.can_scan(".hidden.py") is True
        assert scanner.can_scan(".gitignore") is False


class TestBaseScannerValidateContent:
    """Tests for validate_content method."""

    def test_validate_content_non_empty(self):
        """Non-empty content should be valid."""
        scanner = MockPythonScanner()

        assert scanner.validate_content("import os") is True
        assert scanner.validate_content("x = 1") is True
        assert scanner.validate_content("a") is True

    def test_validate_content_empty(self):
        """Empty content should be invalid."""
        scanner = MockPythonScanner()

        assert scanner.validate_content("") is False

    def test_validate_content_whitespace_only(self):
        """Whitespace-only content should be invalid."""
        scanner = MockPythonScanner()

        assert scanner.validate_content("   ") is False
        assert scanner.validate_content("\n\n\n") is False
        assert scanner.validate_content("\t  \n  ") is False


class TestBaseScannerScanFile:
    """Tests for scan_file high-level method."""

    def test_scan_file_success(self):
        """scan_file should return dependencies for valid input."""
        scanner = MockPythonScanner()

        deps = scanner.scan_file("test.py", "import os")

        assert len(deps) == 1
        assert deps[0].dependency_type == DependencyType.IMPORT

    def test_scan_file_unsupported_type(self):
        """scan_file should raise for unsupported file types."""
        scanner = MockPythonScanner()

        with pytest.raises(UnsupportedFileTypeError, match="does not support"):
            scanner.scan_file("test.js", "import foo")

    def test_scan_file_empty_content(self):
        """scan_file should return empty list for empty content."""
        scanner = MockPythonScanner()

        deps = scanner.scan_file("test.py", "")

        assert deps == []

    def test_scan_file_no_dependencies(self):
        """scan_file should return empty list when no deps found."""
        scanner = MockPythonScanner()

        deps = scanner.scan_file("test.py", "x = 1\ny = 2")

        assert deps == []


class TestBaseScannerRepr:
    """Tests for string representation."""

    def test_repr_includes_class_name(self):
        """__repr__ should include class name."""
        scanner = MockPythonScanner()
        repr_str = repr(scanner)

        assert "MockPythonScanner" in repr_str

    def test_repr_includes_extensions(self):
        """__repr__ should include supported extensions."""
        scanner = MockPythonScanner()
        repr_str = repr(scanner)

        assert ".py" in repr_str
        assert ".pyi" in repr_str

    def test_scanner_name_property(self):
        """scanner_name should return class name."""
        scanner = MockPythonScanner()

        assert scanner.scanner_name == "MockPythonScanner"


# =============================================================================
# CONTRACT TESTS
# These tests validate ANY scanner implementation against the BaseScanner contract.
# Use these when implementing new scanners (Video, Audio, Document, etc.)
# =============================================================================

class ScannerContractTests:
    """
    Contract tests for BaseScanner implementations.

    Any scanner implementation should pass ALL of these tests.
    To use: create a pytest fixture that returns your scanner instance,
    then run these tests against it.

    Example:
        @pytest.fixture
        def scanner():
            return MyNewScanner()

        class TestMyNewScannerContract(ScannerContractTests):
            pass
    """

    @pytest.fixture
    def scanner(self) -> BaseScanner:
        """Override this fixture in subclass to provide scanner instance."""
        raise NotImplementedError("Subclass must provide scanner fixture")

    def test_contract_has_supported_extensions(self, scanner: BaseScanner):
        """Scanner must have supported_extensions property."""
        extensions = scanner.supported_extensions

        assert isinstance(extensions, set), \
            f"supported_extensions must be a set, got {type(extensions)}"
        assert len(extensions) > 0, \
            "supported_extensions must not be empty"

    def test_contract_extensions_are_lowercase_with_dot(self, scanner: BaseScanner):
        """All extensions must be lowercase and start with dot."""
        for ext in scanner.supported_extensions:
            assert ext.startswith('.'), \
                f"Extension must start with dot: {ext}"
            assert ext == ext.lower(), \
                f"Extension must be lowercase: {ext}"

    def test_contract_can_scan_returns_bool(self, scanner: BaseScanner):
        """can_scan must return boolean."""
        result = scanner.can_scan("test.xyz")

        assert isinstance(result, bool), \
            f"can_scan must return bool, got {type(result)}"

    def test_contract_extract_dependencies_returns_list(self, scanner: BaseScanner):
        """extract_dependencies must return a list."""
        # Use first supported extension
        ext = next(iter(scanner.supported_extensions))
        result = scanner.extract_dependencies(f"test{ext}", "content")

        assert isinstance(result, list), \
            f"extract_dependencies must return list, got {type(result)}"

    def test_contract_dependencies_are_valid(self, scanner: BaseScanner):
        """All returned dependencies must be valid Dependency objects."""
        ext = next(iter(scanner.supported_extensions))
        deps = scanner.extract_dependencies(f"test{ext}", "some content here")

        for dep in deps:
            assert isinstance(dep, Dependency), \
                f"All items must be Dependency, got {type(dep)}"
            assert 0.0 <= dep.confidence <= 1.0, \
                f"Confidence out of range: {dep.confidence}"
            assert dep.target, "Target path cannot be empty"
            assert dep.source, "Source path cannot be empty"

    def test_contract_validate_content_returns_bool(self, scanner: BaseScanner):
        """validate_content must return boolean."""
        result = scanner.validate_content("test content")

        assert isinstance(result, bool), \
            f"validate_content must return bool, got {type(result)}"

    def test_contract_scan_file_respects_can_scan(self, scanner: BaseScanner):
        """scan_file should raise for unsupported files."""
        # Find an extension that's NOT supported
        unsupported = ".definitely_not_supported_xyz"
        assert not scanner.can_scan(f"test{unsupported}")

        with pytest.raises(UnsupportedFileTypeError):
            scanner.scan_file(f"test{unsupported}", "content")

    def test_contract_empty_content_no_crash(self, scanner: BaseScanner):
        """Scanner should handle empty content gracefully."""
        ext = next(iter(scanner.supported_extensions))

        # Should not raise
        result = scanner.scan_file(f"test{ext}", "")
        assert isinstance(result, list)

    def test_contract_large_content_no_crash(self, scanner: BaseScanner):
        """Scanner should handle large content without crashing."""
        ext = next(iter(scanner.supported_extensions))
        large_content = "x = 1\n" * 10000  # 10K lines

        # Should not raise
        result = scanner.extract_dependencies(f"test{ext}", large_content)
        assert isinstance(result, list)


# =============================================================================
# Apply Contract Tests to Mock Implementations
# =============================================================================

class TestMockPythonScannerContract(ScannerContractTests):
    """Contract tests for MockPythonScanner."""

    @pytest.fixture
    def scanner(self) -> BaseScanner:
        return MockPythonScanner()


class TestMockEmptyScannerContract(ScannerContractTests):
    """Contract tests for MockEmptyScanner."""

    @pytest.fixture
    def scanner(self) -> BaseScanner:
        return MockEmptyScanner()


class TestMockMultiExtensionScannerContract(ScannerContractTests):
    """Contract tests for MockMultiExtensionScanner."""

    @pytest.fixture
    def scanner(self) -> BaseScanner:
        return MockMultiExtensionScanner()
