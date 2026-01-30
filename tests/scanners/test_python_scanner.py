# ========================================
# MARKER: Phase 72.3 Python Scanner Tests
# Date: 2026-01-19
# File: tests/scanners/test_python_scanner.py
# Purpose: Test AST-based Python dependency scanner
# ========================================
"""
Tests for PythonScanner (Phase 72.3).

Test categories:
1. Basic import extraction (import, from import)
2. Relative imports (., .., ...)
3. Conditional imports (TYPE_CHECKING)
4. Dynamic imports (__import__, importlib)
5. Real VETKA-like patterns
6. Edge cases and error handling
"""

import pytest
from pathlib import Path
from typing import List

from src.scanners.python_scanner import PythonScanner, ExtractedImport
from src.scanners.dependency import Dependency, DependencyType
from src.scanners.exceptions import ParseError, UnsupportedFileTypeError


class TestPythonScannerBasics:
    """Test basic PythonScanner functionality."""

    def test_scanner_creation(self, tmp_path: Path):
        """Test creating scanner without files."""
        scanner = PythonScanner(project_root=tmp_path)
        assert scanner.project_root == tmp_path
        assert scanner.supported_extensions == {'.py', '.pyi'}
        assert scanner.scanner_name == 'PythonScanner'

    def test_scanner_with_files(self, sample_project: Path, sample_files: List[str]):
        """Test creating scanner with files."""
        scanner = PythonScanner(
            project_root=sample_project,
            scanned_files=sample_files
        )
        assert len(scanner.scanned_files) > 0
        assert scanner.resolver is not None

    def test_can_scan_python(self, tmp_path: Path):
        """Test can_scan for Python files."""
        scanner = PythonScanner(project_root=tmp_path)
        assert scanner.can_scan('test.py') is True
        assert scanner.can_scan('test.pyi') is True
        assert scanner.can_scan('test.js') is False
        assert scanner.can_scan('test.txt') is False

    def test_update_files(self, sample_project: Path, sample_files: List[str]):
        """Test updating scanned files."""
        scanner = PythonScanner(project_root=sample_project)
        assert scanner.resolver is None

        scanner.update_files(sample_files)
        assert scanner.resolver is not None
        assert len(scanner.scanned_files) > 0


class TestImportExtraction:
    """Test import extraction from Python source."""

    @pytest.fixture
    def scanner(self, tmp_path: Path) -> PythonScanner:
        """Create scanner for extraction tests."""
        return PythonScanner(project_root=tmp_path)

    def test_simple_import(self, scanner: PythonScanner):
        """Test: import module"""
        content = "import os"
        imports = scanner.extract_imports_only(content)

        assert len(imports) == 1
        assert imports[0].module == 'os'
        assert imports[0].names == ['os']
        assert imports[0].is_relative is False

    def test_multiple_imports(self, scanner: PythonScanner):
        """Test: import a, b, c"""
        content = "import os, sys, json"
        imports = scanner.extract_imports_only(content)

        assert len(imports) == 3
        modules = [imp.module for imp in imports]
        assert 'os' in modules
        assert 'sys' in modules
        assert 'json' in modules

    def test_import_as(self, scanner: PythonScanner):
        """Test: import module as alias"""
        content = "import numpy as np"
        imports = scanner.extract_imports_only(content)

        assert len(imports) == 1
        assert imports[0].module == 'numpy'
        assert imports[0].names == ['np']

    def test_from_import(self, scanner: PythonScanner):
        """Test: from module import name"""
        content = "from os import path"
        imports = scanner.extract_imports_only(content)

        assert len(imports) == 1
        assert imports[0].module == 'os'
        assert imports[0].names == ['path']

    def test_from_import_multiple(self, scanner: PythonScanner):
        """Test: from module import a, b, c"""
        content = "from pathlib import Path, PurePath, PosixPath"
        imports = scanner.extract_imports_only(content)

        assert len(imports) == 1
        assert imports[0].module == 'pathlib'
        assert 'Path' in imports[0].names
        assert 'PurePath' in imports[0].names
        assert 'PosixPath' in imports[0].names

    def test_from_import_star(self, scanner: PythonScanner):
        """Test: from module import *"""
        content = "from os.path import *"
        imports = scanner.extract_imports_only(content)

        assert len(imports) == 1
        assert imports[0].module == 'os.path'
        assert '*' in imports[0].names

    def test_dotted_import(self, scanner: PythonScanner):
        """Test: import foo.bar.baz"""
        content = "import xml.etree.ElementTree"
        imports = scanner.extract_imports_only(content)

        assert len(imports) == 1
        assert imports[0].module == 'xml.etree.ElementTree'

    def test_line_numbers(self, scanner: PythonScanner):
        """Test line number tracking."""
        content = """import os

import sys
from pathlib import Path
"""
        imports = scanner.extract_imports_only(content)

        assert len(imports) == 3
        line_numbers = [imp.line_number for imp in imports]
        assert 1 in line_numbers  # import os
        assert 3 in line_numbers  # import sys
        assert 4 in line_numbers  # from pathlib


