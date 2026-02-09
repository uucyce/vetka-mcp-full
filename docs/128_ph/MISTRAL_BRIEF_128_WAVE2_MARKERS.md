# MISTRAL BRIEF Wave 2: Marker Placement for 128.4-128.6

## Your Role
Place MARKER_ comments at exact locations where new code should go.
DO NOT write code — only place markers with descriptions.

## Task M2: Diff Generation Markers

### File: `src/orchestration/agent_pipeline.py`

1. Find `_extract_and_write_files` method (~line 1460)
   Place: `# MARKER_128.4C_DIFF_GEN: Generate unified diff before writing`
   Location: BEFORE the `path_obj.write_text(code)` call

2. Find `_scout_prefetch` method (~line 379)
   Place: `# MARKER_128.4D_CACHE_ORIGINAL: Cache original file content for diff`
   Location: After `_read_file_snippets` call, where full content could be cached

3. Find `_execute_subtask` method (~line 2404)
   Place: `# MARKER_128.4E_SAVE_DIFF: Save diff_patch to subtask result`
   Location: After FC loop returns content, before saving result

### File: `src/api/routes/debug_routes.py`

4. Find `get_pipeline_results` endpoint
   Place: `# MARKER_128.4F_INCLUDE_DIFF: Include diff_patch in results response`
   Location: In the subtask list comprehension

## Task M3: MCP Async Markers

### File: `src/mcp/vetka_mcp_bridge.py`

5. Find where MCP tools are registered (tool list)
   Place: `# MARKER_128.5_MCP_ASYNC: Consider async tool execution here`
   Location: Near tool registration loop

6. Find the main MCP request handler
   Place: `# MARKER_128.5_MCP_TIMEOUT: Add timeout to prevent blocking`
   Location: At the entry point of tool execution

## Output Format
```
MARKER PLACEMENT REPORT — Wave 2
=================================
agent_pipeline.py:
  line {N} — MARKER_128.4C_DIFF_GEN (before write_text)
  line {N} — MARKER_128.4D_CACHE_ORIGINAL (after read_snippets)
  ...
```

## Rules
- Only add `# MARKER_XXX:` comment lines
- Do NOT modify any code logic
- Use `#` for Python, `//` for TypeScript
- Include brief description after marker ID
