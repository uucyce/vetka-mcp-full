#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

IMPORT_RE = re.compile(r'^(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))')


def module_to_relpath(module_name: str) -> str:
    return module_name.replace('.', '/') + '.py'


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def collect_manifest_python_paths(manifest: dict) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for group in manifest.get('groups', []):
        name = str(group.get('name', '')).strip()
        paths = [str(p) for p in group.get('paths', []) if str(p).endswith('.py')]
        groups[name] = paths
    return groups


def audit_dependencies(source_root: Path, manifest_path: Path) -> dict:
    manifest = load_manifest(manifest_path)
    groups = collect_manifest_python_paths(manifest)
    manifest_paths = {p for paths in groups.values() for p in paths}

    imports_by_file: dict[str, list[str]] = {}
    all_internal_modules: set[str] = set()
    unresolved_modules: set[str] = set()

    for rel_path in sorted(manifest_paths):
        file_path = source_root / rel_path
        imports: list[str] = []
        if not file_path.exists():
            imports_by_file[rel_path] = imports
            continue
        for line in file_path.read_text(encoding='utf-8').splitlines():
            match = IMPORT_RE.match(line.strip())
            if not match:
                continue
            module_name = match.group(1) or match.group(2)
            if not module_name.startswith('src.') or module_name in {'src', 'src.api.routes'}:
                continue
            imports.append(module_name)
            all_internal_modules.add(module_name)
            candidate = source_root / module_to_relpath(module_name)
            if not candidate.exists():
                unresolved_modules.add(module_name)
        imports_by_file[rel_path] = sorted(set(imports))

    transitive_relpaths = sorted(module_to_relpath(m) for m in all_internal_modules)
    missing_from_manifest = [p for p in transitive_relpaths if p not in manifest_paths and (source_root / p).exists()]
    unresolved_relpaths = sorted(module_to_relpath(m) for m in unresolved_modules)

    return {
        'schema_version': 'cut_core_dep_audit_v1',
        'manifest_path': str(manifest_path),
        'source_root': str(source_root),
        'manifest_groups': groups,
        'mirrored_python_paths': sorted(manifest_paths),
        'imports_by_file': imports_by_file,
        'transitive_internal_relpaths': transitive_relpaths,
        'missing_from_manifest_relpaths': missing_from_manifest,
        'unresolved_internal_relpaths': unresolved_relpaths,
        'summary': {
            'mirrored_python_file_count': len(manifest_paths),
            'transitive_internal_count': len(transitive_relpaths),
            'missing_from_manifest_count': len(missing_from_manifest),
            'unresolved_internal_count': len(unresolved_relpaths),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Audit transitive internal dependencies for the CUT core mirror manifest.')
    parser.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--manifest', type=Path, default=Path(__file__).resolve().parents[2] / 'config' / 'cut' / 'cut_core_mirror_manifest.example.json')
    parser.add_argument('--output', type=Path, default=None, help='Optional JSON output path.')
    args = parser.parse_args()

    report = audit_dependencies(args.source_root.resolve(), args.manifest.resolve())
    rendered = json.dumps(report, indent=2, ensure_ascii=True) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding='utf-8')
        print(f"[MARKER_170.CORE.BOOT_REPORT] wrote {args.output}")
    else:
        print(rendered)
    print('[MARKER_170.CORE.BOOT_AUDIT] dependency audit complete')
    print('[MARKER_170.CORE.DEP_AUDIT_SCRIPT] audit_cut_core_mirror_deps.py ready')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
