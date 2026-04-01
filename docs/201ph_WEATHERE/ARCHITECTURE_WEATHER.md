# WEATHER — Web Execution & Adaptive Task Heuristic Environment Router

**Phase:** 201
**Date:** 2026-03-31 (updated 2026-04-02)
**Status:** PARKED — conservation until after CUT MVP

> **Conservation Note (2026-04-02):** WEATHER is a critical long-term vision but CUT MVP takes priority. This document has been rewritten to reflect the correct architecture (compose from existing, not build from scratch). All obsolete adapter tasks closed. New P4 tasks created for when we return. — Captain Polaris

---

## 1. Overview

WEATHER is the **browser automation + local model orchestration layer** of VETKA. It connects the TaskBoard to free-tier AI chat services (Gemini, Kimi, Grok, Perplexity, Mistral) via Playwright/Chromium automation, orchestrated by local models through the localgays harness.

**Why WEATHER:** Agents operate "in the weather" — navigating dynamic web conditions (captcha, rate limits, UI changes, session expiry). The system adapts to conditions like weather.

**Key insight from Grok research (2026-04-01):** Do NOT build separate adapters or fork external solutions (browser-use). WEATHER = **compose from existing VETKA components**. ~70-95% of infrastructure already exists across phases 136-147, MCC, localgays, and the agent registry.

```
TaskBoard → localgays orchestrator → Playwright pool → AI Service (browser) → Code extraction → Git → TaskBoard update
```

---

## 2. Architecture — Compose from Existing

WEATHER is NOT a standalone system. It is a **glue layer** that connects existing VETKA components into a pipeline:

```
┌──────────────────────────────────────────────────────────────────────┐
│                         WEATHER Layer                                │
│                                                                      │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────────┐    │
│  │  TaskBoard  │───▶│  localgays   │───▶│  Playwright Pool     │    │
│  │  (SQLite)   │    │  (harness)   │    │  (browser automation)│    │
│  └─────────────┘    └──────┬───────┘    └──────────┬───────────┘    │
│                            │                        │                │
│  ┌─────────────────────────▼────────────────────────▼───────────┐    │
│  │              AI Service Sessions (browser)                    │    │
│  │         Gemini / Kimi / Grok / Perplexity / Mistral           │    │
│  └────────────────────────────┬─────────────────────────────────┘    │
│                               │                                       │
│  ┌────────────────────────────▼─────────────────────────────────┐    │
│  │              Code Extract + Validator                         │    │
│  │         (DOM parsing + OCR + syntax check + security)         │    │
│  └────────────────────────────┬─────────────────────────────────┘    │
│                               │                                       │
│                        git commit → push → need_qa                    │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.1 Component Sources (Where Each Piece Lives)

| WEATHER Component | Source | Path | Status |
|-------------------|--------|------|--------|
| **Browser Shell** | VETKA Tauri (phases 136-147) | `client/src-tauri/` | ✅ Working (web search, viewport save, contextual retrieval) |
| **Orchestrator** | localgays harness | `src/services/` | 🔄 In progress (local model integration) |
| **Playwright Pool** | Already used by Codex/Claude Code | E2E infrastructure | ✅ Available (50+ E2E tests use Playwright) |
| **Agent Phonebook** | unified_key_manager | `src/services/` | ✅ Working (provider credentials) |
| **Chat (local + API)** | MCC/VETKA chat panels | `client/src/components/chat/` | ✅ Working |
| **TaskBoard Sidebar** | MCC | MCC UI | ✅ Working (needs project/agent filters) |
| **Code Extractor** | code_extractor.py | `src/services/code_extractor.py` | ✅ Working (DOM + OCR + validation) |
| **MCC Playground** | MCC workflow env | MCC | ✅ Working (orchestration environment) |

---

## 3. Design Principles

### 3.1 No Separate Adapters
**Decision (2026-04-02):** Do NOT build per-service adapters (kimi_adapter.py, grok_adapter.py, etc.). Instead:
- One universal Playwright context pool
- Sessions managed by profile (userDataDir), not by adapter class
- Selectors handled heuristically (ARIA roles, text matching, OCR fallback)
- Provider-specific logic lives in `config/browser_agents.yaml` (selectors, URLs), not in code

### 3.2 Compose, Don't Build
Every WEATHER component already exists somewhere in VETKA. WEATHER = wiring:
- **Browser** → VETKA Tauri shell (phases 136-147)
- **Chat** → MCC/VETKA chat panels
- **Keys** → unified_key_manager (agent phonebook)
- **Orchestration** → localgays harness + MCC playground
- **Playwright** → existing E2E infrastructure
- **TaskBoard** → MCC sidebar (add filters)

### 3.3 Local-First
- Local model (Qwen via LiteRT/Ollama) = primary orchestrator
- Free AI services (Gemini/Kimi/Grok web UI) = execution layer
- No API keys needed for web UI — sessions via browser cookies
- All data stays local (SQLite TaskBoard, cookie profiles)

---

## 4. Session Management

```
data/browser_sessions/
├── gemini_account_1/
│   ├── cookies.json
│   ├── local_storage.json
│   └── last_active: timestamp
├── kimi_account_1/
│   └── ...
└── ...
```

- Sessions saved every 5 minutes
- Max lifetime: 4 hours
- Auto-restore on restart
- Session profiles = Playwright `userDataDir` (persistent contexts)
- Rotation: round-robin + LRU eviction (evict after 1h idle)

---

## 5. Captcha Handling

### Detection
- Monitor for `.g-recaptcha`, `.h-captcha`, `[data-sitekey]`, `#turnstile-widget`
- Check page title/content for "verify you're human"

