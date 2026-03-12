# Unified Session Capability Broker Architecture

## Problem

Agents currently see different TaskBoard availability depending on which MCP transport is live in their session:

- `vetka_task_board` is deprecated and only points to `mycelium_task_board`
- `mycelium_task_board` is unavailable when MCP MYCELIUM is not connected
- the underlying board data is still available through REST or direct file access

Result: the board is alive, but the agent may stop because the canonical tool path is missing.

## Root Cause

We currently expose the same logical capability through multiple transport layers:

1. MCP MYCELIUM tool path
2. VETKA / MCC REST path
3. direct JSON/file fallback

These are not unified behind one runtime broker. Session init loads context, but it does not guarantee a complete capability manifest or fallback routing table.

## Design Goal

Make `vetka_session_init` the main ecosystem entry point and return not only context, but also capability availability and transport policy.

For MCC, add a dedicated `mcc_session_init` that carries MCC-specific execution context.

Agents should not guess which transport to call. They should resolve one logical tool and let the broker choose the transport.

## Core Idea

Introduce a unified capability broker with three responsibilities:

1. discover available transports at session start
2. expose one canonical logical capability per domain
3. route calls through primary transport with safe fallbacks

## Session Model

### `vetka_session_init`

General system entry point.

Should return:

- active MCP servers
- available canonical tools
- transport availability
- preferred transport per capability
- fallback chain per capability

Example capability result:

```json
{
  "capabilities": {
    "task_board": {
      "primary_transport": "mycelium_mcp",
      "fallback_transports": ["rest_api", "file_fallback"],
      "available": ["rest_api", "file_fallback"],
      "selected_transport": "rest_api",
      "state_authority": "task_board.json"
    }
  }
}
```

### `mcc_session_init`

MCC-specific execution entry point.

Should include:

- active project
- selected task / selected node
- workflow focus
- task packet availability
- viewport summary
- pinned summary
- localguys runtime state
- transport capability manifest

This is intentionally different from generic VETKA chat init.

## Transport Policy

Each logical capability must declare:

- `primary_transport`
- `fallback_transports`
- `write_safety`
- `state_authority`

### Example: TaskBoard

- primary: `mycelium_mcp`
- fallback 1: `rest_api`
- fallback 2: `file_fallback`
- authority: `task_board.json`

### Example: Workflow Dispatch

- primary: `mycelium_mcp`
- fallback: optional `rest_api`
- file fallback: usually blocked

Not every tool should support every fallback. Fallback policy must be per capability.

## Unified Facade

Agents should call one logical interface, not transport-specific names.

Suggested facades:

- `taskboard_unified`
- `workflow_unified`
- `artifacts_unified`

The facade should:

1. inspect capability manifest
2. select transport
3. execute call
4. report which transport was used

Example runtime message:

- `using fallback transport: rest_api`

instead of:

- `tool unavailable`

## Why Deprecated Alias Is Not Enough

Current alias mapping solves naming compatibility, but not availability.

`vetka_task_board -> mycelium_task_board` still fails if MYCELIUM MCP is absent.

So aliasing alone is not a transport strategy. We need runtime fallback resolution.

## Safety Rules

Fallback must be policy-based, not blind forwarding.

Examples:

- TaskBoard CRUD can safely fall back to REST or file authority
- workflow dispatch should not silently fall back to file writes
- artifact mutation may require stricter transport guarantees

## Recommended Implementation Order

1. add capability manifest to `vetka_session_init`
2. define `mcc_session_init` contract
3. implement `task_board` fallback chain: MCP -> REST -> file
4. add unified facade for agents
5. extend the same pattern to workflow dispatch and artifacts

## Expected Outcome

After this change:

- agents stop reasoning about transport names
- session init becomes the real entry point into the system
- missing MCP transport no longer blocks normal TaskBoard work
- MCC gets its own execution-aware init without copying generic chat behavior

## Recommended Task Pack

1. `Unified session capability broker`
2. `TaskBoard transport fallback chain`
3. `MCC session init contract`
4. `Agent migration to unified capability facade`
