# src/scanners/local_project_scanner.py
"""
Scan local project directories to create Phase 9 format data.
FIXED: Limits + symlinks protection (Haiku bug #6)
MARKER_136.W3A: Added project type auto-detection (Phase 136 Wave 3)

@status: active
@phase: 136
@depends: config.design_system
@used_by: tree_routes, visualization
"""

import os
import hashlib
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.design_system import SCANNER_LIMITS


class LocalProjectScanner:
    """Scans local project and creates Phase 9 compatible data."""

    IGNORE_PATTERNS = [
        '.git', '__pycache__', 'node_modules', '.env',
        '.DS_Store', '*.pyc', 'build', 'dist', 'venv', '.venv',
        '.idea', '.vscode', 'target', '.gradle', 'Pods',
        # MARKER_149.SCAN_SKIP: Prevent indexing temporary agent worktrees
        '.playgrounds', '.claude',  # Playground sandboxes + Codex worktrees
        'site-packages', 'venv_mcp',  # Virtual environments
    ]

    LANG_MAP = {
        '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
        '.jsx': 'jsx', '.tsx': 'tsx', '.java': 'java',
        '.cpp': 'cpp', '.c': 'c', '.go': 'go', '.rs': 'rust',
        '.rb': 'ruby', '.php': 'php', '.sql': 'sql',
        '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml',
        '.md': 'markdown', '.txt': 'text', '.html': 'html',
        '.css': 'css', '.scss': 'scss', '.swift': 'swift',
        '.kt': 'kotlin', '.scala': 'scala'
    }

    # MARKER_136.W3A: Project type detection signatures
    PROJECT_SIGNATURES = {
        # Frontend frameworks
        'react': ['package.json', 'src/App.tsx', 'src/App.jsx', 'src/index.tsx'],
        'vue': ['package.json', 'src/App.vue', 'vue.config.js', 'vite.config.ts'],
        'angular': ['angular.json', 'package.json', 'src/app/app.module.ts'],
        'svelte': ['svelte.config.js', 'src/App.svelte'],
        'next': ['next.config.js', 'next.config.mjs', 'pages/', 'app/'],

        # Backend frameworks
        'fastapi': ['requirements.txt', 'main.py', 'app/main.py'],
        'django': ['manage.py', 'settings.py', 'requirements.txt'],
        'flask': ['app.py', 'requirements.txt', 'wsgi.py'],
        'express': ['package.json', 'server.js', 'app.js', 'index.js'],
        'nestjs': ['nest-cli.json', 'package.json', 'src/main.ts'],

        # Languages
        'python': ['requirements.txt', 'setup.py', 'pyproject.toml', '*.py'],
        'node': ['package.json', 'node_modules'],
        'rust': ['Cargo.toml', 'src/main.rs', 'src/lib.rs'],
        'go': ['go.mod', 'go.sum', 'main.go'],
        'java': ['pom.xml', 'build.gradle', 'src/main/java'],
        'swift': ['Package.swift', '*.xcodeproj', '*.xcworkspace'],

        # Tools
        'tauri': ['src-tauri/', 'tauri.conf.json'],
        'electron': ['electron.js', 'main.js', 'package.json'],
        'docker': ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml'],
        'monorepo': ['lerna.json', 'pnpm-workspace.yaml', 'turbo.json'],
    }

    def scan(self, directory: str) -> dict:
        """Scan directory and return Phase 9 format data."""
        root = Path(directory)
        if not root.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        # Collect files with limits
        files = []
        for item in self._walk_safe(root):
            if item.is_file() and len(files) < SCANNER_LIMITS["max_files"]:
                files.append({
                    "name": item.name,
                    "path": str(item.relative_to(root)),
                    "language": self._detect_lang(item),
                    "size_bytes": item.stat().st_size
                })

        # Create workflow ID
        workflow_id = f"scan_{root.name}_{hashlib.md5(str(root).encode()).hexdigest()[:8]}"

        # Find tests
        test_files = [f["name"] for f in files if self._is_test(f["name"])]

        # MARKER_136.W3A: Detect project type
        project_info = self.detect_project_type(directory)

        return {
            "workflow_id": workflow_id,
            "timestamp": datetime.now().isoformat(),
            "source": "local_scan",
            "scanned_path": str(root.absolute()),

            # MARKER_136.W3A: Project type info
            "project_type": project_info,

            "pm_result": {
                "plan": f"Local project: {root.name}",
                "description": f"Scanned {len(files)} files",
                "eval_score": 0.75
            },

            "architect_result": {
                "description": f"Project structure of {root.name}",
                "directories": list(set(str(Path(f["path"]).parent) for f in files))[:20],
                "eval_score": 0.70
            },

            "dev_result": {
                "files": files,
                "total_files": len(files),
                "eval_score": 0.80
            },

            "qa_result": {
                "tests": test_files,
                "passed": len(test_files),
                "failed": 0,
                "coverage": 0,
                "eval_score": 0.60 if test_files else 0.30
            },

            "arc_suggestions": [
                {"transformation": "Add documentation", "success": 0.85}
            ] if not any(f["language"] == "markdown" for f in files) else [],

            "metrics": {
                "total_files": len(files),
                "scan_time_ms": 0
            }
        }

    def _walk_safe(self, root: Path, current_depth: int = 0, visited: set = None):
        """
        Walk directory with protection against:
        - Infinite loops (symlinks)
        - Too many directories
        - Too deep nesting
        FIXED: Haiku bug #6
        """
        if visited is None:
            visited = set()

        # Check depth limit
        if current_depth > SCANNER_LIMITS["max_depth"]:
            return

        # Prevent infinite loops (symlinks)
        try:
            real_path = root.resolve()
        except OSError:
            return

        if real_path in visited:
            return
        visited.add(real_path)

        # Check total directories limit
        if len(visited) > SCANNER_LIMITS["max_directories"]:
            return

        try:
            items = sorted(root.iterdir())[:SCANNER_LIMITS["max_items_per_dir"]]
            for item in items:
                if self._should_ignore(item):
                    continue

                yield item

                # Recurse into directories (but not symlinks)
                if item.is_dir() and not item.is_symlink():
                    yield from self._walk_safe(item, current_depth + 1, visited)

        except (PermissionError, OSError):
            pass

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored."""
        name = path.name
        for pattern in self.IGNORE_PATTERNS:
            if pattern.startswith('*'):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern or name.startswith(pattern):
                return True
        return False

    def _detect_lang(self, path: Path) -> str:
        """Detect language from extension."""
        return self.LANG_MAP.get(path.suffix.lower(), 'unknown')

    def _is_test(self, filename: str) -> bool:
        """Check if file is a test."""
        name_lower = filename.lower()
        return any(p in name_lower for p in ['test_', '_test.', '.spec.', '.test.'])

    # MARKER_136.W3A: Detect project type from signature files
    def detect_project_type(self, directory: str) -> dict:
        """
        Detect project type based on signature files.
        Returns: {type: str, framework: str, languages: list, confidence: float}
        """
        root = Path(directory)
        if not root.is_dir():
            return {"type": "unknown", "framework": None, "languages": [], "confidence": 0.0}

        # Collect root-level files and directories
        try:
            root_items = set(item.name for item in root.iterdir())
        except PermissionError:
            return {"type": "unknown", "framework": None, "languages": [], "confidence": 0.0}

        detected = []
        languages = set()

        # Check each signature
        for project_type, signatures in self.PROJECT_SIGNATURES.items():
            matches = 0
            for sig in signatures:
                if sig.endswith('/'):
                    # Check for directory
                    if sig.rstrip('/') in root_items and (root / sig.rstrip('/')).is_dir():
                        matches += 1
                elif sig.startswith('*.'):
                    # Check for extension pattern
                    ext = sig[1:]  # e.g., '.py'
                    if any(f.endswith(ext) for f in root_items):
                        matches += 1
                elif '/' in sig:
                    # Check for nested path
                    if (root / sig).exists():
                        matches += 1
                else:
                    # Check for exact file
                    if sig in root_items:
                        matches += 1

            if matches > 0:
                confidence = matches / len(signatures)
                detected.append((project_type, confidence))

        # Determine primary language from file extensions
        for item in root_items:
            if item.endswith('.py') or item == 'requirements.txt' or item == 'pyproject.toml':
                languages.add('python')
            if item.endswith(('.ts', '.tsx')) or item == 'tsconfig.json':
                languages.add('typescript')
            if item.endswith(('.js', '.jsx')) or item == 'package.json':
                languages.add('javascript')
            if item.endswith('.rs') or item == 'Cargo.toml':
                languages.add('rust')
            if item.endswith('.go') or item == 'go.mod':
                languages.add('go')
            if item.endswith('.java') or item == 'pom.xml':
                languages.add('java')
            if item.endswith('.swift') or item == 'Package.swift':
                languages.add('swift')

        # Sort by confidence and pick top results
        detected.sort(key=lambda x: x[1], reverse=True)

        if detected:
            best = detected[0]
            # Separate framework from language type
            framework_types = {'react', 'vue', 'angular', 'svelte', 'next', 'fastapi', 'django', 'flask', 'express', 'nestjs', 'tauri', 'electron'}
            framework = best[0] if best[0] in framework_types else None
            project_type = best[0] if best[0] not in framework_types else (detected[1][0] if len(detected) > 1 else list(languages)[0] if languages else 'unknown')

            return {
                "type": project_type,
                "framework": framework,
                "languages": list(languages),
                "confidence": best[1],
                "all_detected": [{"type": d[0], "confidence": round(d[1], 2)} for d in detected[:5]]
            }

        return {
            "type": list(languages)[0] if languages else "unknown",
            "framework": None,
            "languages": list(languages),
            "confidence": 0.5 if languages else 0.0,
            "all_detected": []
        }