class TestRelativeImports:
    """Test relative import extraction."""

    @pytest.fixture
    def scanner(self, tmp_path: Path) -> PythonScanner:
        return PythonScanner(project_root=tmp_path)

    def test_single_dot_import(self, scanner: PythonScanner):
        """Test: from . import module"""
        content = "from . import utils"
        imports = scanner.extract_imports_only(content)

        assert len(imports) == 1
        assert imports[0].module == '.'
        assert imports[0].is_relative is True
        assert imports[0].level == 1
        assert 'utils' in imports[0].names

    def test_single_dot_import_with_module(self, scanner: PythonScanner):
        """Test: from .module import name"""
        content = "from .helper import helper_func"
        imports = scanner.extract_imports_only(content)

        assert len(imports) == 1
        assert imports[0].module == '.helper'
        assert imports[0].is_relative is True
        assert imports[0].level == 1
        assert 'helper_func' in imports[0].names

    def test_double_dot_import(self, scanner: PythonScanner):
        """Test: from .. import module"""
        content = "from .. import parent"
        imports = scanner.extract_imports_only(content)

        assert len(imports) == 1
        assert imports[0].module == '..'
        assert imports[0].is_relative is True
        assert imports[0].level == 2

    def test_triple_dot_import(self, scanner: PythonScanner):
        """Test: from ... import module"""
        content = "from ...root import config"
        imports = scanner.extract_imports_only(content)

        assert len(imports) == 1
        assert imports[0].module == '...root'
        assert imports[0].is_relative is True
        assert imports[0].level == 3


class TestConditionalImports:
    """Test TYPE_CHECKING conditional import detection."""

    @pytest.fixture
    def scanner(self, tmp_path: Path) -> PythonScanner:
        return PythonScanner(project_root=tmp_path)

    def test_type_checking_block(self, scanner: PythonScanner):
        """Test TYPE_CHECKING block detection."""
        content = """
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import User
    from .schemas import Schema

import os
"""
        imports = scanner.extract_imports_only(content)

        # Find imports
        type_checking_import = next((i for i in imports if i.module == 'typing'), None)
        user_import = next((i for i in imports if 'User' in i.names), None)
        schema_import = next((i for i in imports if 'Schema' in i.names), None)
        os_import = next((i for i in imports if i.module == 'os'), None)

        assert type_checking_import is not None
        assert user_import is not None
        assert schema_import is not None
        assert os_import is not None

        # TYPE_CHECKING imports should be marked as conditional
        assert user_import.is_conditional is True
        assert schema_import.is_conditional is True

        # Normal imports should not be conditional
        assert type_checking_import.is_conditional is False
        assert os_import.is_conditional is False

    def test_typing_type_checking(self, scanner: PythonScanner):
        """Test typing.TYPE_CHECKING form."""
        content = """
import typing

if typing.TYPE_CHECKING:
    from .models import Model
"""
        imports = scanner.extract_imports_only(content)

        model_import = next((i for i in imports if 'Model' in i.names), None)
        assert model_import is not None
        assert model_import.is_conditional is True


class TestDynamicImports:
    """Test dynamic import detection."""

    @pytest.fixture
    def scanner(self, tmp_path: Path) -> PythonScanner:
        return PythonScanner(project_root=tmp_path)

    def test_dunder_import(self, scanner: PythonScanner):
        """Test __import__('module') detection."""
        content = """
module = __import__('dynamic_module')
"""
        imports = scanner.extract_imports_only(content)

        assert len(imports) == 1
        assert imports[0].module == 'dynamic_module'
        assert imports[0].is_dynamic is True
        assert '__import__' in imports[0].context

    def test_importlib_import_module(self, scanner: PythonScanner):
        """Test importlib.import_module('module') detection."""
        content = """
import importlib
module = importlib.import_module('plugin')
"""
        imports = scanner.extract_imports_only(content)

        # Should have importlib import and dynamic import
        importlib_import = next((i for i in imports if i.module == 'importlib'), None)
        dynamic_import = next((i for i in imports if i.is_dynamic), None)

        assert importlib_import is not None
        assert dynamic_import is not None
        assert dynamic_import.module == 'plugin'
        assert 'importlib.import_module' in dynamic_import.context

    def test_dynamic_with_variable_not_detected(self, scanner: PythonScanner):
        """Dynamic import with variable should not be detected (can't resolve)."""
        content = """
name = 'mymodule'
module = __import__(name)
"""
        imports = scanner.extract_imports_only(content)

        # Variable-based imports are not detected (can't resolve at static time)
        dynamic = [i for i in imports if i.is_dynamic]
        assert len(dynamic) == 0


