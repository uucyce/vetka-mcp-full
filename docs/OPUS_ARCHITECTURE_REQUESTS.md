# Architecture Research Requests for Claude Opus / Grok

## Context
VETKA - AI multi-agent workspace with 3D tree visualization. Agents collaborate in group chats, creating artifacts. Current state: Phase 57.8.3 complete.

---

## REQUEST 1: Chat vs Artifacts Architecture

### Problem
Agents respond in chat with code blocks (markdown), but this is NOT real code:
- Chat = discussion, explanations, plans
- Artifacts = actual files on VETKA tree (3D nodes)

Dev agent writes `\`\`\`python` blocks in chat, but they're not artifacts.

### Questions
1. When should agents create artifacts vs chat responses?
2. Should code blocks in chat auto-convert to artifacts?
3. How to teach agents the difference?

### Current Tools
```python
# Agent can create artifacts:
create_artifact(name, content, type, language)
# Emits 'artifact_tree_node' to 3D tree
```

### Desired Flow
```
User: "Create a calculator"
Architect: "I'll design this..." (chat)
           @Dev please implement...
Dev: "Creating calculator.py..." (chat intro)
     [CREATES ARTIFACT: calculator.py] ← appears on tree
     @QA please review
QA: Reviews artifact, scores it (chat)
```

---

## REQUEST 2: Task Nodes from Agent Responses

### Observation
Agent responses have clear structure:
```
## Analysis (intro - stays in chat)

## Tasks
**Task 1:** @Dev implement X  ← should be NODE
**Task 2:** @QA test Y        ← should be NODE

## Acceptance Criteria...
```

### Desired Behavior
1. Parse agent response for task sections
2. Create separate node for each task
3. Node becomes workspace for assigned agent
4. Agent "enters" node to work, reports back to chat

### Questions
1. How to parse structured tasks from markdown?
2. What's the node structure for a task?
3. How does agent "work inside" a node?
4. How to link task completion back to parent chat?

---

## REQUEST 3: Dynamic Group Member Discovery

### Current State
When user types `@` in group chat, popup shows hardcoded agents.
Agents don't know actual team composition.

### Desired Behavior
1. When group created → all members notified about each other
2. Agent prompts include: "Your team: @Dev (model: X), @QA (model: Y)..."
3. When new member joins → announce to group
4. @ popup shows only actual group members

### Questions
1. How to propagate participant list to agents?
2. How to announce new members in real-time?
3. Should agents have "memory" of past collaborations?

---

## REQUEST 4: Artifact-in-Chat Interaction

### Observation (from screenshot)
Chat shows agent response with code. User wants to:
1. See artifact preview in chat
2. Click to open full artifact
3. Type @ inside artifact to call agent FOR THIS ARTIFACT

### Questions
1. How should artifacts embed in chat?
2. What's the interaction model for editing artifacts?
3. How does @mention inside artifact work?

---

## REQUEST 5: Anti-Gravity & Collision Avoidance

### From Grok Research (already have)
Using Sugiyama layout with forces:
- Y-axis: layers by depth
- X-axis: spread within layer
- Z-axis: rotation for branch viewing
- Forces: repulsion, spring, gravity

### Questions
1. How to prevent overlapping nodes when tree grows?
2. How to animate smooth transitions during updates?
3. How to handle 100+ nodes without performance issues?

---

## Technical Context

### Files to Review
- `src/agents/tools.py` - CreateArtifactTool
- `src/agents/role_prompts.py` - Agent system prompts
- `src/api/handlers/group_message_handler.py` - Group chat flow
- `client/src/components/chat/MentionPopup.tsx` - @ mentions UI
- `client/src/hooks/useSocket.ts` - Socket events

### Current Agent Types
- PM, Dev, QA, Architect, Researcher, Hostess

### Socket Events
- `group_message` - chat messages
- `artifact_tree_node` - new artifact on tree
- `artifact_complete` - artifact panel update

---

## Prioritization

1. **HIGH**: Task Nodes from Agent Responses (transforms workflow)
2. **HIGH**: Chat vs Artifacts clarity (agent training)
3. **MEDIUM**: Dynamic Group Discovery (UX polish)
4. **MEDIUM**: Artifact-in-Chat Interaction (UX)
5. **LOW**: Anti-Gravity optimization (have basic solution)

---

## Expected Deliverables

From Opus/Grok:
1. Architecture diagrams for task-node flow
2. Updated agent prompts with artifact guidelines
3. Socket event schema for task nodes
4. UI wireframes for artifact-in-chat
5. Code snippets for key implementations
