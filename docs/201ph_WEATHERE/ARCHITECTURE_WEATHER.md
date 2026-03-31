# WEATHER — Web Execution & Adaptive Task Heuristic Environment Router

**Phase:** 201
**Date:** 2026-03-31
**Status:** Architecture document — implementation in progress

### Acronym Breakdown

| Letter | Word | Meaning |
|--------|------|---------|
| **W** | Web | Browser-based automation (Playwright/Chromium) |
| **E** | Execution | Runs tasks: navigate, click, type, extract |
| **A** | Adaptive | Responds to captcha, rate limits, UI changes |
| **T** | Task | Driven by TaskBoard — claim → execute → submit |
| **H** | Heuristic | Smart selectors, pattern matching, fallbacks |
| **E** | Environment | Multi-service: Gemini, Kimi, Grok, Perplexity, Mistral |
| **R** | Router | Routes tasks to the right browser/account/adapter |

---

## 1. Overview

WEATHER is the browser automation layer of VETKA. It connects the TaskBoard to free-tier AI chat services (Gemini, Kimi, Grok, Perplexity, Mistral) via Playwright/Chromium automation.

**Why WEATHER:** Agents operate "in the weather" — navigating dynamic web conditions (captcha, rate limits, UI changes, session expiry). The system adapts to conditions like weather.

```
TaskBoard → WEATHER Orchestrator → Playwright → AI Service → Code extraction → Git
```

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      WEATHER Layer                           │
│                                                              │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────┐  │
│  │ Orchestrator│───▶│Browser Manager│───▶│Service Adapters│  │
│  │  (proxy.py) │    │  (manager.py) │    │  (gemini/kimi) │  │
│  └──────┬──────┘    └──────┬───────┘    └───────┬────────┘  │
│         │                  │                     │            │
│  ┌──────▼──────────────────▼─────────────────────▼──────┐    │
│  │              Code Extractor                           │    │
│  │         (DOM parsing + OCR + validation)              │    │
│  └──────────────────────┬───────────────────────────────┘    │
│                         │                                     │
│                  git commit → push → need_qa                  │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Components

### 3.1 Orchestrator (`src/services/browser_agent_proxy.py`)
- Polls TaskBoard Gateway API for pending tasks
- Assigns tasks to available browser slots
- Routes to appropriate service adapter
- Handles commit + push + status update

### 3.2 Browser Manager (`src/services/browser_manager.py`)
- Launches/manages N Chromium instances
- Session persistence (cookies/localStorage)
- Health checks + memory monitoring
- Account rotation on captcha

### 3.3 Service Adapters (`src/services/adapters/`)
- `base_adapter.py` — abstract interface
- `gemini_adapter.py` — Google AI Studio
- `kimi_adapter.py` — Moonshot Kimi (TODO)
- `grok_adapter.py` — xAI Grok (TODO)
- `perplexity_adapter.py` — Perplexity (TODO)
- `mistral_adapter.py` — Mistral Le Chat (TODO)

### 3.4 Code Extractor (`src/services/code_extractor.py`)
- DOM parsing (primary) — `<pre>`, `<code>`, markdown blocks
- OCR fallback (Tesseract) — for image-rendered code
- Language detection (15+ languages)
- Syntax validation (ast.parse, tsc, node --check)
- Security checks (path traversal, injection)

---

## 4. Captcha Handling

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

## 5. Session Management

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

---

## 6. Configuration

`config/browser_agents.yaml` — account credentials, timing, rate limits, selectors.

---

## 7. Integration Points

| System | Connection | Protocol |
|--------|-----------|----------|
| TaskBoard | Gateway API | HTTP REST |
| Git | Direct | subprocess |
| AI Services | Playwright | Browser automation |
| User | macOS notifications | osascript |

---

## 8. Scalability

| Metric | Value |
|--------|-------|
| Max browser instances | 6 |
| RAM per instance | ~200MB |
| Total RAM | ~1.2GB |
| Parallel tasks | 3 |
| Sessions per service | 10 accounts |

---

## 9. File Map

| File | Status | Description |
|------|--------|-------------|
| `src/services/browser_agent_proxy.py` | ✅ | Orchestrator |
| `src/services/browser_manager.py` | ✅ | Browser lifecycle |
| `src/services/adapters/base_adapter.py` | ✅ | Abstract interface |
| `src/services/adapters/gemini_adapter.py` | ✅ | Gemini adapter |
| `src/services/adapters/kimi_adapter.py` | ❌ TODO | Kimi adapter |
| `src/services/adapters/grok_adapter.py` | ❌ TODO | Grok adapter |
| `src/services/adapters/perplexity_adapter.py` | ❌ TODO | Perplexity adapter |
| `src/services/adapters/mistral_adapter.py` | ❌ TODO | Mistral adapter |
| `src/services/code_extractor.py` | ✅ | Code extraction |
| `config/browser_agents.yaml` | ✅ | Configuration |
| `tests/test_browser_proxy_*.py` | ❌ TODO | Integration tests |

---

*WEATHER: Web Execution & Adaptive Task Heuristic Environment Router*