class TestDependencyExtraction:
    """Test full dependency extraction with resolution."""

    def test_extract_dependencies(
        self,
        sample_project: Path,
        sample_files: List[str]
    ):
        """Test extracting dependencies from file."""
        scanner = PythonScanner(
            project_root=sample_project,
            scanned_files=sample_files,
            src_roots=['src']
        )

        # main.py imports utils
        main_py = sample_project / 'main.py'
        content = main_py.read_text()

        deps = scanner.extract_dependencies(str(main_py), content)

        # Should find utils dependency
        assert len(deps) >= 1
        utils_dep = next((d for d in deps if 'utils' in d.source), None)
        assert utils_dep is not None
        assert utils_dep.dependency_type == DependencyType.IMPORT
        assert utils_dep.target == str(main_py)

    def test_relative_dependency_resolution(
        self,
        relative_imports_project: Path
    ):
        """Test resolving relative import dependencies."""
        files = [str(f) for f in relative_imports_project.rglob('*.py')]
        scanner = PythonScanner(
            project_root=relative_imports_project,
            scanned_files=files
        )

        # pkg/a.py has: from . import b
        a_py = relative_imports_project / 'pkg' / 'a.py'
        content = a_py.read_text()

        deps = scanner.extract_dependencies(str(a_py), content)

        # Should have at least one dependency with relative flag
        # The source could be the module name '.' or resolved path
        assert len(deps) >= 1
        # All deps from this file should be relative
        assert all(d.metadata.get('is_relative') is True for d in deps)

    def test_external_packages_filtered(
        self,
        sample_project: Path,
        sample_files: List[str]
    ):
        """Test that external packages are filtered by default."""
        scanner = PythonScanner(
            project_root=sample_project,
            scanned_files=sample_files
        )

        content = """
import os
import sys
import json
from pathlib import Path
import utils  # local
"""
        deps = scanner.extract_dependencies(str(sample_project / 'test.py'), content)

        # Should only have local utils
        modules = [d.source for d in deps]
        assert not any('os' == m for m in modules)
        assert not any('sys' == m for m in modules)
        assert not any('json' == m for m in modules)

    def test_include_external(
        self,
        sample_project: Path,
        sample_files: List[str]
    ):
        """Test including external packages."""
        scanner = PythonScanner(
            project_root=sample_project,
            scanned_files=sample_files,
            include_external=True
        )

        content = "import os"
        deps = scanner.extract_dependencies(str(sample_project / 'test.py'), content)

        # With include_external=True, should have os
        assert len(deps) == 1
        assert deps[0].source == 'os'


class TestVetkaPatterns:
    """Test patterns from real VETKA codebase."""

    def test_vetka_like_imports(self, vetka_like_project: Path):
        """Test VETKA-style absolute imports."""
        files = [str(f) for f in vetka_like_project.rglob('*.py')]
        scanner = PythonScanner(
            project_root=vetka_like_project,
            scanned_files=files,
            src_roots=['src']
        )

        # cam_engine.py imports from src.agents and src.memory
        cam_engine = vetka_like_project / 'src' / 'orchestration' / 'cam_engine.py'
        content = cam_engine.read_text()

        deps = scanner.extract_dependencies(str(cam_engine), content)

        # Should resolve both imports
        assert len(deps) >= 2

        sources = [d.source for d in deps]
        # Should have resolved to actual files or at least have the module names
        # Source could be resolved path or module name
        sources_lower = [s.lower() for s in sources]
        sources_str = ' '.join(sources_lower)
        # Either resolved path or module name should contain these
        # Note: src.agents resolves to __init__.py, src.agents.learner_agent to learner_agent.py
        assert 'agents' in sources_str
        assert 'qdrant' in sources_str or 'memory' in sources_str

    def test_circular_deps_with_type_checking(
        self,
        circular_deps_project: Path
    ):
        """Test TYPE_CHECKING pattern for circular deps."""
        files = [str(f) for f in circular_deps_project.rglob('*.py')]
        scanner = PythonScanner(
            project_root=circular_deps_project,
            scanned_files=files
        )

        # circular_a.py uses TYPE_CHECKING
        a_py = circular_deps_project / 'pkg' / 'circular_a.py'
        content = a_py.read_text()

        deps = scanner.extract_dependencies(str(a_py), content)

        # Should mark the import as conditional
        b_dep = next((d for d in deps if 'circular_b' in d.source.lower()), None)
        assert b_dep is not None
        assert b_dep.metadata.get('is_conditional') is True


