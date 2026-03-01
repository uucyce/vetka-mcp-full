# VETKA Canonical Runtime Contract (2026-03-01)

## Scope
Defines the single operational startup path for backend runtime to prevent drift after environment recovery.

## Canonical contract
1. Virtual environment: `.venv` only.
2. Backend entrypoint: `main:socket_app` (FastAPI + Socket.IO).
3. Backend port: `5001` by default.
4. Qdrant transport: HTTP URL (`http://localhost:6333`), no gRPC-only assumptions.
5. Launcher: `./run.sh` is the canonical startup command for local backend runtime.

## Canonical startup commands
```bash
python3 -m venv .venv
source .venv/bin/activate
./run.sh
```

## Allowed variants
- `VETKA_RELOAD=true ./run.sh` for local dev reload.
- `MCC_JEPA_HTTP_ENABLE=0 ./run.sh` to disable JEPA sidecar startup.

## Explicitly non-canonical
- Activating `venv` in this repository.
- Running backend on legacy `5000`.
- Flask terminology in active operational docs.

## Follow-up
`requirements.txt` update is intentionally deferred until architecture and runtime behavior are stabilized.
