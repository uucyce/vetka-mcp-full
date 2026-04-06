# GEMMA-BRIDGE: LiteLLM Proxy + free-code Tool Use Test
**Date:** 2026-04-06 | **Agent:** Eta | **Task:** tb_1775501542_84886_19

## Verdict: PARTIAL

Gemma4:e4b attempted a tool call but output it as raw JSON text instead of using Anthropic tool_use XML/JSON format.

---

## Step 1: LiteLLM Proxy

```bash
# Install (clean venv required — system litellm has broken imports)
/opt/homebrew/opt/python@3.13/bin/python3.13 -m venv /tmp/litellm_venv
source /tmp/litellm_venv/bin/activate
pip install 'litellm[proxy]'

# Start (MUST use --drop_params to avoid context_management error)
LITELLM_MASTER_KEY=sk-ollama /tmp/litellm_venv/bin/litellm \
  --model ollama/gemma4:e4b --port 4000 --drop_params &
```

**Result:** PASS — proxy running, health check returns 200.

### Issues encountered:
- System litellm (pip install) has broken `from proxy_server import` — use venv
- Missing deps: backoff, orjson, apscheduler, cryptography — `litellm[proxy]` installs all
- `--api_key` flag doesn't exist — use `LITELLM_MASTER_KEY` env var
- Must use `--drop_params` — free-code sends `context_management` param unsupported by Ollama

---

## Step 2: free-code via LiteLLM

```bash
cd ~/Documents/VETKA_Project/free-code
ANTHROPIC_BASE_URL=http://localhost:4000 \
ANTHROPIC_API_KEY=sk-ollama \
./cli-dev --model gemma4:e4b --print \
  "Read the file README.md and tell me the first 3 lines"
```

**Terminal output (exact):**
```json
{
  "tool_name": "file_search",
  "parameters": {
    "query": "README.md",
    "limit": 1
  }
}
```

**Result:** PARTIAL

---

## Step 3: Analysis

| Criteria | Result | Notes |
|----------|--------|-------|
| Gemma called Read tool via Anthropic format? | NO | Did not use `tool_use` block |
| Gemma attempted tool call? | YES | Output JSON with tool_name + parameters |
| Gemma answered with text only? | NO | It tried to call a tool |
| Error/crash? | NO | Clean exit |

### Root Cause
Gemma4:e4b understands the CONCEPT of tool calling but outputs it as raw JSON text. LiteLLM translates Anthropic Messages API to OpenAI format, but Gemma's tool call format doesn't match either Anthropic's `tool_use` content block or OpenAI's `function_call` field. The model outputs tool calls as plain text content.

### Next Steps (priority order)
1. **Prompt engineering:** Add explicit instructions like "Use the tool_use content block format" in system prompt
2. **LiteLLM tool mapping:** Configure LiteLLM to map Gemma's native function calling format to Anthropic's
3. **Post-processing:** Parse raw JSON tool calls from Gemma's text output and execute them programmatically
4. **Alternative:** Use opencode (already works with Qwen fleet) — proven path, skip free-code entirely
5. **Alternative:** Use aider (`aider --model ollama/gemma4:e4b`) — may handle tool calls better

### Key Discovery
free-code validates model names against a hardcoded list. Direct Ollama endpoint (`ANTHROPIC_BASE_URL=http://localhost:11434/v1`) fails with "model may not exist". LiteLLM proxy is REQUIRED as translation layer — it makes Gemma appear as an Anthropic model to free-code.

### Infrastructure Ready
- LiteLLM venv: `/tmp/litellm_venv/bin/litellm`
- Gemma4 models: e2b (7.2GB), e4b (9.6GB), 26b (17GB) — all loaded in Ollama
- free-code binary: `~/Documents/VETKA_Project/free-code/cli-dev`
- Proxy command: `LITELLM_MASTER_KEY=sk-ollama /tmp/litellm_venv/bin/litellm --model ollama/gemma4:e4b --port 4000 --drop_params`
