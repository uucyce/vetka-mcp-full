# ========================================
# MARKER: Phase 72.1 Foundation
# Created: 2026-01-19
# File: src/scanners/exceptions.py
# Purpose: Custom exceptions for dependency scanning system
# ========================================
"""
Custom exceptions for VETKA dependency scanning system.

Hierarchy:
    ScannerError (base)
    ├── UnsupportedFileTypeError
    ├── ParseError
    └── DependencyValidationError

@status: active
@phase: 96
@depends: builtins
@used_by: base_scanner, dependency, python_scanner
"""


class ScannerError(Exception):
    """
    Base exception for all scanner-related errors.

    All scanner exceptions inherit from this class,
    allowing for catch-all handling when needed.
    """
    pass


class UnsupportedFileTypeError(ScannerError):
    """
    Raised when attempting to scan a file type not supported by the scanner.

    Example:
        Trying to scan a .mp4 file with CodeScanner
    """
    pass


class ParseError(ScannerError):
    """
    Raised when content parsing fails.

    Examples:
        - Invalid Python syntax for AST parsing
        - Malformed JSON/YAML
        - Corrupted file content
    """
    pass


class DependencyValidationError(ScannerError):
    """
    Raised when a Dependency object fails validation.

    Examples:
        - Confidence score out of range (not 0.0-1.0)
        - Empty target or source paths
        - Invalid dependency type
    """
    pass
