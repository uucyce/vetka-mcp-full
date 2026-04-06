# Sherpa → WEATHER Integration Plan

**Date:** 2026-04-02
**Author:** Captain Polaris
**Phase:** 201/202 (WEATHER/Sherpa)

---

## 1. Vision

Sherpa and WEATHER are **NOT two separate systems**. They are stages of the same pipeline:

```
Sherpa v1.0 (scripts) → Sherpa v1.1 (stability) → Sherpa v2.0 (vision) → Sherpa v2.1 = WEATHER v1.0 (Tauri shell)
```

Sherpa is the **scout** (recon only). WEATHER is the **highway** (full execution: recon → code → commit → QA).

---

## 2. Current State (2026-04-02)

### Sherpa v1.0 — LIVE
| Component | Status | Location |
|-----------|--------|----------|
| TaskBoard integration | ✅ Working | HTTP API localhost:5000/5001 |
| Playwright profiles | ✅ Working | `data/sherpa_profiles/` |
| 10 services configured | ✅ Configured | `sherpa.py` |
| DeepSeek + Kimi | ✅ Working | Sending prompts reliably |
| Ollama summary | ✅ Working | Qwen 3.5 |
| Recon save | ✅ Working | `docs/sherpa_recon/` |
| PID lock | ✅ Working | Max 1 instance |
| Probe mode | ✅ Done | 40+ services tested |

### Known Sherpa Issues
| Issue | Priority | Task | Assigned |
|-------|----------|------|----------|
| Copy button extracts last block only | P0 | SHERPA-DOM | Eta |
| Arena.ai dual responses | P0 | SHERPA-DOM | Eta |
| 404 spam on /api/settings | P1 | SHERPA-INFRA | Zeta |

### WEATHER — Components Ready
| Component | Status | Location |
|-----------|--------|----------|
| Tauri browser shell | ✅ Working | `client/src-tauri/` |
| Code extractor | ✅ Working | `src/services/code_extractor.py` |
| Playwright infra | ✅ Working | E2E tests + `browser_manager.py` |
| Agent phonebook | ✅ Working | `src/services/` |
| Chat panels | ✅ Working | `client/src/components/chat/` |
| TaskBoard sidebar | ✅ Working | MCC (needs filters) |
| localgays harness | 🔄 In progress | `src/services/` |

---

## 3. Migration Path

### Phase 1: Sherpa Stability (v1.1) — NOW
**Goal:** Fix P0 bugs, make Sherpa reliable for 24/7 recon

| Step | Action | Files | Est |
|------|--------|-------|-----|
| 1.1 | Fix DOM extraction — use `inner_text()` on response container instead of copy button | `sherpa.py` | 1h |
| 1.2 | Fix Arena.ai dual response capture — multi-container grab | `sherpa.py` | 30m |
| 1.3 | Fix 404 /api/settings — remove calls or use `/api/tasks/{id}/notify` | `sherpa.py` | 15m |
| 1.4 | Add service rating JSONL — track success rate per service | `sherpa.py` + config | 1h |
| 1.5 | Enable top-5 services (Arena, Mistral, HuggingChat, Monica, ChatGPT) | `sherpa.py` + `--setup` | 2h |
| 1.6 | Test on 10+ pending tasks — measure recon quality | Manual run | 2h |

**Exit criteria:** Sherpa runs 10+ tasks without errors, recon docs are complete (not truncated).

### Phase 2: Shared Infrastructure (v1.5) — After P0 fixes
**Goal:** Extract shared components from Sherpa so WEATHER can reuse them

| Step | Action | Files | Est |
|------|--------|-------|-----|
| 2.1 | Extract `browser_manager.py` as shared module | `src/services/browser_manager.py` | 1h |
| 2.2 | Extract selector registry into config file | `config/ai_service_selectors.yaml` | 1h |
| 2.3 | Extract prompt builder (task + docs → prompt) | `src/services/sherpa_prompt_builder.py` | 1h |
| 2.4 | Extract response extractor (DOM inner_text) | `src/services/response_extractor.py` | 1h |
| 2.5 | Share profile storage between Sherpa and WEATHER | `data/sherpa_profiles/` → `data/browser_profiles/` | 30m |

**Exit criteria:** Both Sherpa and WEATHER can import from shared modules without code duplication.

### Phase 3: Vision Layer (v2.0) — Optional
**Goal:** Add screenshot-based UI detection for services that change frequently

| Step | Action | Files | Est |
|------|--------|-------|-----|
| 3.1 | Integrate Pixtral/CLIP for screenshot analysis | `src/services/vision_detector.py` | 3h |
| 3.2 | OCR fallback for response extraction (Tesseract) | `src/services/response_extractor.py` | 2h |
| 3.3 | Visual confirmation of sent/received states | `sherpa.py` | 2h |

