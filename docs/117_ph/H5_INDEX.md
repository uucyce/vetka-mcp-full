# H5 Scout Analysis: Complete Index

## Overview
This is a comprehensive analysis of how chat messages can be injected as context into VETKA Mycelium pipeline prompts (architect, researcher, coder).

**Status:** Chat history injection is **NOT YET IMPLEMENTED** but infrastructure is ready.

---

## Documents Generated

### 1. H5_SUMMARY.txt (START HERE)
**Purpose:** Executive summary, 2-minute read
**Contains:**
- Key findings at a glance
- The 4 markers you asked for
- Current state vs desired state
- Implementation roadmap
- Answer to your 5 questions

**Read this first for quick understanding.**

---

### 2. H5_SCOUT_CONTEXT_INJECTION_ANALYSIS.md
**Purpose:** Detailed technical deep-dive
**Length:** ~2400 lines (detailed)
**Contains:**
- Full architecture explanation
- 5 working context sources documented
- Why chat history is missing
- Implementation path
- Discovery section
- Code markers table
- Recommendations

**Read this for complete understanding.**

---

### 3. H5_MARKERS_QUICK_REFERENCE.md
**Purpose:** Quick lookup and search guide
**Length:** ~400 lines
**Contains:**
- Definition of each marker
- Code location + line numbers
- Search commands to find markers
- Source breakdown (1-6)
- Architecture diagram
- Implementation checklist

**Use this to find specific code sections.**

---

### 4. H5_IMPLEMENTATION_CODE_EXAMPLES.md
**Purpose:** Step-by-step implementation guide
**Length:** ~700 lines
**Contains:**
- Current researcher call (USES inject_context)
- Current architect call (NO inject_context)
- Step 1: Update schema
- Step 2: Add chat history source
- Step 3-5: Enable in pipeline
- Before/after examples
- Testing checklist
- Performance analysis
- Q&A

**Use this to implement the feature.**

---

### 5. H5_INDEX.md (This File)
**Purpose:** Navigation guide
**Contains:**
- Document index
- Key findings summary
- Marker definitions
- File navigation
- Implementation checklist

---

## The 4 Markers You Asked For

### Marker 1: H5_ARCHITECT_PROMPT_LINE
```
File:     src/orchestration/agent_pipeline.py
Lines:    1144-1158
What:     Architect LLM call setup
Status:   No inject_context (opportunity)
```
**Find it:** Line 1151, start of `call_args = {`

### Marker 2: H5_INJECT_SOURCES
```
File:     src/mcp/tools/llm_call_tool.py
Lines:    346-454
What:     5 context sources implemented:
          1. Files (358-373)
          2. Session state (375-386)
          3. User prefs (388-400)
          4. CAM nodes (402-413)
          5. Semantic search (415-434)
Status:   Working, researcher uses daily
Missing:  Source 6 (chat history)
```
**Find it:** Method `_gather_inject_context()`

### Marker 3: H5_CHAT_HISTORY_INJECT
```
Status:   PARTIAL - Infrastructure exists, not wired up
Tools:    
  - vetka_read_group_messages (MCP tool)
  - vetka_get_chat_digest (MCP tool)
  - ChatHistoryManager (Python class)
```
**Find it:** Search for ChatHistoryManager in codebase

### Marker 4: H5_PROMPT_TEMPLATE_FILE
```
File:     data/templates/pipeline_prompts.json
Backup:   src/orchestration/agent_pipeline.py (lines 142-192)
What:     External prompt storage
Status:   Working, supports 4 roles (architect, researcher, coder, verifier)
```
**Find it:** `data/templates/pipeline_prompts.json`

---

## Quick Answers to Your Questions

**Q1: How are prompts built for architect/researcher/coder?**
- Loaded from JSON file or in-code defaults
- Researcher: Includes `inject_context` with semantic search + prefs
- Architect/Coder: No context injection (yet)

**Q2: Where are system prompts defined?**
- Primary: `data/templates/pipeline_prompts.json` (lines 7-24)
- Fallback: `src/orchestration/agent_pipeline.py` (lines 142-192)

**Q3: Does inject_context support chat history?**
- Current: NO
- Should: YES (H5 goal)
- Effort: 4-6 hours to implement

**Q4: What sources does _gather_inject_context support?**
- 5 sources: files, session, prefs, CAM, semantic
- Missing 6th: chat_history

**Q5: Is there a way to inject recent chat messages?**
- Tools exist but not connected
- Implementation is straightforward
- All code examples provided

---

## Key Files to Know

### Core Pipeline
- `src/orchestration/agent_pipeline.py` — Architect, researcher, coder orchestration
- `src/mcp/tools/llm_call_tool.py` — Context injection implementation
- `data/templates/pipeline_prompts.json` — Prompt storage

