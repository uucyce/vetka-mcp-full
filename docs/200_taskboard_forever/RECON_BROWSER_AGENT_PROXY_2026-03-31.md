# RECON: Browser Agent Proxy — Universal AI Automation via Playwright

**Task:** `tb_1774968028_51219_1`
**Date:** 2026-03-31
**Phase:** 196.14
**Project:** MCC

---

## 1. Executive Summary

Goal: Connect TaskBoard to free-tier AI chat services (Gemini, Kimi, Grok, Perplexity, Mistral) via browser automation. Local Qwen orchestrates Playwright/Chromium instances, sends prompts, extracts code responses, and commits to git.

**Verdict: Feasible with moderate effort.** Existing infrastructure covers 60% of needs.

---

## 2. Existing Infrastructure Audit

### 2.1 Playwright ✅
- **Version:** 1.58.2
- **Config:** `client/playwright.config.ts`
- **Tests:** 50+ E2E specs in `client/e2e/`
- **Browsers:** Headless Chromium, 1440x900 viewport
- **Workers:** 3 parallel (configurable)
- **Global setup:** Shared Vite server pattern

### 2.2 OCR ✅
- **Tesseract:** 5.5.1 installed (`/opt/homebrew/bin/tesseract`)
- **OCR Processor:** `src/ocr/ocr_processor.py` — full pipeline with:
  - Image processing (`process_image`)
  - PDF processing (`process_pdf`)
  - Vision model fallback (optional)
  - Caching layer (`OCRCache`)
  - Rate limiting
- **Missing:** `pytesseract` Python package (but tesseract binary is available)

### 2.3 VETKA Browser (Tauri) ⚠️
- Tauri-based custom browser
- Could be used for automation but Playwright is simpler
- **Recommendation:** Use Playwright Chromium for automation, VETKA browser for manual review

### 2.4 TaskBoard Gateway API ✅
- `/api/gateway/tasks` — list, claim, complete
- Agent registration with API keys
- 6 external agents pre-registered

---

## 3. Architecture Design

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  TaskBoard  │────▶│  Qwen Orchestrator│────▶│  Playwright     │
│  (SQLite)   │◀────│  (Python script)  │◀────│  (Chromium × N) │
└─────────────┘     └────────┬─────────┘     └────────┬────────┘
                             │                        │
                      git commit              ┌───────┼───────┐
                      push → need_qa          │       │       │
                                        Gemini  Kimi  Grok  ...
                                       (free)  (free) (free)
