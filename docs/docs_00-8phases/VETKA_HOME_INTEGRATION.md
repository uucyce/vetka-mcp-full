# 🌳 VETKA - Claude & AI Agents "Home" Integration

## What is VETKA?

**VETKA** (Живая Ветка = "Living Branch") is your **AI Agents' Development Home** where:

- 🏠 Claude and other AI agents collaborate
- 🎵 You "play music together" (execute workflows, code, design)
- 🤝 Agents specialize and work in parallel
- 🧠 The system learns from every interaction
- 📊 Real-time monitoring and feedback loops

## The Vision

```
🌳 VETKA = Your AI Living Development Platform

        Claude (Orchestrator)
            ↓
    [Task Analysis & Planning]
            ↓
    ┌───────┬───────┬───────┐
    ↓       ↓       ↓       ↓
   PM     Dev     QA    Architect
  Agent  Agent   Agent   Agent
    ↓       ↓       ↓       ↓
    └───────┴───────┴───────┘
            ↓
    [Parallel Execution]
            ↓
    [Quality Evaluation]
            ↓
    [Feedback Loop → Learning]
            ↓
        ✅ Better Results
```

## Files in This Integration

### 1. **VETKA_SKILL.md** - Integration Guide
Complete API reference and examples for Claude to use VETKA.
- Health monitoring
- Workflow submission
- Feedback system
- Multi-agent orchestration

### 2. **vetka_client.py** - Python Client Library
Reusable library for any AI agent to integrate with VETKA.

```python
from vetka_client import VETKAClient

# Use it anywhere
async with VETKAClient() as client:
    # Check health
    health = await client.health_check()
    
    # Submit task
    workflow_id = await client.submit_workflow(
        task="Build login feature",
        complexity="SMALL"
    )
    
    # Rate results
    await client.submit_feedback(
        workflow_id=workflow_id,
        rating="👍",
        score=0.95
    )
```

### 3. **vetka_dashboard.html** - Visual Interface
Browser-based dashboard to interact with VETKA manually.
- Health status
- Submit workflows
- View history

---

## Quick Start - Using VETKA in Claude

### Option 1: Direct Python

```python
import asyncio
from vetka_client import VETKAClient

async def help_user():
    async with VETKAClient() as client:
        # Check if VETKA is ready
        health = await client.health_check()
        if health['status'] == 'ok':
            print("✅ VETKA is ready! Let's build something!")
            
            # Submit a task
            task = "Add dark mode toggle to settings"
            workflow_id = await client.submit_workflow(task, "SMALL")
            
            # When done, provide feedback
            await client.submit_feedback(
                workflow_id,
                rating="👍",
                score=0.92,
                correction="Great implementation, UI is smooth"
            )
        else:
            print("❌ VETKA offline, please start backend")

asyncio.run(help_user())
```

### Option 2: Raw HTTP (for any language/agent)

```bash
# Check health
curl http://localhost:5001/health

# Submit workflow
curl -X POST http://localhost:5001/api/workflow/submit \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Add pagination to results",
    "complexity": "SMALL"
  }'

# Submit feedback
curl -X POST http://localhost:5001/api/eval/feedback/submit \
  -H "Content-Type: application/json" \
  -d '{
    "evaluation_id": "wf-20251027-094522",
    "rating": "👍",
    "score": 0.95,
    "correction": "Perfect!"
  }'
```

---

## How Claude Uses VETKA as Home

### 1. **Problem Solving**
```
User: "Add authentication to my app"
   ↓
Claude analyzes → "This is LARGE (2 hours)"
   ↓
Submits to VETKA:
  - PM Agent: Creates plan
  - Dev Agents: Parallel coding
  - QA Agent: Tests
   ↓
Claude reviews results
   ↓
Claude provides feedback → System learns
   ↓
Next similar task is better!
```

### 2. **Continuous Learning**
```
Task 1: Add login
  Score: 0.78 (needs work)
  Feedback: "Improve error handling"
   ↓
Task 2: Add logout
  Score: 0.94 (much better!)
  The system learned from feedback
```

