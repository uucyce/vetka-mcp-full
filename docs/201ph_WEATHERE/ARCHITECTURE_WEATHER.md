# WEATHER — Web Execution & Adaptive Task Heuristic Environment Router

**Phase:** 201
**Date:** 2026-03-31 (updated 2026-04-02)
**Status:** ACTIVE — Sherpa v1.0 MVP live, WEATHER = Sherpa v2.x backend

> **Status Update (2026-04-02):** Sherpa v1.0 is now operational — TaskBoard integration, Playwright profiles, 10 services configured, DeepSeek+Kimi working, Ollama summary, recon save. WEATHER is no longer parked; it is the **upgrade path for Sherpa** (v2.1: Tauri browser shell + multi-agent pool). CUT MVP still takes priority for code work, but docs/planning for Sherpa→WEATHER integration is active. — Captain Polaris

---

## 1. Overview

WEATHER is the **browser automation + local model orchestration layer** of VETKA. It connects the TaskBoard to free-tier AI chat services (Gemini, Kimi, Grok, Perplexity, Mistral) via Playwright/Chromium automation, orchestrated by local models through the localgays harness.

**Why WEATHER:** Agents operate "in the weather" — navigating dynamic web conditions (captcha, rate limits, UI changes, session expiry). The system adapts to conditions like weather.

**Key insight from Grok research (2026-04-01):** Do NOT build separate adapters or fork external solutions (browser-use). WEATHER = **compose from existing VETKA components**. ~70-95% of infrastructure already exists across phases 136-147, MCC, localgays, and the agent registry.

**Sherpa → WEATHER evolution (2026-04-02):** Sherpa v1.0 is the **pragmatic first step** — a standalone recon script using existing Playwright + Chrome. WEATHER is the **evolutionary upgrade**: Sherpa running inside VETKA's Tauri browser shell with multi-agent pool, TaskBoard sidebar, and shared browser infrastructure. See `docs/202ph_SHERPA/` for Sherpa docs and `docs/201ph_WEATHERE/SHERPA_INTEGRATION_PLAN.md` for migration path.

```
Sherpa v1.0 (NOW) → Playwright scripts + Chrome
       ↓
Sherpa v1.1 → Stability (DOM extraction, service rating)
       ↓
Sherpa v2.0 → Vision (Pixtral OCR, screenshot-based UI detection)
       ↓
Sherpa v2.1 = WEATHER v1.0 → VETKA Tauri browser shell + multi-agent pool
       ↓
WEATHER v2.x → Full browser automation platform
```

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
| **Orchestrator** | localgays harness + Sherpa | `src/services/` + `sherpa.py` | ✅ Sherpa v1.0 live, localgays in progress |
| **Playwright Pool** | Sherpa `browser_manager.py` | `src/services/browser_manager.py` | ✅ Working (persistent contexts, 10 services) |
| **Agent Phonebook** | unified_key_manager | `src/services/` | ✅ Working (provider credentials) |
| **Chat (local + API)** | MCC/VETKA chat panels | `client/src/components/chat/` | ✅ Working |
| **TaskBoard Sidebar** | MCC | MCC UI | ✅ Working (needs project/agent filters) |
| **Code Extractor** | code_extractor.py | `src/services/code_extractor.py` | ✅ Working (DOM + OCR + validation) |
| **MCC Playground** | MCC workflow env | MCC | ✅ Working (orchestration environment) |
| **Recon Engine** | Sherpa pipeline | `sherpa.py` | ✅ MVP live (DeepSeek+Kimi working) |

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
- **Sherpa Concept:** `docs/202ph_SHERPA/SHERPA_CONCEPT.md`
  - Recon engine vision, economics, pipeline design
- **Sherpa Architecture:** `docs/202ph_SHERPA/ARCHITECTURE_SHERPA.md`
  - Current state, bugs, roadmap, integration with WEATHER
- **Sherpa Probe:** `docs/202ph_SHERPA/RECON_SERVICES.md`
  - 40 AI services tested, zero bot detection, top-5 recommendations
