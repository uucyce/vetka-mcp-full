# ========================================
# MARKER: Phase 72.2 Python Import Resolution
# Date: 2026-01-19
# File: tests/scanners/test_import_resolver.py
# Purpose: Unit tests for ImportResolver
# Research: IMPORT_PATTERNS_AUDIT.md (Haiku)
# Goal: 95%+ coverage
# ========================================
"""
Unit tests for ImportResolver (Phase 72.2).

Based on:
- Haiku audit: IMPORT_PATTERNS_AUDIT.md
- Real examples from VETKA project

Test Categories:
1. Module Index Building
2. Exact Resolution
3. Relative Resolution (., .., ...)
4. Fuzzy Fallback
5. External Packages
6. Edge Cases (7 critical)
7. Batch Resolution
8. Statistics

Coverage target: 95%+
"""

import pytest
from pathlib import Path
from typing import List

from src.scanners.import_resolver import ImportResolver, ResolvedImport
from src.scanners.path_utils import (
    get_python_files,
    is_package,
    get_module_name,
    path_to_module_candidates,
    normalize_path,
)


# =============================================================================
# Tests for path_utils.py
# =============================================================================

class TestPathUtils:
    """Tests for path utility functions."""

    def test_get_python_files_finds_py(self, tmp_path: Path):
        """Should find all .py files recursively."""
        # Create files
        (tmp_path / 'a.py').touch()
        (tmp_path / 'b.py').touch()
        sub = tmp_path / 'sub'
        sub.mkdir()
        (sub / 'c.py').touch()

        files = get_python_files(tmp_path)

        assert len(files) == 3
        names = {f.name for f in files}
        assert names == {'a.py', 'b.py', 'c.py'}

    def test_get_python_files_excludes_patterns(self, tmp_path: Path):
        """Should exclude specified patterns."""
        (tmp_path / 'good.py').touch()
        cache = tmp_path / '__pycache__'
        cache.mkdir()
        (cache / 'bad.py').touch()

        files = get_python_files(tmp_path)

        assert len(files) == 1
        assert files[0].name == 'good.py'

    def test_is_package_with_init(self, tmp_path: Path):
        """Directory with __init__.py is a package."""
        pkg = tmp_path / 'pkg'
        pkg.mkdir()
        (pkg / '__init__.py').touch()

        assert is_package(pkg) is True

    def test_is_package_without_init(self, tmp_path: Path):
        """Directory without __init__.py is not a package."""
        notpkg = tmp_path / 'notpkg'
        notpkg.mkdir()

        assert is_package(notpkg) is False

    def test_is_package_file(self, tmp_path: Path):
        """File is not a package."""
        f = tmp_path / 'file.py'
        f.touch()

        assert is_package(f) is False

    def test_get_module_name_simple(self, tmp_path: Path):
        """Simple module: utils.py -> 'utils'."""
        f = tmp_path / 'utils.py'
        f.touch()

        name = get_module_name(f, tmp_path)

        assert name == 'utils'

    def test_get_module_name_nested(self, tmp_path: Path):
        """Nested module: foo/bar/baz.py -> 'foo.bar.baz'."""
        nested = tmp_path / 'foo' / 'bar'
        nested.mkdir(parents=True)
        f = nested / 'baz.py'
        f.touch()

        name = get_module_name(f, tmp_path)

        assert name == 'foo.bar.baz'

    def test_get_module_name_init(self, tmp_path: Path):
        """Package init: pkg/__init__.py -> 'pkg'."""
        pkg = tmp_path / 'pkg'
        pkg.mkdir()
        f = pkg / '__init__.py'
        f.touch()

        name = get_module_name(f, tmp_path)

        assert name == 'pkg'

    def test_get_module_name_outside_root(self, tmp_path: Path):
        """File outside root should raise ValueError."""
        other = tmp_path.parent / 'other.py'

        with pytest.raises(ValueError, match="not under root"):
            get_module_name(other, tmp_path)

    def test_path_to_module_candidates(self, tmp_path: Path):
        """Should generate module and package paths."""
        candidates = path_to_module_candidates('foo.bar', tmp_path)

        assert len(candidates) == 2
        assert candidates[0] == tmp_path / 'foo' / 'bar.py'
        assert candidates[1] == tmp_path / 'foo' / 'bar' / '__init__.py'

    def test_normalize_path_absolute(self, tmp_path: Path):
        """Absolute path should be preserved."""
        p = tmp_path / 'file.py'
        p.touch()

        result = normalize_path(str(p), tmp_path)

        assert result == str(p.resolve())


