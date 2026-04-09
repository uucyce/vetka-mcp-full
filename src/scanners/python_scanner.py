# ========================================
# MARKER: Phase 72.3 Python Scanner
# Date: 2026-01-19
# File: src/scanners/python_scanner.py
# Purpose: AST-based Python dependency scanner
# Integrates: BaseScanner (72.1), ImportResolver (72.2)
# ========================================
"""
Python Dependency Scanner for VETKA Phase 72.3

Uses AST (Abstract Syntax Tree) to extract imports from Python files,
then uses ImportResolver to resolve them to actual file paths.

Features:
- Handles all Python import forms (import X, from X import Y)
- Detects conditional imports (TYPE_CHECKING blocks)
- Detects dynamic imports (__import__, importlib)
- Extracts line numbers and context for each import
- Integrates with ImportResolver for path resolution

Statistics from VETKA (Haiku audit):
- 1,156 absolute imports
- 160 relative imports
- 4 dynamic imports
- 3 conditional imports (TYPE_CHECKING)

@status: active
@phase: 96
@depends: ast, base_scanner, dependency, exceptions, import_resolver, known_packages
@used_by: dependency_calculator, embedding_pipeline
"""

import ast
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, Tuple

from .base_scanner import BaseScanner
from .dependency import Dependency, DependencyType
from .exceptions import ParseError
from .import_resolver import ImportResolver, ResolvedImport
from .known_packages import is_external_package

logger = logging.getLogger(__name__)


@dataclass
class ExtractedImport:
    """
    Raw import extracted from AST before resolution.

    Attributes:
        module: Module name (e.g., "os", "src.utils", ".helper")
        names: Imported names (e.g., ["path", "join"] from "from os import path, join")
        line_number: Line number in source file
        is_relative: True if starts with dots (relative import)
        level: Number of dots in relative import (0 for absolute)
        is_conditional: True if inside TYPE_CHECKING block
        is_dynamic: True if dynamic import (__import__, importlib.import_module)
        context: Original import statement as string
    """
    module: str
    names: List[str]
    line_number: int
    is_relative: bool = False
    level: int = 0
    is_conditional: bool = False
    is_dynamic: bool = False
    context: Optional[str] = None


