# Grok Consultation: MCP Strategy for VETKA

**Date:** 2026-01-26
**Purpose:** Get Grok's perspective on MCP vs Native implementation

---

## CONTEXT FOR GROK

VETKA is a 3D knowledge visualization system with:
- Multi-LLM orchestration (GPT, Claude, Grok, Gemini, Ollama)
- Qdrant vector search
- File watching + auto-indexing
- Group chat between AI models
- MCP server exposing 18 tools

**Current State:**
- MCP bridge works (18 tools, stdio/HTTP/SSE)
- Engram memory built but NOT connected
- Jarvis enricher built but NOT connected
- User history WORKING
- Parallel execution via asyncio.gather

---

## QUESTIONS FOR GROK

### Question 1: Session Initialization

We want Claude Code (via MCP) to start with context. Two options:

**Option A: Fat Session Init**
```json
// Single tool call returns everything
vetka_session_init() → {
  project_summary: "...",
  user_context: "...",
  recent_files: [...],
  available_tools: [...]
}
```

**Option B: Lazy Loading**
```json
// Multiple smaller calls
vetka_get_project_context() → brief summary
vetka_get_user_memory() → user prefs
vetka_get_recent_artifacts() → file list
```

**Which approach is better for token efficiency and UX?**

---

### Question 2: Tool Composition

Should we expose compound tools via MCP or keep them atomic?

**Option A: Atomic Only**
```
Client calls: search → read → summarize (3 MCP calls)
```

**Option B: Compound Tools**
```
Client calls: vetka_research(topic) (1 MCP call, does all 3)
```

**Trade-offs?**

---

### Question 3: Agent Workflow via MCP

We want PM → Architect → Dev || QA workflow. Options:

**Option A: MCP-Native Workflow**
```
Claude Code calls: vetka_pm_decompose()
Claude Code calls: vetka_architect_plan()
Claude Code calls: vetka_parallel_dev([tasks])
Claude Code calls: vetka_qa_verify()
```

**Option B: VETKA-Internal Workflow**
```
Claude Code calls: vetka_execute_workflow({
  type: "pm_to_qa",
  request: "Add feature X"
})
// VETKA handles all orchestration internally
```

**Which gives better control vs simplicity?**

---

### Question 4: MCP-to-MCP Bridging

Should VETKA MCP server be able to call OTHER MCPs?

**Scenario:** User asks VETKA to search GitHub. Options:
- A: VETKA calls GitHub MCP directly
- B: Return instruction to Claude Code, let it call GitHub MCP
- C: Don't bridge, keep MCPs isolated

**Security and architecture considerations?**

---

### Question 5: State Management

For parallel agent tasks, where should shared state live?

**Options:**
- A: Redis (external, fast, TTL support)
- B: In-memory dict (simple, no deps, lost on restart)
- C: Qdrant (vector + metadata, already running)
- D: SQLite (persistent, local, ACID)

**For a single-user desktop app, what's pragmatic?**

---

## DOCUMENTS TO PIN

Before calling Grok in VETKA chat, pin these:

1. `docs/94_ph/HAIKU_4_MCP_ARCHITECTURE.md` - MCP details
2. `docs/94_ph/HAIKU_5_AGENT_WORKFLOW.md` - Workflow gaps
3. `docs/94_ph/HAIKU_1_ENGRAM_STATUS.md` - Memory status

---

## EXPECTED OUTPUT

From Grok, we want:
1. Clear recommendation per question
2. Code snippets if applicable
3. Warnings about edge cases
4. Priority order for implementation

---

## HOW TO USE

Copy this prompt to VETKA chat:

```
@grok

Контекст в запиненных документах. Ответь на 5 вопросов из GROK_PROMPT_MCP_STRATEGY.md:

1. Session Init: Fat vs Lazy?
2. Tool Composition: Atomic vs Compound?
3. Workflow: MCP-Native vs VETKA-Internal?
4. MCP-to-MCP: Bridge or Isolate?
5. State: Redis vs Memory vs Qdrant vs SQLite?

Дай конкретные рекомендации с примерами кода где уместно.
```
