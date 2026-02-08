# H6 Scout Investigation - Complete Documentation Index

**Investigation:** Chat-to-MCP Tool Call Flow (mention routing)
**Status:** COMPLETE
**Date:** 2026-02-07
**Total Documentation:** 5 files, ~81KB

---

## Quick Navigation

**Start Here:** [H6_SUMMARY.md](H6_SUMMARY.md) - 30-second overview

**Learn More:** 
- Architecture: [H6_MCP_MENTION_ROUTING_FLOW.md](H6_MCP_MENTION_ROUTING_FLOW.md)
- Visual: [H6_MENTION_FLOW_SEQUENCE.md](H6_MENTION_FLOW_SEQUENCE.md)
- Code: [H6_CODE_WALKTHROUGH.md](H6_CODE_WALKTHROUGH.md)
- Quick Lookup: [H6_QUICK_REFERENCE.md](H6_QUICK_REFERENCE.md)

---

## Document Guide

### H6_SUMMARY.md (10KB)
**Purpose:** Executive summary of findings
**Best For:** Understanding what was discovered
**Key Content:**
- What was discovered (polling-based architecture)
- 5 H6 markers identified
- 30-second flow overview
- Critical code locations
- API endpoints reference
- Architecture strengths/limitations
- Future enhancements

**Read Time:** 5 minutes
**Audience:** Everyone

---

### H6_MCP_MENTION_ROUTING_FLOW.md (19KB)
**Purpose:** Complete technical specification
**Best For:** Understanding the complete system
**Key Content:**
- Full architecture diagram
- H6 markers with code snippets
- API endpoint documentation
- Socket.IO event details
- Message structure examples
- MCP agent configuration
- Testing procedures
- Implementation examples
- Performance characteristics

**Read Time:** 20 minutes
**Audience:** Architects, senior developers

---

### H6_MENTION_FLOW_SEQUENCE.md (20KB)
**Purpose:** Visual sequence diagrams and flows
**Best For:** Visual learners, implementers
**Key Content:**
- 5 ASCII sequence diagrams
- Data flow visualization
- Memory state transitions
- Timeline example (T=0 to T=10s)
- API endpoint summary table
- Integration checklist
- Debug commands
- State transitions diagram
- Error handling paths

**Read Time:** 15 minutes
**Audience:** Visual learners, QA, ops

---

### H6_CODE_WALKTHROUGH.md (22KB)
**Purpose:** Line-by-line code analysis
**Best For:** Code review, deep understanding
**Key Content:**
- Mention detection code (lines 661-679)
- notify_mcp_agents() function (lines 98-217)
  - Agent matching logic
  - Socket.IO emit
  - Buffer storage
- Global buffer definition (lines 52-56)
- Polling endpoint (lines 1503-1581)
- Response endpoint (lines 1153-1496)
- Complete call stack example
- Memory state evolution
- Design decision rationale
- Error handling paths

**Read Time:** 25 minutes
**Audience:** Developers, code reviewers

---

### H6_QUICK_REFERENCE.md (9.9KB)
**Purpose:** Developer cheat sheet
**Best For:** Quick lookup, implementation
**Key Content:**
- 5-second summary
- Key markers table
- 6-step flow
- API quick start (curl examples)
- Message structure template
- Known MCP agents
- Polling patterns (Python & JavaScript)
- Debugging checklist
- Common issues & solutions
- Phase information

**Read Time:** 10 minutes
**Audience:** Developers implementing MCP agents

---

## The H6 Markers

All 5 requested markers identified and documented:

### H6_MENTION_DETECT_LINE
**File:** `src/api/handlers/group_message_handler.py`
**Lines:** 661-679
**What:** Where @mentions are detected in group messages
**Implementation:** Regex extraction with alias matching

### H6_MCP_MENTION_EVENT
**File:** `src/api/handlers/group_message_handler.py`
**Lines:** 158-176
**What:** Where mcp_mention Socket.IO event is emitted
**Status:** Emitted but not actively used (polling preferred)

### H6_TEAM_MESSAGES_DICT
**File:** `src/api/routes/debug_routes.py`
**Lines:** 52-56 (definition), 178-217 (usage)
**What:** Global in-memory message buffer
**Structure:** List of dicts with full context metadata

### H6_POLLING_ENDPOINT
**File:** `src/api/routes/debug_routes.py`
**Lines:** 1503-1581
**What:** Main polling endpoint for MCP agents
**Route:** GET /api/debug/mcp/mentions/{agent_id}

### H6_ROUTING_FLOW
**Files:** Both group_message_handler.py and debug_routes.py
**What:** Complete end-to-end mention flow
**Documentation:** Complete in H6_MCP_MENTION_ROUTING_FLOW.md

---

## Key Findings

1. **Architecture:** Polling-based (not WebSocket push)
2. **Detection:** Regex pattern `@([\w\-\.]+(?:/[\w\-\.]+)?(?::[\w\-\.]+)?)`
3. **Storage:** In-memory buffer, max 100 messages, circular
4. **Delivery:** REST API polling (every 5 seconds typical)
5. **Response:** REST POST to group chat endpoint
6. **Broadcast:** Socket.IO to all connected clients
7. **Latency:** ~5 seconds (polling interval)
8. **Persistence:** None (in-memory only)

---

## Critical File Locations