# =============================================================================
# Tests for ImportResolver - Module Index
# =============================================================================

class TestImportResolverModuleIndex:
    """Tests for module index building."""

    def test_index_simple_module(self, sample_project: Path, sample_files: List[str]):
        """Simple module: utils.py -> 'utils'."""
        resolver = ImportResolver(sample_project, sample_files)

        assert 'utils' in resolver.module_index
        assert resolver.module_index['utils'].endswith('utils.py')

    def test_index_package(self, sample_project: Path, sample_files: List[str]):
        """Package: package/__init__.py -> 'package'."""
        resolver = ImportResolver(sample_project, sample_files)

        assert 'package' in resolver.module_index
        assert resolver.module_index['package'].endswith('__init__.py')

    def test_index_nested_module(self, sample_project: Path, sample_files: List[str]):
        """Nested module: package/module.py -> 'package.module'."""
        resolver = ImportResolver(sample_project, sample_files)

        assert 'package.module' in resolver.module_index

    def test_index_deep_module(self, sample_project: Path, sample_files: List[str]):
        """Deep module: package/subpackage/deep.py -> 'package.subpackage.deep'."""
        resolver = ImportResolver(sample_project, sample_files)

        assert 'package.subpackage.deep' in resolver.module_index

    def test_index_src_pattern(self, vetka_like_project: Path):
        """VETKA-like src/ pattern should be indexed."""
        files = [str(f) for f in vetka_like_project.rglob('*.py')]
        resolver = ImportResolver(
            vetka_like_project,
            files,
            src_roots=['src']
        )

        # Should have both src.agents and just agents (from src_root)
        assert 'src.agents' in resolver.module_index
        assert 'agents' in resolver.module_index

    def test_index_statistics(self, sample_project: Path, sample_files: List[str]):
        """Statistics should be accurate."""
        resolver = ImportResolver(sample_project, sample_files)

        stats = resolver.get_statistics()

        assert stats['total_files'] == len(sample_files)
        assert stats['indexed_modules'] > 0
        assert stats['external_packages'] > 0


# =============================================================================
# Tests for ImportResolver - Exact Resolution
# =============================================================================

class TestImportResolverExact:
    """Tests for exact import resolution."""

    def test_resolve_exact_simple(self, import_resolver, sample_project: Path):
        """Resolve exact match: import utils."""
        result = import_resolver.resolve('utils', str(sample_project / 'main.py'))

        assert result.resolution_type == 'exact'
        assert result.confidence == 1.0
        assert result.resolved_path.endswith('utils.py')

    def test_resolve_exact_package(self, import_resolver, sample_project: Path):
        """Resolve exact match: import package."""
        result = import_resolver.resolve('package', str(sample_project / 'main.py'))

        assert result.resolution_type == 'exact'
        assert result.resolved_path.endswith('__init__.py')

    def test_resolve_exact_dotted(self, import_resolver, sample_project: Path):
        """Resolve dotted: import package.module."""
        result = import_resolver.resolve(
            'package.module',
            str(sample_project / 'main.py')
        )

        assert result.resolution_type == 'exact'
        assert result.resolved_path.endswith('module.py')

    def test_resolve_exact_deep(self, import_resolver, sample_project: Path):
        """Resolve deep: import package.subpackage.deep."""
        result = import_resolver.resolve(
            'package.subpackage.deep',
            str(sample_project / 'main.py')
        )

        assert result.resolution_type == 'exact'
        assert result.resolved_path.endswith('deep.py')


