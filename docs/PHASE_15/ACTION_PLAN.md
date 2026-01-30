# 🎯 VETKA - ACTION PLAN (what to do starting NOW)

---

## TODAY (21 December)

### ✅ ALREADY DONE:
- You sent Claude Code Tasks 1-2 (resize + Elisya socket)
- You got this comprehensive roadmap
- You understand phases 1-7

### 🔴 YOUR NEXT ACTIONS:

**Action 1.1:** Monitor Claude Code
```
Wait for Claude Code to complete:
  ✓ Task 1: Resize handle in chat panel
  ✓ Task 2: node_path + context transmission via socket

Timeline: ~2-3 hours
Check: Look for commit message or notification
```

**Action 1.2:** Prepare Grok research
```
Read file: GROK_RESEARCH_REQUESTS.md
Understand 3 requests
Copy REQUEST #1 entirely (artifact architecture)
Keep REQUEST #2, #3 ready for tomorrow
```

**Action 1.3:** Quick design decision
```
DECISION NEEDED: Where to store artifacts?

Options:
  a) /vetka_live_03/artifacts/ folder (recommended)
  b) Embedded in tree_data.json
  c) Next to source file

Recommendation: Go with (a), Grok will confirm
```

**Timeline for Today:** 30 minutes (mostly waiting for Claude Code)

---

## TOMORROW (22 December)

### PHASE 1 START: Elisya Backend Integration

**Action 2.1:** Copy code from prompts
```
File exists: CLAUDE_CODE_FINAL_CHAT_PROMPT.md (from your chat history)

Copy this code into main.py:
  ✓ Function: get_file_context_with_elisya()
  ✓ Update: handle_user_message() with Elisya call
  ✓ Update: Agent responses to include context

Total: ~40-50 lines of code (straightforward copy/paste)
```

**Action 2.2:** Test file reading
```bash
# Verify Elisya can read files
$ python3 -c "
from src.orchestration.elisya import ContextManager
cm = ContextManager()
result = cm.filter_context('path/to/file.py', 'what is this?')
print(result)
"

Expected:
  ✓ File content loaded
  ✓ Key lines extracted
  ✓ Summary generated
```

**Action 2.3:** Send REQUEST #1 to Grok
```
Send GROK_RESEARCH_REQUESTS.md REQUEST #1
Ask for:
  - Artifact JSON schema
  - Storage location strategy
  - Naming convention
  
You'll get answer in 2-4 hours
```

**Action 2.4:** Test socket integration
```html
<!-- Open browser console, run: -->
const node = document.querySelector('[data-node-path]');
socket.emit('user_message', {
  text: 'test',
  node_id: node.dataset.nodeId,
  node_path: node.dataset.nodePath,
  context: {semantic_query: 'test'}
});

Expected in console:
  [Chat] Message on src/main.py: test...
  [Elisya] Reading context for src/main.py...
  [Elisya] ✅ Got context: ...
```

**Timeline for Tomorrow:** 3-4 hours (mostly Phase 1 implementation + testing)

---

## DAY 3-4 (23-24 December)

### PHASE 2 START: Artifact Architecture Definition

**Action 3.1:** Receive Grok answer
```
✓ You'll have artifact JSON schema
✓ You'll have storage location recommended
✓ You'll have naming convention
```

**Action 3.2:** Make architecture decisions
```
Based on Grok findings, decide:
  1. Artifact JSON format (use Grok's recommendation)
  2. Storage folder: /artifacts/ or another?
  3. File naming: timestamp_uuid.json?
  4. Artifact types: code, document, media, canvas
  5. Max artifact size? (no limit or yes?)
```

**Action 3.3:** Send REQUEST #2 and #3 to Grok
```
Send both requests now (can be parallel):
  - REQUEST #2: CAM + Artifacts
  - REQUEST #3: Incremental tree update

These block Phase 6 and Phase 4, so get answers early
```

**Action 3.4:** Create artifact.py module
```python
# src/artifacts/artifact_manager.py

from dataclasses import dataclass
import uuid
from typing import Optional

@dataclass
class Artifact:
    id: str
    type: str  # 'code', 'document', 'media', 'canvas'
    content: str
    language: Optional[str]  # for code
    created_by: str
    parent_node_id: str
    tags: list
    metadata: dict
    
class ArtifactManager:
    def __init__(self, storage_path):
        self.storage_path = storage_path
        
    def create(self, artifact: Artifact) -> bool:
        """Save artifact to disk"""
        pass
        
    def get(self, artifact_id: str) -> Optional[Artifact]:
        """Load artifact from disk"""
        pass
        
    def list_by_node(self, node_id: str) -> list:
        """Get all artifacts for a node"""
        pass
        
    def validate(self, artifact: Artifact) -> bool:
        """Validate artifact JSON schema"""
        pass
```

**Timeline for Days 3-4:** 4-5 hours (decision making + module creation)

---

## WEEK 2 (25-31 December)

### PHASE 3-4: Artifact Creation & Left Panel

**Action 4.1:** Build artifact UI
```
File: src/static/artifact-panel.js

Features:
  - Socket.on('artifact_created') listener
  - Render artifact preview
  - Tabs: Preview | Editor | Media | Canvas
  - Close button

Use libraries:
  - CodeMirror (code editor)
  - pdf.js (PDF viewer)
  - Plain HTML5 <video> for media
  - HTML5 Canvas for drawing
```

**Action 4.2:** Artifact creation flow
```python
# Update main.py

@socketio.on('create_artifact')
def handle_create_artifact(data):
    """Save artifact to disk + update tree"""
    
    artifact_data = data.get('artifact')
    
    # 1. Create Artifact object
    # 2. Validate with ArtifactManager
    # 3. Save to disk
    # 4. Update tree_data.json (add leaf)
    # 5. Recalculate Sugiyama (only affected layer)
    # 6. emit('artifact_created', {artifact_id, positions})
    
    pass
```

