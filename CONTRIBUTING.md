# Contributing to VETKA

Thanks for contributing.

## Development Setup
1. Use project virtualenv:
   - `source .venv/bin/activate`
2. Start backend/UI using project scripts:
   - `./run.sh`

## Branch and Commits
- Use focused branches and small commits.
- Keep commit scope narrow and descriptive.
- Do not mix unrelated refactors with bug fixes.

## Code Style
- Follow existing style and architecture patterns.
- Add tests for behavior changes.
- Prefer explicit markers in critical runtime paths.

## Pull Requests
- Use the PR template.
- Include:
  - problem statement
  - implementation summary
  - test evidence
  - rollback/risk notes

## Reporting Bugs
Use the Bug report template and include reproducible steps and logs.

## CUT (NLE Editor) Contributions

When modifying CUT components, handlers, or stores, use this checklist:

- [ ] **No duplicate object keys** — Run `npm run check:dupe-keys` before committing
- [ ] **Hotkey handlers organized by phase** — Use MARKER comments to separate old/new sections
- [ ] **Store methods are unique** — Each setter/action defined once in the store
- [ ] **Build passes** — `npm run build` succeeds with zero TS1117 errors
- [ ] **Tests updated** — Add/update tests for modified handlers or store methods

### Preventing Duplicate Key Errors

TypeScript compiler (TS1117) and the duplicate key checker prevent merge conflicts where old+new implementations coexist:

```bash
# Before committing CUT changes:
npm run check:dupe-keys

# Quick verification for specific files:
npx tsc --noEmit client/src/components/cut/CutEditorLayoutV2.tsx
```

See `docs/VETKA_CUT_MANUAL.md` for architecture overview.

## Security
Do not publish secrets/keys in code, logs, screenshots, or issues.