```

### 3.1 Orchestrator (`src/services/browser_agent_proxy.py`)
- Polls TaskBoard for pending tasks
- Assigns tasks to available browser slots
- Sends prompts via Playwright
- Extracts code from responses
- Commits and pushes

### 3.2 Browser Manager (`src/services/browser_manager.py`)
- Manages N Chromium instances
- Handles login/session persistence
- Rotates accounts on captcha
- Health checks

### 3.3 Service Adapters
- `adapters/gemini_adapter.py` — Google AI Studio
- `adapters/kimi_adapter.py` — Moonshot Kimi
- `adapters/grok_adapter.py` — xAI Grok
- `adapters/perplexity_adapter.py` — Perplexity
- `adapters/mistral_adapter.py` — Mistral Le Chat

---

## 4. Captcha Handling Strategy

### 4.1 Prevention (80% of cases)
- **Session persistence:** Save cookies/localStorage between runs
- **Rate limiting:** Max 10 requests/hour per account
- **Human-like timing:** Random delays (2-5s) between actions
- **User-Agent rotation:** Realistic browser fingerprints

### 4.2 Detection + Notification
- **Detect:** Monitor for captcha elements (`.g-recaptcha`, `hcaptcha`, `turnstile`)
- **Notify:** macOS notification (`osascript -e 'display notification'`)
- **Pause:** Auto-pause browser slot, move task to next slot
- **Resume:** User solves captcha → script continues

### 4.3 Fallback
- **Account rotation:** 10 Gmail accounts per service
- **Cooldown:** 30-min pause after captcha before retrying account
- **Manual mode:** User can solve captcha in visible browser window

---

## 5. Code Extraction Strategy

### 5.1 DOM Parsing (primary)
- Extract `<pre>`, `<code>`, markdown code blocks from response
- Most reliable — no OCR needed
- Works for all services

### 5.2 OCR (fallback)
- Screenshot → Tesseract → text
- Only for services that render code as images
- Lower accuracy, slower

### 5.3 Validation
- Syntax check (Python: `ast.parse`, TS: `tsc --noEmit`)
- File path matching against `allowed_paths`
- Minimum code length check (>50 chars)

---

## 6. Scalability Analysis

| Metric | Value | Notes |
|--------|-------|-------|
| Browser instances | 6-10 | ~200MB RAM each = 1.2-2GB total |
| CPU usage | 10-20% per instance | M-series Macs handle well |
| Parallel tasks | 3-6 | Limited by free-tier rate limits |
| Session lifetime | 1-4 hours | Depends on service |
| Captcha frequency | 1 per 20-50 prompts | Varies by service |

---

## 7. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Service changes UI | High | Adapter pattern — isolate per-service selectors |
| Account ban | High | Conservative rate limits, human-like behavior |
| Captcha storms | Medium | Account rotation, user notification |
| Code extraction errors | Medium | DOM + OCR fallback, syntax validation |
| Memory leaks | Low | Periodic browser restart, memory monitoring |

---

## 8. Implementation Plan

### Phase 1: Foundation (2-3 days)
1. **BP-1.1:** Create orchestrator skeleton (`browser_agent_proxy.py`)
2. **BP-1.2:** Create browser manager (Playwright setup, session management)
3. **BP-1.3:** Create Gemini adapter (login, send prompt, extract code)
4. **BP-1.4:** Create code extractor (DOM parsing + validation)
5. **BP-1.5:** Wire up TaskBoard integration (claim → submit flow)

### Phase 2: Multi-Service (2-3 days)
6. **BP-2.1:** Kimi adapter
7. **BP-2.2:** Grok adapter
8. **BP-2.3:** Perplexity adapter
9. **BP-2.4:** Account rotation system
10. **BP-2.5:** Session persistence (cookies/localStorage)

### Phase 3: Robustness (2-3 days)
11. **BP-3.1:** Captcha detection + macOS notification
12. **BP-3.2:** OCR fallback (Tesseract integration)
13. **BP-3.3:** Error handling + retry logic
14. **BP-3.4:** Health monitoring dashboard
15. **BP-3.5:** Logging + audit trail

### Phase 4: Scale (1-2 days)
16. **BP-4.1:** Parallel browser management
17. **BP-4.2:** Rate limiting per service
18. **BP-4.3:** Task queue with priority
19. **BP-4.4:** Graceful shutdown + state recovery

---

## 9. File Plan

| File | Phase | Description |
|------|-------|-------------|
| `src/services/browser_agent_proxy.py` | 1 | Main orchestrator |
| `src/services/browser_manager.py` | 1 | Playwright browser lifecycle |
| `src/services/adapters/base_adapter.py` | 1 | Abstract adapter interface |
| `src/services/adapters/gemini_adapter.py` | 1 | Google AI Studio adapter |
| `src/services/adapters/kimi_adapter.py` | 2 | Kimi adapter |
| `src/services/adapters/grok_adapter.py` | 2 | Grok adapter |
| `src/services/adapters/perplexity_adapter.py` | 2 | Perplexity adapter |
| `src/services/code_extractor.py` | 1 | DOM + OCR code extraction |
| `src/services/captcha_handler.py` | 3 | Captcha detection + notification |
| `src/services/session_store.py` | 2 | Cookie/session persistence |
| `config/browser_agents.yaml` | 1 | Account credentials config |
| `tests/test_browser_proxy.py` | 3 | Integration tests |

---

## 10. Dependencies

| Package | Purpose | Status |
|---------|---------|--------|
| `playwright` | Browser automation | ✅ Already installed |
| `tesseract` | OCR fallback | ✅ Already installed |
| `pytesseract` | Python Tesseract wrapper | ❌ Need to install |
| `notify-py` | macOS notifications | ❌ Need to install |
| `pyyaml` | Config files | ✅ Already installed |

---

## 11. Conclusion

**Feasible.** 60% of infrastructure already exists (Playwright, Tesseract, Gateway API, TaskBoard). The main work is:
1. Building adapters for each AI service
2. Captcha handling + notification system
3. Code extraction + validation pipeline

Estimated effort: **7-11 days** for full implementation, **3-4 days** for MVP (Gemini only).