# =============================================================================
# Tests for ImportResolver - Relative Resolution
# =============================================================================

class TestImportResolverRelative:
    """Tests for relative import resolution (., .., ...)."""

    def test_resolve_relative_same_dir(self, relative_imports_project: Path):
        """Relative same dir: from . import b."""
        files = [str(f) for f in relative_imports_project.rglob('*.py')]
        resolver = ImportResolver(relative_imports_project, files)

        # From pkg/a.py, resolve .b
        result = resolver.resolve('.b', str(relative_imports_project / 'pkg' / 'a.py'))

        assert result.resolution_type == 'relative'
        assert result.confidence == 1.0
        assert result.resolved_path.endswith('b.py')

    def test_resolve_relative_parent(self, relative_imports_project: Path):
        """Relative parent: from .. import a."""
        files = [str(f) for f in relative_imports_project.rglob('*.py')]
        resolver = ImportResolver(relative_imports_project, files)

        # From pkg/sub/c.py, resolve ..a
        result = resolver.resolve('..a', str(relative_imports_project / 'pkg' / 'sub' / 'c.py'))

        assert result.resolution_type == 'relative'
        assert result.resolved_path.endswith('a.py')

    def test_resolve_relative_grandparent(self, relative_imports_project: Path):
        """Relative grandparent: from ... import root_utils."""
        files = [str(f) for f in relative_imports_project.rglob('*.py')]
        resolver = ImportResolver(relative_imports_project, files)

        # From pkg/sub/d.py, resolve ...root_utils
        result = resolver.resolve(
            '...root_utils',
            str(relative_imports_project / 'pkg' / 'sub' / 'd.py')
        )

        assert result.resolution_type == 'relative'
        assert result.resolved_path.endswith('root_utils.py')

    def test_resolve_relative_init(self, relative_imports_project: Path):
        """Relative init: from . import (gets __init__.py)."""
        files = [str(f) for f in relative_imports_project.rglob('*.py')]
        resolver = ImportResolver(relative_imports_project, files)

        # From pkg/a.py, resolve just .
        result = resolver.resolve('.', str(relative_imports_project / 'pkg' / 'a.py'))

        assert result.resolution_type == 'relative'
        assert '__init__.py' in result.resolved_path

    def test_resolve_relative_out_of_bounds(self, relative_imports_project: Path):
        """Relative out of bounds should fail gracefully."""
        files = [str(f) for f in relative_imports_project.rglob('*.py')]
        resolver = ImportResolver(relative_imports_project, files)

        # Try to go way beyond project root
        result = resolver.resolve(
            '......outside',
            str(relative_imports_project / 'pkg' / 'a.py')
        )

        # Should be unresolved (not crash)
        assert result.resolution_type == 'unresolved'
        assert result.resolved_path is None


# =============================================================================
# Tests for ImportResolver - Fuzzy Fallback
# =============================================================================

class TestImportResolverFuzzy:
    """Tests for fuzzy fallback resolution."""

    def test_resolve_fuzzy_file(self, tmp_path: Path):
        """Fuzzy should find file by trying .py extension."""
        # Create a file not indexed directly
        (tmp_path / 'orphan.py').write_text('X = 1\n')

        # Create resolver with empty initial scan
        resolver = ImportResolver(tmp_path, [])

        result = resolver.resolve('orphan', str(tmp_path / 'main.py'))

        assert result.resolution_type == 'fuzzy'
        assert result.confidence == 0.7
        assert result.resolved_path.endswith('orphan.py')

    def test_resolve_fuzzy_package(self, tmp_path: Path):
        """Fuzzy should find package by trying __init__.py."""
        pkg = tmp_path / 'hidden_pkg'
        pkg.mkdir()
        (pkg / '__init__.py').write_text('X = 1\n')

        resolver = ImportResolver(tmp_path, [])

        result = resolver.resolve('hidden_pkg', str(tmp_path / 'main.py'))

        assert result.resolution_type == 'fuzzy'
        assert result.resolved_path.endswith('__init__.py')


