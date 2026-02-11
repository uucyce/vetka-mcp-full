# Grok Research Prompt: BMAD + Autonomous Agent Loops

## Context
VETKA project — 3D knowledge graph with multi-agent pipeline (Dragon team).
We have pieces of BMAD (Build-Measure-Analyze-Decide) and RALFloop (Retry And Learn Feedback) but they're disconnected.

## Research Questions

### Q1: BMAD Best Practices
Search for: "BMAD loop agent pipeline", "Build Measure Analyze Decide AI agents", "approval workflow autonomous agents"

- How do modern multi-agent systems implement BMAD?
- What's the typical flow: agent generates → who reviews → who approves → who deploys?
- Are there good open-source examples of pipeline-integrated approval systems?
- What approval patterns work for autonomous coding agents? (auto-approve for small changes, human review for large)

### Q2: RALFloop / Self-Improving Agent Patterns
Search for: "self-improving agent loop", "retry with feedback AI", "agent auto-correction patterns"

- What are best patterns for agent self-correction loops?
- How to implement: score < threshold → retry with feedback → learn from mistakes?
- Few-shot learning from past successes — what's the optimal approach?
- How to prevent infinite retry loops? (max retries, progressive backoff, escalation)

### Q3: Multi-Client Task Protocol
Search for: "task queue multi-agent protocol", "universal task API design agents", "MCP task dispatch"

- What's the best REST API design for a universal task board that ANY client can use?
- How do systems like Linear, Asana, or Jira handle multi-agent task claiming?
- Is there a standard protocol for agent-to-agent task handoff?
- What about optimistic locking for task claims in distributed agent systems?

### Q4: Autonomous Heartbeat Patterns
Search for: "background polling agent loop", "autonomous agent wakeup pattern", "event-driven vs polling agents"

- Event-driven vs polling for autonomous agent monitoring — which is better?
- How to handle: agent crashes mid-task → restart → resume?
- What's the standard for "dead letter queue" in agent systems?
- How to prevent task storms (100 tasks queued at once)?

## Files to Check in VETKA Codebase
- `src/orchestration/agent_pipeline.py` — main pipeline, no approval integration
- `src/services/approval_service.py` — exists but disconnected
- `src/agents/eval_agent.py` — has evaluate_with_retry() but never called
- `src/orchestration/task_board.py` — TaskBoard with claim/complete
- `src/orchestration/mycelium_heartbeat.py` — heartbeat engine, no daemon

## Expected Output
1. Best practices for each question (with links)
2. Code patterns we can adapt
3. Specific recommendations for VETKA architecture
4. Priority: What to implement first for maximum autonomy gain
