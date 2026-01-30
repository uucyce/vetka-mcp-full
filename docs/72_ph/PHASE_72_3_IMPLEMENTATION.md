# Phase 72.3: Python Scanner Implementation

**Date:** 2026-01-19
**Status:** COMPLETE

## Overview

Phase 72.3 implements the PythonScanner - an AST-based Python dependency scanner that integrates with the ImportResolver from Phase 72.2.

## Files Created

### 1. `src/scanners/python_scanner.py` (132 lines)

Main Python scanner implementation:

```python
class PythonScanner(BaseScanner):
    """
    Python dependency scanner using AST parsing.

    Features:
    - Handles all Python import forms (import X, from X import Y)
    - Detects conditional imports (TYPE_CHECKING blocks)
    - Detects dynamic imports (__import__, importlib)
    - Extracts line numbers and context for each import
    - Integrates with ImportResolver for path resolution
    """
```

Key methods:
- `extract_dependencies(file_path, content) -> List[Dependency]`
- `extract_imports_only(content, file_path) -> List[ExtractedImport]`
- `update_files(scanned_files)` - rebuild module index

### 2. `src/scanners/known_packages.py` (239 lines)

Centralized known packages registry:

```python
# Python standard library (~100 modules)
PYTHON_STDLIB: FrozenSet[str] = _get_stdlib_modules()

# Common third-party packages (~150 packages by category)
PYTHON_THIRD_PARTY: FrozenSet[str] = frozenset({
    # Data Science / ML
    'numpy', 'pandas', 'scipy', ...
    # NLP / AI
    'transformers', 'langchain', 'openai', ...
    # Web Frameworks
    'flask', 'django', 'fastapi', ...
    # ...organized by category
})

def is_external_package(package_name: str) -> bool
def get_all_external_python() -> Set[str]
```

### 3. `tests/scanners/test_python_scanner.py` (44 tests)

Test categories:
- `TestPythonScannerBasics` - creation, can_scan, update_files
- `TestImportExtraction` - all import forms
- `TestRelativeImports` - ., .., ...
- `TestConditionalImports` - TYPE_CHECKING blocks
- `TestDynamicImports` - __import__, importlib
- `TestDependencyExtraction` - full resolution pipeline
- `TestVetkaPatterns` - real VETKA-style imports
- `TestErrorHandling` - syntax errors, unsupported files
- `TestDependencyMetadata` - line numbers, context, confidence
- `TestEdgeCases` - no imports, comments, strings
- `TestRealVetkaFiles` - VETKA import patterns

## Key Features

### AST-Based Parsing

Uses Python's `ast` module for reliable import extraction:

```python
def _extract_imports_from_ast(self, content: str, file_path: str) -> List[ExtractedImport]:
    tree = ast.parse(content, filename=file_path)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            # import X, import X as Y
        elif isinstance(node, ast.ImportFrom):
            # from X import Y, from . import Y
        elif isinstance(node, ast.Call):
            # __import__('X'), importlib.import_module('X')
```

### TYPE_CHECKING Detection

Detects imports inside TYPE_CHECKING blocks:

```python
def _find_type_checking_lines(self, tree: ast.AST) -> Set[int]:
    """Find all line numbers inside TYPE_CHECKING blocks."""
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            if self._is_type_checking_condition(node.test):
                # Mark all lines in the body
```

### Dynamic Import Detection

Detects dynamic imports:

```python
def _check_dynamic_import(self, node: ast.Call) -> Optional[ExtractedImport]:
    # __import__('module')
    # importlib.import_module('module')
```

### Integration with ImportResolver

Full resolution pipeline:

```
Python File → AST Parser → ExtractedImport → ImportResolver → ResolvedImport → Dependency
```

## Test Results

```
=============================== test results ===============================
180 passed in 0.62s
Coverage: 94%

Name                             Stmts   Miss  Cover
--------------------------------------------------------------
src/scanners/known_packages.py      13      2    85%
src/scanners/python_scanner.py     132      6    95%
--------------------------------------------------------------
TOTAL                              145      8    94%
```

## Architecture

```
Phase 72.1: Foundation
├── Dependency, DependencyType  (universal structure)
├── BaseScanner                 (abstract base class)
└── exceptions                  (error types)

Phase 72.2: Import Resolution
├── ImportResolver              (module index + resolution)
├── ResolvedImport             (resolution result)
└── path_utils                 (helper functions)

Phase 72.3: Python Scanner      ← NEW
├── PythonScanner              (AST + ImportResolver)
├── ExtractedImport           (raw import data)
└── known_packages            (stdlib + third-party registry)
```

## Usage Example

```python
from src.scanners import PythonScanner, Dependency

# Create scanner with project files
scanner = PythonScanner(
    project_root=Path("/project"),
    scanned_files=["/project/main.py", "/project/utils.py"],
    src_roots=["src"]
)

# Extract dependencies from a file
content = Path("/project/main.py").read_text()
deps = scanner.extract_dependencies("/project/main.py", content)

for dep in deps:
    print(f"{dep.source} -> {dep.target}")
    print(f"  Line: {dep.line_number}")
    print(f"  Context: {dep.context}")
    print(f"  Confidence: {dep.confidence}")
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `project_root` | required | Root directory for resolution |
| `scanned_files` | `[]` | List of Python files for module index |
| `src_roots` | `[]` | Additional source roots (e.g., `["src"]`) |
| `include_external` | `False` | Include stdlib/third-party deps |

## Next Steps (Phase 72.4)

- Integrate PythonScanner with file watcher
- Add incremental scanning support
- Batch processing for large codebases
- Performance optimization for real-time updates
