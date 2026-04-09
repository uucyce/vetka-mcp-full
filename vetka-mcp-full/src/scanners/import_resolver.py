# ========================================
# MARKER: Phase 72.2 Python Import Resolution
# Date: 2026-01-19
# File: src/scanners/import_resolver.py
# Purpose: Resolve Python imports to file paths
# Research: IMPORT_PATTERNS_AUDIT.md (Haiku audit)
# Edge Cases: 7 critical cases documented
# ========================================
"""
Python Import Resolution System for VETKA Phase 72.2

Resolves import statements to actual file paths using:
1. Module index (O(1) lookup)
2. Relative path resolution (., .., ...)
3. Fuzzy fallback (try extensions)

Statistics from VETKA project (Haiku audit):
- 1,156 absolute imports (246 unique)
- 160 relative imports (132 unique)
- 302 local project imports (189 unique)
- 4 dynamic imports
- 3 conditional imports (TYPE_CHECKING)

7 Critical Edge Cases Handled:
1. Relative imports (., .., ...)
2. Circular dependencies (no crash - handled via TYPE_CHECKING at runtime)
3. Dynamic/conditional imports (marked as special type)
4. Package vs module distinction (__init__.py handling)
5. Namespaced imports (dotted paths like foo.bar.baz)
6. External vs internal packages (stdlib detection)
7. Syntax errors / out-of-bounds (graceful fallback)

@status: active
@phase: 96
@depends: dataclasses, pathlib, path_utils, known_packages
@used_by: python_scanner
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import logging

from .path_utils import path_to_module_candidates
from .known_packages import get_all_external_python

logger = logging.getLogger(__name__)


@dataclass
class ResolvedImport:
    """
    Result of import resolution.

    Attributes:
        import_name: Original import statement ("utils", ".helper", "foo.bar")
        resolved_path: Resolved absolute file path, or None if unresolved
        resolution_type: How the import was resolved:
            - "exact": Direct match in module index
            - "relative": Resolved via relative path (., ..)
            - "fuzzy": Found via fuzzy matching (extensions)
            - "external": Standard library or third-party package
            - "dynamic": Dynamic import (__import__, importlib)
            - "conditional": Inside TYPE_CHECKING block
            - "unresolved": Could not resolve
        confidence: Resolution confidence score:
            - 1.0: Exact match or known external
            - 0.7: Fuzzy match
            - 0.0: Unresolved
    """
    import_name: str
    resolved_path: Optional[str]
    resolution_type: str
    confidence: float

    def __repr__(self) -> str:
        if self.resolved_path:
            return f"ResolvedImport({self.import_name!r} -> {Path(self.resolved_path).name}, {self.resolution_type}, conf={self.confidence:.1f})"
        return f"ResolvedImport({self.import_name!r} -> None, {self.resolution_type})"


class ImportResolver:
    """
    Resolve Python imports to file paths.

    Strategy:
    1. Build module index from scanned files (one-time O(N) cost)
    2. For each import, try:
       a. Check if external package (stdlib)
       b. Exact match in module index
       c. Relative path resolution for . and .. imports
       d. Fuzzy fallback (try .py, try __init__.py)
    3. Return resolved path with confidence score

    Performance:
    - Index build: O(N) where N = number of files
    - Resolution: O(1) average case (dict lookup)
    - Total: O(N) + O(M) where M = number of imports

    Usage:
        >>> resolver = ImportResolver(
        ...     project_root=Path("/project"),
        ...     scanned_files=["/project/main.py", "/project/utils.py"]
        ... )
        >>> result = resolver.resolve("utils", "/project/main.py")
        >>> print(result.resolved_path)
        /project/utils.py
    """

    def __init__(
        self,
        project_root: Path,
        scanned_files: List[str],
        external_packages: Optional[Set[str]] = None,
        src_roots: Optional[List[str]] = None
    ):
        """
        Initialize resolver.

        Args:
            project_root: Project root directory
            scanned_files: List of absolute paths to Python files
            external_packages: Known external packages (optional, adds to stdlib)
            src_roots: Additional source roots for import resolution (e.g., ["src"])
        """
        self.project_root = Path(project_root).resolve()
        self.scanned_files = [Path(f).resolve() for f in scanned_files]
        self.src_roots = [self.project_root / r for r in (src_roots or [])]

        # Build external packages set from centralized registry + user-provided
        # Uses known_packages.py (Phase 72.3) for stdlib + third-party
        self.external_packages = get_all_external_python()
        if external_packages:
            self.external_packages.update(external_packages)

        # Build module index: module_name -> file_path
        self.module_index: Dict[str, str] = self._build_module_index()

        logger.info(
            f"ImportResolver initialized: "
            f"{len(self.scanned_files)} files, "
            f"{len(self.module_index)} modules indexed"
        )

    def _build_module_index(self) -> Dict[str, str]:
        """
        Build index: module_name → file_path

        Handles:
        - Simple modules: utils.py → "utils"
        - Packages: utils/__init__.py → "utils"
        - Nested: foo/bar/baz.py → "foo.bar.baz"
        - Submodules: foo/bar.py → "foo.bar"
        - src-relative: src/utils.py → "src.utils" AND "utils" (if src is source root)
        """
        index: Dict[str, str] = {}

        for file_path in self.scanned_files:
            # Skip non-Python files (shouldn't happen, but be safe)
            if file_path.suffix != '.py':
                continue

            # Add entries relative to project root
            self._add_to_index(index, file_path, self.project_root)

            # Also add entries relative to each src_root
            # This allows "from utils import X" when utils.py is in src/
            for src_root in self.src_roots:
                if file_path.is_relative_to(src_root):
                    self._add_to_index(index, file_path, src_root)

        return index

    def _add_to_index(
        self,
        index: Dict[str, str],
        file_path: Path,
        root: Path
    ) -> None:
        """Add a file to the module index relative to a root."""
        try:
            rel_path = file_path.relative_to(root)
        except ValueError:
            # File not under this root
            return

        file_path_str = str(file_path)

        # Case 1: Package __init__.py
        if file_path.name == '__init__.py':
            # utils/__init__.py → "utils"
            package_name = rel_path.parent.name
            if package_name:
                if package_name not in index:
                    index[package_name] = file_path_str

            # Also: foo/bar/__init__.py → "foo.bar"
            parts = list(rel_path.parent.parts)
            if parts:
                dotted = '.'.join(parts)
                if dotted not in index:
                    index[dotted] = file_path_str

        # Case 2: Regular module file
        else:
            # utils.py → "utils"
            module_name = rel_path.stem
            if module_name not in index:
                index[module_name] = file_path_str

            # foo/bar/utils.py → "foo.bar.utils"
            parts = list(rel_path.parent.parts) + [rel_path.stem]
            parts = [p for p in parts if p]  # Filter empty
            if parts:
                dotted = '.'.join(parts)
                if dotted not in index:
                    index[dotted] = file_path_str

    def resolve(
        self,
        import_name: str,
        from_file_path: str,
        is_dynamic: bool = False,
        is_conditional: bool = False
    ) -> ResolvedImport:
        """
        Resolve import to file path.

        Args:
            import_name: Import statement (e.g., "utils", ".helper", "foo.bar")
            from_file_path: File where import appears
            is_dynamic: True if this is a dynamic import (__import__, importlib)
            is_conditional: True if inside TYPE_CHECKING block

        Returns:
            ResolvedImport with path and confidence

        Examples:
            >>> resolver.resolve("utils", "/project/main.py")
            ResolvedImport(import_name="utils",
                         resolved_path="/project/utils.py",
                         resolution_type="exact",
                         confidence=1.0)

            >>> resolver.resolve("..utils", "/project/src/main.py")
            ResolvedImport(import_name="..utils",
                         resolved_path="/project/utils.py",
                         resolution_type="relative",
                         confidence=1.0)
        """
        # Handle empty/invalid imports
        if not import_name or not isinstance(import_name, str):
            return ResolvedImport(
                import_name=str(import_name) if import_name else "",
                resolved_path=None,
                resolution_type="unresolved",
                confidence=0.0
            )

        from_path = Path(from_file_path).resolve()

        # Mark special import types
        if is_dynamic:
            return ResolvedImport(
                import_name=import_name,
                resolved_path=None,
                resolution_type="dynamic",
                confidence=0.5
            )

        if is_conditional:
            # Try to resolve, but mark as conditional
            result = self._do_resolve(import_name, from_path)
            if result.resolved_path:
                return ResolvedImport(
                    import_name=import_name,
                    resolved_path=result.resolved_path,
                    resolution_type="conditional",
                    confidence=result.confidence
                )
            return ResolvedImport(
                import_name=import_name,
                resolved_path=None,
                resolution_type="conditional",
                confidence=0.5
            )

        return self._do_resolve(import_name, from_path)

    def _do_resolve(self, import_name: str, from_path: Path) -> ResolvedImport:
        """Internal resolution logic."""

        # Get base module name (first component, strip dots)
        base_module = import_name.split('.')[0].lstrip('.')

        # Strategy 1: Check if external package (stdlib or known third-party)
        if base_module in self.external_packages:
            return ResolvedImport(
                import_name=import_name,
                resolved_path=None,
                resolution_type="external",
                confidence=1.0
            )

        # Strategy 2: Relative import (starts with .)
        if import_name.startswith('.'):
            resolved = self._resolve_relative(import_name, from_path)
            if resolved:
                return ResolvedImport(
                    import_name=import_name,
                    resolved_path=resolved,
                    resolution_type="relative",
                    confidence=1.0
                )

        # Strategy 3: Exact match in module index
        if import_name in self.module_index:
            return ResolvedImport(
                import_name=import_name,
                resolved_path=self.module_index[import_name],
                resolution_type="exact",
                confidence=1.0
            )

        # Strategy 4: Try with "src." prefix (common pattern)
        src_prefixed = f"src.{import_name}"
        if src_prefixed in self.module_index:
            return ResolvedImport(
                import_name=import_name,
                resolved_path=self.module_index[src_prefixed],
                resolution_type="exact",
                confidence=0.9
            )

        # Strategy 5: Fuzzy fallback
        resolved = self._resolve_fuzzy(import_name)
        if resolved:
            return ResolvedImport(
                import_name=import_name,
                resolved_path=resolved,
                resolution_type="fuzzy",
                confidence=0.7
            )

        # Strategy 6: Unresolved - might be third-party not in our list
        logger.debug(f"Could not resolve: {import_name} from {from_path}")
        return ResolvedImport(
            import_name=import_name,
            resolved_path=None,
            resolution_type="unresolved",
            confidence=0.0
        )

    def _resolve_relative(
        self,
        import_name: str,
        from_path: Path
    ) -> Optional[str]:
        """
        Resolve relative import (., .., ...).

        Python relative import rules:
        - from . import foo → same package
        - from .. import foo → parent package
        - from ... import foo → grandparent package

        Number of dots = number of directories to go up from current package.

        Examples:
            from . import utils        → same directory as from_file
            from .. import helper      → parent directory
            from ...config import X    → grandparent/config
        """
        # Count leading dots
        dots = len(import_name) - len(import_name.lstrip('.'))
        module_name = import_name.lstrip('.')

        if dots == 0:
            return None  # Not a relative import

        # Start from file's directory
        current_dir = from_path.parent

        # Go up (dots - 1) levels
        # 1 dot = same dir, 2 dots = parent, 3 dots = grandparent
        for _ in range(dots - 1):
            current_dir = current_dir.parent

            # Check bounds - don't go outside project root
            try:
                current_dir.relative_to(self.project_root)
            except ValueError:
                logger.warning(
                    f"Relative import goes outside project: "
                    f"{import_name} from {from_path}"
                )
                return None

        # Base case: from . import (no module name after dots)
        if not module_name:
            init_file = current_dir / '__init__.py'
            if init_file.exists():
                return str(init_file)
            return None

        # Convert module.submodule to path
        path_parts = module_name.split('.')

        # Try as module file: foo/bar.py
        module_path = current_dir.joinpath(*path_parts[:-1]) if len(path_parts) > 1 else current_dir
        module_file = module_path / (path_parts[-1] + '.py')
        if module_file.exists():
            return str(module_file)

        # Try as package: foo/bar/__init__.py
        package_path = current_dir.joinpath(*path_parts) / '__init__.py'
        if package_path.exists():
            return str(package_path)

        # Try just the directory with any .py file that matches last component
        dir_path = current_dir.joinpath(*path_parts)
        if dir_path.is_dir():
            init_file = dir_path / '__init__.py'
            if init_file.exists():
                return str(init_file)

        return None

    def _resolve_fuzzy(self, import_name: str) -> Optional[str]:
        """
        Fuzzy fallback: try adding .py or __init__.py

        When exact match fails, try common variations:
        - utils → utils.py
        - utils → utils/__init__.py
        - foo.bar → foo/bar.py
        - foo.bar → foo/bar/__init__.py

        Also tries under each src_root.
        """
        # Get candidate paths
        candidates = path_to_module_candidates(import_name, self.project_root)

        # Also try under src roots
        for src_root in self.src_roots:
            candidates.extend(path_to_module_candidates(import_name, src_root))

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

        return None

    def resolve_all(
        self,
        imports: List[Tuple[str, str]]
    ) -> List[ResolvedImport]:
        """
        Resolve multiple imports.

        Args:
            imports: List of (import_name, from_file_path) tuples

        Returns:
            List of ResolvedImport in same order as input
        """
        return [
            self.resolve(import_name, from_path)
            for import_name, from_path in imports
        ]

    def get_statistics(self) -> Dict[str, int]:
        """Get resolution statistics for debugging."""
        return {
            'total_files': len(self.scanned_files),
            'indexed_modules': len(self.module_index),
            'external_packages': len(self.external_packages),
            'src_roots': len(self.src_roots)
        }

    def get_index_sample(self, limit: int = 20) -> Dict[str, str]:
        """Get a sample of the module index for debugging."""
        items = list(self.module_index.items())[:limit]
        return dict(items)

    def is_external(self, module_name: str) -> bool:
        """Check if a module name is external (stdlib or third-party)."""
        base = module_name.split('.')[0]
        return base in self.external_packages
