# VETKA Browser Agent Guide

> **Phase 80.2** | For AI assistants helping debug VETKA from browser

## Quick Start (New Sessions)

### First Command - Run This Immediately:
```javascript
await vetkaAPI.quickStatus()
```

This single command tells you:
- Is tree healthy?
- How many files indexed?
- Are Qdrant and Memory Manager working?
- Any errors present?
- What to do next

### Example Output:
```
╔══════════════════════════════════════════════════════════════╗
║              🌳 VETKA QUICK STATUS REPORT                    ║
╠══════════════════════════════════════════════════════════════╣
║  ✅ VETKA is healthy! 44 files indexed, all systems operational.
╠══════════════════════════════════════════════════════════════╣
║  Tree Health:    ✅ Healthy
║  Files Indexed:  44
║  Qdrant:         ✅ Connected
║  Memory Manager: ✅ Active
║  Errors:         ✅ None
╚══════════════════════════════════════════════════════════════╝
```

---

## All Commands Reference

| Need to know | Command | What it shows |
|--------------|---------|---------------|
| **Everything at once** | `quickStatus()` | Health, errors, components, next steps |
| Overall health | `getTreeState()` | Tree status, file count, Qdrant |
| Full state | `inspect()` | All components, modes, memory |
| Filtered state | `inspect('keyword')` | Only matching keys |
| Errors | `getErrors()` | What went wrong |
| Layout formulas | `getFormulas('mode')` | How 3D positions calculated |
| Available modes | `getModes()` | Directory, Knowledge, Force, Sugiyama |
| Debug logs | `getLogs()` | Execution trace |
| API docs | `getAgentInfo()` | Full endpoint documentation |
| Chat context | `getChatContext()` | Same data as internal agents |
| Chat + history | `getChatContext(true)` | With recent messages |
| Focus camera | `focusCamera('file.py')` | Control 3D view |
| Focus overview | `focusCamera('overview', 'far')` | Show full tree |
| **Send to Claude Code** | `sendTeamMessage(msg)` | Direct agent-to-agent chat! |
| **Read messages** | `readTeamMessages()` | Check incoming messages |
| **Quick check** | `checkMessages()` | Unread count + latest |
| **Team members** | `getTeamAgents()` | List of known agents |
| Help | `help()` | Show command list |

---

## Red Flags (Report to Claude Code Immediately)

When you see any of these, tell Claude Code (MCP):

| Red Flag | Meaning | What to report |
|----------|---------|----------------|
| `healthy: false` | Tree data broken | "Tree unhealthy, needs investigation" |
| `status: "red"` | Qdrant in bad state | "Qdrant status RED" |
| `qdrant_connected: false` | Database offline | "Qdrant not connected" |
| `memory_manager_active: false` | Memory system down | "Memory manager inactive" |
| `recent_errors_count > 0` | Errors occurred | Run `getErrors()` and share details |

---

## Debugging Workflows

### Tree Not Rendering?
```javascript
// Step 1: Check health
await vetkaAPI.getTreeState()

// Step 2: If unhealthy, check what mode is active
await vetkaAPI.getModes()

// Step 3: Check formulas for that mode
await vetkaAPI.getFormulas('directory')  // or 'knowledge', 'force_directed'
```

### Strange Layout / Positions Wrong?
```javascript
// Check which mode's formulas are being used
await vetkaAPI.getFormulas('directory')
await vetkaAPI.getFormulas('knowledge')

// Look for blend-related state
await vetkaAPI.inspect('blend')
```

### Performance Issues?
```javascript
// Check for errors
await vetkaAPI.getErrors()

// Check component status
await vetkaAPI.inspect('memory')

// Check logs for slow operations
await vetkaAPI.getLogs(50, 'performance')
```

### Unknown State / Need Overview?
```javascript
// Full state dump
await vetkaAPI.inspect()

// Or filter by keyword
await vetkaAPI.inspect('qdrant')
await vetkaAPI.inspect('mode')
await vetkaAPI.inspect('cache')
```

---

## Architecture Understanding

### What Browser Agents CAN Do:
- Read all tree state and metrics
- Analyze errors and logs
- Understand layout formulas
- Inspect component health
- Suggest fixes and improvements
- **Control 3D camera** (focus on files, zoom, highlight)
- **See chat context** (same data as internal VETKA agents)

