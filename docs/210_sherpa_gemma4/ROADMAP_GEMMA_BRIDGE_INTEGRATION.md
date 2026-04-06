# ROADMAP: Gemma 4 Integration into Agent Pipeline (Alpha-Eta)
**Date:** 2026-04-06 | **Author:** Eta (Harness) | **Phase:** 212+
**Task:** tb_1775502957_73663_1 follow-up

## Status: BRIDGE 90% BUILT, NEEDS CLEAN APPROACH

### What We Have (on main + harness-eta)
- LiteLLM proxy: translates Anthropic Messages API -> OpenAI -> Ollama -> Gemma4
- free-code binary: Claude Code fork, works with LiteLLM as backend
- json_strip.py: Gemma markdown->JSON extraction (9.5x speedup proven)
- model_router.py: task-type routing to Gemma4 models (e2b/e4b/26b)
- Benchmark results: Gemma4:e4b wins on enrichment (2x faster than Qwen 3.5)

### What Was Built Wrong (lessons learned)
- `scripts/litellm_gemma_bridge.py` (250 lines) — SSE buffer + JSON->tool_use converter
- **This is a crutch.** It works (7 tool calls converted in E2E test) but adds complexity
- Root cause: we jumped to building a converter instead of asking Gemma to output correctly

### The Correct Path (from Grok's analysis, April 6)

**Priority A: Native OpenAI function calling via LiteLLM**

```
free-code -> LiteLLM (port 4000) -> Ollama (with tools param) -> Gemma4
                                          ^
                                   tools=[{function schemas}]
```

Steps:
1. Pass `tools` array in LiteLLM request to Ollama
2. Gemma 4 supports native function calling through Ollama
3. LiteLLM auto-converts OpenAI `tool_calls` -> Anthropic `tool_use`
4. **Zero custom code needed**

Verification curl:
```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma4:e4b",
    "messages": [
      {"role": "system", "content": "You are a helpful coding assistant. When you need to use a tool, respond ONLY with a valid tool call. Do not add extra text."},
      {"role": "user", "content": "List all files in the current directory."}
    ],
    "tools": [{"type": "function", "function": {"name": "list_dir", "description": "List files and directories", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}}],
    "tool_choice": "auto",
    "stream": false
  }'
```

Expected: `choices[0].message.tool_calls[0].function.name = "list_dir"`

**Priority B (fallback): System prompt + thin XML parser**

If native function calling doesn't work, use Grok's system prompt approach:
- Tell Gemma to output `<tool_use>` XML blocks
- Parse XML -> Anthropic JSON (15 lines, not 250)
- This is the proven pattern (STRICT_JSON_PROMPT worked for JSON output)

**Priority C (deprecated): SSE converter proxy**
- `scripts/litellm_gemma_bridge.py` stays as reference but should NOT be the production path
- It proves the concept works but adds unnecessary complexity

### Task Sequence for Next Session

| # | Task | Priority | Complexity |
|---|------|----------|------------|
| 1 | Test native function calling: curl test A above | P0 | 5 min |
| 2a | If PASS: E2E test free-code with native tools | P0 | 15 min |
| 2b | If FAIL: Apply system prompt + XML parser | P0 | 30 min |
| 3 | Run 10-shot reliability test (tool call success rate) | P1 | 20 min |
| 4 | Wire system prompt into CLAUDE.md/AGENTS.md template | P1 | 15 min |
| 5 | Document final architecture in this file | P2 | 10 min |

### Anti-Patterns to Avoid
- **No more converter layers.** If Gemma can't call tools natively, fix the prompt, not the pipe.
- **No opencode pivot.** free-code has full Claude Code toolset; opencode does not.
- **No "PARTIAL = failure" decisions.** PARTIAL means 90% done, not 0% done.

### Key Insight (Commander Bell near-miss)
Eta reported PARTIAL -> Commander interpreted as failure -> nearly pivoted to opencode.
This would have been a regression: opencode lacks Claude Code tools (Read, Edit, Bash, Glob, Grep).
The JSON output from Gemma was FASTER than alternatives (3-5x speedup, proven in benchmarks).
Lesson: always read the full report before deciding. PARTIAL != FAIL.