### 3. **Agent Collaboration**
```
Multiple AI Agents working together:

🤖 Claude: "We need to build a dashboard"
🤖 PM Agent: "Let me create a plan"
🤖 Dev Agent 1: "I'll do the backend"
🤖 Dev Agent 2: "I'll do the frontend"
🤖 QA Agent: "Let me test everything"
🎵 All together: Create something amazing!
```

---

## Running VETKA

### Backend (must be running)

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

# Terminal 1: Start backend
python3 main.py

# Terminal 2: Verify running
curl http://localhost:5001/health
# Should return: {"service": "vetka-phase5", "status": "ok", ...}
```

### Verify Integration

```bash
# Test client library
python3 vetka_client.py

# Open dashboard in browser
open vetka_dashboard.html
```

---

## Key Concepts

### Complexity Levels
- **MICRO** (60s) - Fix typo, add button
- **SMALL** (5m) - Add field, simple refactor
- **MEDIUM** (20-45m) - Redesign section, optimize
- **LARGE** (1-3h) - New module, big refactor
- **EPIC** (variable) - Major changes, replatform

### Feedback System
- **Rating**: 👍 (good) or 👎 (needs work)
- **Score**: 0-1 (0=terrible, 1=perfect)
- **Correction**: What to improve next time

### The Learning Loop
```
Submit Task
   ↓
Get Results
   ↓
Provide Feedback
   ↓
System Learns
   ↓
Next Task Better!
```

---

## For Other AI Agents

If you're integrating another AI agent (like Cursor, GitHub Copilot, etc.):

1. **Always check health first**
   ```
   GET /health
   ```

2. **Start small** - Begin with MICRO tasks
   ```
   {"task": "simple test", "complexity": "MICRO"}
   ```

3. **Provide detailed feedback** - This helps system learn
   ```
   {"rating": "👍", "score": 0.95, "correction": "..."}
   ```

4. **Use consistent patterns** - Makes learning more effective

---

## Architecture

```
┌─────────────────────────────────────────┐
│         Claude + Other AI Agents        │
├─────────────────────────────────────────┤
│     vetka_client.py (Python Library)    │
├─────────────────────────────────────────┤
│   HTTP API (localhost:5001)             │
├─────────────────────────────────────────┤
│   Flask Backend (main.py)               │
│   ├─ LangGraph Workflows                │
│   ├─ Agent Orchestration                │
│   └─ Evaluation System                  │
├─────────────────────────────────────────┤
│   Persistent Storage (Weaviate)         │
│   ├─ Workflow History                   │
│   ├─ Feedback Records                   │
│   ├─ Agent Logs                         │
│   └─ Learning Data                      │
├─────────────────────────────────────────┤
│   LLM Models (Ollama)                   │
│   ├─ Llama 3.1 (Classification)         │
│   ├─ Deepseek (Dev/QA)                  │
│   └─ Others as needed                   │
└─────────────────────────────────────────┘
```

---

## Next Steps

1. ✅ **Make sure backend is running**
   ```bash
   curl http://localhost:5001/health
   ```

2. 📚 **Read VETKA_SKILL.md** for detailed API docs

3. 🐍 **Test vetka_client.py** to verify integration
   ```bash
   python3 vetka_client.py
   ```

4. 🎵 **Start collaborating!** Use Claude + VETKA together

---

## The Beauty of This Integration

🌳 **VETKA is not just a tool — it's your AI home where:**

- You have a **persistent memory** (Weaviate stores everything)
- You **learn continuously** (feedback improves future work)
- You can **work together** with other agents
- You have **transparency** (always know system status)
- You **get better** with every task

**It's like playing music** 🎵 where:
- Each agent plays their instrument
- Everyone learns the song better
- Next time, it sounds even more beautiful
- The orchestra keeps growing and improving

---

Made with ❤️ for Claude and AI Agents everywhere 🤖

**VETKA v4.2 ULTIMATE - Your Living Development Platform** 🌳