# =============================================================================
# Tests for ImportResolver - External Packages
# =============================================================================

class TestImportResolverExternal:
    """Tests for external package detection."""

    def test_resolve_external_stdlib(self, minimal_project: Path):
        """Stdlib packages should be marked as external."""
        files = [str(f) for f in minimal_project.rglob('*.py')]
        resolver = ImportResolver(minimal_project, files)

        for stdlib in ['os', 'sys', 'json', 'typing', 'pathlib']:
            result = resolver.resolve(stdlib, str(minimal_project / 'main.py'))

            assert result.resolution_type == 'external', f"Failed for {stdlib}"
            assert result.resolved_path is None
            assert result.confidence == 1.0

    def test_resolve_external_third_party(self, minimal_project: Path):
        """Known third-party packages should be external."""
        files = [str(f) for f in minimal_project.rglob('*.py')]
        resolver = ImportResolver(minimal_project, files)

        # These are in COMMON_THIRD_PARTY
        for pkg in ['numpy', 'pandas', 'requests', 'flask', 'pytest']:
            result = resolver.resolve(pkg, str(minimal_project / 'main.py'))

            assert result.resolution_type == 'external', f"Failed for {pkg}"

    def test_resolve_external_custom(self, minimal_project: Path):
        """Custom external packages should be respected."""
        files = [str(f) for f in minimal_project.rglob('*.py')]
        resolver = ImportResolver(
            minimal_project,
            files,
            external_packages={'my_custom_lib', 'another_lib'}
        )

        result = resolver.resolve('my_custom_lib', str(minimal_project / 'main.py'))

        assert result.resolution_type == 'external'

    def test_is_external_method(self, minimal_project: Path):
        """is_external() method should work correctly."""
        files = [str(f) for f in minimal_project.rglob('*.py')]
        resolver = ImportResolver(minimal_project, files)

        assert resolver.is_external('os') is True
        assert resolver.is_external('sys') is True
        assert resolver.is_external('numpy') is True
        # Local module should not be external
        assert resolver.is_external('utils') is False


# =============================================================================
# Tests for ImportResolver - Edge Cases (7 Critical)
# =============================================================================

