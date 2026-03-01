# VETKA Qdrant Recovery Report (2026-03-01)

## Executive summary
- Root cause: data/runtime drift after environment cleanup + mixed `venv` usage + Qdrant version mismatch.
- Critical mismatch: repository/runtime was switched to `qdrant/qdrant:v1.10.0` while existing Qdrant volume data is from newer server format.
- Result: startup flapping (`503` on `/readyz`, `0 nodes`, repeated reconnect attempts), and on recreate with `v1.10.0` container panicked during collection load.

## Evidence
- Backup created before destructive actions:
  - `data/qdrant_snapshots/backup_20260301_185855/raw/storage`
  - `data/qdrant_snapshots/backup_20260301_185855/raw/snapshots`
- Recreate with `v1.10.0` failed with serialization panic when loading collection metadata.
- Rollback to `latest` restored stable readiness; logs reported Qdrant server `Version: 1.16.2`.
- `PROXY_ENV={}`; proxy is not the cause.
- Runtime drift detail: two qdrant containers/volumes existed at different points:
  - live container: `qdrant` on volume `qdrant_storage`
  - compose-created container: `vetka_live_03-qdrant-1` on volume `vetka_live_03_qdrant_data`
  This caused "same logs/no effect" confusion because services were not always using the same storage/runtime path.

## Version matrix (locked)
- Docker Desktop: `4.62.0`
- Qdrant server image: `qdrant/qdrant:v1.16.2` (pinned, no `latest`)
- Python client: `qdrant-client` (current project runtime) must stay compatible with server `1.16.2` behavior.
- Canonical endpoint: `http://127.0.0.1:6333`

## Code/runtime stabilization applied
1. Qdrant startup/retry: avoid false-positive "connected" on HTTP `503`.
2. Tree routes: lazy Qdrant recovery when DB becomes ready after backend startup.
3. Runtime safety: TTS autostart is disabled by default (`VETKA_TTS_AUTOSTART=0`) to avoid MLX/Metal crash path during boot.
4. Jarvis socket handler guarded by `VETKA_JARVIS_ENABLE`.

## Operational notes
- Files `docs/155_ph/!usage limit.rtf` and `docs/156_ph/!!limit.rtf` are user notes/artifacts (not executable code, not backend crash source).
- Keep only one environment: `.venv`.
- `requirements.txt` update remains intentionally deferred until final architecture stabilization.

## Canonical commands
```bash
source .venv/bin/activate
./run.sh
```

For explicit qdrant pin on existing storage volume:
```bash
docker stop qdrant
docker rm qdrant
docker run -d --name qdrant -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant:v1.16.2
```

## Acceptance checklist
1. `curl -i http://127.0.0.1:6333/readyz` returns `200` consistently.
2. `curl -i http://127.0.0.1:6333/collections` returns `200` consistently.
3. Backend starts once on `:5001` (no `address already in use`).
4. `GET /api/tree/data` returns non-empty nodes (`nodes > 0` in UI/API).
5. No repeating Qdrant `503` loop in backend logs after warmup.
