# VETKA Incomplete TODOs: Phase 117-125

**Generated:** 2026-02-09
**Source:** docs/117_ph, docs/119_ph, docs/121_ph, docs/123_ph, docs/125_ph
**Current Phase:** 124.9 (Scout Places Markers) COMPLETED

---

## Summary

| Category | Count | Priority Range |
|----------|-------|----------------|
| Balance/Keys Bugs (Phase 117) | 5 | P1-P2 |
| Backend Technical Debt | 6 | P2-P3 |
| Pipeline Improvements (Phase 123) | 7 | P0-P3 |
| UI/UX Features | 14 | P2-P4 |
| Chat System Bugs | 6 | P1-P2 |
| Future Roadmap (Phase 125+) | 7 | P3-P4 |
| **TOTAL** | **45** | |

---

## P0 - CRITICAL (Blocking Quality)

### 1. Coder Function Calling [Phase 123]
**Source:** `GROK_RESEARCH_PROMPT_PHASE_123_PIPELINE_FC.md`
**Problem:** Coder gets file NAMES from Scout but can't READ file contents. Produces generic code.
**Solution:** Give coder `vetka_read_file` via function calling (llm_call_tool already supports it)
**Files:** `agent_pipeline.py`, `llm_call_tool.py`
**Effort:** Small

---

## P1 - HIGH (Core Functionality)

### 2. OpenRouter Fake Balance - BUG-1 [Phase 117.1]
**Source:** `PHASE_117_BUGS_AND_NEXT_SESSION.md`
**Problem:** Shows $9999.79 but keys get 402 Payment Required
**Cause:** Parsing `limit_remaining` (credit limit) as balance
**Solution:** Check `is_free_tier`, if 402 → force balance=0
**Files:** `unified_key_manager.py:465-469`

### 3. balance_percent Not Sent to Frontend - BUG-2 [Phase 117.1]
**Source:** `PHASE_117_BUGS_AND_NEXT_SESSION.md`
**Problem:** Balance bar shows 0% always
**Solution:** Add `percent` calculation to `/api/keys/balance` response
**Files:** `config_routes.py:608-610`, `ModelDirectory.tsx:439`

### 4. 402 Doesn't Zero Balance - BUG-4 [Phase 117.1]
**Source:** `PHASE_117_BUGS_AND_NEXT_SESSION.md`
**Problem:** Key gets 402, marked rate-limited, but UI shows $9999.79
**Solution:** In `_report_key_failure()` at 402 → set `record.balance = 0`
**Files:** `unified_key_manager.py`

### 5. Same Balance for All Provider Keys - BUG-5 [Phase 117.1]
**Source:** `PHASE_117_BUGS_AND_NEXT_SESSION.md`
**Problem:** All OpenRouter keys show identical balance
**Solution:** Fetch balance per key, not per provider
**Files:** `config_routes.py`, `ModelDirectory.tsx`

### 6. Question → Scout Trigger [Phase 123]
**Source:** `GROK_RESEARCH_PROMPT_PHASE_123_PIPELINE_FC.md`
**Problem:** If coder can't answer, pipeline fails
**Solution:** Detect question in output → auto-trigger Scout/tool fallback
**Files:** `agent_pipeline.py`

### 7. Scout Report as Chat Artifact [Phase 123]
**Source:** `GROK_RESEARCH_PROMPT_PHASE_123_PIPELINE_FC.md`
**Problem:** Scout findings invisible to user
**Solution:** Emit Scout report as ChatMessage artifact before coder starts
**Files:** `agent_pipeline.py`, chat handlers

### 8. Chat Edit Name Creates New Chat [Phase 119]
**Source:** `119_dragon_todo.txt`
**Problem:** Edit name in group chat creates duplicate, loses content
**Condition:** Happens when chat has file context
**Files:** Chat handlers, chat_history.json logic

### 9. Provider Not Persisted in Solo Chat [Phase 119]
**Source:** `119_dragon_todo.txt`
**Problem:** Model provider/key not saved in chat, falls back to openrouter
**Files:** Chat state persistence

---

## P2 - MEDIUM (Quality of Life)