class TestImportResolverEdgeCases:
    """Tests for 7 critical edge cases."""

    # Edge Case 1: Relative imports - covered in TestImportResolverRelative

    # Edge Case 2: Circular dependencies
    def test_circular_deps_no_crash(self, circular_deps_project: Path):
        """Circular dependencies via TYPE_CHECKING should not crash."""
        files = [str(f) for f in circular_deps_project.rglob('*.py')]
        resolver = ImportResolver(circular_deps_project, files)

        # Resolve both directions - should not crash
        result_a = resolver.resolve(
            '.circular_b',
            str(circular_deps_project / 'pkg' / 'circular_a.py')
        )
        result_b = resolver.resolve(
            '.circular_a',
            str(circular_deps_project / 'pkg' / 'circular_b.py')
        )

        # Both should resolve
        assert result_a.resolved_path is not None
        assert result_b.resolved_path is not None

    # Edge Case 3: Dynamic imports
    def test_dynamic_imports(self, minimal_project: Path):
        """Dynamic imports should be marked specially."""
        files = [str(f) for f in minimal_project.rglob('*.py')]
        resolver = ImportResolver(minimal_project, files)

        result = resolver.resolve(
            'json',
            str(minimal_project / 'main.py'),
            is_dynamic=True
        )

        assert result.resolution_type == 'dynamic'
        assert result.confidence == 0.5

    # Edge Case 4: Conditional imports
    def test_conditional_imports(self, minimal_project: Path):
        """Conditional imports (TYPE_CHECKING) should be marked."""
        files = [str(f) for f in minimal_project.rglob('*.py')]
        resolver = ImportResolver(minimal_project, files)

        # Conditional import of stdlib
        result = resolver.resolve(
            'typing',
            str(minimal_project / 'main.py'),
            is_conditional=True
        )

        assert result.resolution_type == 'conditional'

    # Edge Case 5: Package vs module distinction
    def test_package_vs_module(self, sample_project: Path, sample_files: List[str]):
        """Package and module should resolve correctly."""
        resolver = ImportResolver(sample_project, sample_files)

        # Package (has __init__.py)
        pkg_result = resolver.resolve('package', str(sample_project / 'main.py'))
        assert '__init__.py' in pkg_result.resolved_path

        # Module (single .py file)
        mod_result = resolver.resolve('utils', str(sample_project / 'main.py'))
        assert mod_result.resolved_path.endswith('utils.py')
        assert '__init__' not in mod_result.resolved_path

    # Edge Case 6: External vs internal packages
    def test_external_vs_internal(self, minimal_project: Path):
        """External packages should not resolve to local files."""
        # Create local file with stdlib name
        (minimal_project / 'json.py').write_text('LOCAL = True\n')

        files = [str(f) for f in minimal_project.rglob('*.py')]
        resolver = ImportResolver(minimal_project, files)

        # Even though json.py exists locally, 'json' should resolve as external
        # because it's in stdlib
        result = resolver.resolve('json', str(minimal_project / 'main.py'))

        assert result.resolution_type == 'external'

    # Edge Case 7: Syntax errors / graceful fallback
    def test_empty_import_name(self, minimal_project: Path):
        """Empty import name should not crash."""
        files = [str(f) for f in minimal_project.rglob('*.py')]
        resolver = ImportResolver(minimal_project, files)

        result = resolver.resolve('', str(minimal_project / 'main.py'))

        assert result.resolution_type == 'unresolved'
        assert result.confidence == 0.0

    def test_none_import_name(self, minimal_project: Path):
        """None import name should not crash."""
        files = [str(f) for f in minimal_project.rglob('*.py')]
        resolver = ImportResolver(minimal_project, files)

        result = resolver.resolve(None, str(minimal_project / 'main.py'))  # type: ignore

        assert result.resolution_type == 'unresolved'

    def test_nonexistent_module(self, minimal_project: Path):
        """Nonexistent module should be unresolved."""
        files = [str(f) for f in minimal_project.rglob('*.py')]
        resolver = ImportResolver(minimal_project, files)

        result = resolver.resolve(
            'totally_nonexistent_module',
            str(minimal_project / 'main.py')
        )

        assert result.resolution_type == 'unresolved'
        assert result.confidence == 0.0


# =============================================================================
# Tests for ImportResolver - Batch Resolution
# =============================================================================

class TestImportResolverBatch:
    """Tests for batch import resolution."""

    def test_resolve_all(self, import_resolver, sample_project: Path):
        """Batch resolution should process all imports."""
        main_py = str(sample_project / 'main.py')

        imports = [
            ('utils', main_py),
            ('os', main_py),
            ('package', main_py),
            ('nonexistent', main_py),
        ]

        results = import_resolver.resolve_all(imports)

        assert len(results) == 4
        assert results[0].resolution_type == 'exact'      # utils
        assert results[1].resolution_type == 'external'   # os
        assert results[2].resolution_type == 'exact'      # package
        assert results[3].resolution_type == 'unresolved' # nonexistent

    def test_resolve_all_preserves_order(self, import_resolver, sample_project: Path):
        """Batch resolution should preserve input order."""
        main_py = str(sample_project / 'main.py')

        imports = [
            ('config', main_py),
            ('utils', main_py),
            ('package', main_py),
        ]

        results = import_resolver.resolve_all(imports)

        assert results[0].import_name == 'config'
        assert results[1].import_name == 'utils'
        assert results[2].import_name == 'package'