**Action 4.3:** Test full flow
```bash
# In browser console:
socket.emit('create_artifact', {
  artifact: {
    type: 'code',
    language: 'python',
    content: 'def hello(): print("world")',
    created_by: 'Dev',
    parent_node_id: 'src_main_py',
    tags: ['example', 'function']
  }
});

Expected:
  ✓ File saved to /artifacts/
  ✓ tree_data.json updated
  ✓ Left panel shows artifact
  ✓ Tree grows (new leaf visible)
  ✓ Animation smooth (no jerk)
```

**Timeline for Week 2:** 8-10 hours

---

## WEEK 3 (1-7 January)

### PHASE 5-6: LangGraph (optional) + CAM Integration

**Action 5.1:** Receive Grok answers for CAM
```
Use findings for:
  - Branching threshold
  - Accommodation algorithm
  - Pruning criteria
  - Merging strategy
```

**Action 5.2:** Implement CAM operations
```python
# src/memory/cam_operations.py

def should_branch(artifact) -> bool:
    """Does artifact size warrant branching?"""
    return len(artifact.content) > 1000

def accommodate_tree(new_artifact) -> dict:
    """Update tree layout for new artifact"""
    # Soft repulsion stronger for new artifact
    # Animation: 500-1000ms
    return updated_positions

def prune_artifacts(node_id) -> list:
    """Remove low-quality artifacts"""
    # QA score < 0.5 → mark for deletion
    pass

def merge_artifacts(artifact_a, artifact_b) -> dict:
    """Merge similar artifacts"""
    # similarity > 0.92 → can merge
    pass
```

**Timeline for Week 3:** 6-8 hours

---

## AFTER WEEK 3: POLISH + OPTIONAL FEATURES

### Action 6.1: LangGraph (optional)
```
If you want cleaner agent workflow:
  - Install langgraph
  - Define StateGraph with PM/Dev/QA nodes
  - Add artifact creation node
  - Replace current agent routing

Timeline: 2-3 hours
Not critical, can skip for now
```

### Action 6.2: Phase 7 (KG + Artifacts)
```
In Knowledge Graph mode:
  - Artifacts become examples of concepts
  - Artifact edges = "example of X"
  - Media artifacts = visual examples

Timeline: Phase 17+, not urgent
```

---

## PARALLEL TRACKS

```
TRACK A (You + Claude Code):
  ✓ Phase 0: Claude Code tasks (now)
  ✓ Phase 1: Elisya integration (tomorrow)
  ✓ Phase 3-4: Artifact panel + flow (week 2)
  ✓ Phase 6: CAM integration (week 3)

TRACK B (Grok):
  ✓ REQUEST #1: Artifact architecture (today)
  ✓ REQUEST #2: CAM + artifacts (tomorrow)
  ✓ REQUEST #3: Tree update (tomorrow)
  └─ Results ready for Phase 2-6

Both tracks parallel = faster! 🚀
```

---

## CHECKPOINT MILESTONES

### Milestone 1 (3 days):
```
✅ Node clicks → file content loaded
✅ Chat sends file context
✅ Agents mention file content in response
```

### Milestone 2 (1 week):
```
✅ Artifact panel visible (left side)
✅ Agents can trigger artifact creation
✅ Artifact saved to disk
✅ Tree updates with new leaf
```

### Milestone 3 (2 weeks):
```
✅ Multiple artifact types working (code, media, etc)
✅ CAM operations visible (branching, pruning)
✅ Smooth tree growth without collisions
```

### Milestone 4 (3 weeks):
```
✅ Full integration: chat → artifact → tree
✅ Agents helping create knowledge
✅ System feels alive (grows naturally)
✅ Ready for Phase 7+ (KG mode)
```

---

## CRITICAL DATES

```
TODAY (21 Dec):
  └─ Decision: Artifact storage location

TOMORROW (22 Dec):
  ├─ Phase 1 code integration
  ├─ REQUEST #1-3 to Grok
  └─ Begin socket testing

By Dec 24:
  └─ Phase 1 fully working

By Dec 31:
  └─ Phase 3-4 complete (artifact flow)

By Jan 7:
  └─ Phase 6 complete (CAM integration)
  └─ Full integration ready!
```

---

## FILES TO USE

```
START HERE:
  1. VETKA_QUICK_SUMMARY.md (this explains everything)
  2. VETKA_CHAT_ARTIFACTS_CHECKLIST_ROADMAP.md (all details)

FOR IMPLEMENTATION:
  3. GROK_RESEARCH_REQUESTS.md (send to Grok)
  4. Code examples in chat history (copy/paste)

FOR PHASE-BY-PHASE:
  5. This file (ACTION_PLAN.md) ← you are here
```

---

## SUCCESS = LIVING SYSTEM

```
BEFORE:
  - Chat without context
  - No artifacts
  - Tree static

AFTER (3 weeks):
  - Chat WITH context (file-aware)
  - Artifacts appearing naturally
  - Tree GROWS when agents work
  - System helps humans create knowledge
  - CAM operations visible (intelligence)

THAT'S VETKA! 🌳
```

---

## NEXT ACTION RIGHT NOW

1. Read VETKA_QUICK_SUMMARY.md (5 min)
2. Read this file again (10 min)
3. Wait for Claude Code to finish Tasks 1-2 (check browser)
4. Prepare REQUEST #1 for Grok (copy from GROK_RESEARCH_REQUESTS.md)
5. Have coffee ☕

**By tomorrow: Phase 1 starts!**
