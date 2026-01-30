# HOSTESS LOCAL MODEL SCENARIOS - QUICK REFERENCE
## The 7 Scenarios at a Glance

**Phase**: 80.50+
**Date**: 2026-01-23
**Audience**: Developers, Architects, DevOps

---

## THE 7 SCENARIOS (One-Liners)

| # | Scenario | Trigger | Action | Benefit | Time | Cost |
|---|----------|---------|--------|---------|------|------|
| 1 | Chat Summarization | User leaves chat | Extract summary + keywords | Faster context retrieval | 2-5s | Free |
| 2 | Link Discovery | File change | Find semantic connections between code | Better knowledge graph | 5-10s | Free |
| 3 | Context Preprocessing | Before API call | Extract relevant code + classify question | Save 30-50 tokens/call | 1-2s | Free |
| 4 | Message Routing | Message in group | Decide: Hostess/PM/Dev/QA | Smarter agent selection | 1s | Free |
| 5 | Memory Compression | Daily + history growth | Compress old chat, keep essence | Reduce history by 60-80% | 3-5s | Free |
| 6 | Metadata Generation | File created/modified | Generate title, tags, purpose | Better semantic indexing | 1-2s | Free |
| 7 | Code Review | User submits code | Quick check for obvious bugs | Fast feedback, saves tokens | 1-2s | Free |

**Total Time**: All run in background (non-blocking)
**Total Cost**: $0 (local Qwen 0.5B-2B)
**Total Benefit**: ~150K tokens/month saved (~$2-3 at scale)

---

## WHICH SCENARIOS FIRST?

### Phase 80.51 (Week 1) - START HERE:
- **Scenario 3**: Context Preprocessing (highest token savings)
- **Scenario 4**: Message Routing (best UX improvement)
- **Scenario 7**: Code Review (fast feedback)

### Phase 80.52 (Week 2):
- **Scenario 1**: Chat Summarization (quality of life)
- **Scenario 6**: Metadata Generation (search improvement)

### Phase 80.53 (Week 3):
- **Scenario 2**: Link Discovery (nice to have)
- **Scenario 5**: Memory Compression (future scalability)

---

## THE CODE (40-50 lines each)

### Scenario 3: Context Preprocessing
```python
# Before calling expensive Claude/GPT-4:
context_task = asyncio.create_task(
    hostess_prepare_context(user_message)
)

# Claude receives optimized context instead of raw message
response = await call_expensive_model(enriched_message)
```

### Scenario 4: Message Routing
```python
# Decide who should respond:
routing = await hostess_route_message(message_text)
target_agent = routing['agent']  # "PM", "Dev", "QA", or "Hostess"

# Route to correct agent
response = await orchestrator.call_agent(message, agent_name=target_agent)
```

### Scenario 7: Code Review
```python
# Quick feedback before full review:
quick_review = await hostess_quick_code_review(code, language='python')

if quick_review['critical']:
    return quick_review  # Show critical issues immediately
else:
    full_review = await dev_agent.review(code)  # Full review if needed
```

---

## INTEGRATION (3 Steps)

### Step 1: Add Infrastructure
```bash
# Copy these files:
cp examples/hostess_background_tasks.py src/orchestration/
cp examples/hostess_utils.py src/agents/
cp examples/hostess_scenarios.py src/orchestration/
cp examples/hostess_routes.py src/api/routes/
```

### Step 2: Modify main.py
```python
# In lifespan():
from src.orchestration.hostess_background_tasks import get_hostess_queue
queue = get_hostess_queue()
app.state.hostess_queue = queue

# In routes:
from src.api.routes.hostess_routes import router as hostess_router
app.include_router(hostess_router)
```

### Step 3: Use in Your Code
```python
# Schedule a background task
task_id = await schedule_hostess_task(
    "summary_123",
    hostess_summarize_chat(messages),
    timeout=2.0
)

# Get result (non-blocking)
result = await wait_for_hostess_task(task_id, timeout=2.0)
```

---

## MONITORING

### Health Check
```bash
curl http://localhost:5001/api/hostess/stats
```

### Expected Output
```json
{
  "stats": {
    "total": 234,
    "completed": 231,
    "errors": 2,
    "timeouts": 1,
    "avg_time_ms": 197,
    "error_rate": 0.0086
  },
  "active_tasks": 2
}
```

### What's Good?
- Error rate < 1%
- Avg time < 500ms
- Timeouts < 5%
- Active tasks < max_concurrent

---

## ARCHITECTURE

```
┌─ User Action (Socket.IO) ─┐
│        (No blocking)        │
└────────────┬────────────────┘
             │
      ┌──────┴──────┐
      │              │
   IMMEDIATE    BACKGROUND
  (User sees)   (Hostess)
      │              │
   Response      Task 1-7
                     │
              Qwen 0.5B (Ollama)
                     │
              1-2s complete
              ~100 tokens
              $0 cost
```

---

## FEATURE FLAGS

### Enable Individual Scenarios
```python
# config/hostess_config.py
SCENARIOS_ENABLED = {
    'chat_summarization': True,
    'link_discovery': False,  # Disable for now
    'context_preprocessing': True,
    'message_routing': True,
    'memory_compression': False,  # Phase 80.53
    'metadata_generation': True,
    'code_review': True
}
```

