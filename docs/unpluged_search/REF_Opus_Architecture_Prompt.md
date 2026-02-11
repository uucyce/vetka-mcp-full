# Architecture Design Request: Chat vs Artifacts in VETKA

## Context

VETKA is a multi-agent AI workspace where agents (PM, Dev, QA, Architect, Researcher, Hostess) collaborate in group chats. Users can select models for each agent (OpenAI, Anthropic, OpenRouter, Ollama).

**Current Problem:**
Agents respond in chat with code blocks, but there's no clear separation between:
1. **Chat messages** - discussion, planning, explanations
2. **Artifacts** - actual code files that should appear on the VETKA tree (3D visualization)

When Dev writes code in chat, it's just markdown - not a real file. We need agents to understand when to use `create_artifact()` tool to generate actual files.

## Current Infrastructure

### Agent Tools Available (src/agents/tools.py)
```python
class CreateArtifactTool:
    """Creates a code artifact and emits to VETKA tree"""
    async def execute(name, content, artifact_type, language, metadata):
        # Saves to data/artifacts/{name}
        # Emits 'artifact_tree_node' socket event for tree visualization
```

### Role Prompts (src/agents/role_prompts.py)
Each agent has a system prompt defining:
- Their role (PM plans, Dev codes, QA reviews)
- Available tools
- Output format

### Socket Events
- `artifact_tree_node` - adds node to VETKA 3D tree
- `group_stream_*` - streaming chat messages

## Design Questions

1. **When should Dev use chat vs artifact?**
   - Chat: Explaining approach, discussing options, showing snippets
   - Artifact: Complete, working code files ready for use

2. **What triggers artifact creation?**
   - User explicitly asks for "create file", "write to disk"
   - Task completion where deliverable is code
   - PM's acceptance criteria met

3. **How do artifacts relate to VETKA tree?**
   - Artifacts should become nodes in the 3D knowledge graph
   - Parent-child relationships (e.g., module → files)
   - Metadata: language, creation date, agent author

4. **Chain flow with artifacts:**
   - PM: "Tasks for Dev: Create UserService class"
   - Dev: [chat] "I'll create the service..." + [artifact] creates `user_service.py`
   - QA: [chat] "Reviewing the artifact..." references the file

5. **What metadata should artifacts have?**
   - Creator agent
   - Related task/conversation
   - Dependencies
   - Version/iteration

## Proposed Solution Options

### Option A: Explicit Tool Usage
Dev must explicitly call `create_artifact()` when creating real code.
- Pro: Clear separation, agent decides
- Con: Agent might forget, inconsistent

### Option B: Code Block Markers
Use special markers like `[ARTIFACT:filename.py]` in chat
- Pro: Easy to implement
- Con: Parsing complexity, false positives

### Option C: Two-Phase Response
1. Chat response with explanation
2. Separate artifact emission
- Pro: Clean separation
- Con: More complex flow

### Option D: PM Directive
PM explicitly specifies "create as artifact" in task
- Pro: Clear chain of command
- Con: Extra step for PM

## Current Agent Prompts (Relevant Sections)

### Dev Agent
```
## YOUR TOOLS (Phase 17-L)
- create_artifact(name, content, type, language): Create code artifacts for UI
- write_code_file(path, content): Write/update files

## WORKFLOW WITH TOOLS
1. read_code_file() to see existing code
2. Write your changes
3. validate_syntax() before write_code_file()
4. create_artifact() for user visibility
```

### Architect Agent
```
## YOUR TEAM (use @mentions to delegate)
- @Dev — Implementation, coding, file creation, bug fixes
```

## What We Need

1. **Clear guidelines** for when agents should create artifacts vs chat
2. **Prompt updates** to make agents artifact-aware
3. **Flow diagram** showing chat → artifact → tree pipeline
4. **Metadata schema** for artifacts on VETKA tree

## Questions for Architect/Opus

1. Should artifacts be created automatically when Dev writes complete code blocks?
2. How should artifacts reference their source conversation?
3. Should QA review trigger artifact versioning?
4. How do artifacts connect to the VETKA spatial tree (parent nodes, categories)?
5. Should Hostess be able to navigate to artifacts via camera_focus?

---

**Please provide:**
1. Recommended architecture for chat/artifact separation
2. Updated prompt sections for Dev, QA, Architect
3. Artifact metadata schema
4. Socket event flow for artifact creation
5. Integration with VETKA tree visualization
