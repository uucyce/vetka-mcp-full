# Phase 72.1: Foundation - Dependency Dataclass + BaseScanner ABC

**Date:** 2026-01-19
**Status:** COMPLETED
**Author:** Claude Opus 4.5

---

## Overview

Phase 72.1 establishes the foundation for VETKA's universal dependency scanning system.
This phase creates the core data structures and abstractions that all future scanners
will build upon.

### Goals Achieved

- [x] `Dependency` dataclass - Universal structure for all content types
- [x] `DependencyType` enum - Extensible types (import, reference, temporal_semantic, etc.)
- [x] `BaseScanner` ABC - Abstract base class with contract tests
- [x] Custom exceptions - `ScannerError`, `ParseError`, etc.
- [x] 77 unit tests passing
- [x] >90% coverage on new code

---

## Files Created/Modified

### New Files

| File | Purpose | Lines |
|------|---------|-------|
| `src/scanners/exceptions.py` | Custom exceptions | 53 |
| `src/scanners/dependency.py` | Dependency dataclass + DependencyType enum | 180 |
| `src/scanners/base_scanner.py` | BaseScanner ABC | 115 |
| `tests/scanners/__init__.py` | Test package | 12 |
| `tests/scanners/test_dependency.py` | Dependency unit tests | 230 |
| `tests/scanners/test_base_scanner.py` | BaseScanner tests + contract tests | 280 |

### Modified Files

| File | Changes |
|------|---------|
| `src/scanners/__init__.py` | Extended with Phase 72.1 exports (legacy preserved) |

---

## Architecture

### Dependency Structure

```
Dependency(A → B) means "B depends on A"

Examples:
- Code: main.py imports utils.py
        → Dependency(target="main.py", source="utils.py", type=IMPORT)

- Doc:  report.md references data.csv
        → Dependency(target="report.md", source="data.csv", type=REFERENCE)

- Video: tutorial_02.mp4 continues tutorial_01.mp4
         → Dependency(target="tutorial_02.mp4", source="tutorial_01.mp4",
                      type=CONTINUATION)
```

### DependencyType Enum

```python
class DependencyType(Enum):
    # Code
    IMPORT = "import"
    REQUIRE = "require"

    # Documents
    REFERENCE = "reference"
    CITATION = "citation"
    FOOTNOTE = "footnote"

    # Semantic (computed)
    TEMPORAL_SEMANTIC = "temporal_semantic"
    PREREQUISITE = "prerequisite"

    # Media (future)
    DERIVED = "derived"
    CONTINUATION = "continuation"
    CHAPTER = "chapter"
```

### BaseScanner ABC

```python
class BaseScanner(ABC):
    @property
    @abstractmethod
    def supported_extensions(self) -> Set[str]: ...

    @abstractmethod
    def extract_dependencies(self, file_path: str, content: str) -> List[Dependency]: ...

    def can_scan(self, file_path: str) -> bool: ...
    def validate_content(self, content: str) -> bool: ...
    def scan_file(self, file_path: str, content: str) -> List[Dependency]: ...
```

---

## Test Coverage

```
Name                         Stmts   Miss  Cover
------------------------------------------------
src/scanners/__init__.py         7      0   100%
src/scanners/base_scanner.py    30      2    93%
src/scanners/dependency.py      66      1    98%
src/scanners/exceptions.py       8      0   100%
------------------------------------------------
NEW CODE TOTAL                 111      3    97%
```

### Contract Tests

Contract tests ensure ANY future scanner automatically validates:

```python
class ScannerContractTests:
    def test_contract_has_supported_extensions(self, scanner): ...
    def test_contract_extensions_are_lowercase_with_dot(self, scanner): ...
    def test_contract_can_scan_returns_bool(self, scanner): ...
    def test_contract_extract_dependencies_returns_list(self, scanner): ...
    def test_contract_dependencies_are_valid(self, scanner): ...
    def test_contract_validate_content_returns_bool(self, scanner): ...
    def test_contract_scan_file_respects_can_scan(self, scanner): ...
    def test_contract_empty_content_no_crash(self, scanner): ...
    def test_contract_large_content_no_crash(self, scanner): ...
```

Usage for new scanners:

```python
class TestVideoScannerContract(ScannerContractTests):
    @pytest.fixture
    def scanner(self):
        return VideoScanner()
```

---

## Usage Examples

### Creating Dependencies

```python
from src.scanners import Dependency, DependencyType

# Explicit import
dep = Dependency(
    target="main.py",
    source="utils.py",
    dependency_type=DependencyType.IMPORT,
    confidence=1.0,
    line_number=5,
    context="from utils import helper"
)

# Serialization
data = dep.to_dict()
restored = Dependency.from_dict(data)

# Check type
dep.is_explicit()   # True for IMPORT, REQUIRE, REFERENCE
dep.is_inferred()   # True for TEMPORAL_SEMANTIC, PREREQUISITE
```

### Implementing a Scanner

```python
from src.scanners import BaseScanner, Dependency, DependencyType

class MyScanner(BaseScanner):
    @property
    def supported_extensions(self) -> Set[str]:
        return {'.my', '.myext'}

    def extract_dependencies(self, file_path: str, content: str) -> List[Dependency]:
        dependencies = []
        # Parse content and find dependencies
        # ...
        return dependencies
```

---

## Next Steps

### Phase 72.2: Import Resolution Research

- Research Python import resolution (sys.path, relative imports)
- Research JS/TS module resolution (node_modules, aliases)
- Document fallback strategies
- Create `ImportResolver` prototype

### Phase 72.3: CodeScanner

- Implement Python scanner with AST
- Implement JS/TS scanner with regex
- Add async wrappers
- Integration with ImportResolver

---

## Acceptance Criteria - VERIFIED

- [x] All 7 files created and implemented
- [x] Dependency dataclass fully functional
- [x] BaseScanner ABC properly abstracted
- [x] All tests pass (77/77)
- [x] Coverage >90% (97% on new code)
- [x] No warnings/errors in linters
- [x] Markers installed in all files
- [x] Code follows PEP 8
- [x] Docstrings for all public methods
- [x] Contract tests for future scanners

---

*Phase 72.1 Complete. Ready for review and commit.*