class TestErrorHandling:
    """Test error handling."""

    def test_syntax_error(self, tmp_path: Path):
        """Test handling syntax errors."""
        scanner = PythonScanner(project_root=tmp_path)

        content = """
def broken
    pass
"""
        with pytest.raises(ParseError) as exc_info:
            scanner.extract_dependencies(str(tmp_path / 'broken.py'), content)

        assert 'syntax error' in str(exc_info.value).lower()

    def test_unsupported_file_type(self, tmp_path: Path):
        """Test scanning unsupported file type."""
        scanner = PythonScanner(project_root=tmp_path)

        with pytest.raises(UnsupportedFileTypeError):
            scanner.scan_file('test.js', 'console.log("hi")')

    def test_empty_content(self, tmp_path: Path):
        """Test scanning empty content."""
        scanner = PythonScanner(project_root=tmp_path)

        deps = scanner.scan_file('test.py', '')
        assert deps == []

    def test_whitespace_only(self, tmp_path: Path):
        """Test scanning whitespace-only content."""
        scanner = PythonScanner(project_root=tmp_path)

        deps = scanner.scan_file('test.py', '   \n\n   ')
        assert deps == []


class TestDependencyMetadata:
    """Test Dependency object metadata."""

    def test_dependency_line_number(
        self,
        sample_project: Path,
        sample_files: List[str]
    ):
        """Test line number in dependencies."""
        scanner = PythonScanner(
            project_root=sample_project,
            scanned_files=sample_files
        )

        content = """
import os

import sys
from pathlib import Path
"""
        deps = scanner.extract_dependencies(str(sample_project / 'test.py'), content)

        # All dependencies should have line numbers
        for dep in deps:
            assert dep.line_number is not None
            assert dep.line_number >= 1

    def test_dependency_context(
        self,
        sample_project: Path,
        sample_files: List[str]
    ):
        """Test context in dependencies."""
        scanner = PythonScanner(
            project_root=sample_project,
            scanned_files=sample_files,
            include_external=True  # Include external to test context
        )

        content = "from os.path import join, dirname"
        deps = scanner.extract_dependencies(str(sample_project / 'test.py'), content)

        assert len(deps) >= 1
        # Context should contain original import statement
        assert deps[0].context is not None
        assert 'from' in deps[0].context

    def test_dependency_confidence(
        self,
        sample_project: Path,
        sample_files: List[str]
    ):
        """Test confidence scores."""
        scanner = PythonScanner(
            project_root=sample_project,
            scanned_files=sample_files
        )

        # main.py imports utils (local file)
        main_py = sample_project / 'main.py'
        content = main_py.read_text()

        deps = scanner.extract_dependencies(str(main_py), content)

        # Local resolved imports should have high confidence
        for dep in deps:
            assert 0.0 <= dep.confidence <= 1.0


class TestStatistics:
    """Test scanner statistics."""

    def test_get_statistics(
        self,
        sample_project: Path,
        sample_files: List[str]
    ):
        """Test statistics retrieval."""
        scanner = PythonScanner(
            project_root=sample_project,
            scanned_files=sample_files,
            src_roots=['src']
        )

        stats = scanner.get_statistics()

        assert 'scanner' in stats
        assert stats['scanner'] == 'PythonScanner'
        assert 'extensions' in stats
        assert '.py' in stats['extensions']
        assert 'scanned_files' in stats
        assert stats['scanned_files'] > 0
        assert 'resolver' in stats


