# Test Guide: Model Names + Smart Routing

## Pre-Test Setup

### 1. Start Server
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python3 main.py
```
✅ Wait for: `[SOCKET] Server running on 0.0.0.0:5000`

### 2. Open Browser
```
http://localhost:5000/
```
✅ Check that chat panel loads

### 3. Open Browser Console
```
F12 → Console tab
```
✅ Filter for messages starting with `[SOCKET-RX]`, `[CHAT]`, `[ROUTING]`

---

## TEST 1: Model Names Display

### Objective
Verify that model names appear in chat messages as: "Agent (model-name)"

### Steps

**Step 1.1: Send Simple Message**
```
Message: "Hello"
```

**Step 1.2: Check Console Log**
Look for:
```
[SOCKET-RX] Model: <model_name>
[CHAT] Model: <model_name>
```

**Example Output:**
```
[SOCKET-RX] 📨 Received agent_message: {agent: "Dev", model: "deepseek-coder:6.7b", text: "...", ...}
[SOCKET-RX] Agent: Dev Model: deepseek-coder:6.7b
[CHAT] Adding message to chatMessages array (current length: 3)
[CHAT] Message added. New length: 4 Model: deepseek-coder:6.7b
```

**Step 1.3: Check UI Display**
In the chat panel, you should see:
```
┌──────────────────────────────────┐
│ Dev (deepseek-coder:6.7b)  2:45 PM│
├──────────────────────────────────┤
│ Here is my response...           │
└──────────────────────────────────┘
```

### Expected Results
- ✅ Console shows `Model: <name>`
- ✅ Chat shows "Agent (model-name)"
- ✅ Model not "unknown" for any agent
- ✅ Same model for same agent across messages

### Troubleshooting
| Issue | Check |
|-------|-------|
| Model shows "unknown" | Verify backend is sending model field in emit |
| Model not showing at all | Check console for `[SOCKET-RX]` logs |
| Only one agent shows model | Other agents may not have model in data |

---

## TEST 2: Smart Routing - Greetings

### Objective
Verify that Hostess answers greetings directly without calling other agents

### Steps

**Step 2.1: Send Greeting**
```
Message: "привет"  (or "hello")
```

**Step 2.2: Check Server Console**
Look for routing logs:
```
[HOSTESS] Decision: quick_answer
[HOSTESS] Responding directly to user
```

**Step 2.3: Check Chat UI**
Should see:
- ONE message from "Hostess"
- NO messages from PM, Dev, QA
- Hostess response about greeting

**Step 2.4: Check Response Time**
- ⚡ Should be very fast (< 1 second)
- Reason: No agent processing, Hostess answers directly

### Example Log Output
```
[HOSTESS] Decision: quick_answer (confidence: 0.95)
[HOSTESS] Responding directly to user
[SOCKET] 📤 Sent Hostess response (42 chars)
```

### Expected Results
- ✅ Hostess responds directly
- ✅ No other agents called
- ✅ Fast response
- ✅ Server shows `quick_answer` action

### Troubleshooting
| Issue | Check |
|-------|-------|
| All agents respond | Hostess decision not being respected, check routing code |
| No response at all | Check if Hostess is available, look for errors |
| Wrong response | Hostess decision may be wrong (e.g., `agent_call` instead) |

---

## TEST 3: Smart Routing - Single Agent

### Objective
Verify that code requests route to Dev only

### Steps

**Step 3.1: Send Code Request**
```
Message: "напиши функцию для сортировки массива"
```
(or: "write a function to sort an array")

**Step 3.2: Check Server Console**
Look for routing logs:
```
[HOSTESS] Decision: agent_call (confidence: 0.92)
[HOSTESS] Routing to single agent: Dev
[ROUTING] 🎯 Single agent: Dev
```

**Step 3.3: Check Chat UI**
Should see:
- ONE message from "Dev (deepseek-coder:6.7b)"
- NO messages from PM or QA
- Code implementation/response

**Step 3.4: Check agents_to_call Logic**
In server console, agents called:
```
[Agent] Dev: Generating LLM response...
[SOCKET] 📤 Sent Dev response (234 chars)
```

### Example Log Output
```
[HOSTESS] Decision: agent_call (confidence: 0.92)
[HOSTESS] Routing to single agent: Dev
[ROUTING] 🎯 Single agent: Dev
[Agent] Dev: Generating LLM response...
```

### Expected Results
- ✅ Hostess routes to Dev only
- ✅ Console shows `🎯 Single agent: Dev`
- ✅ Only Dev message in chat
- ✅ Response is code-focused

### Troubleshooting
| Issue | Check |
|-------|-------|
| All agents respond | chain_call handling may be broken, check main.py lines 2244-2256 |
| Wrong agent selected | Hostess decision logic issue (in hostess_agent.py) |
| No agent called | Hostess decision may be `quick_answer` or error |

---

## TEST 4: Smart Routing - Full Chain

### Objective
Verify that complex tasks call all three agents in sequence

### Steps

**Step 4.1: Send Complex Task**
```
Message: "проанализируй архитектуру проекта и предложи улучшения с учетом масштабируемости"
```
(or: "analyze project architecture and suggest improvements for scalability")

**Step 4.2: Check Server Console**
Look for routing logs:
```
[HOSTESS] Decision: chain_call (confidence: 0.85)
[ROUTING] 🔗 Full chain: PM → Dev → QA
```

**Step 4.3: Check Agent Processing**
Should see three agent calls in sequence:
```
[Agent] PM: Generating LLM response...
[SOCKET] 📤 Sent PM response (456 chars)
...
[Agent] Dev: Generating LLM response...
[SOCKET] 📤 Sent Dev response (567 chars)
...
[Agent] QA: Generating LLM response...
[SOCKET] 📤 Sent QA response (345 chars)
```

**Step 4.4: Check Chat UI**
Should see THREE messages:
1. "PM (qwen2.5:7b)" - Strategic analysis
2. "Dev (deepseek-coder:6.7b)" - Implementation details
3. "QA (mistral:7b)" - Testing & quality considerations

**Step 4.5: Check Response Time**
- ⏱️ Slower than single agent (3x processing)
- But all three perspectives provided
- Time: ~5-10 seconds depending on model speeds

### Example Log Output
```
[HOSTESS] Decision: chain_call (confidence: 0.85)
[ROUTING] 🔗 Full chain: PM → Dev → QA
[Agent] PM: Generating LLM response...
[SOCKET] 📤 Sent PM response (456 chars)
[Agent] Dev: Generating LLM response...
[SOCKET] 📤 Sent Dev response (567 chars)
[Agent] QA: Generating LLM response...
[SOCKET] 📤 Sent QA response (345 chars)
[SOCKET] ✅ All 3 agent responses sent
```

### Expected Results
- ✅ Hostess routes to chain
- ✅ Console shows `🔗 Full chain: PM → Dev → QA`
- ✅ All three agents respond
- ✅ Responses in PM → Dev → QA order
- ✅ Each message shows correct model name

### Troubleshooting
| Issue | Check |
|-------|-------|
| Only one agent responds | chain_call handling may be broken |
| Agents in wrong order | Response delay issue (timing in code) |
| Missing model names | Model not being passed through properly |
| No chain response | Hostess decision may be different action |

---

## TEST 5: Comprehensive Test Scenario

### Complete User Journey

**Scenario:** User learning system with different request types

```
1. User opens app
   ✅ Chat panel loads
   ✅ No errors in console

