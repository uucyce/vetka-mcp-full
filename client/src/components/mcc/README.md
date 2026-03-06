# mycelium

Mycelium Command Center is a DAG-native operator UI for multi-agent runtime control.

## Hero

![Mycelium Hero](docs/showcase/01-overview.png)

From global graph view to focused execution in one surface:
- read system topology at a glance,
- open operational windows without losing context,
- keep task flow, chat, context, and telemetry synchronized in real time.

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

## Visual Showcase

![MCC overview](docs/showcase/01-overview.png)
![DAG drilldown](docs/showcase/02-drilldown.png)
![Chat panel (base)](docs/showcase/03-chat-empty.png)
![Chat panel (MYCO linked)](docs/showcase/04-chat-myco.png)
![Left rail + graph workspace](docs/showcase/05-left-rail.png)
![Tasks expanded modal](docs/showcase/06-tasks-modal.png)
![Stats expanded modal](docs/showcase/07-stats-modal.png)
![Wide command-center layout](docs/showcase/08-wide-layout.png)

## How It Works (Simple)

1. The center canvas is the project DAG and workflow graph.
2. Each mini-window is a focused operational surface (Tasks, Chat, Context, Stats, Balance).
3. A window can be expanded or minimized to dock, then restored to the last user position.
4. New workflow scope can be opened as a new visual tab/window context.
5. Operator actions in one surface update others through shared runtime state.

## MYCO (Mycelium Context Operator)

MYCO is the in-graph context companion for operators.

![MYCO logo (alert)](docs/showcase/12-myco-logo-alert.png)
![MYCO logo (speak)](docs/showcase/13-myco-logo-speak.png)
![MYCO loop (APNG)](docs/showcase/14-myco-logo-loop.apng)
![MYCO loop (GIF fallback)](docs/showcase/15-myco-logo-loop.gif)

What MYCO does:
- sees current task and graph context,
- suggests next actions when the state changes,
- speaks/animates when new messages arrive,
- escalates to a senior route when deeper support is needed.

Design origin:
- homage to the mushroom from Mario,
- visual wink to the bitten-apple era, but as a bitten mushroom,
- light reference to *Alice in Wonderland*,
- and a personal easter egg from Ryazan folklore:
  `У нас в Рязани, грибы с глазами, их едят, они глядят.`
  Approximate English sense: `In Ryazan, mushrooms have eyes; when eaten, they still watch.`

## Ecosystem Dependencies

`mycelium` is UI-first, but it reaches full value in the VETKA module graph:
- `vetka-orchestration-core`: execution orchestration contracts and state flow.
- `vetka-elisya-runtime`: runtime routing and assistant behavior integration.
- `vetka-mcp-core`: MCP transport and tool gateway layer.
- `vetka-bridge-core`: cross-agent bridge integration.
- `vetka-memory-stack`: long/short memory and context persistence path.
- `vetka-search-retrieval` + `vetka-ingest-engine`: semantic retrieval and ingest pipeline.

Without these modules, `mycelium` remains a strong standalone UI shell; with them, it becomes a full command center.

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
