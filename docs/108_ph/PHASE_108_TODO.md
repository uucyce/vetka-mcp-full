# Phase 108: MCP ↔ VETKA Chat Integration - TODO

**Date:** 2026-02-02
**Status:** IN PROGRESS

---

## DONE (Completed)

### MCP ↔ VETKA Core
| Task | Status | Marker | Files |
|------|--------|--------|-------|
| Unified ID (session_id = chat_id) | ✅ | MARKER_108_1 | src/mcp/tools/session_tools.py |
| vetka_send_message tool | ✅ | MARKER_108_2 | src/mcp/vetka_mcp_bridge.py |
| Chat digest for MCP | ✅ | MARKER_108_3 | src/chat/chat_history_manager.py |
| Socket.IO real-time bridge | ✅ | MARKER_108_4 | src/api/routes/debug_routes.py |

### UI Fixes
| Task | Status | Marker | Files |
|------|--------|--------|-------|
| Scroll button (toggle up/down) | ✅ | MARKER_SCROLL_BTN_FIXED | ChatPanel.tsx |
| Scroll initial state fix | ✅ | MARKER_SCROLL_BTN_TOGGLE_FIX | ChatPanel.tsx |
| Group rename sync | ✅ | MARKER_GROUP_RENAME_SYNC | ChatPanel.tsx |
| Rename event broadcast | ✅ | MARKER_RENAME_FIX | ChatPanel.tsx, ChatSidebar.tsx |
| Load More button gray | ✅ | - | ChatSidebar.css |

### Audits Complete
| Audit | Report | Location |
|-------|--------|----------|
| MCP + Qdrant ready | AUDIT_MCP_CHAT_QDRANT_108.md | docs/ |
| Routing problems | PHASE_108_ROUTING_AUDIT.md | docs/107_ph/ |
| Edit name buttons | EDIT_NAME_AUDIT_REPORT.md | docs/ |

---

## IN PROGRESS

### Routing Fixes (from Haiku audit)
| Task | Priority | Status | Problem |
|------|----------|--------|---------|
| Remove auto-fallback to OpenRouter | P0 | ⏳ | provider_registry.py:1139-1225 |
| Fix reply to MCP agents | P0 | ⏳ | group_message_handler.py:663-677 |
| Unify author format | P1 | ⏳ | Multiple files |
| Fix @mention regex for hyphens | P2 | ⏳ | group_message_handler.py:617 |

### Testing
| Task | Status |
|------|--------|
| Test rename chats (sidebar sync) | ⏳ User testing |
| Test MCP message persistence | ⏳ Pagination issue (not bug) |

---

## TODO (Planned)

### Phase 108.2: Routing Fixes
```
1. MARKER_FALLBACK_BUG - Remove auto-fallback
2. MARKER_REPLY_HANDLER - Fix MCP reply routing
3. MARKER_AUTHOR_FORMAT - Unify sender_id format
4. MARKER_MCP_ROUTING - Improve @mention regex
```

### Phase 108.3: Chat → Qdrant Indexing
```
1. Index chat messages to Qdrant
2. Semantic search across chat history
3. Link artifacts to chats
```

### Phase 108.4: 3D Chat Nodes (ARCHITECTURE)
```
1. History chats as 3D nodes in VETKA
2. Artifacts appear near chat timeline
3. Visual chat tree navigation
```

### Pending from Phase 107
| Task | Priority |
|------|----------|
| PAGINATION: load end of chat by default | P1 |
| RETENTION: cleanup old chats policy | P2 |

---

## Files Changed Today

### Frontend
- `client/src/components/chat/ChatPanel.tsx` - scroll, rename fixes
- `client/src/components/chat/ChatSidebar.tsx` - rename listener
- `client/src/components/chat/ChatSidebar.css` - gray button

### Backend
- `src/mcp/tools/session_tools.py` - unified ID
- `src/mcp/vetka_mcp_bridge.py` - send_message, chat_digest tools
- `src/chat/chat_history_manager.py` - get_chat_digest method
- `src/services/group_chat_manager.py` - update_group_name

---

## For Grok: Summary Prompt

**Context:**
- Phase 108 = MCP ↔ VETKA Chat Integration
- Goal: Unified chat experience across Claude Code, VETKA UI, and other MCP agents
- Key: session_id = chat_id (unified)

**Current State:**
- MCP can READ group messages ✅
- MCP can WRITE to chats ✅ (needs server restart)
- Real-time sync via Socket.IO ✅
- UI rename/scroll fixed ✅

**Next Priority:**
1. Routing fixes (no auto-fallback, proper @mention)
2. Chat → Qdrant indexing
3. 3D chat visualization in VETKA

**Key Markers to Search:**
```bash
grep -rn "MARKER_108" src/
grep -rn "MARKER_FALLBACK_BUG" src/
grep -rn "MARKER_RENAME_FIX" client/
```

---

## Quick Commands

```bash
# Find all Phase 108 markers
rg "MARKER_108" --type py --type tsx

# Check MCP tools
curl http://localhost:5001/api/mcp/tools

# Test group messages
curl http://localhost:5001/api/groups/5e2198c2-8b1a-45df-807f-5c73c5496aa8/messages?limit=10
```