### 10. Balance Only for OpenRouter + Polza - BUG-3 [Phase 117]
**Source:** `PHASE_117_BUGS_AND_NEXT_SESSION.md`
**Problem:** No balance for Gemini, xAI, Anthropic
**Note:** May not have public API endpoints

### 11. 103 print() → logger [Phase 116]
**Source:** `PHASE_117_FINAL_REPORT.md`
**File:** `user_message_handler.py`

### 12. flask_config Compat Layer Remove [Phase 116]
**Source:** `PHASE_117_FINAL_REPORT.md`
**Details:** 3 references to remove

### 13. chat_routes.py → FastAPI Depends() [Phase 116]
**Source:** `PHASE_117_FINAL_REPORT.md`

### 14. Inter-Agent Communication [Phase 123]
**Source:** `GROK_RESEARCH_PROMPT_PHASE_123_PIPELINE_FC.md`
**Problem:** Agents isolated, no bidirectional messaging
**Options:** ElisyaState, STM expansion, new PipelineState

### 15. Variative Cycles - User Pipeline Control [Phase 123]
**Source:** `GROK_RESEARCH_PROMPT_PHASE_123_PIPELINE_FC.md`
**Goal:** User chooses models/tools per agent, sees decision points

### 16. Smart Chat Anchor [Phase 123.3]
**Source:** `PHASE_123_DECISIONS.md`
**Problem:** Chats without file context go to root (useless)
**Solution:** Semantic-first: file → pinned → viewport → Qdrant search → root
**Files:** chat_handlers.py (MARKER_123.3A-E)

### 17. Chat Favorites (Stars) [Phase 119]
**Source:** `119_dragon_todo.txt`
**Goal:** Allow users to star favorite chats

### 18. Folder Collapse/Expand [Phase 119]
**Source:** `119_dragon_todo.txt`
**Goal:** Collapse/expand files within folders

### 19. MGC Integration for Agent Glow [Phase 121]
**Source:** `PHASE_121_LABEL_HEAT_SYSTEM.md`
**Goal:** Add `mgcScore` for agent activity tracking, blue glow for worked files
**Requires:** Track per-file read/write in MGCCache, `/api/mgc/activity` endpoint

### 20. Dynamic Chat Rebinding [Phase 123.3]
**Source:** `PHASE_123_DECISIONS.md`
**Goal:** When files appear in later messages, auto-rebind chat anchor
**File:** chat_handlers.py (MARKER_123.3B)

---

## P3 - LOW (Polish & Optimization)

### 21. 6 Filesystem Tests → Mock for CI/CD [Phase 116]
**Source:** `PHASE_117_FINAL_REPORT.md`

### 22. 14 Pre-existing Test Failures [Phase 116]
**Source:** `PHASE_117_FINAL_REPORT.md`
**Details:** CAM ops (6), MCP concurrency (2), audit (1), compat (1), agent tools (1), memory (1), other (2)

### 23. DELETE Endpoint Mismatch [Phase 117]
**Source:** `PHASE_117_FINAL_REPORT.md`
**Problem:** Frontend/backend delete endpoint paths differ

### 24. Balance Caching TTL 5min [Phase 117]
**Source:** `PHASE_117_FINAL_REPORT.md`

### 25. Elisya Integration - Shared Tool Loop [Phase 123]
**Source:** `GROK_RESEARCH_PROMPT_PHASE_123_PIPELINE_FC.md`
**Goal:** Extract `_call_llm_with_tools_loop` into shared utility

### 26. BMAD Activation - Git Branches for Pipeline [Phase 123]
**Source:** `GROK_RESEARCH_PROMPT_PHASE_123_PIPELINE_FC.md`
**Status:** 60% built (`git_tool.py`), not wired to pipeline
**Files:** `git_tool.py`, `agent_pipeline.py`

### 27. Message Overlays for 3D Tree [Phase 123.4]
**Source:** `PHASE_123_DECISIONS.md`
**Goal:** Show message badges on tree nodes (overlays, not real nodes)
**File:** MessageBadge.tsx (new)

### 28. @titan Command in Chat Popup [Phase 119]
**Source:** `119_dragon_todo.txt`

