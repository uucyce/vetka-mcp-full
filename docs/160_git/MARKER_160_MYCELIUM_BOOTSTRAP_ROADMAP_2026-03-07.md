# MARKER_160_MYCELIUM_BOOTSTRAP_ROADMAP_2026-03-07

Date: 2026-03-07
Scope: installation UX for users who start from `mycelium` mirror and then hit hidden runtime dependencies
Status: implementation slice completed (bootstrap/update/doctor scripts + shared install guide)

## Recon Summary (what we validated)

1. `mycelium` is a module mirror (`client/src/components/mcc`), not standalone runtime.
2. Full runtime depends on backend layers in monorepo:
   - orchestration (`src/orchestration`),
   - elisya (`src/elisya`),
   - mcp + bridge (`src/mcp`, `src/bridge`),
   - memory + search + ingest (`src/memory`, `src/search`, `src/scanners`).
3. Existing startup path is backend-first (`./run.sh`) with health endpoint `/api/health`.
4. Infra dependency for useful runtime is at least Qdrant (`docker compose up -d qdrant`).

## Implemented Artifacts

- `docs/INSTALL_VETKA_STACK.md`
- `scripts/install/bootstrap_mycelium.sh`
- `scripts/install/update_stack.sh`
- `scripts/install/doctor.sh`
- README links added in root + MCC README.

## 3-Point Implementation Roadmap

### 1) Unified Bootstrap (now)

Goal: one command for first-time setup from MYCELIUM perspective.

Delivered:
- create `.venv` if missing;
- install backend (`requirements.txt`) and frontend (`client/package.json`) deps;
- optional infra startup via docker compose;
- optional direct backend/frontend launch flags.

Entry point:
- `./scripts/install/bootstrap_mycelium.sh`

### 2) Safe Update Flow (now)

Goal: keep dependencies and local stack current without manual guesswork.

Delivered:
- guarded `git pull --rebase` (skips when dirty);
- refresh Python + Node deps;
- optional docker image pull.

Entry point:
- `./scripts/install/update_stack.sh`

### 3) Runtime Doctor (now, extensible)

Goal: quickly answer "why does it not work" after install/update.

Delivered checks:
- required commands (`python3`, `npm`, `curl`);
- `.venv` and core python imports;
- Docker daemon + qdrant container + qdrant health;
- backend health (`/api/health`);
- frontend dev-server reachability (`:5173`).

Entry point:
- `./scripts/install/doctor.sh`

## Next hardening slice (if we continue)

1. Add non-interactive CI profile (`--ci`) to bootstrap/update scripts.
2. Add OS-specific hints (macOS/Linux) for Docker desktop and optional Ollama lanes.
3. Add lightweight telemetry file (`data/install_state.json`) to track last successful bootstrap/update.
