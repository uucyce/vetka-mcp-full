# ========================================
# MARKER: Phase 72.1-72.4 Dependency Scanning Pipeline
# Updated: 2026-01-19
# File: src/scanners/__init__.py
# Purpose: Export all scanner components
# ========================================
"""
VETKA Scanners Module - Package exports for file scanning and indexing.

@status: active
@phase: 96
@depends: local_project_scanner, file_watcher, qdrant_updater, dependency, base_scanner,
          import_resolver, path_utils, python_scanner, known_packages, dependency_calculator
@used_by: src.api.routes.watcher_routes, src.api.routes.tree_routes, src.initialization.components_init

Legacy (Phase 12 + Phase 54):
    - LocalProjectScanner
    - VetkaFileWatcher, AdaptiveScanner
    - QdrantIncrementalUpdater

Phase 72.1 Foundation:
    - Dependency, DependencyType (universal structure)
    - BaseScanner (abstract base class)
    - Scanner exceptions

Phase 72.2 Import Resolution:
    - ImportResolver, ResolvedImport
    - Path utilities (get_python_files, is_package, get_module_name)

Phase 72.3 Python Scanner:
    - PythonScanner (AST-based dependency extraction)
    - ExtractedImport (raw import structure)
    - Known packages registry (PYTHON_STDLIB, PYTHON_THIRD_PARTY)

Phase 72.4 Dependency Scoring:
    - DependencyCalculator (Kimi K2 formula)
    - ScoringConfig, ScoringInput, ScoringResult
    - QdrantSemanticProvider, combine_import_and_semantic
"""

# Legacy exports (Phase 12 + Phase 54)
from .local_project_scanner import LocalProjectScanner
from .file_watcher import VetkaFileWatcher, get_watcher, AdaptiveScanner
from .qdrant_updater import QdrantIncrementalUpdater, get_qdrant_updater

# Phase 72.1: Foundation
from .dependency import Dependency, DependencyType
from .base_scanner import BaseScanner
from .exceptions import (
    ScannerError,
    UnsupportedFileTypeError,
    ParseError,
    DependencyValidationError,
)

# Phase 72.2: Import Resolution
from .import_resolver import ImportResolver, ResolvedImport
from .path_utils import (
    get_python_files,
    is_package,
    get_module_name,
    path_to_module_candidates,
    normalize_path,
)

# Phase 72.3: Python Scanner
from .python_scanner import PythonScanner, ExtractedImport
from .known_packages import (
    PYTHON_STDLIB,
    PYTHON_THIRD_PARTY,
    get_all_external_python,
    is_external_package,
)

# Phase 72.4: Dependency Scoring
from .dependency_calculator import (
    DependencyCalculator,
    ScoringConfig,
    ScoringInput,
    ScoringResult,
    FileMetadata,
    QdrantSemanticProvider,
    calculate_dependency_score,
    combine_import_and_semantic,
)

__all__ = [
    # Legacy
    'LocalProjectScanner',
    'VetkaFileWatcher',
    'get_watcher',
    'AdaptiveScanner',
    'QdrantIncrementalUpdater',
    'get_qdrant_updater',
    # Phase 72.1
    'Dependency',
    'DependencyType',
    'BaseScanner',
    'ScannerError',
    'UnsupportedFileTypeError',
    'ParseError',
    'DependencyValidationError',
    # Phase 72.2
    'ImportResolver',
    'ResolvedImport',
    'get_python_files',
    'is_package',
    'get_module_name',
    'path_to_module_candidates',
    'normalize_path',
    # Phase 72.3
    'PythonScanner',
    'ExtractedImport',
    'PYTHON_STDLIB',
    'PYTHON_THIRD_PARTY',
    'get_all_external_python',
    'is_external_package',
    # Phase 72.4
    'DependencyCalculator',
    'ScoringConfig',
    'ScoringInput',
    'ScoringResult',
    'FileMetadata',
    'QdrantSemanticProvider',
    'calculate_dependency_score',
    'combine_import_and_semantic',
]