### 29. highlight_artifacts Not Used in Frontend [Phase 119]
**Source:** `119_dragon_todo.txt`
**Note:** Backend emits but frontend doesn't use

### 30. CAM Surprise Metrics / Engram Connection [Phase 119]
**Source:** `119_dragon_todo.txt`

### 31. Watchdog Hybrid Fallback [Phase 125]
**Source:** `125_ph_united_data_commander.txt`
**Problem:** Watchdog sometimes misses events on macOS
**Solution:** Watchdog + polling fallback (2 misses threshold)

---

## P4 - NICE TO HAVE (Future)

### 32. xAI/Anthropic Balance via Rate-Limit Headers [Phase 117]
**Source:** `PHASE_117_BUGS_AND_NEXT_SESSION.md`

### 33. New Models Marker [Phase 117 dream]
**Source:** `todo_dream_117.txt`
**Goal:** Mark newly added models with "new" badge

### 34. Art Models Section (Video/Audio Generation) [Phase 117 dream]
**Source:** `todo_dream_117.txt`

### 35. Embedding/Search Models Category [Phase 117 dream]
**Source:** `todo_dream_117.txt`
**Goal:** How to display tavily, embedding models

### 36. Larger Folder Labels for Drag-n-Drop [Phase 117 dream]
**Source:** `todo_dream_117.txt`

### 37. Unified Search Window (Jarvis) [Phase 125]
**Source:** `todo_dream_117.txt`, `125_ph_united_data_commander.txt`
**Goal:** Single search: /vetka, /local, /web, /social, /cloud

### 38. Folder Modes: Workflow/Code/Media/Knowledge [Phase 117 dream]
**Source:** `todo_dream_117.txt`
**Goal:** Auto-detect folder mode by content type

### 39. Chat Message Compression (500 chars) [Phase 117 dream]
**Source:** `todo_dream_117.txt`
**Goal:** Compress user messages too, full chain linked to files

### 40. VETKA Timeline (Undo History) [Phase 119]
**Source:** `todo_titans_119.txt`
**Goal:** Time-based slider to rewind VETKA state

### 41. Mermaid/Tables in Artifact Display [Phase 119]
**Source:** `todo_titans_119.txt`
**Goal:** Render markdown tables and mermaid diagrams in artifacts

### 42. File Preview on Camera Focus [Phase 119]
**Source:** `todo_titans_119.txt`
**Problem:** Preview doesn't load when camera focuses on file

### 43. New Files in Directed Mode → Add at Top [Phase 119]
**Source:** `119_dragon_todo.txt`
**Problem:** New files added to middle, should be at top (Y axis)

### 44. File Import Only Works for Folders [Phase 119]
**Source:** `119_dragon_todo.txt`
**Problem:** Can't drag single file, only folders work

### 45. Hostess Fallback (Local Ollama) [Phase 119]
**Source:** `119_dragon_todo.txt`
**Goal:** If all keys fail, use local ollama to say "wait, trying another line"

---

## Future Roadmap (Not Started)

From `125_ph_united_data_commander.txt`:

| Phase | Goal | Effort |
|-------|------|--------|
| 120 | Local Files (Finder Clone) - ripgrep + Whoosh | 2-3 weeks |
| 121 | Web Fetch & Index - Crawl4AI + Meilisearch | 3-4 weeks |
| 122 | Social Networks - X/Reddit API | 2 weeks |
| 123 | Cloud Storage - Google Drive/Dropbox/S3 | 3 weeks |
| 124 | Ingestion Pipeline - auto-import all types | 4 weeks |
| 125 | Unified Window - single UI + MCP integration | 3-4 weeks |

**Messenger Integration:** Telegram (pyTelegramBotAPI) + WhatsApp (pywa)

---

## Recommended Next Steps

1. **Phase 126.0:** Fix Balance Bugs (BUG-1 through BUG-5) - 1 day
2. **Phase 126.1:** Coder Function Calling (P0) - 0.5 day
3. **Phase 126.2:** Chat anchor system (MARKER_123.3) - 1.5 days
4. **Phase 126.3:** Clean up 14 pre-existing test failures - 1 day

---

**Report generated by:** Claude Opus 4.5 (Claude Code)
