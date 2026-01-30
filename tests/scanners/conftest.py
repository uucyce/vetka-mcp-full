# ========================================
# MARKER: Phase 72.2 Python Import Resolution
# Date: 2026-01-19
# File: tests/scanners/conftest.py
# Purpose: Pytest fixtures for scanner tests
# ========================================
"""
Pytest fixtures for VETKA scanner tests.

Provides:
- Temporary project structures for testing
- Pre-configured ImportResolver instances
- Sample Python files with various import patterns
"""

import pytest
from pathlib import Path
from typing import List


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """
    Create a sample project structure for testing.

    Structure:
        tmp_path/
        ├── main.py
        ├── utils.py
        ├── config.py
        ├── package/
        │   ├── __init__.py
        │   ├── module.py
        │   └── subpackage/
        │       ├── __init__.py
        │       └── deep.py
        └── src/
            ├── __init__.py
            ├── api/
            │   ├── __init__.py
            │   └── handlers.py
            └── utils/
                ├── __init__.py
                └── helper.py
    """
    # Root level files
    (tmp_path / 'main.py').write_text('# Main entry point\nimport utils\n')
    (tmp_path / 'utils.py').write_text('# Utilities\ndef helper(): pass\n')
    (tmp_path / 'config.py').write_text('# Configuration\nDEBUG = True\n')

    # Simple package
    pkg = tmp_path / 'package'
    pkg.mkdir()
    (pkg / '__init__.py').write_text('from .module import Module\n')
    (pkg / 'module.py').write_text('class Module: pass\n')

    # Nested subpackage
    subpkg = pkg / 'subpackage'
    subpkg.mkdir()
    (subpkg / '__init__.py').write_text('from .deep import DeepClass\n')
    (subpkg / 'deep.py').write_text('class DeepClass: pass\n')

    # src directory (common pattern)
    src = tmp_path / 'src'
    src.mkdir()
    (src / '__init__.py').write_text('')

    # src/api
    api = src / 'api'
    api.mkdir()
    (api / '__init__.py').write_text('from .handlers import handle\n')
    (api / 'handlers.py').write_text('def handle(): pass\n')

    # src/utils
    src_utils = src / 'utils'
    src_utils.mkdir()
    (src_utils / '__init__.py').write_text('from .helper import help_func\n')
    (src_utils / 'helper.py').write_text('def help_func(): pass\n')

    return tmp_path


@pytest.fixture
def sample_files(sample_project: Path) -> List[str]:
    """Get list of all Python files in sample project."""
    return [str(f) for f in sample_project.rglob('*.py')]


@pytest.fixture
def import_resolver(sample_project: Path, sample_files: List[str]):
    """Create ImportResolver with sample project."""
    from src.scanners.import_resolver import ImportResolver

    return ImportResolver(
        project_root=sample_project,
        scanned_files=sample_files,
        src_roots=['src']
    )


@pytest.fixture
def minimal_project(tmp_path: Path) -> Path:
    """
    Create minimal project for basic tests.

    Structure:
        tmp_path/
        ├── main.py
        └── utils.py
    """
    (tmp_path / 'main.py').write_text('import utils\n')
    (tmp_path / 'utils.py').write_text('X = 1\n')
    return tmp_path


@pytest.fixture
def relative_imports_project(tmp_path: Path) -> Path:
    """
    Create project structure for testing relative imports.

    Structure:
        tmp_path/
        ├── root_utils.py
        └── pkg/
            ├── __init__.py
            ├── a.py
            ├── b.py
            └── sub/
                ├── __init__.py
                ├── c.py
                └── d.py
    """
    # Root level
    (tmp_path / 'root_utils.py').write_text('ROOT = True\n')

    # Package
    pkg = tmp_path / 'pkg'
    pkg.mkdir()
    (pkg / '__init__.py').write_text('PKG_INIT = True\n')
    (pkg / 'a.py').write_text('# Module A\nfrom . import b\n')
    (pkg / 'b.py').write_text('# Module B\nB_VAR = 1\n')

    # Subpackage
    sub = pkg / 'sub'
    sub.mkdir()
    (sub / '__init__.py').write_text('SUB_INIT = True\n')
    (sub / 'c.py').write_text('# Module C\nfrom .. import a\nfrom ..b import B_VAR\n')
    (sub / 'd.py').write_text('# Module D\nfrom ... import root_utils\n')

    return tmp_path


@pytest.fixture
def circular_deps_project(tmp_path: Path) -> Path:
    """
    Create project with TYPE_CHECKING-based circular dependency pattern.

    Structure:
        tmp_path/
        └── pkg/
            ├── __init__.py
            ├── circular_a.py  (TYPE_CHECKING import of B)
            └── circular_b.py  (direct import of A)
    """
    pkg = tmp_path / 'pkg'
    pkg.mkdir()
    (pkg / '__init__.py').write_text('')

    # A uses TYPE_CHECKING to avoid runtime cycle
    (pkg / 'circular_a.py').write_text('''
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .circular_b import ClassB

class ClassA:
    def use_b(self, b: 'ClassB') -> str:
        return f"Using {b}"
''')

    # B imports A directly (safe because A doesn't import B at runtime)
    (pkg / 'circular_b.py').write_text('''
from .circular_a import ClassA

class ClassB:
    def __init__(self):
        self.a = ClassA()
''')

    return tmp_path


@pytest.fixture
def deep_nesting_project(tmp_path: Path) -> Path:
    """
    Create deeply nested project structure.

    Structure:
        tmp_path/
        └── a/
            └── b/
                └── c/
                    └── d/
                        └── e/
                            └── module.py
    """
    current = tmp_path
    for name in ['a', 'b', 'c', 'd', 'e']:
        current = current / name
        current.mkdir()
        (current / '__init__.py').write_text(f'{name.upper()}_INIT = True\n')

    (current / 'module.py').write_text('DEEP_MODULE = True\n')
    return tmp_path


@pytest.fixture
def vetka_like_project(tmp_path: Path) -> Path:
    """
    Create project structure similar to VETKA.

    Structure:
        tmp_path/
        └── src/
            ├── __init__.py
            ├── agents/
            │   ├── __init__.py
            │   └── learner_agent.py
            ├── orchestration/
            │   ├── __init__.py
            │   ├── cam_engine.py
            │   └── services/
            │       ├── __init__.py
            │       └── memory_service.py
            └── memory/
                ├── __init__.py
                └── qdrant_client.py
    """
    src = tmp_path / 'src'
    src.mkdir()
    (src / '__init__.py').write_text('')

    # agents
    agents = src / 'agents'
    agents.mkdir()
    (agents / '__init__.py').write_text('from .learner_agent import LearnerAgent\n')
    (agents / 'learner_agent.py').write_text('class LearnerAgent: pass\n')

    # orchestration
    orch = src / 'orchestration'
    orch.mkdir()
    (orch / '__init__.py').write_text('')
    (orch / 'cam_engine.py').write_text(
        'from src.agents import LearnerAgent\n'
        'from src.memory.qdrant_client import QdrantManager\n'
        'class CAMEngine: pass\n'
    )

    # orchestration/services
    services = orch / 'services'
    services.mkdir()
    (services / '__init__.py').write_text('from .memory_service import MemoryService\n')
    (services / 'memory_service.py').write_text(
        'from src.memory.qdrant_client import QdrantManager\n'
        'class MemoryService: pass\n'
    )

    # memory
    memory = src / 'memory'
    memory.mkdir()
    (memory / '__init__.py').write_text('from .qdrant_client import QdrantManager\n')
    (memory / 'qdrant_client.py').write_text('class QdrantManager: pass\n')

    return tmp_path
