#!/usr/bin/env python3
"""
Analyze Python files for unused imports using AST.
"""
import ast
import os
import sys
from pathlib import Path
from collections import defaultdict


class ImportAnalyzer(ast.NodeVisitor):
    """Analyze imports and name usage in Python files."""

    def __init__(self):
        self.imports = {}  # name -> (module, lineno, type)
        self.used_names = set()
        self.in_import = False

    def visit_Import(self, node):
        """Track 'import X' statements."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name.split('.')[0]
            self.imports[name] = (alias.name, node.lineno, 'import')
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Track 'from X import Y' statements."""
        for alias in node.names:
            if alias.name == '*':
                # Can't analyze star imports
                continue
            name = alias.asname if alias.asname else alias.name
            module = node.module or ''
            self.imports[name] = (module, node.lineno, 'from')
        self.generic_visit(node)

    def visit_Name(self, node):
        """Track name usage."""
        self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        """Track attribute access (e.g., module.function)."""
        # Extract the base name
        if isinstance(node.value, ast.Name):
            self.used_names.add(node.value.id)
        self.generic_visit(node)

    def visit_arg(self, node):
        """Track function arguments."""
        # Don't count function parameters as used imports
        self.generic_visit(node)

    def get_unused_imports(self):
        """Return list of unused imports."""
        unused = []
        for name, (module, lineno, imp_type) in self.imports.items():
            if name not in self.used_names:
                # Special cases to skip
                if name in ['__all__', '__version__']:
                    continue
                unused.append({
                    'name': name,
                    'module': module,
                    'lineno': lineno,
                    'type': imp_type
                })
        return unused


def analyze_file(filepath):
    """Analyze a single Python file for unused imports."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Skip empty files
        if not content.strip():
            return []

        tree = ast.parse(content, filename=str(filepath))
        analyzer = ImportAnalyzer()
        analyzer.visit(tree)
        return analyzer.get_unused_imports()
    except SyntaxError as e:
        print(f"Syntax error in {filepath}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}", file=sys.stderr)
        return []


def main():
    src_dir = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src')

    if not src_dir.exists():
        print(f"Directory not found: {src_dir}")
        return

    results = defaultdict(list)
    file_count = 0

    # Analyze all Python files
    for py_file in src_dir.rglob('*.py'):
        file_count += 1
        unused = analyze_file(py_file)
        if unused:
            results[str(py_file)] = unused

    # Print summary
    print("=" * 80)
    print(f"UNUSED IMPORTS ANALYSIS - VETKA CODEBASE")
    print("=" * 80)
    print(f"Total Python files analyzed: {file_count}")
    print(f"Files with unused imports: {len(results)}")
    print()

    # Sort by number of unused imports
    sorted_results = sorted(results.items(), key=lambda x: len(x[1]), reverse=True)

    # Print top offenders
    print("=" * 80)
    print("TOP 20 FILES BY UNUSED IMPORT COUNT")
    print("=" * 80)
    for filepath, unused in sorted_results[:20]:
        print(f"\n{filepath}")
        print(f"  Unused imports: {len(unused)}")

    # Print detailed report
    print("\n" + "=" * 80)
    print("DETAILED REPORT")
    print("=" * 80)

    total_unused = 0
    for filepath, unused in sorted_results:
        if not unused:
            continue

        print(f"\n{filepath}")
        for item in sorted(unused, key=lambda x: x['lineno']):
            total_unused += 1
            if item['type'] == 'import':
                print(f"  Line {item['lineno']:4d}: import {item['module']} (as {item['name']})")
            else:
                print(f"  Line {item['lineno']:4d}: from {item['module']} import {item['name']}")

    print("\n" + "=" * 80)
    print(f"TOTAL UNUSED IMPORTS: {total_unused}")
    print("=" * 80)

    # Pattern analysis
    print("\n" + "=" * 80)
    print("COMMON UNUSED IMPORT PATTERNS")
    print("=" * 80)

    import_freq = defaultdict(int)
    for filepath, unused in results.items():
        for item in unused:
            if item['type'] == 'import':
                import_freq[f"import {item['module']}"] += 1
            else:
                import_freq[f"from {item['module']} import {item['name']}"] += 1

    print("\nMost frequent unused imports:")
    for import_stmt, count in sorted(import_freq.items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"  {count:3d}x: {import_stmt}")


if __name__ == '__main__':
    main()
