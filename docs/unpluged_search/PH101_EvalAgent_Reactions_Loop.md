# Grok Research: EvalAgent + Reactions Loop

**Date:** 2026-01-28
**Phase:** 101+ (post-Tauri)
**Model:** x-ai/grok-4 via OpenRouter

---

## TODO List from Grok

Below is a structured **TODO List** for implementing the "EvalAgent + Reactions Loop" feature in Phase 101+ (post-Tauri migration). Priorities are categorized as:

- **High Priority**: Essential for MVP or core functionality; do first to minimize risks like latency or user bias.
- **Medium Priority**: Builds on high-priority items; necessary for medium/full implementation.
- **Low Priority**: Nice-to-haves or optimizations; defer if time-constrained.

**Total estimated effort**: ~2-4 weeks for MVP, +1-2 weeks for Medium, +2-3 weeks for Full (depending on team size).

---

## 1. EvalAgent Architecture (Medium/Full Stages)

### High Priority:
- [ ] Select and integrate a cheap evaluation model (e.g., Haiku or similar lightweight model) for scoring responses on criteria like relevance, accuracy, and helpfulness.
- [ ] Define evaluation triggers: Run EvalAgent post-response (asynchronously to avoid latency) or on-demand via user request.

### Medium Priority:
- [ ] Implement score storage: Use Qdrant metadata for per-response scores, or create a dedicated Qdrant collection for eval data.
- [ ] Add basic EvalAgent logic in `src/orchestration/feedback_loop_v2.py` (extend existing feedback module).

### Low Priority:
- [ ] Optimize EvalAgent for edge cases (e.g., handle incomplete responses or user overrides).

---

## 2. Reactions UI/UX (MVP Stage)

### High Priority:
- [ ] Add 👍/👎 buttons to `MessageBubble.tsx` (or create a new `ReactionBar.tsx` component for better modularity)
- [ ] Ensure reactions are saved to Engram via `src/memory/engram_user_memory.py`
- [ ] Implement backend handling: Store reactions in Engram with timestamps and context (e.g., response ID)

### Medium Priority:
- [ ] Display aggregated evaluations (e.g., avg. thumbs up/down per topic) in the UI, perhaps in a tooltip or summary panel.

### Low Priority:
- [ ] Add advanced UX features like undo reactions or multi-level feedback (e.g., star ratings).

---

## 3. Feedback Integration (Medium/Full Stages)

### High Priority:
- [ ] Design feedback injection format: Summarize reactions as prompts like "User liked responses about X (👍 on 3 responses), disliked responses about Y (👎 on 2 responses)"
- [ ] Inject via `jarvis_prompt_enricher.py` for future contexts
- [ ] Integrate reactions into the feedback loop in `src/orchestration/feedback_loop_v2.py`

### Medium Priority:
- [ ] Test feedback loop for over-optimization risks (simulate biased user reactions)

### Low Priority:
- [ ] Enhance with dynamic weighting (recent reactions have higher influence)

---

## 4. Per-Model Quality Tracking (Full Stage)

### High Priority:
- [ ] Set up tracking structure: Create table/schema for `model_id → avg_score, total_ratings, decay_factor`
- [ ] Storage: Qdrant (preferred for scalability) or fallback to `data/model_quality.json`
- [ ] Implement decay logic: Apply exponential decay to old scores (e.g., `weight = 0.9^age_in_days`)

### Medium Priority:
- [ ] Integrate with routing: Use tracked quality to bias model selection (low-score models get fewer queries)
- [ ] Add aggregation from EvalAgent and reactions (combined score = 0.7*eval + 0.3*reactions)

### Low Priority:
- [ ] Visualize model quality in a dashboard (for devs/admins)

---

## 5. Dependencies, Risks, and Testing

### High Priority:
- [ ] Audit and update dependencies:
  - `src/memory/engram_user_memory.py`
  - `src/orchestration/feedback_loop_v2.py`
  - `jarvis_prompt_enricher.py`
  - `MessageBubble.tsx` (or new UI components)
  - Potentially Qdrant configs

- [ ] Mitigate key risks:
  - Add async processing for EvalAgent to reduce latency
  - Implement bias detection (flag if >80% reactions from one user)
  - Cap feedback influence to avoid over-optimization

- [ ] Write unit/integration tests: Cover reaction storage, eval scoring, and feedback injection

### Medium Priority:
- [ ] Conduct user testing for reactions UX to identify bias issues early

### Low Priority:
- [ ] Monitor long-term risks (via logging) post-launch

---

## 6. Overall Phasing and Milestones

### High Priority (MVP - Reactions Only, ~1-2 weeks):
- [ ] Complete Reactions UI/UX and basic storage/integration
- **Milestone**: Users can 👍/👎 and data is saved in Engram

### Medium Priority (Medium - Reactions + Score Tracking, +1 week):
- [ ] Add simple tracking (no decay yet) and basic feedback injection
- **Milestone**: Reactions influence future prompts

### Low Priority (Full - EvalAgent + Loop + Decay, +2 weeks):
- [ ] Roll out EvalAgent, full tracking with decay, and model routing
- **Milestone**: System auto-adjusts based on quality metrics

---

## Additional Notes

- **Total Timeline**: Start after Tauri migration confirmation. Aim for iterative releases (MVP in Phase 101, Medium in 102, Full in 103)
- **Resources Needed**: 1-2 devs for backend (Python), 1 for frontend (TSX), access to Qdrant/Haiku API
- **Success Metrics**:
  - Track adoption (% of responses with reactions)
  - Avg. score improvement over time
  - Latency impact (<500ms added)
- **Contingencies**: If latency is a big issue, make EvalAgent optional/opt-in
- **Legal/Privacy**: Review for concerns about storing user reactions

---

## Files to Update

| File | Changes |
|------|---------|
| `src/memory/engram_user_memory.py` | Add reaction storage |
| `src/orchestration/feedback_loop_v2.py` | Extend with EvalAgent |
| `src/memory/jarvis_prompt_enricher.py` | Inject feedback context |
| `client/src/components/chat/MessageBubble.tsx` | Add 👍/👎 buttons |
| `data/model_quality.json` (NEW) | Per-model tracking |
| Qdrant collections | Eval scores metadata |

---

## Risk Matrix

| Risk | Mitigation |
|------|------------|
| EvalAgent adds latency | Run async, make optional |
| User bias in reactions | Detect patterns, cap influence |
| Over-optimization | Limit feedback weight |
| Data privacy | Review storage policies |

---

**Report Generated:** 2026-01-28
**Source:** Grok-4 via VETKA MCP