class TestEdgeCases:
    """Test edge cases."""

    def test_no_imports(self, tmp_path: Path):
        """Test file with no imports."""
        scanner = PythonScanner(project_root=tmp_path)

        content = """
def hello():
    print("Hello, World!")

x = 1 + 2
"""
        deps = scanner.extract_dependencies(str(tmp_path / 'test.py'), content)
        assert deps == []

    def test_comments_not_imports(self, tmp_path: Path):
        """Test that commented imports are not extracted."""
        scanner = PythonScanner(project_root=tmp_path)

        content = """
# import os
# from sys import path
def main():
    pass
"""
        deps = scanner.extract_dependencies(str(tmp_path / 'test.py'), content)
        assert deps == []

    def test_string_not_imports(self, tmp_path: Path):
        """Test that strings containing import keywords are not extracted."""
        scanner = PythonScanner(project_root=tmp_path)

        content = '''
text = """
import os
from sys import path
"""
'''
        deps = scanner.extract_dependencies(str(tmp_path / 'test.py'), content)
        assert deps == []

    def test_many_imports(
        self,
        sample_project: Path,
        sample_files: List[str]
    ):
        """Test file with many imports."""
        scanner = PythonScanner(
            project_root=sample_project,
            scanned_files=sample_files,
            include_external=True
        )

        content = "\n".join([f"import module_{i}" for i in range(100)])
        deps = scanner.extract_dependencies(str(sample_project / 'test.py'), content)

        # All unresolved, but should still process
        assert len(deps) == 100

    def test_encoding_utf8(self, tmp_path: Path):
        """Test UTF-8 content handling."""
        scanner = PythonScanner(project_root=tmp_path)

        content = """
# -*- coding: utf-8 -*-
# Комментарий на русском
import os
"""
        imports = scanner.extract_imports_only(content)
        assert len(imports) == 1
        assert imports[0].module == 'os'


class TestRealVetkaFiles:
    """Test with real VETKA file content patterns."""

    @pytest.fixture
    def scanner_no_files(self, tmp_path: Path) -> PythonScanner:
        """Scanner without file resolution for pattern testing."""
        return PythonScanner(project_root=tmp_path)

    def test_vetka_import_pattern_1(self, scanner_no_files: PythonScanner):
        """VETKA pattern: from src.module import Class"""
        content = """
from src.agents.learner_agent import LearnerAgent
from src.memory.qdrant_client import QdrantManager
from src.orchestration.services.memory_service import MemoryService
"""
        imports = scanner_no_files.extract_imports_only(content)

        assert len(imports) == 3
        modules = [i.module for i in imports]
        assert 'src.agents.learner_agent' in modules
        assert 'src.memory.qdrant_client' in modules
        assert 'src.orchestration.services.memory_service' in modules

    def test_vetka_import_pattern_2(self, scanner_no_files: PythonScanner):
        """VETKA pattern: relative imports in packages"""
        content = """
from . import handlers
from .services import MemoryService
from ..memory import QdrantManager
"""
        imports = scanner_no_files.extract_imports_only(content)

        assert len(imports) == 3
        assert all(i.is_relative for i in imports)
        levels = [i.level for i in imports]
        assert 1 in levels  # from .
        assert 2 in levels  # from ..

    def test_vetka_import_pattern_3(self, scanner_no_files: PythonScanner):
        """VETKA pattern: mixed stdlib, third-party, local"""
        content = """
import os
import sys
from pathlib import Path
from typing import List, Optional, Dict

import fastapi
from pydantic import BaseModel

from src.config import settings
from src.api.handlers import handle_request
"""
        imports = scanner_no_files.extract_imports_only(content)

        # Count import types
        stdlib = ['os', 'sys', 'pathlib', 'typing']
        third_party = ['fastapi', 'pydantic']
        local = ['src.config', 'src.api.handlers']

        found_modules = [i.module for i in imports]

        for m in stdlib:
            assert m in found_modules

        for m in third_party:
            assert m in found_modules

        for m in local:
            assert m in found_modules

    def test_vetka_type_checking_pattern(self, scanner_no_files: PythonScanner):
        """VETKA pattern: TYPE_CHECKING with circular deps"""
        content = """
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.orchestration.cam_engine import CAMEngine
    from src.agents.learner_agent import LearnerAgent

class MyClass:
    def process(self, engine: 'CAMEngine') -> None:
        pass
"""
        imports = scanner_no_files.extract_imports_only(content)

        # Find conditional imports
        conditional = [i for i in imports if i.is_conditional]
        assert len(conditional) == 2

        # Verify they're the right ones
        cond_modules = [i.module for i in conditional]
        assert 'src.orchestration.cam_engine' in cond_modules
        assert 'src.agents.learner_agent' in cond_modules