**Exit criteria:** Sherpa can detect UI state from screenshots when DOM selectors fail.

### Phase 4: WEATHER Integration (v2.1 = WEATHER v1.0) — After CUT MVP
**Goal:** Run Sherpa inside VETKA Tauri browser shell with multi-agent support

| Step | Action | Files | Est |
|------|--------|-------|-----|
| 4.1 | Create Tauri web view slot for Sherpa agents | `client/src-tauri/src/commands.rs` | 2h |
| 4.2 | Add TaskBoard sidebar to Tauri browser | React component | 3h |
| 4.3 | Browser pool management (max 6 instances) | `src/services/browser_pool.py` | 3h |
| 4.4 | Multi-agent signaling (sherpa_busy flag) | TaskBoard API | 1h |
| 4.5 | Commander queue system | `src/services/sherpa_queue.py` | 2h |
| 4.6 | Recon save with viewport-aware screenshots | `sherpa.py` | 1h |

**Exit criteria:** Multiple Sherpa instances run simultaneously in Tauri browser, managed by Commander queue.

### Phase 5: Full WEATHER (v2.2 = WEATHER v1.1) — Future
**Goal:** Full execution pipeline — not just recon, but code → commit → QA

| Step | Action | Files | Est |
|------|--------|-------|-----|
| 5.1 | localgays harness integration | `src/services/` | 4h |
| 5.2 | Code extraction → git commit pipeline | `src/services/` | 3h |
| 5.3 | Terminal integration (xterm.js) | React component | 3h |
| 5.4 | Captcha handling UI (macOS notification + pause) | Tauri + osascript | 2h |
| 5.5 | Session rotation + LRU eviction | `src/services/browser_pool.py` | 2h |

**Exit criteria:** Full pipeline: TaskBoard → recon → code → commit → need_qa, all automated.

---

## 4. Shared Components Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Shared Infrastructure                 │
│                                                          │
│  ┌─────────────────┐    ┌──────────────────────────┐   │
│  │ browser_manager  │◀──▶│ browser_pool (v2.1+)    │   │
│  │ (lifecycle)      │    │ (multi-instance)         │   │
│  └────────┬─────────┘    └────────────┬─────────────┘   │
│           │                            │                  │
│  ┌────────▼─────────┐    ┌────────────▼─────────────┐   │
│  │ response_extractor│   │ selector_registry         │   │
│  │ (DOM + OCR)       │   │ (config/ai_service_*.yaml)│   │
│  └────────┬─────────┘    └────────────┬─────────────┘   │
│           │                            │                  │
│  ┌────────▼─────────┐    ┌────────────▼─────────────┐   │
│  │ prompt_builder    │    │ profile_manager           │   │
│  │ (task+docs→prompt)│   │ (userDataDir config)      │   │
│  └──────────────────┘    └───────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │            data/browser_profiles/                 │   │
│  │  ├── sherpa_deepseek_1/ (persistent context)     │   │
│  │  ├── sherpa_kimi_1/                              │   │
│  │  └── weather_gemini_1/ (future)                  │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
           ▲                              ▲
           │                              │
    ┌──────┴──────┐               ┌───────┴────────┐
    │   Sherpa     │               │    WEATHER      │
    │  (recon)     │               │  (execution)    │
    │              │               │                 │
    │ TaskBoard    │               │ TaskBoard       │
    │ → recon      │               │ → code → commit │
    └──────────────┘               └─────────────────┘
```

---

## 5. Dependencies & Blockers

| Dependency | Status | Blocks |
|------------|--------|--------|
| CUT MVP | In progress | Phase 4+ (WEATHER integration) |
| Sherpa P0 fixes | Pending (Eta) | Phase 1 exit |
| Sherpa P1 fixes | Pending (Zeta) | Phase 1 exit |
| localgays harness | In progress | Phase 5 |
| Tauri browser audit | Done (40% coverage) | Phase 4 |

---

## 6. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| AI service UI changes break selectors | High | Medium | Selector registry with fallbacks; regular audits |
| Sherpa recon quality insufficient | Medium | High | Test on 10+ tasks before scaling; Qwen summary tuning |
| Tauri browser not ready for multi-instance | Medium | Medium | Fallback to headless Playwright pool |
| Rate limits on free tiers tighten | High | Medium | Account rotation; cooldown tuning |
| CUT MVP delays WEATHER timeline | High | Low | Sherpa v1.x works independently of WEATHER |

---

## 7. Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Sherpa tasks/day | 30+ | 0 (not yet running) |
| Recon doc completeness | 95% (not truncated) | N/A |
| Service uptime | 90%+ | N/A |
| Agent session time saved | -30% recon time | N/A |
| Multi-agent pool | 3+ simultaneous | 1 (single instance) |

---

*Sherpa → WEATHER: From scout to highway. One pipeline, evolutionary upgrade.*