# =============================================================================
# Tests for ResolvedImport dataclass
# =============================================================================

class TestResolvedImport:
    """Tests for ResolvedImport dataclass."""

    def test_repr_with_path(self):
        """ResolvedImport repr should show file name."""
        ri = ResolvedImport(
            import_name='utils',
            resolved_path='/project/utils.py',
            resolution_type='exact',
            confidence=1.0
        )

        repr_str = repr(ri)

        assert 'utils' in repr_str
        assert 'exact' in repr_str
        assert '1.0' in repr_str

    def test_repr_without_path(self):
        """ResolvedImport repr should handle None path."""
        ri = ResolvedImport(
            import_name='numpy',
            resolved_path=None,
            resolution_type='external',
            confidence=1.0
        )

        repr_str = repr(ri)

        assert 'numpy' in repr_str
        assert 'external' in repr_str
        assert 'None' in repr_str


# =============================================================================
# Integration Tests - VETKA-like patterns
# =============================================================================

class TestVetkaPatterns:
    """Integration tests using VETKA-like project structure."""

    def test_vetka_agents_import(self, vetka_like_project: Path):
        """Test VETKA pattern: from src.agents import LearnerAgent."""
        files = [str(f) for f in vetka_like_project.rglob('*.py')]
        resolver = ImportResolver(
            vetka_like_project,
            files,
            src_roots=['src']
        )

        result = resolver.resolve(
            'src.agents',
            str(vetka_like_project / 'src' / 'orchestration' / 'cam_engine.py')
        )

        assert result.resolution_type == 'exact'
        assert '__init__.py' in result.resolved_path

    def test_vetka_memory_import(self, vetka_like_project: Path):
        """Test VETKA pattern: from src.memory.qdrant_client import QdrantManager."""
        files = [str(f) for f in vetka_like_project.rglob('*.py')]
        resolver = ImportResolver(
            vetka_like_project,
            files,
            src_roots=['src']
        )

        result = resolver.resolve(
            'src.memory.qdrant_client',
            str(vetka_like_project / 'src' / 'orchestration' / 'cam_engine.py')
        )

        assert result.resolution_type == 'exact'
        assert result.resolved_path.endswith('qdrant_client.py')

    def test_vetka_services_import(self, vetka_like_project: Path):
        """Test VETKA pattern: from src.orchestration.services.memory_service import X."""
        files = [str(f) for f in vetka_like_project.rglob('*.py')]
        resolver = ImportResolver(
            vetka_like_project,
            files,
            src_roots=['src']
        )

        result = resolver.resolve(
            'src.orchestration.services.memory_service',
            str(vetka_like_project / 'src' / 'main.py')
        )

        assert result.resolution_type == 'exact'
        assert result.resolved_path.endswith('memory_service.py')

    def test_vetka_src_root_shortcut(self, vetka_like_project: Path):
        """Test src_roots allows shorter imports: agents instead of src.agents."""
        files = [str(f) for f in vetka_like_project.rglob('*.py')]
        resolver = ImportResolver(
            vetka_like_project,
            files,
            src_roots=['src']
        )

        # 'agents' (without src.) should also work
        result = resolver.resolve(
            'agents',
            str(vetka_like_project / 'src' / 'orchestration' / 'cam_engine.py')
        )

        assert result.resolved_path is not None
        assert 'agents' in result.resolved_path


# =============================================================================
# Performance Tests
# =============================================================================

class TestImportResolverPerformance:
    """Performance tests for ImportResolver."""

    def test_large_project_initialization(self, deep_nesting_project: Path):
        """Resolver should handle deeply nested projects."""
        files = [str(f) for f in deep_nesting_project.rglob('*.py')]
        resolver = ImportResolver(deep_nesting_project, files)

        # Should have indexed the deep module
        assert 'a.b.c.d.e.module' in resolver.module_index

    def test_index_sample(self, sample_project: Path, sample_files: List[str]):
        """get_index_sample should return limited results."""
        resolver = ImportResolver(sample_project, sample_files)

        sample = resolver.get_index_sample(limit=5)

        assert len(sample) <= 5
        assert isinstance(sample, dict)


