# Phase 86: MCP @Mention Trigger Fix

## Summary
Fixed MCP endpoint to properly trigger responding agents when @mention is detected in message content.

## What Was Fixed
MCP endpoint at `src/api/routes/debug_routes.py` (lines 1163-1237) now correctly invokes `select_responding_agents()` when a message contains @mention references.

## Implementation Details
- **Location:** `src/api/routes/debug_routes.py` (1163-1237)
- **Trigger Mechanism:** Agents activate based on @mention detection in message content
- **Entry Point:** MCP message handler routes @mention patterns to agent selection logic

## Phase 80.6 Isolation Compliance
Agent isolation protection maintained:
- Agents without @mention in their context DO NOT trigger other agents
- Prevents automatic agent chain reactions and loops
- Each agent operates independently unless explicitly mentioned

## Status
✓ COMPLETE - MCP endpoint properly handles @mention-based agent triggering
