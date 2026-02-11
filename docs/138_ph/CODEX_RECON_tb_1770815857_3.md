# MARKER_138.RECON_S2_2_JARVIS_MCP
# Recon Report: tb_1770815857_3 (S2.2 Jarvis MCP)

Date: 2026-02-11
Workspace: /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

## Task
S2.2 Jarvis MCP: dedicated non-blocking MCP server with Engram + workflow router.

## Findings
1. Task exists in TaskBoard and is pending:
- `tb_1770815857_3`

2. Existing building blocks are present:
- Jarvis LLM and context: `src/voice/jarvis_llm.py`
- Voice pipeline: `src/voice/streaming_pipeline.py`
- Engram + prompt enrichment: `src/memory/jarvis_prompt_enricher.py`, `src/memory/engram_user_memory.py`

3. Missing target files from task description:
- `src/mcp/jarvis_mcp_server.py` (not found)
- `src/jarvis/workflow_router.py` (not found)
- `src/jarvis/engram_bridge.py` (not found)

## Risk notes
- Need strict isolation from existing pipeline server loops to avoid blocking behavior.
- Must avoid touching existing `src/mcp/mycelium_mcp_server.py` behavior unless explicitly required.

## Proposed next step
Implement minimal standalone Jarvis MCP server + router + engram bridge with isolated tool set and async flow, then add targeted tests.
