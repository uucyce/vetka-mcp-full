# mycelium

Mycelium Command Center is a DAG-native operator UI for multi-agent runtime control.

It is built for live orchestration, not generic chat dashboards:
- graph-first workspace where each operation is contextual to node/task state,
- persistent mini-window cockpit (Tasks, Chat, Context, Stats, Balance),
- fast window choreography: expand, minimize to dock, restore at last user position,
- low-noise black-and-white interface optimized for dense operational sessions.

## Why This Module Exists

`mycelium` is split as a standalone OSS module so contributors can evolve MCC UX/runtime coupling independently from the full VETKA monorepo.

Source-of-truth path in monorepo:
- `client/src/components/mcc`

## Core Capabilities

- DAG-centric command center with selection-aware side windows.
- Multi-window runtime shell (drag, resize, maximize, minimize/dock, restore).
- Taskboard and heartbeat control surfaces for execution flow.
- Embedded chat/context loop for operator-in-the-graph workflows.
- Balance/stats overlays for runtime cost and throughput visibility.

## Open Source Attribution

Primary upstream libraries and licenses are listed in:
- `OPEN_SOURCE_CREDITS.md`

## Contributing

1. Fork and create a feature branch.
2. Use Conventional Commits.
3. Include screenshots/video for UI behavior changes.
4. Open PR with concise behavioral notes.

## License

MIT (`LICENSE`).
