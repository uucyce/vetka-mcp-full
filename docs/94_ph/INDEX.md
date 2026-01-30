# Phase 94: Provider Filters & Model Duplication

## 📚 Documentation Index

### Phase 94.4: Model Duplication Investigation

#### Quick Links
- **TL;DR**: [`PHASE_94_4_SUMMARY.md`](./PHASE_94_4_SUMMARY.md) - Executive summary (5 min read)
- **Full Report**: [`PHASE_94_4_MODEL_DUPLICATION.md`](./PHASE_94_4_MODEL_DUPLICATION.md) - Complete investigation (15 min read)
- **Diagrams**: [`PHASE_94_4_DATA_FLOW_DIAGRAM.md`](./PHASE_94_4_DATA_FLOW_DIAGRAM.md) - Visual architecture (10 min read)

---

## 🎯 What is Phase 94.4?

**Goal**: Show models available from multiple sources (e.g., xAI direct + OpenRouter) as separate entries with clear badges.

**Example**:
```
Before:
- Grok 2 Latest  (ambiguous - which API?)

After:
- Grok 2 Latest (Direct)  [Direct API badge]
- Grok 2 Latest (OR)      [OpenRouter badge]
```

---

## 📖 Quick Navigation

### If you want to...

**Understand the problem** → Read [`PHASE_94_4_SUMMARY.md`](./PHASE_94_4_SUMMARY.md) (Section: Current State)

**See the solution** → Read [`PHASE_94_4_SUMMARY.md`](./PHASE_94_4_SUMMARY.md) (Section: Recommended Solution)

**Understand the architecture** → Read [`PHASE_94_4_DATA_FLOW_DIAGRAM.md`](./PHASE_94_4_DATA_FLOW_DIAGRAM.md)

**Implement it** → Read [`PHASE_94_4_MODEL_DUPLICATION.md`](./PHASE_94_4_MODEL_DUPLICATION.md) (Section: Pseudocode Solution)

**Test it** → Read [`PHASE_94_4_MODEL_DUPLICATION.md`](./PHASE_94_4_MODEL_DUPLICATION.md) (Section: Testing Checklist)

---

## 🗂️ File Structure

```
docs/94_ph/
├── INDEX.md                              ← You are here
├── PHASE_94_4_SUMMARY.md                 ← Start here (executive summary)
├── PHASE_94_4_MODEL_DUPLICATION.md       ← Full investigation report
└── PHASE_94_4_DATA_FLOW_DIAGRAM.md       ← Visual diagrams
```

---

## 🔑 Key Concepts

### Model Sources
- **Direct API**: Model called via provider's native API (OpenAI, xAI, Anthropic, Google)
- **OpenRouter**: Model called via OpenRouter proxy (unified interface)

### Dual-Source Models
Models that exist in BOTH Direct API AND OpenRouter:
- Grok (xAI direct + OpenRouter `x-ai/*`)
- GPT-4 (OpenAI direct + OpenRouter `openai/*`)
- Claude (Anthropic direct + OpenRouter `anthropic/*`)
- Gemini (Google direct + OpenRouter `google/*`)

### Provider Detection
Based on model ID prefix:
- `grok-2-latest` → xAI Direct
- `x-ai/grok-2-latest` → OpenRouter
- `gpt-4o` → OpenAI Direct
- `openai/gpt-4o` → OpenRouter

---

## 🚀 Implementation Status

### ✅ Completed
- [x] Investigation and analysis
- [x] Architecture design
- [x] Pseudocode solution
- [x] Documentation

### ⏳ Pending
- [ ] Create `ModelDuplicator` service
- [ ] Integrate into `/api/models` route
- [ ] Add frontend badges
- [ ] Testing
- [ ] Deployment

---

## 📊 Code Locations

### Backend
- **Model Registry**: `src/services/model_registry.py`
- **Provider Detection**: `src/elisya/provider_registry.py:detect_provider()`
- **API Routes**: `src/api/routes/model_routes.py`
- **Model Fetcher**: `src/elisya/model_fetcher.py`

### Frontend
- **Phone Book UI**: `client/src/components/ModelDirectory.tsx`
- **Model List**: Line 234 (`allModels` combination)
- **Filters**: Line 239-323 (`filteredModels`)
- **Badges**: Line 799-809 (proposed location)

---

## 🎓 Learning Resources

### Understand the System
1. Read `PHASE_94_4_SUMMARY.md` (5 min)
2. Look at `PHASE_94_4_DATA_FLOW_DIAGRAM.md` (visual)
3. Read provider_registry.py source (actual code)

### Implement the Feature
1. Read pseudocode in `PHASE_94_4_MODEL_DUPLICATION.md`
2. Check "Files to Modify" section
3. Follow implementation plan (Phase 1 → 2 → 3)

### Debug Issues
1. Check testing checklist in full report
2. Review edge cases section
3. Verify provider routing logic

---

## 🔗 Related Phases

- **Phase 60.5**: Dynamic model discovery (partially complete)
- **Phase 80.35**: xAI provider integration
- **Phase 93.11**: Model status tracking
- **Phase 94.0**: Provider filters in ModelDirectory

---

## 📝 Notes

- **No code changes made yet** - this is pure investigation/design phase
- All solutions are in **pseudocode** - ready for implementation
- **Backend approach recommended** over frontend duplication
- Estimated implementation time: **1-2 hours for MVP**

---

## ✉️ Questions?

See the **Edge Cases** section in `PHASE_94_4_MODEL_DUPLICATION.md` for common scenarios.

---

**Last Updated**: Phase 94.4 Investigation Complete
**Status**: Ready for Implementation