# =============================================================================
# Additional Coverage Tests
# =============================================================================

class TestAdditionalCoverage:
    """Additional tests for edge cases and coverage."""

    def test_conditional_import_with_resolved_path(self, sample_project: Path, sample_files: List[str]):
        """Conditional import that resolves to local file."""
        resolver = ImportResolver(sample_project, sample_files, src_roots=['src'])

        # 'utils' exists locally and should resolve even in conditional
        result = resolver.resolve(
            'utils',
            str(sample_project / 'main.py'),
            is_conditional=True
        )

        assert result.resolution_type == 'conditional'
        assert result.resolved_path is not None
        assert result.resolved_path.endswith('utils.py')

    def test_resolve_with_non_relative_in_relative_method(self, sample_project: Path, sample_files: List[str]):
        """Non-relative import passed to relative resolver returns None."""
        resolver = ImportResolver(sample_project, sample_files)

        # This tests the dots == 0 path in _resolve_relative
        result = resolver._resolve_relative('utils', sample_project / 'main.py')

        assert result is None

    def test_src_prefix_resolution(self, vetka_like_project: Path):
        """Test src. prefix resolution fallback."""
        files = [str(f) for f in vetka_like_project.rglob('*.py')]
        # Create resolver WITHOUT src_roots to test src. prefix path
        resolver = ImportResolver(vetka_like_project, files)

        # 'agents' won't be in index directly, but 'src.agents' will be
        # So importing 'agents' should try 'src.agents' as fallback
        result = resolver.resolve(
            'agents',
            str(vetka_like_project / 'src' / 'orchestration' / 'cam_engine.py')
        )

        # Should find via src. prefix fallback
        assert result.resolved_path is not None

    def test_relative_import_to_package_init(self, tmp_path: Path):
        """Test relative import resolving to package __init__.py."""
        # Create structure: pkg/sub/module.py importing ..other_pkg
        pkg = tmp_path / 'pkg'
        pkg.mkdir()
        (pkg / '__init__.py').write_text('')

        sub = pkg / 'sub'
        sub.mkdir()
        (sub / '__init__.py').write_text('')
        (sub / 'module.py').write_text('from ..other import X\n')

        # Create other as package
        other = pkg / 'other'
        other.mkdir()
        (other / '__init__.py').write_text('X = 1\n')

        files = [str(f) for f in tmp_path.rglob('*.py')]
        resolver = ImportResolver(tmp_path, files)

        # From pkg/sub/module.py, resolve ..other (package)
        result = resolver.resolve(
            '..other',
            str(sub / 'module.py')
        )

        assert result.resolution_type == 'relative'
        assert result.resolved_path.endswith('__init__.py')

    def test_non_py_files_in_scanned_list(self, tmp_path: Path):
        """Non-.py files in scanned list should be skipped."""
        # Create files
        (tmp_path / 'good.py').write_text('X = 1\n')

        # Include non-.py file in scanned list (as Path objects)
        txt_file = tmp_path / 'bad.txt'
        txt_file.write_text('not python')

        files = [
            str(tmp_path / 'good.py'),
            str(txt_file),  # Not a .py file
        ]

        # Should not crash, and should only index .py files
        resolver = ImportResolver(tmp_path, files)

        assert 'good' in resolver.module_index
        assert 'bad' not in resolver.module_index

    def test_file_outside_src_root(self, tmp_path: Path):
        """Files outside src_root should still be indexed from project root."""
        # Create src structure
        src = tmp_path / 'src'
        src.mkdir()
        (src / '__init__.py').write_text('')
        (src / 'mod.py').write_text('X = 1\n')

        # Create file outside src
        (tmp_path / 'outside.py').write_text('Y = 2\n')

        files = [
            str(src / '__init__.py'),
            str(src / 'mod.py'),
            str(tmp_path / 'outside.py'),
        ]

        resolver = ImportResolver(tmp_path, files, src_roots=['src'])

        # 'outside' should be indexed (from project root)
        assert 'outside' in resolver.module_index
        # 'mod' should be indexed (from src_root)
        assert 'mod' in resolver.module_index
        # 'src.mod' should also be indexed (from project root)
        assert 'src.mod' in resolver.module_index

    def test_relative_import_to_directory_with_init(self, tmp_path: Path):
        """Test relative import that finds directory with __init__.py."""
        # Create pkg/sub/module.py importing ..sibling (which is a directory)
        pkg = tmp_path / 'pkg'
        pkg.mkdir()
        (pkg / '__init__.py').write_text('')

        sub = pkg / 'sub'
        sub.mkdir()
        (sub / '__init__.py').write_text('')
        (sub / 'module.py').write_text('')

        # Create sibling directory with __init__.py
        sibling = pkg / 'sibling'
        sibling.mkdir()
        (sibling / '__init__.py').write_text('SIBLING = True\n')

        files = [str(f) for f in tmp_path.rglob('*.py')]
        resolver = ImportResolver(tmp_path, files)

        # From pkg/sub/module.py, resolve ..sibling
        result = resolver.resolve(
            '..sibling',
            str(sub / 'module.py')
        )

        assert result.resolution_type == 'relative'
        assert 'sibling' in result.resolved_path
        assert '__init__.py' in result.resolved_path

    def test_src_prefix_fallback_exact(self, tmp_path: Path):
        """Test src. prefix fallback when short name is taken by external."""
        # Create src/mymodule.py
        src = tmp_path / 'src'
        src.mkdir()
        (src / 'mymodule.py').write_text('X = 1\n')

        # Create main.py at root
        (tmp_path / 'main.py').write_text('')

        files = [str(f) for f in tmp_path.rglob('*.py')]
        resolver = ImportResolver(tmp_path, files)

        # Both 'mymodule' and 'src.mymodule' should be in index
        assert 'mymodule' in resolver.module_index
        assert 'src.mymodule' in resolver.module_index

        # Resolution should find it directly (exact match)
        result = resolver.resolve('mymodule', str(tmp_path / 'main.py'))

        assert result.resolution_type == 'exact'
        assert result.resolved_path.endswith('mymodule.py')

        # Also test src.mymodule explicitly
        result2 = resolver.resolve('src.mymodule', str(tmp_path / 'main.py'))
        assert result2.resolution_type == 'exact'
        assert result2.resolved_path.endswith('mymodule.py')

    def test_src_prefix_fallback_only_dotted(self, tmp_path: Path):
        """Test src. prefix fallback when ONLY dotted name is indexed."""
        # Create src/subdir/deep.py
        src = tmp_path / 'src'
        src.mkdir()
        subdir = src / 'subdir'
        subdir.mkdir()
        (subdir / 'deep.py').write_text('X = 1\n')

        # Create main.py at root
        (tmp_path / 'main.py').write_text('')

        # Only index the deep.py file directly (not through normal discovery)
        # This simulates a case where short name collision occurs
        resolver = ImportResolver(tmp_path, [str(tmp_path / 'main.py')])

        # Manually add only the dotted name to simulate edge case
        resolver.module_index['src.subdir.deep'] = str(subdir / 'deep.py')

        # Now 'subdir.deep' is NOT in index, but 'src.subdir.deep' is
        # Resolution should find it via src. prefix fallback
        result = resolver.resolve('subdir.deep', str(tmp_path / 'main.py'))

        assert result.resolution_type == 'exact'
        assert result.confidence == 0.9  # src. prefix fallback
        assert result.resolved_path.endswith('deep.py')