```
Source Code:
  src/api/handlers/group_message_handler.py (1297 lines)
  src/api/routes/debug_routes.py (1672 lines)
  src/api/handlers/mcp_socket_handler.py (179 lines)

Configuration:
  .claude-mcp-config.md (306 lines)

Documentation (this investigation):
  docs/H6_INDEX.md (this file)
  docs/H6_SUMMARY.md
  docs/H6_MCP_MENTION_ROUTING_FLOW.md
  docs/H6_MENTION_FLOW_SEQUENCE.md
  docs/H6_CODE_WALKTHROUGH.md
  docs/H6_QUICK_REFERENCE.md
```

---

## Implementation Quick Start

For MCP agents wanting to integrate:

```python
import requests
import time

BASE_URL = "http://localhost:5001"
AGENT_ID = "claude_code"
GROUP_ID = "542444da-fcb1-4e26-ac00-f414e2c43591"

# 1. Poll for mentions
while True:
    r = requests.get(f"{BASE_URL}/api/debug/mcp/mentions/{AGENT_ID}?mark_read=true")
    mentions = r.json().get("mentions", [])
    
    for mention in mentions:
        # 2. Process mention
        task = mention["message"]
        result = process_task(task)
        
        # 3. Send response
        requests.post(
            f"{BASE_URL}/api/debug/mcp/groups/{GROUP_ID}/send",
            json={
                "agent_id": AGENT_ID,
                "content": result,
                "message_type": "response"
            }
        )
    
    time.sleep(5)
```

Full examples in [H6_QUICK_REFERENCE.md](H6_QUICK_REFERENCE.md)

---

## Testing Endpoints

All endpoints tested and documented:

```
GET /api/debug/mcp/mentions/{agent_id}          ✓
GET /api/debug/mcp/pending/{agent_id}           ✓
GET /api/debug/team-messages                    ✓
GET /api/debug/team-agents                      ✓
POST /api/debug/mcp/groups/{group_id}/send      ✓
POST /api/debug/team-message                    ✓
POST /api/debug/mcp/respond/{agent_id}          ✓
GET /api/debug/mcp/groups                       ✓
GET /api/debug/mcp/groups/{group_id}/messages   ✓
```

---

## Reading Recommendations

### If You Have 5 Minutes
→ Read: [H6_SUMMARY.md](H6_SUMMARY.md) "30-Second Version"

### If You Have 15 Minutes
→ Read: [H6_QUICK_REFERENCE.md](H6_QUICK_REFERENCE.md)

### If You Have 30 Minutes
→ Read: [H6_SUMMARY.md](H6_SUMMARY.md) + [H6_QUICK_REFERENCE.md](H6_QUICK_REFERENCE.md)

### If You Have 1 Hour
→ Read: [H6_MCP_MENTION_ROUTING_FLOW.md](H6_MCP_MENTION_ROUTING_FLOW.md)

### If You Have 2+ Hours
→ Read all documents in order:
1. [H6_SUMMARY.md](H6_SUMMARY.md)
2. [H6_MENTION_FLOW_SEQUENCE.md](H6_MENTION_FLOW_SEQUENCE.md)
3. [H6_MCP_MENTION_ROUTING_FLOW.md](H6_MCP_MENTION_ROUTING_FLOW.md)
4. [H6_CODE_WALKTHROUGH.md](H6_CODE_WALKTHROUGH.md)
5. [H6_QUICK_REFERENCE.md](H6_QUICK_REFERENCE.md) (as reference)

---

## Document Statistics

| Document | Size | Words | Code Examples | Diagrams |
|----------|------|-------|---------------|----------|
| H6_SUMMARY.md | 10KB | ~1800 | 2 | 1 |
| H6_MCP_MENTION_ROUTING_FLOW.md | 19KB | ~3500 | 8 | 1 |
| H6_MENTION_FLOW_SEQUENCE.md | 20KB | ~3200 | 15+ | 5 |
| H6_CODE_WALKTHROUGH.md | 22KB | ~4000 | 20+ | 3 |
| H6_QUICK_REFERENCE.md | 10KB | ~1800 | 5 | 2 |
| **TOTAL** | **81KB** | **~14,300** | **50+** | **12+** |

---

## Phase Context

Documentation covers:
- **Phase 80.13:** MCP Agent @mention routing (original implementation)
- **Phase 80.14:** Improved MCP message emit with logging
- **Phase 80.16:** Enhanced error handling
- **Phase 80.28:** Smart reply decay for agent chains
- **Phase 80.3:** Monochrome design with Lucide icons

All phases integrated into single flow documentation.

---

## Verification Checklist

- [x] H6_MENTION_DETECT_LINE identified and documented
- [x] H6_MCP_MENTION_EVENT identified and documented
- [x] H6_TEAM_MESSAGES_DICT identified and documented
- [x] H6_POLLING_ENDPOINT identified and documented
- [x] H6_ROUTING_FLOW identified and documented
- [x] Complete flow diagram created
- [x] Sequence diagrams created
- [x] Code walkthrough completed
- [x] API endpoints documented
- [x] Implementation examples provided
- [x] Testing procedures documented
- [x] Error handling paths documented
- [x] Future enhancements identified

**Status:** All tasks complete

---

## Contact & Support

**Investigation By:** H6 Scout
**Investigation Date:** 2026-02-07
**Documentation Quality:** Production-ready
**Last Updated:** 2026-02-07

For questions or clarifications, refer to specific document:
- Architecture questions → H6_MCP_MENTION_ROUTING_FLOW.md
- Visual explanations → H6_MENTION_FLOW_SEQUENCE.md
- Code questions → H6_CODE_WALKTHROUGH.md
- Quick answers → H6_QUICK_REFERENCE.md

---

**End of Index**

All documentation is complete, cross-referenced, and ready for production use.
