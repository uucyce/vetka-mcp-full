# VETKA Team Architecture (Phase 35+)

## Current State (After Phase 32.9)

### Active Agent Files (23 files)

```
src/agents/
├── __init__.py              # Exports: BaseAgent, VETKA*Agent, aliases
├── base_agent.py            # Abstract base class
├── agentic_tools.py         # Tool definitions for agents
├── tools.py                 # Tool registry and permissions
│
├── # CORE AGENTS (used in workflows)
├── vetka_pm.py              # PM Agent - planning
├── vetka_dev.py             # Dev Agent - coding
├── vetka_qa.py              # QA Agent - testing
├── vetka_architect.py       # Architect Agent - design
├── hostess_agent.py         # Entry point, routing
├── streaming_agent.py       # WebSocket streaming wrapper
│
├── # EVALUATION & ROUTING
├── eval_agent.py            # Response evaluation (7 imports!)
├── classifier_agent.py      # Task complexity classification
├── arc_solver_agent.py      # ARC puzzle solver
│
├── # LEARNER SYSTEM (6 files)
├── base_learner.py          # Abstract learner
├── learner_factory.py       # Factory pattern
├── learner_initializer.py   # Initialization logic
├── smart_learner.py         # Main learner implementation
├── pixtral_learner.py       # Pixtral model learner
├── qwen_learner.py          # Qwen model learner
│
├── # STUDENT SYSTEM
├── student_level_system.py  # Level progression
├── student_portfolio.py     # Student tracking
│
├── # ENHANCEMENT
├── hope_enhancer.py         # HOPE enhancement
├── embeddings_projector.py  # Embeddings visualization
│
└── role_prompts.py          # System prompts for roles
```

### Deleted Files (Phase 32.9)
- `pm_agent_enhanced.py` - Duplicate
- `dev_agent_enhanced.py` - Duplicate
- `vetka_ops.py` - Placeholder (aliased to PM)
- `vetka_visual.py` - Placeholder (aliased to PM)
- `learner_agent.py` - Superseded by factory
- `learner_agent_init.py` - Superseded by factory

---

## Future Architecture (Phase 35+)

### Concept: Teams as Group Chats

Instead of fixed workflows, agents form dynamic teams:
- Teams are like group chats with assigned roles
- Any agent can be added/removed dynamically
- Teams have a shared context and memory
- Multiple teams can work in parallel

### Proposed Structure

```
src/agents/
├── __init__.py
│
├── base/
│   ├── base_agent.py         # Abstract base class
│   ├── agent_registry.py     # Global agent registry
│   └── capabilities.py       # Agent capability definitions
│
├── core/
│   ├── hostess_agent.py      # Entry point, team dispatcher
│   ├── pm_agent.py           # Planning & task breakdown
│   ├── dev_agent.py          # Code implementation
│   ├── qa_agent.py           # Testing & validation
│   ├── architect_agent.py    # System design
│   └── eval_agent.py         # Quality evaluation
│
├── specialist/
│   ├── arc_solver.py         # ARC puzzles
│   ├── classifier.py         # Task classification
│   └── learner.py            # Consolidated learner
│
├── tools/
│   ├── registry.py           # Tool registry
│   ├── executor.py           # Safe execution
│   └── builtin/              # Built-in tools
│       ├── code_tools.py
│       ├── file_tools.py
│       └── search_tools.py
│
├── teams/                     # NEW!
│   ├── team_manager.py       # Team lifecycle
│   ├── team_config.py        # Team configuration
│   ├── team_memory.py        # Shared team context
│   └── presets/
│       ├── code_team.py      # PM + Dev + QA
│       ├── research_team.py  # Analyst + Researcher
│       ├── debug_team.py     # Dev + QA + Debugger
│       └── review_team.py    # Architect + QA
│
├── streaming/
│   └── stream_wrapper.py     # WebSocket streaming
│
└── prompts/
    ├── system_prompts.py     # Base system prompts
    └── role_prompts.py       # Role-specific prompts
```

### Team Configuration Example

```python
# teams/presets/code_team.py

class CodeTeam(BaseTeam):
    """Standard development team: PM → Architect → Dev → QA"""

    members = [
        TeamMember(role="pm", agent=PMAgent, lead=True),
        TeamMember(role="architect", agent=ArchitectAgent),
        TeamMember(role="dev", agent=DevAgent),
        TeamMember(role="qa", agent=QAAgent),
    ]

    workflow = [
        Step("pm", action="plan"),
        Step("architect", action="design"),
        Step("dev", action="implement"),
        Step("qa", action="validate"),
        Step("pm", action="approve"),
    ]

    shared_context = True
    parallel_enabled = True
```

### Team Manager API

```python
# Usage example
from src.agents.teams import TeamManager, CodeTeam

manager = TeamManager()

# Create team from preset
team = manager.create_team(CodeTeam, task="Add user authentication")

# Or create custom team
team = manager.create_team(
    members=["pm", "dev", "security_expert"],
    task="Security audit"
)

# Execute
result = await team.execute()

# Add member mid-execution
team.add_member("qa")

# Team chat
team.send_message("Let's focus on the API endpoints", from_member="pm")
```

---

## Migration Plan

### Phase 35: Team Foundation
1. Create `teams/` directory structure
2. Implement `BaseTeam` and `TeamManager`
3. Create `CodeTeam` preset
4. Migrate existing workflow to use teams

### Phase 36: Specialist Consolidation
1. Merge 6 learner files → 1 consolidated learner
2. Move `arc_solver` and `classifier` to `specialist/`
3. Consolidate `tools.py` and `agentic_tools.py`

### Phase 37: Dynamic Teams
1. Implement dynamic member addition/removal
2. Add team memory and shared context
3. Create team chat interface
4. Add parallel team execution

### Phase 38: Tool System Refactor
1. Move tools to `agents/tools/`
2. Implement tool registry
3. Add capability-based tool permissions
4. Create built-in tool library

---

## Consolidation Opportunities

### Learner System (6 → 1)
Current files:
- `base_learner.py`
- `learner_factory.py`
- `learner_initializer.py`
- `smart_learner.py`
- `pixtral_learner.py`
- `qwen_learner.py`

Proposed: Single `learner.py` with:
- `BaseLearner` class
- `LearnerFactory.create(model_type)` method
- Model-specific adapters as internal classes

### Tool Files (2 → 1)
Current:
- `tools.py` - Registry and permissions
- `agentic_tools.py` - Tool definitions

Proposed: Merge into `tools/registry.py`

### Student System (2 → 1)
Current:
- `student_level_system.py`
- `student_portfolio.py`

Proposed: Single `student/` subdirectory or consolidated file

---

## Notes

- Keep `hostess_agent.py` as entry point
- `eval_agent.py` is critical (7 imports) - don't change
- `streaming_agent.py` is WebSocket wrapper - keep separate
- `role_prompts.py` should move to `prompts/` directory

**End of Architecture Plan**