### Response
1. **Notify:** macOS notification (`osascript`)
2. **Pause:** Auto-pause browser slot
3. **Rotate:** Move task to next available account
4. **Resume:** User solves → script continues

### Prevention
- Session persistence (save/restore cookies)
- Human-like timing (2-5s random delays)
- Rate limiting (10 req/hour per account)
- User-Agent rotation

---

## 6. Code Extraction Pipeline

```
AI Response → DOM Parser → Code Block → Syntax Check → Security Scan → Git
     │              │            │            │              │
     └── Fallback: OCR (Tesseract) if DOM fails
```

| Method | Accuracy | When |
|--------|----------|------|
| DOM Parsing | 98% | Primary — `<pre>`, `<code>`, markdown blocks |
| OCR (Tesseract) | 92% | Fallback — screenshot when DOM fails |
| Vision Model | 75% | Experimental — screenshot-to-code |

Validation: `ast.parse` (Python), `tsc --noEmit` (TS), `node --check` (JS), Bandit (security)

---

## 7. Scalability

| Metric | Value |
|--------|-------|
| Max browser instances | 6 |
| RAM per instance | ~200MB |
| Total RAM | ~1.2GB |
| Parallel tasks | 3 |
| Sessions per service | 10 accounts |
| Tasks/day (estimate) | 50-100 |

---

## 8. Integration Points

| System | Connection | Protocol |
|--------|-----------|----------|
| TaskBoard | MCP tools + Gateway API | HTTP REST |
| Git | Direct | subprocess |
| AI Services | Playwright | Browser automation |
| Local Model | localgays / Ollama | HTTP / subprocess |
| User | macOS notifications + MCC UI | osascript + SSE |

---

## 9. Research References

- **Grok Research:** `docs/201ph_WEATHERE/weather_vetka-grok_research.md`
  - browser-use (2.5k stars) — 80% ready, but we compose from existing instead
  - Captcha/rate-limit/session patterns with success rates
  - Tauri + Playwright integration options
- **Polaris Experience:** `docs/190_ph_CUT_WORKFLOW_ARCH/feedback/EXPERIENCE_POLARIS_2026-03-31.md`
  - Key insight: "Start with universal approach, not separate adapters"
- **RECON:** `docs/201ph_WEATHERE/RECON_WEATHER_BROWSER_2026-03-31.md`
  - Tauri browser audit — 40% coverage, 60% needs new work

---

## 10. Conservation Status

**Status:** PARKED
**Date:** 2026-04-02
**Reason:** CUT MVP takes priority. WEATHER is critical but not blocking.
**When to return:** After CUT MVP gate (MERGE POINT 4: Save + Render + Export)
**What's ready now:**
- ✅ Browser shell (VETKA Tauri phases 136-147)
- ✅ Code extractor
- ✅ Playwright infrastructure (E2E tests)
- ✅ Agent phonebook (unified_key_manager)
- ✅ Chat panels (MCC/VETKA)
- ✅ TaskBoard sidebar (MCC — needs filters)
- 🔄 localgays harness (in progress)

**What needs building (when we return):**
- Glue layer: TaskBoard → localgays → Playwright → AI
- Browser session pool + multi-account rotation
- TaskBoard sidebar filters (project, agent)
- WEATHER UI integration in VETKA browser

---

*WEATHER: Web Execution & Adaptive Task Heuristic Environment Router*
*Composed from existing VETKA components — not built from scratch*
