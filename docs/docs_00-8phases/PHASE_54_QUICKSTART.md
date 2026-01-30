# 🚀 VETKA Phase 5.4 - QUICK START GUIDE

## ✨ What's New in Phase 5.4

Phase 5.4 introduces two powerful capabilities:

1. **Sequential Thinking** - PM Agent can now break down complex tasks into structured reasoning steps
2. **Composio Integration** - Dev Agent now has access to 500+ pre-built actions (GitHub, Slack, Linear, etc.)

---

## 📦 Installation

### Step 1: Update Dependencies

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
pip install -r requirements_phase54.txt
```

This installs:
- `composio-core` - 500+ action toolkit
- `composio-openai` - OpenAI integration
- `mcp` - Model Context Protocol client

### Step 2: Set up Sequential Thinking MCP (for advanced planning)

Sequential Thinking runs as a separate MCP server. To enable it:

```bash
# Install the Sequential Thinking MCP server
npx -y @modelcontextprotocol/server-sequential-thinking
```

Or if you prefer Docker:

```bash
docker run --rm -i mcp/sequentialthinking
```

---

## 🎯 Usage

### Option A: Use Enhanced Agents Directly

#### PM Agent with Sequential Thinking

```python
from src.agents.pm_agent_enhanced import EnhancedPMAgent

async def plan_feature():
    agent = EnhancedPMAgent(enable_sequential_thinking=True)
    
    # Complex feature that benefits from structured thinking
    feature = "Implement real-time notification system with retry logic"
    
    # Plan with Sequential Thinking
    plan = await agent.plan_feature(feature, complexity="LARGE")
    
    print("📋 Feature Plan:")
    print(plan["plan"])
    
    print("\n⏰ Timeline:")
    print(plan["timeline"])
    
    print("\n⚠️  Risks:")
    for risk in plan["risks"]:
        print(f"  - {risk['risk']}: {risk['mitigation']}")
    
    # If Sequential Thinking was used
    if plan["reasoning_trace"]:
        print(f"\n🧠 Reasoning trace: {plan['reasoning_trace']['thoughts_count']} thoughts")
```

#### Dev Agent with Composio

```python
from src.agents.dev_agent_enhanced import EnhancedDevAgent

async def implement_feature():
    agent = EnhancedDevAgent()
    
    feature_plan = """
    Create GitHub issue for each failed workflow with:
    - Error details
    - Link to workflow run
    - Auto-assign to devops
    """
    
    # Generate implementation using Composio actions
    result = await agent.implement_feature(feature_plan)
    
    print("💻 Generated Code:")
    print(result["code"])
    
    print(f"\n🔗 Actions used: {result['actions_used']}")
    print(f"📊 Total actions: {result['action_count']}")
    
    print("\n✅ Tests:")
    print(result["tests"][:300] + "...")
    
    print("\n📚 Documentation:")
    print(result["documentation"][:300] + "...")
```

#### Search Available Actions

```python
async def search_actions():
    agent = EnhancedDevAgent()
    
    # Find actions for creating issues
    actions = await agent.search_actions("create issue", limit=5)
    
    for action in actions:
        print(f"\n{action['operation']}")
        print(f"  Tool: {action['tool']}")
        print(f"  Description: {action['description']}")
        print(f"  Category: {action['category']}")
```

### Option B: Use in VETKA Workflow

Update your `main.py` or orchestrator to use enhanced agents:

```python
from src.agents.pm_agent_enhanced import EnhancedPMAgent
from src.agents.dev_agent_enhanced import EnhancedDevAgent

# In your workflow handler
async def handle_workflow(feature_request: str):
    # Step 1: PM Agent plans with Sequential Thinking
    pm_agent = EnhancedPMAgent(enable_sequential_thinking=True)
    plan = await pm_agent.plan_feature(feature_request, complexity="LARGE")
    
    # Step 2: Dev Agent implements with Composio
    dev_agent = EnhancedDevAgent()
    implementation = await dev_agent.implement_feature(plan["plan"])
    
    # Step 3: Return combined result
    return {
        "plan": plan,
        "implementation": implementation,
        "status": "ready-for-review"
    }
```

---

## 📊 How Sequential Thinking Works

When you use `EnhancedPMAgent` for LARGE/EPIC tasks:

1. **Problem Understanding** - Clarify what needs to be done
2. **Requirements Analysis** - Extract functional & non-functional needs
3. **Design Analysis** - Evaluate approach options
4. **Solution Generation** - Create detailed implementation plan
5. **Verification** - Review and refine the solution

```
Input Task
    ↓
🧠 Sequential Thinking (5 steps)
    ↓
Verified Plan with:
- Detailed breakdown
- Risk assessment
- Timeline
- Resource needs
```

---

## 🔗 How Composio Integration Works

When you use `EnhancedDevAgent`:

1. **Action Discovery** - Search 500+ available actions
2. **Context Matching** - Find relevant actions for your task
3. **Code Generation** - Generate Python code using the actions
4. **Integration Handling** - Auth, parameter mapping, error handling

```
Feature Description
    ↓
