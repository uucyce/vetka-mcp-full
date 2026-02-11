# VETKA Dual-Stack Hygiene: FastAPI + Tauri

> **Source:** Grok Analysis + Legacy Hygiene Rules (2026-01-29)
> **Status:** Active Policy
> **Scope:** Параллельная разработка SaaS (FastAPI) и Desktop (Tauri)

## Core Principle: Monorepo + Trunk-Based Development

**Одна репа, один main branch, атомарные коммиты.**

```
vetka_live_03/
├── src/                    # FastAPI Backend (Python)
│   ├── api/
│   ├── agents/
│   ├── memory/
│   └── ...
├── client/                 # Shared Frontend (React/TS)
│   ├── src/
│   ├── src-tauri/          # Tauri-specific (Rust)
│   └── package.json
├── shared/                 # NEW: Cross-stack contracts
│   ├── api-specs/          # OpenAPI schemas
│   └── types/              # Shared TypeScript types
├── docs/
└── scripts/
```

## Branching Strategy

### DO: Trunk-Based Development
- `main` branch ВСЕГДА deployable
- Feature branches: **короткие** (1-2 дня), по фиче, НЕ по стеку
- Пример: `feat/artifact-save` затрагивает и backend, и frontend

### DON'T: Отдельные ветки по стекам
- ❌ `dev-tauri`, `dev-fastapi` - приводит к drift
- ❌ Долгоживущие feature branches

## File Marking (Обязательно!)

### Python Files
```python
"""
@file artifact_extractor.py
@status active
@phase 17-J
@depends response_formatter, qdrant_client
@used_by user_message_handler, response_manager
@stack shared (works with both FastAPI and Tauri frontend)
"""
```

### TypeScript/React Files
```typescript
/**
 * @file ArtifactPanel.tsx
 * @status active
 * @phase 96
 * @depends useSocket, FloatingWindow
 * @used_by App
 * @stack frontend (browser + tauri webview)
 */
```

### Rust Files (Tauri)
```rust
/// @file main.rs
/// @status active
/// @phase 100.5
/// @stack tauri-only (desktop native features)
```

## Stack Markers

| Marker | Meaning |
|--------|---------|
| `@stack shared` | Works everywhere (API handlers, common utils) |
| `@stack frontend` | React components (browser + Tauri WebView) |
| `@stack backend` | FastAPI-only (server routes, sockets) |
| `@stack tauri-only` | Native desktop features (Rust, IPC) |
| `@stack browser-only` | Browser-specific (Service Workers, etc.) |

## Compatibility Rules

### Rule 1: API Contracts in `shared/`
```yaml
# shared/api-specs/artifacts.yaml
openapi: 3.0.0
paths:
  /api/artifacts/{id}:
    get:
      responses:
        200:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Artifact'
```

Generate clients:
```bash
# Python (backend tests)
openapi-python-client generate --path shared/api-specs/artifacts.yaml

# TypeScript (frontend)
npx openapi-typescript shared/api-specs/artifacts.yaml -o client/src/types/api.d.ts
```

### Rule 2: Feature Detection, Not Branching
```typescript
// client/src/config/tauri.ts
export function isTauri(): boolean {
  return typeof window !== 'undefined' && '__TAURI__' in window;
}

// Usage in components
if (isTauri()) {
  await saveArtifactNative(filename, content);  // Tauri IPC
} else {
  await saveArtifactHTTP(filename, content);    // FastAPI endpoint
}
```

### Rule 3: Socket Events Are Universal
```python
# Backend emits same events for both platforms
socketio.emit('artifact_created', {...})  # Both browser and Tauri receive
```

```typescript
// Frontend handles identically
socket.on('artifact_created', (data) => {
  // Same logic for browser and Tauri WebView
});
```

## Daily Workflow

### Morning
```bash
git pull origin main
cd client && npm run dev          # Frontend
cd .. && python -m src.main       # Backend
# OR for Tauri:
cd client && npm run tauri dev    # Tauri dev server
```

### Development
1. Edit files across both stacks if needed
2. Small commits: "backend: add artifact endpoint" then "frontend: handle artifact socket"
3. Test both platforms before PR

### Before Commit
```bash
# Run hygiene checks
./scripts/audit.sh

# Checklist:
# [ ] New files have @status, @stack markers
# [ ] No duplicate function names
# [ ] DEPENDENCY_MAP.md updated if routes changed
# [ ] Both `npm run dev` and `npm run tauri dev` work
```

## CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: Dual-Stack CI

on: [pull_request, push]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Python Tests
        run: |
          pip install -r requirements.txt
          pytest tests/ --cov
      - name: Lint
        run: ruff check src/

  frontend-browser:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Browser
        run: |
          cd client
          npm ci
          npm run build
      - name: Lint
        run: cd client && npm run lint

  frontend-tauri:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Tauri
        uses: tauri-apps/tauri-action@v0
        with:
          args: --debug

  integration:
    runs-on: ubuntu-latest
    needs: [backend, frontend-browser]
    steps:
      - uses: actions/checkout@v4
      - name: Start Backend
        run: |
          pip install -r requirements.txt
          python -m src.main &
          sleep 5
      - name: E2E Tests
        run: |
          cd client
          npm ci
          npm run test:e2e

  api-contract:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate OpenAPI
        run: |
          npx @openapitools/openapi-generator-cli validate \
            -i shared/api-specs/*.yaml
```

## Audit Commands

```bash
# Add to ~/.bashrc or scripts/

# Files without @stack marker
alias vetka-no-stack='grep -rL "@stack" src/**/*.py client/src/**/*.tsx 2>/dev/null | head -20'

# Potential Tauri-browser conflicts
alias vetka-tauri-check='grep -rn "isTauri" client/src/ | wc -l'

# API schema validation
alias vetka-api-check='npx openapi-generator-cli validate -i shared/api-specs/*.yaml'

# Full hygiene audit
alias vetka-audit='./scripts/audit.sh'
```

## Migration Safety

### When Upgrading Tauri
1. Test browser mode first (`npm run dev`)
2. Then Tauri dev (`npm run tauri dev`)
3. If Tauri breaks browser - use feature detection, not branches

### When Upgrading FastAPI
1. Run full test suite
2. Check socket event compatibility
3. Validate API contracts against frontend types

## Signals of Trouble 🚨

| Signal | Problem | Fix |
|--------|---------|-----|
| "Works in browser, fails in Tauri" | Missing feature detection | Add `isTauri()` check |
| "API changed, frontend broken" | Missing contract | Add to `shared/api-specs/` |
| Socket event mismatch | Backend/frontend drift | Use typed events |
| 3+ files with similar names | Confusion | Consolidate or mark clearly |
| Long-lived feature branch | Drift risk | Merge to main sooner |

## Commit Message Convention

```
<scope>: <type> <description>

Scopes: backend, frontend, tauri, shared, docs
Types: add, fix, update, remove, refactor

Examples:
  backend: add artifact save endpoint
  frontend: handle artifact_created socket
  tauri: add native file dialog
  shared: update artifact API schema
  docs: add dual-stack hygiene rules
```

## Emergency Rollback

```bash
# If Tauri build breaks everything
git checkout main -- client/src-tauri/
npm run dev  # Continue with browser-only

# If FastAPI breaks
git checkout main -- src/
docker-compose up backend  # Or revert to last working commit
```

---

**Golden Rule:** Если изменение в одном стеке ломает другой - это баг в архитектуре, не в коде. Используй feature detection и shared contracts.
