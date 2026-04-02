# SHERPA — Scout & Harvest Engine for Recon, Prep & Augmentation

**Phase:** 202
**Date:** 2026-04-02
**Status:** v1.0 live, 10 services configured, P0/P1 bugs tracked
**Origin:** WEATHER simplification — no new browser, no framework, just scripts
**Current Services:** DeepSeek (2x), Kimi (2x), Arena, Z.ai, Mistral, HuggingChat, Monica, Bolt

---

## 1. What Sherpa Is

Sherpa is a **recon agent** powered by a local model (Qwen 2.5 7B on LiteRT/Ollama) armed with scripts that:

1. Takes a pending task from TaskBoard
2. Reads its context_packet (description, arch_docs, recon_docs, hints)
3. Searches the codebase (grep, semantic search, file read)
4. Asks free AI services (Grok/Gemini/Kimi) via existing Chrome tabs for research
5. Saves the research back into the task as enriched recon_docs
6. Leaves the task as `pending` — ready for a real coding agent

**Sherpa does NOT write production code.** It prepares the trail.

---

## 2. What Sherpa Is NOT

- NOT a new project/app/framework
- NOT a browser (uses existing Chrome via Control Chrome MCP)
- NOT a code generator (research + examples only)
- NOT WEATHER (no Playwright, no adapters, no profiles, no Tauri)
- NOT a replacement for Claude/Opus agents — it's their scout

---

## 3. Why Sherpa Exists

**Problem:** 1000+ pending tasks, API token limits, 3-4 hour waits between sessions.

**Insight:** ~30% of every agent session is spent on recon (finding files, understanding architecture, researching approaches). If recon is pre-done for free, each paid session produces 30% more code.

**Economics:**
- Without Sherpa: 10 tasks/session * 2 sessions/day = 20 tasks/day
- With Sherpa: 15 tasks/session * 2 sessions/day = 30 tasks/day
- Delta: +50% throughput at zero additional cost

---

## 4. Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│  TaskBoard   │────▶│  Sherpa Loop  │────▶│  Chrome Tabs     │
│  (SQLite)    │     │  (Python)     │     │  (Grok/Gemini)   │
│              │◀────│  Qwen 2.5     │◀────│  get_page_content│
└─────────────┘     │  orchestrator │     └──────────────────┘
                    │               │
                    │  Tools:       │     ┌──────────────────┐
                    │  - grep/read  │────▶│  Codebase         │
                    │  - semantic   │     │  (local files)    │
                    │  - taskboard  │     └──────────────────┘
                    └──────────────┘
```

**No new infrastructure.** Every component already exists:
- TaskBoard: `src/mcp/tools/task_board_tools.py`
- Chrome control: Control Chrome MCP (already connected)
- Codebase search: `vetka_search_semantic`, `vetka_search_files`, `vetka_read_file`
- Local model: Ollama / Qwen 2.5 via `llm_call_tool.py`

---

## 5. Sherpa Loop (pseudocode)

```python
# sherpa.py — the entire agent, ~200-300 lines

while True:
    # 1. Pick a task
    task = taskboard.claim_next(
        filter_status="pending",
        filter_phase_type="research",  # or tasks with empty recon_docs
        sort="priority"
    )
    if not task:
        sleep(60)
        continue

    # 2. Gather context
    context = taskboard.context_packet(task.id)

    # 3. Local recon — search codebase
    files = codebase_search(task.description, task.allowed_paths)
    snippets = read_relevant(files, limit=5)

    # 4. Build prompt for browser AI
    prompt = f"""
    Task: {task.title}
    Description: {task.description}
    Architecture docs: {context.arch_docs_content}
    Relevant code files: {snippets}

    Research this task:
    1. What files need to be modified?
    2. What's the best approach?
    3. Show example code for the key changes
    4. What are the risks/edge cases?
    """

    # 5. Ask Grok/Gemini via Chrome
    response = chrome.send_to_tab(
        tab="grok.com",
        message=prompt,
        wait_for_response=True
    )

    # 6. Save research back to task
    recon_path = f"docs/sherpa_recon/sherpa_{task.id}.md"
    save_file(recon_path, response)

    taskboard.update(task.id,
        recon_docs=[recon_path],
        status="pending"  # stays pending, now enriched
    )

    # 7. Cooldown (respect rate limits)
    sleep(120)
```

---

## 6. Task Selection Criteria

### Take:
- `phase_type=research` — direct match
- Tasks with empty `recon_docs` — needs investigation
- Tasks with "investigate", "audit", "find", "understand" in description
- New features where insertion point is unclear
- `complexity=high` — most benefit from pre-research

### Skip:
- One-line fixes (rename, import fix, typo)
- Tasks with filled `implementation_hints` — already scouted
- Mechanical bulk changes (update 20 files same pattern)
- Tasks already claimed by another agent

---

## 7. Output Format

Each Sherpa recon saves to `docs/sherpa_recon/sherpa_{task_id}.md`:

```markdown
# Sherpa Recon: {task.title}

## Source: {grok|gemini|kimi}
## Date: {timestamp}
## Task ID: {task_id}

## Files to Modify
- path/to/file1.py (lines 45-67) — reason
- path/to/file2.ts (lines 100-120) — reason

## Recommended Approach
1. Step one...
2. Step two...

## Example Code
\```python
# key implementation snippet
\```

## Risks / Edge Cases
- Risk 1...
- Risk 2...

## Related Code Patterns
- Similar pattern in path/to/existing.py:30
```

---

## 8. Dependencies

| Component | Status | Location |
|-----------|--------|----------|
| TaskBoard MCP tools | Ready | `src/mcp/tools/task_board_tools.py` |
| Control Chrome MCP | Ready | Already connected |
| Ollama + Qwen 2.5 | Ready | Local install |
| `llm_call_tool.py` | Ready | `src/mcp/tools/llm_call_tool.py` |
| Codebase search | Ready | VETKA MCP tools |
| Chrome with accounts | Ready | User's Chrome, logged into Grok/Gemini |

**New code needed:** ~200-300 lines (`sherpa.py` + prompt templates)

---

## 9. Relationship to WEATHER

WEATHER was the grand vision: custom browser, Playwright automation, service adapters, profile management, captcha handling.

Sherpa is the pragmatic extraction: **use what exists, skip everything else.**

If Sherpa proves valuable, WEATHER components can be added incrementally:
- Sherpa works → add Playwright for headless (no Chrome needed)
- Headless works → add profile rotation
- Rotation works → now you have WEATHER

But start with Sherpa. One script. Zero infrastructure.

---

*Sherpa: the one who carries the load and shows the way to the summit.*