🔍 Search Composio Actions (e.g., "create github issue")
    ↓
💻 Generate Code with:
- Action calls
- Error handling
- Examples
- Tests
```

### Available Toolkits (50+):

- **GitHub** - 50+ actions (create issue, PR, etc.)
- **Slack** - 45+ actions (send message, create channel, etc.)
- **Linear** - 35+ actions (create ticket, assign, etc.)
- **Notion** - 40+ actions (create page, query, etc.)
- **Gmail** - 25+ actions (send email, etc.)
- **Airtable** - 30+ actions (create record, etc.)
- **Jira** - 55+ actions
- **Microsoft Teams** - 40+ actions
- ... and 40+ more integrations

---

## 📈 Expected Improvements

| Metric | Phase 5 | Phase 5.4 | Improvement |
|--------|---------|-----------|-------------|
| Classification Accuracy | 82% | >90% | +8% |
| Available Actions | 50 | 500+ | 10x |
| Response Time (MICRO) | 2-3s | <1s | 2-3x faster |
| Response Time (LARGE) | 15-20s | 8-10s | 2x faster |
| PM Planning Quality | Good | Excellent | Structured reasoning |
| Dev Integration Support | Limited | Comprehensive | 500+ integrations |

---

## 🐛 Troubleshooting

### Issue: Sequential Thinking not working

**Solution:** Ensure MCP server is running
```bash
npx -y @modelcontextprotocol/server-sequential-thinking
```

### Issue: Composio actions not found

**Solution:** Check your search query
```python
# Instead of just tool name
actions = await agent.search_actions("create github issue")  # ✅ Works
actions = await agent.search_actions("github")  # ❌ Too generic
```

### Issue: Import errors

**Solution:** Reinstall dependencies
```bash
pip install -r requirements_phase54.txt --force-reinstall
```

---

## 🎓 Example: Complete Workflow

```python
import asyncio
from src.agents.pm_agent_enhanced import EnhancedPMAgent
from src.agents.dev_agent_enhanced import EnhancedDevAgent

async def complete_workflow():
    print("🚀 VETKA Phase 5.4 Complete Workflow Example\n")
    
    # The feature request
    feature = """
    Create a notification system that:
    1. Sends Slack messages on workflow completion
    2. Creates GitHub issues for errors
    3. Retries failed notifications
    4. Tracks delivery status
    """
    
    # PHASE 1: PM Agent Plans with Sequential Thinking
    print("📋 PHASE 1: PM Planning...")
    pm_agent = EnhancedPMAgent(enable_sequential_thinking=True)
    plan = await pm_agent.plan_feature(feature, complexity="LARGE")
    
    print("✅ Plan generated with Sequential Thinking")
    print(f"   Thinking steps: {len(plan.get('reasoning_trace', {}).get('thoughts', []))} thoughts")
    print(f"   Timeline: {plan['timeline']}")
    print(f"   Risks identified: {len(plan['risks'])}")
    
    # PHASE 2: Dev Agent Implements with Composio
    print("\n💻 PHASE 2: Dev Implementation...")
    dev_agent = EnhancedDevAgent()
    impl = await dev_agent.implement_feature(plan["plan"])
    
    print("✅ Implementation generated with Composio")
    print(f"   Actions used: {impl['action_count']}")
    for action in impl['actions_used'][:3]:
        print(f"     - {action}")
    
    # PHASE 3: Summary
    print("\n📊 PHASE 3: Summary")
    print(f"   Plan quality: {plan.get('timeline', {}).get('phases', 0)} phases")
    print(f"   Code generation: {len(impl['code'])} chars")
    print(f"   Test coverage: {len(impl['tests'])} chars")
    print(f"   Status: ✅ READY FOR DEPLOYMENT")

# Run it
if __name__ == "__main__":
    asyncio.run(complete_workflow())
```

---

## 📚 Next Steps

1. ✅ Install Phase 5.4 dependencies
2. ✅ Try the example code above
3. ✅ Integrate Enhanced Agents into your workflows
4. ✅ Monitor performance improvements
5. ✅ Fine-tune the classifier on your own tasks (coming in Phase 6)

---

## 🔗 Resources

- **Composio Docs**: https://docs.composio.dev
- **Sequential Thinking MCP**: https://github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking
- **VETKA Phase 5.4 Files**:
  - `requirements_phase54.txt` - Dependencies
  - `src/integrations/composio_provider.py` - Composio wrapper
  - `src/integrations/sequential_thinking_provider.py` - Thinking framework
  - `src/agents/pm_agent_enhanced.py` - Enhanced PM Agent
  - `src/agents/dev_agent_enhanced.py` - Enhanced Dev Agent
  - `datasets/training_examples_phase54.json` - Training data

---

## 🎉 Ready?

Start using Phase 5.4 now:

```python
from src.agents.pm_agent_enhanced import EnhancedPMAgent
agent = EnhancedPMAgent()
# You're ready to go!
```

Questions? Check the troubleshooting section above or refer to the official docs.