### What Browser Agents CANNOT Do:
- Modify any code
- Change configurations
- Execute shell commands
- Access file system directly
- Create/delete files

### Who Does What:
```
Browser Agent (You)          Claude Code (MCP)
─────────────────           ─────────────────
  Observe                     Execute
  Analyze                     Modify
  Diagnose                    Fix
  Suggest                     Implement
  Report                      Commit
```

---

## Key Files

| File | Purpose |
|------|---------|
| `/src/api/routes/debug_routes.py` | Backend debug API (7 endpoints) |
| `/client/src/utils/browserAgentBridge.ts` | Frontend bridge (window.vetkaAPI) |
| `/src/layout/fan_layout.py` | Directory mode formulas |
| `/src/layout/knowledge_layout.py` | Knowledge mode formulas |

---

## Visualization Modes

### 1. Directory Mode (default)
- Shows file system hierarchy
- Fan layout with Y_PER_DEPTH spacing
- Good for understanding folder structure

### 2. Knowledge Mode
- Groups files by semantic tags
- Files orbit around tag clusters
- Good for understanding relationships

### 3. Force-Directed Mode
- Physics simulation (attraction/repulsion)
- Dynamic positions calculated on frontend
- Good for seeing natural clusters

### 4. Sugiyama Mode (experimental)
- Hierarchical DAG layout
- Layers based on dependency depth
- Good for dependency visualization

---

## Tips for Effective Debugging

1. **Always start with `quickStatus()`** - it catches most issues instantly

2. **Use keyword filters** - `inspect('blend')` is faster than full inspect

3. **Check cache status** - modes show if data is cached or needs recompute

4. **Look at formulas** - wrong Y values often mean wrong mode formulas applied

5. **Report with context** - tell Claude Code what you found + what you tried

---

## Example Session Flow

```javascript
// 1. Start every session with quick status
const status = await vetkaAPI.quickStatus()

// 2. If issues found, dig deeper
if (status.redFlags.length > 0) {
  // Check specific issues
  if (!status.components.qdrant) {
    console.log("Qdrant issue - check if running on port 6333")
  }
  if (status.hasErrors) {
    await vetkaAPI.getErrors()
  }
}

// 3. For layout debugging
await vetkaAPI.getModes()  // see what's active
await vetkaAPI.getFormulas('knowledge')  // check formulas

// 4. Report to Claude Code
// "Found: Qdrant connected but knowledge cache empty.
//  Formulas show directory mode active when expecting knowledge mode.
//  Suggest: Check blend slider value and cache refresh."
```

---

---

## Camera Control Examples

```javascript
// Focus on specific file
await vetkaAPI.focusCamera('src/main.py')

// Focus on folder with zoom out
await vetkaAPI.focusCamera('src/api/', 'far')

// Overview of entire tree
await vetkaAPI.focusCamera('overview', 'far')

// Close-up with highlight
await vetkaAPI.focusCamera('config.json', 'close', true, true)
```

## Chat Context Example

```javascript
// Get context (what internal agents see)
const ctx = await vetkaAPI.getChatContext()
console.log(ctx.summary_for_agent)
// → "VETKA Phase 80.1. Tree has 44 files indexed. Active components: orchestrator, memory_manager..."

// With chat history
const ctxWithHistory = await vetkaAPI.getChatContext(true, 20)
console.log(ctxWithHistory.chat_history)
// → Last 20 messages from chat
```

---

---

## Phase 80.2: Agent-to-Agent Messaging

### Send a message to Claude Code:
```javascript
// Simple message
await vetkaAPI.sendTeamMessage("Found issue in sugiyama_layout.py line 45")

// With context
await vetkaAPI.sendTeamMessage(
  "Found potential bug in layer assignment",
  "claude_code",
  "high",
  { file: "sugiyama_layout.py", line: 45, issue: "empty array" }
)

// Broadcast to all agents
await vetkaAPI.sendTeamMessage("System check complete - all good!", "all")
```

### Check for responses:
```javascript
// Quick check
const { unread, latest } = await vetkaAPI.checkMessages()

// Full list
await vetkaAPI.readTeamMessages()

// Only unread, mark as read
await vetkaAPI.readTeamMessages(10, true, true)
```

### Team members:
```javascript
await vetkaAPI.getTeamAgents()
// Returns: browser_haiku, claude_code, vetka_internal, user
```

---

*Last updated: Phase 80.2 | 2026-01-21*