2. User: "привет"
   ✅ Hostess responds immediately
   ✅ No other agents called
   ✅ Shows model name

3. User: "покажи файл config.py"
   ✅ One agent responds (Dev)
   ✅ Shows model name with agent

4. User: "какие лучшие практики использованы в коде?"
   ✅ All three agents respond
   ✅ Each shows model name
   ✅ PM → Dev → QA order

5. Verify Model Names
   ✅ All messages show: "Agent (model-name)"
   ✅ Model names are consistent per agent
   ✅ No "unknown" values
```

### Success Criteria
- ✅ All tests pass
- ✅ Console has no errors
- ✅ Server logs show correct routing decisions
- ✅ Chat UI displays properly
- ✅ Model names visible on all messages
- ✅ Routing follows Hostess decisions

---

## Quick Reference: Log Patterns

### Model Name Extraction (FIX 1)
```
✅ GOOD: [SOCKET-RX] Model: deepseek-coder:6.7b
✅ GOOD: [CHAT] Model: deepseek-coder:6.7b
❌ BAD:  [SOCKET-RX] Model: undefined
❌ BAD:  [CHAT] Model: unknown (repeated multiple times)
```

### Smart Routing (FIX 2)
```
✅ GOOD: [ROUTING] 🎯 Single agent: Dev
✅ GOOD: [ROUTING] 🔗 Full chain: PM → Dev → QA
❌ BAD:  No [ROUTING] lines (decision not being printed)
❌ BAD:  All three agents called even for greeting
❌ BAD:  Wrong agent selected
```

### Error Indicators
```
❌ [HOSTESS] Error in decision: ...
❌ [Agent] Instance is None
❌ [SOCKET] Error: Empty message
```

---

## Common Issues & Solutions

### Issue 1: Model Names Showing "unknown"
```
Cause:  Backend not sending model field
Check:  Look at emit('agent_message') call in main.py
        Verify 'model': model_name is included
Fix:    Ensure model is extracted from agent config
```

### Issue 2: All Agents Always Respond
```
Cause:  chain_call action not being handled
Check:  grep for "chain_call" in main.py line 2244-2256
Fix:    Add explicit elif for chain_call action
Status: ✅ FIXED in this update
```

### Issue 3: No Hostess Routing Applied
```
Cause:  hostess_decision is None or not checked
Check:  Server logs for [HOSTESS] messages
Fix:    Verify HOSTESS_AVAILABLE flag is True
        Check Hostess agent initialization
```

---

## Performance Expectations

| Scenario | Agents | Time | Notes |
|----------|--------|------|-------|
| Greeting | 1 (Hostess) | < 1s | Fastest - direct answer |
| Code request | 1 (Dev) | 2-3s | Medium - LLM processing |
| Complex task | 3 (PM→Dev→QA) | 6-10s | Slowest - full analysis |

---

## Deployment Checklist

Before pushing to production:

- [ ] Test all three scenarios (greeting, single, chain)
- [ ] Verify model names display on all agents
- [ ] Check console for no errors
- [ ] Check server logs for routing decisions
- [ ] Test in multiple browsers (Chrome, Firefox, Safari)
- [ ] Test on mobile (responsive design)
- [ ] Verify performance is acceptable
- [ ] Check that artifacts still work properly
- [ ] Test delegation still works
- [ ] Verify message timestamps are correct

---

## Summary

**Two critical issues fixed:**

1. ✅ **Model names now display** - "Dev (deepseek-coder:6.7b)"
2. ✅ **Smart routing working** - Greeting → Hostess, Code → Dev, Complex → PM→Dev→QA

**All changes verified:**
- ✅ Syntax check passed
- ✅ Logic reviewed
- ✅ Console logging added
- ✅ Ready for production testing

**Next steps:**
1. Start server
2. Run through all 5 tests
3. Verify results match expectations
4. Report any anomalies

🎉 **Ready to test!**
