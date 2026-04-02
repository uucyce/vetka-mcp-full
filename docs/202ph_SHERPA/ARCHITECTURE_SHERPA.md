# SHERPA Architecture — Phase 202

## Current State (v1.0)
- Text-only mode: all context (docs + code) inserted into prompt textarea
- Playwright browser with persistent profiles (data/sherpa_profiles/)
- 10 services configured: DeepSeek x2, Kimi x2, Arena, Z.ai, Mistral, HuggingChat, Monica, Bolt
- DeepSeek + Kimi working reliably for sending prompts
- TaskBoard integration via HTTP API (localhost:5001)
- Ollama/Qwen 3.5 for response summarization
- PID lock guard: max 1 instance
- Copy button + text stability as response completion trigger
- Probe mode (--probe) tests 40+ services automatically

## Pipeline
```
TaskBoard (pending tasks)
  -> Sherpa claims task
    -> ripgrep searches codebase for relevant files
    -> Reads architecture_docs and recon_docs from task
    -> Builds prompt (task desc + docs + code snippets)
    -> Playwright opens DeepSeek
    -> fill() prompt into textarea
    -> Enter to send
    -> Wait for Copy button + text stability
    -> Extract response via clipboard
    -> Ollama summarizes key points
    -> Save to docs/sherpa_recon/sherpa_{task_id}.md
    -> Update task: recon_docs + implementation_hints
    -> Release task back to pending (enriched)
  -> Cooldown -> next task
```

## Known Issues (P0/P1)

### P0: Copy button extracts last block only
- **Problem:** Copy button grabs last code block (333-1112 chars), not full response (should be 15K+)
- **Impact:** Multi-section responses truncated, code examples incomplete
- **Solutions (pick one):**
  1. Use `inner_text()` on entire response container div (primary)
  2. Scroll down to find master Copy button that covers entire response
  3. Concatenate all individual Copy block results
- **Task:** SHERPA-DOM (phase_type=fix, assigned_to=Eta)

### P0: Arena.ai returns dual responses
- **Problem:** Arena.ai displays TWO responses side-by-side (benchmark arena mode)
- **Impact:** Only capturing one response, missing comparative analysis
- **Solution:** Detect and capture both response containers separately
- **Task:** SHERPA-DOM (part of copy extraction fix)

### P1: 404 spam on /api/settings endpoint
- **Problem:** sherpa.py makes PATCH /api/settings calls that return 404
- **Cause:** Endpoint doesn't exist or wrong URL path
- **Impact:** Noisy logs, failed status updates
- **Solutions:**
  1. Create the endpoint if needed
  2. Use existing TaskBoard notify mechanism instead
  3. Remove the calls from sherpa.py if not critical
- **Task:** SHERPA-INFRA (phase_type=fix, assigned_to=Zeta)

## Roadmap

### v1.1 — Stability (NOW)
- DOM-based response extraction (replace clipboard)
- Self-learning feedback (JSONL log per service: success/fail/chars/time)
- Adaptive service rating (Qwen reads feedback, picks best service)
- Gmail profile rotation (secondary accounts only!)
- Better file relevance: use allowed_paths from task, not just keyword search

### v1.2 — File Attachments
- Upload docs as file attachments (not text in prompt)
- Adaptive wait for upload completion
- Per-service send button detection
- Auto-protocols: Sherpa records what works per service → yaml protocols

### v2.0 — Vision
- Multimodal local model (Pixtral/CLIP) for screenshot-based UI state detection
- OCR fallback for response extraction
- Visual confirmation of sent/received states

### v2.1 — VETKA Browser Integration
- Use VETKA's own Tauri browser shell for Sherpa
- Custom UI adapted for agent workflow
- Built-in TaskBoard sidebar
- Multiple simultaneous agents with browser pool

### v2.2 — Multi-Agent Sherpa
- Commander-only launch with TaskBoard signaling (sherpa_busy flag)
- Queue system: commanders request Sherpa, get notified when free
- Multi-agent Sherpa with Commander queue

## Key Files
- sherpa.py — Main agent script (~500 lines)
- config/sherpa.yaml — Service configuration
- docs/sherpa_recon/ — Recon output directory
- data/sherpa_profiles/ — Playwright browser profiles
- logs/sherpa.log — Agent logs

## Security Notes
- NO passwords in config — only URLs and CSS selectors
- Sessions saved via Playwright persistent context (cookies/localStorage)
- Use SECONDARY gmail accounts only, never primary
- PID lock prevents concurrent access to same browser profiles
