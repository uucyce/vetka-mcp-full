# SHERPA Architecture — Phase 202

## Current State (v1.0)
- Text-only mode: all context (docs + code) inserted into prompt textarea
- Playwright browser with persistent profiles (data/sherpa_profiles/)
- DeepSeek as primary service (unlimited free tier)
- TaskBoard integration via HTTP API (localhost:5001)
- Ollama/Qwen 3.5 for response summarization
- PID lock guard: max 1 instance
- Copy button + text stability as response completion trigger

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

## Roadmap

### v1.1 — Stability
- Chat title appearance as final generation trigger
- Multiple gmail profile rotation (secondary accounts only!)
- Better file relevance: use allowed_paths from task, not just keyword search

### v1.2 — File Attachments
- Upload docs as file attachments (not text in prompt)
- Adaptive wait for upload completion
- Per-service send button detection

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
- arena.ai integration for model-agnostic responses

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