- **Sherpa Infra:** `docs/202ph_SHERPA/RECON_SHERPA_INFRA.md`
  - Infrastructure reconnaissance, existing components
- **Integration Plan:** `docs/201ph_WEATHERE/SHERPA_INTEGRATION_PLAN.md`
  - Migration path from Sherpa scripts to WEATHER Tauri shell

---

## 10. Sherpa Integration Status

**Sherpa v1.0 — LIVE** (see `docs/202ph_SHERPA/`)

### What Sherpa Has Achieved
- ✅ TaskBoard HTTP API integration (localhost:5000/5001)
- ✅ Playwright persistent profiles (`data/sherpa_profiles/`)
- ✅ 10 services configured (DeepSeek x2, Kimi x2, Arena, Z.ai, Mistral, HuggingChat, Monica, Bolt)
- ✅ DeepSeek + Kimi working reliably for sending prompts
- ✅ Ollama/Qwen 3.5 for response summarization
- ✅ Recon save to `docs/sherpa_recon/sherpa_{task_id}.md`
- ✅ Task enrichment (recon_docs + implementation_hints)
- ✅ PID lock guard (max 1 instance)
- ✅ Probe mode tested 40+ services (zero bot detection!)

### Known Sherpa Issues (P0/P1)
- 🔴 **P0: Copy button extracts last block only** — needs DOM `inner_text()` fix (task: SHERPA-DOM, assigned Eta)
- 🔴 **P0: Arena.ai dual responses** — only captures one of two side-by-side responses (part of SHERPA-DOM)
- 🟡 **P1: 404 spam on /api/settings** — PATCH calls returning 404 (task: SHERPA-INFRA, assigned Zeta)

### Sherpa → WEATHER Migration Path
| Sherpa Version | WEATHER Version | Features | Status |
|----------------|-----------------|----------|--------|
| v1.0 (NOW) | — | Single-instance Playwright scripts | ✅ Live |
| v1.1 Stability | — | DOM extraction, service rating, profile rotation | 🔄 Next |
| v2.0 Vision | — | Pixtral OCR, screenshot-based UI detection | Planned |
| v2.1 | WEATHER v1.0 | VETKA Tauri browser shell + TaskBoard sidebar | Planned |
| v2.2 Multi-Agent | WEATHER v1.1 | Commander queue + browser pool | Planned |

### Shared Infrastructure
- `browser_manager.py` — already used by Sherpa, will be WEATHER's browser lifecycle manager
- `data/sherpa_profiles/` — Playwright persistent contexts, reusable by WEATHER
- `code_extractor.py` — shared between Sherpa (future) and WEATHER
- TaskBoard API — single source of truth for task state

### Integration Plan
See `docs/201ph_WEATHERE/SHERPA_INTEGRATION_PLAN.md` for detailed migration steps.

---

## 11. Conservation Status (Legacy)

**Status:** ACTIVE (upgraded from PARKED on 2026-04-02)
**Previous Status:** PARKED — conservation until after CUT MVP
**Date:** 2026-04-02
**Reason for original park:** CUT MVP takes priority. WEATHER is critical but not blocking.
**When to return:** After CUT MVP gate (MERGE POINT 4: Save + Render + Export)
**What's ready now:**
- ✅ Browser shell (VETKA Tauri phases 136-147)
- ✅ Code extractor
- ✅ Playwright infrastructure (E2E tests)
- ✅ Agent phonebook (unified_key_manager)
- ✅ Chat panels (MCC/VETKA)
- ✅ TaskBoard sidebar (MCC — needs filters)
- ✅ **Sherpa v1.0** — recon engine live (NEW)
- 🔄 localgays harness (in progress)

**What needs building (when we return):**
- ~~Glue layer: TaskBoard → localgays → Playwright → AI~~ ← **Sherpa already does this**
- Browser session pool + multi-account rotation (Sherpa v2.2 / WEATHER v1.1)
- TaskBoard sidebar filters (project, agent)
- WEATHER UI integration in VETKA browser (Sherpa v2.1)

---

*WEATHER: Web Execution & Adaptive Task Heuristic Environment Router*
*Composed from existing VETKA components — not built from scratch*
