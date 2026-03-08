# PHASE 166 RECON — MCP/MCC API Favorite Key Autoplay + MYCELIUM/MCC Key Add

Date: 2026-03-08
Mode: RECON + markers (no runtime changes)

## Scope from user
1. Исследовать автопроигрывание (автовыбор) API ключа из `favorite` для вызовов моделей через MCP VETKA / MYCELIUM.
2. Добавить в MYCELIUM Balance окно ввода нового API ключа (регистрация по общим правилам core VETKA), и дать MCC такую же возможность.

---

## MARKER_166.RECON.001 — Current favorite key data flow

### Frontend favorite storage
- `client/src/store/useStore.ts`
  - `favoriteKeys: string[]` in format `"provider:key_masked"`
  - persist via `PUT /api/favorites`
  - load via `GET /api/favorites`

### Backend favorites persistence
- `src/api/routes/config_routes.py`
  - `GET /api/favorites`
  - `PUT /api/favorites`
  - storage file: `data/favorites.json`
  - also writes ENGRAM preferences (`favorite_keys`, `favorite_models`)

Conclusion:
- Favorites currently exist as persisted data and UI sort hint.
- There is **no global auto-apply favorite-on-model-call hook** for MCP `vetka_call_model` path.

---

## MARKER_166.RECON.002 — Existing preferred-key mechanism

### In key manager
- `src/utils/unified_key_manager.py`
  - `set_preferred_key(provider, key_masked)`
  - `get_preferred_key(provider)` (one-shot; clears after first use)
  - `get_key_with_rotation()` checks preferred key first.

### Where it is used now
- `src/orchestration/task_board.py` passes `selected_key` into pipeline.
- `src/orchestration/agent_pipeline.py` calls `km.set_preferred_key(...)` before pipeline run.

Conclusion:
- Mechanism exists, but currently triggered mostly by manual `selectedKey` in MCC, not by persisted `favoriteKeys` auto logic.

---

## MARKER_166.RECON.003 — Why MCP call_model misses favorite today

### Critical mismatch in provider layer
- `src/elisya/provider_registry.py`
  - `OpenAIProvider.call()` uses `km.get_active_key(ProviderType.OPENAI)`
  - `AnthropicProvider.call()` uses `km.get_active_key(ProviderType.ANTHROPIC)`
  - `GoogleProvider.call()` uses `km.get_active_key(ProviderType.GEMINI)`

`get_active_key(...)` bypasses preferred one-shot selection.

### Where preferred works
- `OpenAICompatibleProvider._get_key()` uses `km.get_key(self.provider_name)`
- This path honors preferred/favorite one-shot because `km.get_key()` delegates to `get_key_with_rotation()`.

Conclusion:
- For OpenAI/Anthropic/Gemini provider classes, favorite/preferred is effectively ignored.
- Поэтому вызов через MCP VETKA не всегда берет "звездный" ключ.

---

## MARKER_166.RECON.004 — MYCELIUM/MCC Balance and key-add capability

### Existing UI panels
- `client/src/components/panels/BalancesPanel.tsx`
- `client/src/components/mcc/MiniBalance.tsx`
- `client/src/components/mcc/KeyDropdown.tsx`

Current behavior:
- shows records, selection, favorites star.
- no inline form in Balance panel for adding new key.

### Existing backend add-key API (reusable)
- `src/api/routes/config_routes.py`
  - `POST /api/keys/add-smart` (auto-detect + save)
  - `POST /api/keys/detect`
  - `GET /api/keys`

Conclusion:
- API already exists. Missing piece is UI entry in Balance/MCC using same route.

---

## MARKER_166.RECON.005 — Narrow implementation plan (ready for GO)

### A. Favorite auto-apply for MCP/VETKA calls
1. Add helper in backend (single source):
   - Read `data/favorites.json`.
   - Pick favorite key for detected provider (`provider:key_masked`).
   - Call `km.set_preferred_key(provider, key_masked)` before provider call.
2. Integrate this helper in `llm_call_tool.py` and `llm_call_tool_async.py` before `call_model_v2`.
3. Hard fix provider path:
   - In `provider_registry.py` switch OpenAI/Anthropic/Gemini provider classes from `get_active_key(...)` to `get_key(...)`/rotation-aware path so preferred is honored.

### B. Add key-input window in MYCELIUM Balance (+ MCC)
1. Add compact "Add API key" form in `BalancesPanel.tsx`:
   - textarea/input for raw key
   - submit to `POST /api/keys/add-smart`
   - success/error inline state
2. Surface same capability in MCC:
   - Since MCC expanded Balance uses `BalancesPanel`, this auto-covers MCC.
   - Keep no new global panels/buttons rule: only extend existing Balance surface.
3. After add success:
   - refresh balances/keys
   - optionally auto-select new key row if present in records

### C. Tests (narrow)
1. Unit: favorite auto-apply helper maps provider->masked favorite correctly.
2. Unit/integration: `llm_call_tool(_async)` sets preferred key from favorites before call.
3. Regression: provider_registry OpenAI/Anthropic/Gemini honors preferred key.
4. Frontend: BalancesPanel add-key submit handler success + fail states.

---

## MARKER_166.RECON.006 — Risks and guardrails

1. Mask mismatch risk:
- Favorites use masked key format from UI; ensure same `record.mask()` format.
- Guard: strict compare + fallback to normal rotation if no match.

2. One-shot preferred semantics:
- Current preferred key clears after first consume. This is correct for "next call" behavior.
- If user expects sticky favorite, we should reapply before each call from persisted favorites.

3. Provider aliasing:
- `google` vs `gemini` aliasing must normalize consistently when matching favorite provider key.

---

## GO/NO-GO
Status: RECON complete.

Ready for `GO` to implement narrow patch set:
- favorite auto-apply in MCP call_model
- provider_registry preferred-key honor fix
- key add form in existing Balance panel (MYCELIUM + MCC)
- tests + git commit