class PythonScanner(BaseScanner):
    """
    Python dependency scanner using AST parsing.

    Inherits from BaseScanner and implements:
    - supported_extensions: {'.py', '.pyi'}
    - extract_dependencies: Parse imports and resolve to file paths

    Usage:
        >>> scanner = PythonScanner(
        ...     project_root=Path("/project"),
        ...     scanned_files=["/project/main.py", "/project/utils.py"]
        ... )
        >>> deps = scanner.scan_file("/project/main.py", content)
        >>> for dep in deps:
        ...     print(f"{dep.source} -> {dep.target}")

    Configuration:
        - project_root: Root directory for import resolution
        - scanned_files: List of all Python files (for building module index)
        - src_roots: Additional source roots (e.g., ["src"])
        - include_external: Whether to include external dependencies (default: False)
    """

    def __init__(
        self,
        project_root: Path,
        scanned_files: Optional[List[str]] = None,
        src_roots: Optional[List[str]] = None,
        include_external: bool = False
    ):
        """
        Initialize Python scanner.

        Args:
            project_root: Project root directory
            scanned_files: List of Python files for module index (optional)
            src_roots: Additional source roots for import resolution
            include_external: Include external dependencies in output
        """
        self.project_root = Path(project_root).resolve()
        self.scanned_files = scanned_files or []
        self.src_roots = src_roots or []
        self.include_external = include_external

        # Initialize ImportResolver if we have files
        self._resolver: Optional[ImportResolver] = None
        if self.scanned_files:
            self._init_resolver()

    def _init_resolver(self) -> None:
        """Initialize or reinitialize the ImportResolver."""
        self._resolver = ImportResolver(
            project_root=self.project_root,
            scanned_files=self.scanned_files,
            src_roots=self.src_roots
        )

    def update_files(self, scanned_files: List[str]) -> None:
        """
        Update the list of scanned files and rebuild module index.

        Call this when files are added/removed from the project.

        Args:
            scanned_files: Updated list of Python file paths
        """
        self.scanned_files = scanned_files
        self._init_resolver()

    @property
    def supported_extensions(self) -> Set[str]:
        """Python file extensions."""
        return {'.py', '.pyi'}

    @property
    def resolver(self) -> Optional[ImportResolver]:
        """Get the ImportResolver instance."""
        return self._resolver

    def extract_dependencies(
        self,
        file_path: str,
        content: str
    ) -> List[Dependency]:
        """
        Extract dependencies from Python file content.

        Args:
            file_path: Path to the Python file
            content: File content as string

        Returns:
            List of Dependency objects

        Raises:
            ParseError: If Python syntax is invalid
        """
        # Step 1: Parse AST and extract raw imports
        try:
            raw_imports = self._extract_imports_from_ast(content, file_path)
        except SyntaxError as e:
            raise ParseError(
                f"Python syntax error in {file_path}: {e.msg} "
                f"(line {e.lineno})"
            ) from e

        # Step 2: Resolve imports to file paths
        dependencies: List[Dependency] = []

        for raw_import in raw_imports:
            resolved = self._resolve_import(raw_import, file_path)

            # Skip external packages unless configured to include them
            if resolved.resolution_type == "external" and not self.include_external:
                continue

            # Skip unresolved imports that are likely external
            if resolved.resolution_type == "unresolved":
                # Check if it looks like an external package
                base_module = raw_import.module.split('.')[0].lstrip('.')
                if is_external_package(base_module):
                    continue

            # Create Dependency object
            dep = self._create_dependency(
                raw_import=raw_import,
                resolved=resolved,
                file_path=file_path
            )
            dependencies.append(dep)

        logger.debug(
            f"Extracted {len(dependencies)} dependencies from {file_path} "
            f"({len(raw_imports)} total imports)"
        )

        return dependencies

    def _extract_imports_from_ast(
        self,
        content: str,
        file_path: str
    ) -> List[ExtractedImport]:
        """
        Parse Python AST and extract import statements.

        Handles:
        - import X
        - import X as Y
        - from X import Y
        - from X import Y as Z
        - from . import X (relative)
        - from .. import X (parent relative)
        - TYPE_CHECKING conditional imports
        - Dynamic imports via __import__ and importlib
        """
        tree = ast.parse(content, filename=file_path)
        imports: List[ExtractedImport] = []

        # Track if we're inside TYPE_CHECKING block
        type_checking_lines: Set[int] = self._find_type_checking_lines(tree)

        for node in ast.walk(tree):
            # Handle: import X, import X as Y
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(ExtractedImport(
                        module=alias.name,
                        names=[alias.asname or alias.name],
                        line_number=node.lineno,
                        is_relative=False,
                        level=0,
                        is_conditional=node.lineno in type_checking_lines,
                        context=f"import {alias.name}"
                    ))

            # Handle: from X import Y, from . import Y
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                names = [alias.name for alias in node.names]

                # Build context string
                dots = '.' * node.level
                if module:
                    context = f"from {dots}{module} import {', '.join(names)}"
                else:
                    context = f"from {dots} import {', '.join(names)}"

                # For relative imports, combine level indicator with module
                if node.level > 0:
                    full_module = dots + module
                else:
                    full_module = module

                imports.append(ExtractedImport(
                    module=full_module,
                    names=names,
                    line_number=node.lineno,
                    is_relative=node.level > 0,
                    level=node.level,
                    is_conditional=node.lineno in type_checking_lines,
                    context=context
                ))

            # Handle dynamic imports: __import__('module')
            elif isinstance(node, ast.Call):
                dynamic_import = self._check_dynamic_import(node)
                if dynamic_import:
                    imports.append(dynamic_import)

        return imports

    def _find_type_checking_lines(self, tree: ast.AST) -> Set[int]:
        """
        Find all line numbers inside TYPE_CHECKING blocks.

        Pattern:
            if TYPE_CHECKING:
                from typing import X  # line is in this set
        """
        type_checking_lines: Set[int] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check if condition is TYPE_CHECKING
                if self._is_type_checking_condition(node.test):
                    # Mark all lines in the body
                    for child in ast.walk(node):
                        if hasattr(child, 'lineno'):
                            type_checking_lines.add(child.lineno)

        return type_checking_lines

    def _is_type_checking_condition(self, node: ast.expr) -> bool:
        """Check if an expression is TYPE_CHECKING."""
        # Direct: if TYPE_CHECKING:
        if isinstance(node, ast.Name) and node.id == 'TYPE_CHECKING':
            return True

        # Attribute: if typing.TYPE_CHECKING:
        if isinstance(node, ast.Attribute) and node.attr == 'TYPE_CHECKING':
            return True

        return False

    def _check_dynamic_import(self, node: ast.Call) -> Optional[ExtractedImport]:
        """
        Check if a Call node is a dynamic import.

        Handles:
        - __import__('module')
        - importlib.import_module('module')
        """
        func = node.func

        # Check for __import__
        if isinstance(func, ast.Name) and func.id == '__import__':
            if node.args and isinstance(node.args[0], ast.Constant):
                module_name = str(node.args[0].value)
                return ExtractedImport(
                    module=module_name,
                    names=[],
                    line_number=node.lineno,
                    is_dynamic=True,
                    context=f"__import__('{module_name}')"
                )

        # Check for importlib.import_module
        if isinstance(func, ast.Attribute) and func.attr == 'import_module':
            if isinstance(func.value, ast.Name) and func.value.id == 'importlib':
                if node.args and isinstance(node.args[0], ast.Constant):
                    module_name = str(node.args[0].value)
                    return ExtractedImport(
                        module=module_name,
                        names=[],
                        line_number=node.lineno,
                        is_dynamic=True,
                        context=f"importlib.import_module('{module_name}')"
                    )

        return None

    def _resolve_import(
        self,
        raw_import: ExtractedImport,
        file_path: str
    ) -> ResolvedImport:
        """
        Resolve an extracted import to a file path.

        Uses ImportResolver if available, otherwise returns unresolved.
        """
        if not self._resolver:
            # No resolver - return basic resolution
            return ResolvedImport(
                import_name=raw_import.module,
                resolved_path=None,
                resolution_type="unresolved",
                confidence=0.0
            )

        return self._resolver.resolve(
            import_name=raw_import.module,
            from_file_path=file_path,
            is_dynamic=raw_import.is_dynamic,
            is_conditional=raw_import.is_conditional
        )

    def _create_dependency(
        self,
        raw_import: ExtractedImport,
        resolved: ResolvedImport,
        file_path: str
    ) -> Dependency:
        """
        Create a Dependency object from resolved import.

        Args:
            raw_import: Original extracted import
            resolved: Resolution result
            file_path: Source file path

        Returns:
            Dependency object
        """
        # Use resolved path if available, otherwise use module name
        source = resolved.resolved_path or raw_import.module

        # Build metadata
        metadata = {
            'resolution_type': resolved.resolution_type,
            'is_relative': raw_import.is_relative,
            'level': raw_import.level,
            'imported_names': raw_import.names,
        }

        if raw_import.is_dynamic:
            metadata['is_dynamic'] = True
        if raw_import.is_conditional:
            metadata['is_conditional'] = True

        return Dependency(
            target=file_path,
            source=source,
            dependency_type=DependencyType.IMPORT,
            confidence=resolved.confidence,
            line_number=raw_import.line_number,
            context=raw_import.context,
            metadata=metadata
        )

    def extract_imports_only(
        self,
        content: str,
        file_path: str = "<string>"
    ) -> List[ExtractedImport]:
        """
        Extract raw imports without resolution.

        Useful for analysis and debugging.

        Args:
            content: Python source code
            file_path: Optional file path for error messages

        Returns:
            List of ExtractedImport objects
        """
        try:
            return self._extract_imports_from_ast(content, file_path)
        except SyntaxError as e:
            raise ParseError(
                f"Python syntax error: {e.msg} (line {e.lineno})"
            ) from e

    def get_statistics(self) -> dict:
        """
        Get scanner statistics.

        Returns:
            Dict with scanner and resolver statistics
        """
        stats = {
            'scanner': self.scanner_name,
            'extensions': list(self.supported_extensions),
            'scanned_files': len(self.scanned_files),
            'include_external': self.include_external,
        }

        if self._resolver:
            stats['resolver'] = self._resolver.get_statistics()

        return stats