### Runtime Disable
```python
# If errors spike
HOSTESS_CONFIG['enabled'] = False

# Or specific scenario
HOSTESS_CONFIG['scenarios']['context_preprocessing'] = False
```

---

## EXPECTED METRICS (Production)

### Performance
- **Chat summary**: 2-5 seconds, 50-100 tokens
- **Link discovery**: 5-10 seconds, 200-300 tokens
- **Context prep**: 1-2 seconds, 50-80 tokens
- **Message routing**: 1 second, 30-50 tokens
- **Memory compression**: 3-5 seconds, 100-150 tokens
- **Metadata generation**: 1-2 seconds, 40-60 tokens
- **Code review**: 1-2 seconds, 80-120 tokens

### Cost Savings
- Scenario 3 alone saves 2000 tokens/day
- Total: ~5000-6000 tokens/day
- Monthly: ~150,000 tokens (~$2-3 at typical rates)

### User Experience
- UI never blocks on Hostess tasks (all async)
- Smart routing reduces model confusion
- Code review feedback in <2 seconds
- Chat summaries appear instantly

---

## COMMON ISSUES

### Problem: Tasks timing out
**Solution**: Increase timeout in config
```python
'timeout': 5.0  # Was 3.0
```

### Problem: Qwen model not found
**Solution**: Download model
```bash
ollama pull qwen:0.5b
ollama list  # Verify
```

### Problem: High error rate
**Solution**: Check Ollama health
```bash
curl http://localhost:11434/api/tags
```

### Problem: Too many concurrent tasks
**Solution**: Reduce max_concurrent or increase timeout
```python
'max_concurrent': 10  # Was 5
```

---

## TESTING CHECKLIST

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Start Ollama: `ollama serve`
- [ ] Verify model: `curl http://localhost:11434/api/tags | grep qwen`
- [ ] Run unit tests: `pytest tests/test_hostess_background.py -v`
- [ ] Run integration tests: `pytest tests/test_hostess_integration.py -v`
- [ ] Check stats endpoint: `curl http://localhost:5001/api/hostess/stats`
- [ ] Load test: `pytest tests/test_hostess_load.py -v --workers=10`
- [ ] Monitor for 1 hour: Watch `/api/hostess/stats` in production

---

## FILES YOU NEED

### New Files (Copy from examples/)
```
src/orchestration/hostess_background_tasks.py  (250 lines)
src/agents/hostess_utils.py                    (150 lines)
src/orchestration/hostess_scenarios.py         (200 lines)
src/api/routes/hostess_routes.py               (50 lines)
tests/test_hostess_background.py               (150 lines)
```

### Modified Files
```
main.py                          (~20 lines added in lifespan)
config/hostess_config.py         (~50 lines new file)
```

### Documentation
```
HOSTESS_LOCAL_SCENARIOS.md       (Research + full specs)
HOSTESS_IMPLEMENTATION_GUIDE.md  (Ready-to-deploy code)
HOSTESS_SCENARIOS_INDEX.md       (Navigation guide)
HOSTESS_QUICK_REFERENCE.md       (This file)
```

---

## ROLLBACK

If needed, disable all Hostess tasks:

```python
# main.py
app.state.hostess_queue = None  # Disable

# Or specific scenario
HOSTESS_CONFIG['scenarios']['context_preprocessing'] = False
```

No data corruption, no side effects.

---

## SUCCESS CRITERIA

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Error rate | < 1% | TBD | |
| Avg time | < 500ms | TBD | |
| UI blocking | 0ms | TBD | |
| Token savings | 150K/month | TBD | |
| Cost savings | ~$2-3/month | TBD | |
| User satisfaction | +20% | TBD | |

---

## ONE-PAGER FOR DECISION MAKERS

**What**: Use local Qwen model to handle 7 types of routine AI tasks in background

**Why**:
- Never blocks UI (all async)
- Saves 150K tokens/month (~$2-3)
- Smarter message routing
- Faster feedback
- $0 additional cost

**When**: Phase 80.51 (start) → 80.53 (complete)

**How**:
- Implement infrastructure (~30 min)
- Add 3 high-value scenarios (~2 hours)
- Test & deploy (~2 hours)

**Cost**: ~5-10 engineering hours + zero dollars

**Benefit**: Better UX + $2-3/month saved + smarter routing

**Risk**: Low - all gracefully degrade if Hostess unavailable

---

## GETTING STARTED NOW

1. **Read**: HOSTESS_LOCAL_SCENARIOS.md (30 min)
2. **Review**: HOSTESS_IMPLEMENTATION_GUIDE.md (30 min)
3. **Decide**: Which scenarios first?
4. **Plan**: 3-week rollout (Phase 80.51-53)
5. **Start**: Phase 80.51 with infrastructure

---

## REFERENCES

- Full scenarios: See HOSTESS_LOCAL_SCENARIOS.md
- Implementation code: See HOSTESS_IMPLEMENTATION_GUIDE.md
- Navigation: See HOSTESS_SCENARIOS_INDEX.md
- Questions: Contact architecture team

---

**Status**: READY FOR IMPLEMENTATION
**Next Step**: Phase 80.51 kickoff
**Confidence**: HIGH (all code provided, tested approach)

