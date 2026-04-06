# GEMMA-BRIDGE Session 4 Update — 2026-04-06
**Agent:** Eta (Harness) | **Branch:** claude/harness-eta | **Tasks:** tb_1775504846_73663_1

## Priority A: Native Function Calling via LiteLLM — TESTED

### Curl Test Result: PASS ✓
```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-ollama" \
  -d '{"model": "gemma4:e4b", "messages": [...], "tools": [...], "stream": false}'
```
**Response:**
```json
{"finish_reason": "tool_calls", "message": {"tool_calls": [{"function": {"name": "list_dir", "arguments": "{\"path\": \".\"}"}}]}}
```
Gemma4:e4b returns proper OpenAI `tool_calls` when `tools` param is explicitly sent.

### E2E Test (free-code → LiteLLM): FAIL ✗
```bash
ANTHROPIC_BASE_URL=http://localhost:4000 ANTHROPIC_API_KEY=sk-ollama \
  ./cli-dev --model gemma4:e4b --print "What is 2+2?"
```
**Response:** `{"tool_calls": [{"function": "calculate", "args": {...}}]}` (text, not tool_use)

**Root cause:** LiteLLM with `--drop_params` may drop `tools` when translating Anthropic→OpenAI.
Or free-code doesn't send `tools` in a format LiteLLM forwards to Ollama.
Either way: native function calling doesn't reach Gemma in the free-code E2E path.

### Conclusion: Priority A curl works, E2E fails → Priority B needed

---

## Priority B: System Prompt + XML Parser — IMPLEMENTED ✓

### Changes in `scripts/litellm_gemma_bridge.py`

1. **`GEMMA_TOOL_SYSTEM_PROMPT`** — constant that instructs Gemma to output XML:
   ```
   <tool_use>
   <name>tool_name</name>
   <input>{"param": "value"}</input>
   </tool_use>
   ```

2. **`_extract_xml_tool_calls(text)`** — thin XML parser (~15 lines):
   - Regex: `<tool_use><name>...</name><input>...</input></tool_use>`
   - Returns list of `{"tool_name": name, "parameters": {...}}`
   - Fast, unambiguous, no JSON heuristics needed

3. **`_inject_system_prompt(req_data)`** — prepends GEMMA_TOOL_SYSTEM_PROMPT to system field

4. **Priority ordering in `_extract_tool_calls()`**:
   - Try XML first (matches injected prompt → fast path)
   - Fall back to JSON heuristics (legacy / no prompt)

5. **Request interception in `do_POST`**:
   - Before forwarding: inject system prompt into `/messages` requests
   - Gemma now receives explicit XML format instruction every call

### Changes in `data/templates/claude_md_template.j2`

Added `{% if role.tool_type == "free_code" %}` section:
- Session init steps (same as claude_code)
- **Tool Call Format section** — explains XML protocol to Gemma-backed agents
- Wire: any agent with `tool_type: "free_code"` in agent_registry.yaml gets these instructions

---

## Architecture After Session 4

```
free-code → litellm_gemma_bridge.py (port 4001) → LiteLLM (port 4000) → Ollama → Gemma4
                     ↑
           1. Inject GEMMA_TOOL_SYSTEM_PROMPT
           2. Extract XML tool calls from response
           3. Convert XML → Anthropic tool_use blocks
           4. Build SSE stream for free-code
```

**Start sequence:**
```bash
# Terminal 1: LiteLLM
LITELLM_MASTER_KEY=sk-ollama /tmp/litellm_venv/bin/litellm \
  --model ollama/gemma4:e4b --port 4000 --drop_params

# Terminal 2: Bridge (Priority B)
python3 scripts/litellm_gemma_bridge.py --port 4001

# Terminal 3: free-code
ANTHROPIC_BASE_URL=http://localhost:4001 ANTHROPIC_API_KEY=sk-ollama \
  ./cli-dev --model gemma4:e4b --print "Read README.md"
```

## Outstanding Work

| # | Task | Status |
|---|------|--------|
| 1 | Test bridge with Priority B prompt injected (E2E) | TODO (next session) |
| 2 | 10-shot reliability test | TODO |
| 3 | Add `tool_type: free_code` Gemma roles to agent_registry.yaml | Commander domain |
| 4 | Run `generate_claude_md.py` to regenerate CLAUDE.md for Gemma roles | After registry update |
