# VETKA + MYCELIUM Installation Guide

This guide is for users who discovered `mycelium` first and need the full
runtime stack.

## Important

`mycelium` is a UI module mirror, not a standalone backend runtime.

To run MYCELIUM with real Tasks/Chat/Context/Stats data, use the VETKA monorepo
as the source of truth.

## What MYCELIUM Depends On

Required runtime layers:

- `vetka-orchestration-core` (`src/orchestration`)
- `vetka-elisya-runtime` (`src/elisya`)
- `vetka-mcp-core` (`src/mcp`)
- `vetka-bridge-core` (`src/bridge`)
- `vetka-memory-stack` (`src/memory`)
- `vetka-search-retrieval` (`src/search`)
- `vetka-ingest-engine` (`src/scanners`)

In practice, the easiest way to get all of them aligned is one repo: `vetka`.

## Recommended Setup (Monorepo)

1. Clone VETKA:

```bash
git clone git@github.com:danilagoleen/vetka.git
cd vetka
```

2. Configure environment:

```bash
cp .env.example .env
```

3. Create Python environment and install backend deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. Start required infra (Qdrant at minimum):

```bash
docker compose up -d qdrant
```

Optional extended stack:

```bash
docker compose up -d weaviate ollama
```

5. Run backend:

```bash
./run.sh
```

Backend health:

```bash
curl http://127.0.0.1:5001/api/health
```

6. Run frontend (MYCELIUM surface is inside client app):

```bash
cd client
npm install
npm run dev
```

Open UI:

- `http://127.0.0.1:5173`

## Troubleshooting

- If backend fails on startup:
  - ensure `.venv` exists and `pip install -r requirements.txt` completed.
- If graph loads but runtime panels are empty:
  - verify backend health (`/api/health`) and Qdrant container status.
- If `mycelium` repo alone was cloned:
  - this is expected; clone `vetka` monorepo for full runtime.

## For Contributors Who Want Modular Repos

Public module repos are mirrors for focused contribution/review.
Operational runtime should still be validated against `vetka` monorepo to avoid
cross-repo version skew.