### Chat Management
- `src/chat/chat_history_manager.py` — Manages chat message history
- `src/mcp/vetka_mcp_bridge.py` — Group message tools (read-only)

### Memory Systems
- `src/memory/engram_user_memory.py` — User preferences (Qdrant-backed)
- `src/orchestration/cam_engine.py` — Context-aware memory nodes
- `src/search/hybrid_search.py` — Semantic search over codebase
- `src/memory/elision.py` — Token compression (40-60% savings)

---

## Implementation Roadmap

### Phase 1: Add Chat History Source (2 hours)
- [ ] Update `inject_context` schema in llm_call_tool.py
- [ ] Add chat history gathering in `_gather_inject_context()`
- [ ] Format messages with sender/timestamp
- [ ] Test with mock chat data

### Phase 2: Enable in Pipeline (1 hour)
- [ ] Add inject_context to `_architect_plan()`
- [ ] Add inject_context to `_execute_subtask()`
- [ ] Update prompt templates
- [ ] Integration test

### Phase 3: Testing & Validation (1-2 hours)
- [ ] Unit tests for chat history gathering
- [ ] Integration test with real chat
- [ ] Performance benchmarking
- [ ] Error handling validation

### Phase 4: Deployment (1 hour)
- [ ] Code review
- [ ] Merge to main
- [ ] Monitor in production
- [ ] Gather user feedback

---

## Architecture Summary

```
Pipeline receives task
    ↓
Architect breaks it down (NOW: without chat context)
    ↓
Researcher researches questions (NOW: WITH chat context)
    ↓
Coder executes subtasks (NOW: without chat context)
    ↓
All results streamed to Lightning chat

DESIRED (H5):
    ↓
Architect SEES chat context ← NEW
    ↓
Researcher SEES chat context (already does)
    ↓
Coder SEES chat context ← NEW
```

---

## Search Commands

### Find Architect Prompt Line
```bash
grep -n "call_args = {" src/orchestration/agent_pipeline.py
# Look for first occurrence around line 1151
```

### Find Inject Context Implementation
```bash
grep -n "_gather_inject_context\|# 1\. Read files\|# 5\. Semantic" \
  src/mcp/tools/llm_call_tool.py
```

### Find Prompt Templates
```bash
find . -name "*pipeline*prompt*" -type f
find . -name "model_presets.json" -type f
```

### Find Chat History Manager
```bash
grep -r "ChatHistoryManager\|chat_history_manager" --include="*.py" src/
```

---

## Document Navigation

| If you want... | Read... | Time |
|---|---|---|
| Quick summary | H5_SUMMARY.txt | 2 min |
| Full details | H5_SCOUT_CONTEXT_INJECTION_ANALYSIS.md | 20 min |
| Implementation guide | H5_IMPLEMENTATION_CODE_EXAMPLES.md | 30 min |
| Quick lookup | H5_MARKERS_QUICK_REFERENCE.md | 5 min |
| Navigation help | This file (H5_INDEX.md) | 5 min |

---

## Key Takeaways

1. **Researcher Already Uses inject_context** — Semantic search + prefs
2. **Architect Doesn't Use inject_context** — Missing chat context
3. **5 Sources Are Ready** — Files, session, prefs, CAM, semantic
4. **Chat History Tools Exist** — ChatHistoryManager, group messages API
5. **Implementation Is Straightforward** — Copy pattern from semantic search source
6. **Effort Is Low** — 4-6 hours total (1-2 files modified)
7. **Impact Is High** — All agents get chat context automatically
8. **Risk Is Low** — Backward compatible, graceful fallback

---

## Questions?

All answers are in these documents. Check:
- H5_SUMMARY.txt for quick answers
- H5_SCOUT_CONTEXT_INJECTION_ANALYSIS.md for deep dive
- H5_IMPLEMENTATION_CODE_EXAMPLES.md for how-to
- H5_MARKERS_QUICK_REFERENCE.md for code locations

---

## Version Info

**H5 Scout Analysis**
- Created: 2026-02-07
- Analyzed codebase: /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
- Status: Complete research, ready for implementation
- Documents: 5 files, ~4500 lines of analysis

---

## Next Steps

1. **Read H5_SUMMARY.txt** (2 min) — Get oriented
2. **Review H5_MARKERS_QUICK_REFERENCE.md** (5 min) — Understand the markers
3. **Check H5_IMPLEMENTATION_CODE_EXAMPLES.md** (30 min) — Plan implementation
4. **Execute Phase 1 & 2** (3 hours) — Implement chat history injection
5. **Run tests** (1 hour) — Validate
6. **Deploy** (1 hour) — Enable for production

**Total effort: 4-6 hours**
**Expected impact: Significant improvement in pipeline context awareness**
