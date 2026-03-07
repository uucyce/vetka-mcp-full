# MYCELIUM Installation (with VETKA stack)

`mycelium` is a UI module mirror. For full runtime behavior (Tasks/Chat/Context/Stats),
run it with VETKA backend stack.

## Minimal path (recommended)

1. Clone monorepo:

```bash
git clone git@github.com:danilagoleen/vetka.git
cd vetka
```

2. Bootstrap automatically:

```bash
./scripts/install/bootstrap_mycelium.sh -y
```

3. Start backend:

```bash
./run.sh
```

4. Start frontend:

```bash
cd client
npm run dev
```

5. Health check:

```bash
curl http://127.0.0.1:5001/api/health
```

## Smart maintenance

- Update stack:

```bash
./scripts/install/update_stack.sh
```

- Runtime diagnostics:

```bash
./scripts/install/doctor.sh
```

## Dependency note

MYCELIUM relies on these VETKA runtime layers:
- orchestration (`src/orchestration`)
- elisya (`src/elisya`)
- mcp + bridge (`src/mcp`, `src/bridge`)
- memory + search + ingest (`src/memory`, `src/search`, `src/scanners`)

Canonical shared guide in monorepo:
- `docs/INSTALL_VETKA_STACK.md`
