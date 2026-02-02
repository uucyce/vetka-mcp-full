# 🔴 REAL TODO LIST - What's NOT Done in VETKA
**Date:** 2026-02-02
**Source:** 4 Haiku Scout Agents
**Status:** CRITICAL GAPS IDENTIFIED

---

## 🚨 CRITICAL (P0) - Blocks Core Functionality

### 1. CreateArtifactTool - COMPLETELY MISSING
- **Status:** REMOVED in Phase 92 ("Big Pickle"), NEVER restored
- **Impact:** Dev/Architect agents CANNOT create code files via tool calling
- **Location:** Should be in `src/tools/` but doesn't exist
- **Evidence:** `src/agents/tools.py:1034` - "Note: CreateArtifactTool removed by Big Pickle"
- **Permissions exist:** Lines 914, 945 reference `create_artifact` but tool class is GONE
- **ACTION:** Create `CreateArtifactTool` class + register in tool registry

### 2. Wake Word Detection ("Hey JARVIS") - NOT IMPLEMENTED
- **Status:** DOES NOT EXIST
- **Impact:** No hands-free voice activation - users must click button
- **Missing:** `wake_word.py`, `kws_engine.py`, any keyword spotting
- **ACTION:** Implement lightweight KWS (Silero VAD v5 or TensorFlow Lite)

### 3. Scout Role - COMPLETELY MISSING
- **Status:** Referenced in docs but NEVER created
- **Impact:** Scout → Dev → QA workflow CANNOT work
- **Missing:** No role in `role_prompts.py`, no `VETKAScoutAgent` class
- **ACTION:** Define Scout role + agent class

---

## 🟠 HIGH (P1) - Major Features Broken

### 4. Chat Persistence - PARTIAL
- **What works:** Saving messages to `data/chat_history.json`
- **What's broken:**
  - ❌ No auto-load on startup - chats appear missing until sidebar opened
  - ❌ No pagination - all chats in memory (4.2MB file growing unbounded)
  - ❌ No Qdrant indexing - no semantic chat search
  - ❌ Solo chat streaming may have gaps in persistence
- **ACTION:** Add `useEffect` to load chats on mount, add retention policy

### 5. JARVIS Streaming Pipeline - NOT WIRED
- **Status:** `streaming_pipeline.py` exists but NOT USED
- **Impact:** 5-6s latency - users wait for full audio before hearing anything
- **Current:** `jarvis_handler.py:831-889` uses non-streaming `llm.generate()`
- **ACTION:** Wire `streaming_jarvis_respond()` to Socket.IO for real-time audio

### 6. Engram/Qdrant Context - DISABLED
- **Location:** `jarvis_llm.py:351-353`
- **Status:** Commented out - "TODO: Fix Qdrant vector format issue"
- **Impact:** JARVIS has NO long-term memory, only STM buffer
- **ACTION:** Fix Qdrant 400 Bad Request, re-enable Engram

### 7. Edge-TTS Fast Mode - BROKEN
- **Location:** `jarvis_handler.py:395-397`
- **Status:** Reverted to "quality" mode (Qwen3, 5-6s latency)
- **Intended:** "fast" mode (Edge-TTS, ~1s latency)
- **ACTION:** Debug Edge-TTS integration

---

## 🟡 MEDIUM (P2) - Important but Not Blocking

### 8. Hostess Router - DISABLED
- **Location:** Phase 57.8.2 change
- **Status:** Now passive only (camera/navigation), no intelligent routing
- **Impact:** No auto-routing without explicit @mentions
- **ACTION:** Re-enable or replace with new routing strategy

### 9. Artifact Qdrant Integration - MISSING
- **Status:** Artifacts save to disk but NOT indexed in Qdrant
- **Impact:** No semantic search for artifacts
- **ACTION:** Add vector embeddings on artifact creation

### 10. QA Approval Flow - INCOMPLETE
- **Location:** `group_message_handler.py:906`
- **Status:** Hook identified but not implemented
- **Impact:** Artifacts created without QA verification
- **ACTION:** Wire approval_service integration

### 11. Chat Export Endpoint - MISSING
- **Status:** `export_chat()` method exists, no REST endpoint
- **ACTION:** Add `/api/chats/{id}/export` endpoint

### 12. TTS Server URL - HARD-CODED
- **Location:** `jarvis_handler.py:922`
- **Code:** `Qwen3TTSClient(server_url="http://127.0.0.1:5003")`
- **ACTION:** Make configurable via env var `TTS_SERVER_URL`

---

## 📊 Summary Table

| Feature | Status | Blocker? | Priority |
|---------|--------|----------|----------|
| CreateArtifactTool | ❌ MISSING | YES | P0 |
| Wake Word ("Hey JARVIS") | ❌ MISSING | YES | P0 |
| Scout Role | ❌ MISSING | YES | P0 |
| Chat Auto-Load | 🟡 BROKEN | no | P1 |
| JARVIS Streaming | 🟡 NOT WIRED | no | P1 |
| Engram Memory | ❌ DISABLED | no | P1 |
| Edge-TTS Fast | 🟡 BROKEN | no | P1 |
| Hostess Router | ❌ DISABLED | no | P2 |
| Artifact Search | ❌ MISSING | no | P2 |
| QA Approval | 🟡 PARTIAL | no | P2 |
| Chat Export | ❌ MISSING | no | P2 |

---

## 🎯 Recommended Order of Implementation

### Sprint 1: Core Tools (P0)
1. **CreateArtifactTool** - unblocks Dev/Architect artifact creation
2. **Scout Role** - unblocks Scout→Dev→QA workflow

### Sprint 2: Voice (P1)
3. **Wake Word Detection** - enables hands-free activation
4. **Wire Streaming Pipeline** - reduces latency from 6s to <1s
5. **Re-enable Engram** - gives JARVIS long-term memory

### Sprint 3: Polish (P2)
6. **Chat persistence fixes** - auto-load, pagination, search
7. **Edge-TTS fast mode** - lower latency TTS
8. **QA approval flow** - artifact verification

---

## 📁 Files to Create/Modify

### CREATE:
- `src/tools/create_artifact_tool.py` - CreateArtifactTool class
- `src/voice/wake_word.py` - KWS engine
- `src/agents/scout_agent.py` - VETKAScoutAgent class

### MODIFY:
- `src/agents/role_prompts.py` - add Scout role
- `src/agents/tools.py` - register CreateArtifactTool
- `jarvis_handler.py` - wire streaming pipeline
- `jarvis_llm.py` - re-enable Engram
- `client/src/components/chat/ChatPanel.tsx` - auto-load chats

---

**Generated by:** Claude Opus 4.5 (Architect) + 4 Haiku Scouts
**Report Location:** `/docs/phase_106_multi_agent_mcp/REAL_TODO_LIST.md`
