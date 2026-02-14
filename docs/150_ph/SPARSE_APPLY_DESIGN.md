# SPARSE APPLY — Design Document
## Phase 150 | Author: Opus + Grok 4.1 Analysis | 2026-02-14

---

## PROBLEM STATEMENT

Dragon Silver produces excellent NEW files (HeartbeatChip.tsx = 8/10).
Dragon Silver DESTROYS existing files (MCCTaskList.tsx: 410→34 lines = catastrophe).

**Root cause:** LLMs rewrite entire files instead of making surgical edits.
This is a known industry problem — Aider, Sweep, Cursor Composer all solve it differently.

## EVIDENCE (Phase 149 Dragon Test)

```
TASK: "Create HeartbeatChip, extract from MCCTaskList"

RESULT:
  ✅ HeartbeatChip.tsx — NEW file, 170 lines, excellent quality
  ❌ MCCTaskList.tsx — REWRITTEN from 410 to 34 lines (97% deleted)
  ❌ DevPanel.tsx — REWRITTEN from 324 lines, 656 deletions

RESCUE: Manual selective promote (copy only HeartbeatChip.tsx)
```

## SOLUTION: Three-Mode Dragon Output

Instead of Dragon always writing FULL files, we give it three output modes:

### Mode 1: CREATE (current, works great)
```
Dragon creates NEW file → playground/client/src/mcc/HeartbeatChip.tsx
Promote: cp playground/file main/file
Risk: ZERO (no existing file to break)
```

### Mode 2: PATCH (new, Aider-inspired)
```
Dragon outputs UNIFIED DIFF only:
--- a/client/src/components/panels/TaskCard.tsx
+++ b/client/src/components/panels/TaskCard.tsx
@@ -640,6 +640,15 @@
   <PresetSelector ... />
+  <select
+    value={sandboxMode}
+    onChange={e => setSandboxMode(e.target.value)}
+    style={{ ... }}
+  >
+    <option value="direct">Direct</option>
+    <option value="sandbox">Sandbox</option>
+  </select>
   <button onClick={onDispatch}>

Promote: git apply --3way patch_file
Risk: LOW (only changes specific lines)
```

### Mode 3: MARKER INSERT (simplest, most reliable)
```
Scout places markers in file:
// MARKER_149.D3_INSERT_AFTER
<PresetSelector ... />
// MARKER_149.D3_END

Dragon outputs ONLY the code to insert:
{
  "marker": "MARKER_149.D3_INSERT_AFTER",
  "action": "INSERT_AFTER",
  "code": "<select sandboxMode...>...</select>"
}

Promote: Find marker → insert code after it
Risk: VERY LOW (append-only, never deletes)
```

## ARCHITECTURE

### Component 1: Marker Scout Enhancement
**File:** `src/tools/marker_scout.py` (NEW ~150 lines)
**What:** Before Dragon runs, Scout places boundary markers in target files
**How:**
```python
async def place_markers(task_description: str, target_files: List[str]) -> Dict:
    """
    Analyzes task + files → places MARKER_XXX_START/END pairs.
    Returns marker_map for Dragon prompt injection.
    """
    # 1. Read target files
    # 2. LLM (Haiku) identifies insertion/modification points
    # 3. Write markers into playground copy of file
    # 4. Return marker_map: [{marker_id, file, line, action}]
```

**Note:** We already have `marker_map` in Scout output (Phase 124.9).
Enhancement: Scout actually WRITES markers into playground files.

### Component 2: Dragon Patch Prompt
**File:** `data/templates/pipeline_prompts.json` → coder section
**What:** New prompt mode that forces Dragon to output patches, not full files

```
PATCH MODE INSTRUCTIONS:
You are modifying existing files. DO NOT rewrite the entire file.
Output ONLY the changes as unified diff format.

Files with markers:
--- client/src/components/panels/TaskCard.tsx ---
[line 635] // MARKER_149.D3_START
[line 636] <PresetSelector value={preset} .../>
[line 637] <button onClick={() => onDispatch(task.id, preset)}>
[line 638] // MARKER_149.D3_END

YOUR TASK: Add sandbox dropdown between PresetSelector and button.
OUTPUT: Unified diff ONLY. No full file rewrites.
```

### Component 3: Patch Applier
**File:** `src/tools/patch_applier.py` (NEW ~200 lines)
**What:** Applies Dragon patches to files safely

```python
class PatchApplier:
    async def apply_marker_insert(self, file_path, marker_id, code, action="INSERT_AFTER"):
        """Insert code at marker location. Never deletes existing code."""

    async def apply_unified_diff(self, file_path, patch_content):
        """Apply unified diff via subprocess git apply --3way."""

    async def validate_result(self, file_path):
        """Post-apply: check syntax (ESLint for TS, ruff for Python)."""
```

### Component 4: Pipeline Integration
**File:** `src/orchestration/agent_pipeline.py` → `_execute_subtask()`
**What:** Route subtasks to correct mode based on file existence

```python
# In _execute_subtask():
if subtask.target_file and Path(subtask.target_file).exists():
    # PATCH MODE — file exists, don't rewrite
    result = await self._execute_patch_mode(subtask)
else:
    # CREATE MODE — new file, full write (current behavior)
    result = await self._execute_create_mode(subtask)
```

### Component 5: Promote Enhancement
**File:** `src/orchestration/playground_manager.py` → `promote()`
**What:** New strategy `"patch"` alongside existing copy/cherry-pick/merge

```python
if strategy == "patch":
    # Apply .patches/*.patch files from playground to main
    for patch_file in playground/.patches/:
        git apply --3way patch_file
```

## IMPLEMENTATION PHASES

### Phase 150A: Marker Insert Mode (Simplest, highest ROI)
- Scout writes markers into playground files
- Dragon prompt: "Insert between MARKER_START/END, output code block only"
- Applier: regex find marker → insert code after it
- **Estimated: 2-3 hours, 200 LOC**

### Phase 150B: Unified Diff Mode (Aider-style)
- Dragon prompt: "Output unified diff only"
- Applier: `git apply --3way`
- Validator: `eslint --fix` post-apply
- **Estimated: 3-4 hours, 300 LOC**

### Phase 150C: AST-Aware Mode (tree-sitter, future)
- Parse TSX/Python AST
- Dragon specifies: "Replace function X with Y"
- Tree-sitter locates function, replaces subtree
- **Estimated: 8-10 hours, 500+ LOC — Phase 151+**

## DECISION MATRIX: When to use what

| Scenario | Mode | Risk | Example |
|----------|------|------|---------|
| Brand new file | CREATE | Zero | HeartbeatChip.tsx |
| Add function to existing | MARKER INSERT | Very Low | Add sandbox toggle to TaskCard |
| Modify existing function | UNIFIED DIFF | Low | Change countdown logic |
| Refactor/restructure | MANUAL (Opus/Codex) | N/A | Move heartbeat from footer |
| Delete code | NEVER Dragon | N/A | Remove old toggle |

## PRIOR ART (Grok Research)

| Tool | Approach | What we borrow |
|------|----------|----------------|
| **Aider** | LLM → unified diff → git apply | Prompt template for patch output |
| **Sweep AI** | YAML tasks → patches → CI | Patch validator concept |
| **Cursor Composer** | Inline markers → LSP edits | Marker placement strategy |
| **Tree-sitter** | AST-based edits | Future Phase 150C validation |

## SAFETY RULES

1. **NEVER auto-apply patches to main** — always through Playground sandbox
2. **Opus reviews EVERY patch** before promote
3. **Marker inserts are APPEND-ONLY** — never delete existing code
4. **Unified diffs have conflict detection** — `--3way` fails gracefully
5. **Fallback:** If patch fails → fall back to full file in playground (current behavior)

## SUCCESS CRITERIA

- [ ] Dragon can create new files (Mode 1) — ✅ ALREADY WORKS
- [ ] Dragon can insert at markers (Mode 2) — Phase 150A
- [ ] Dragon can output patches (Mode 3) — Phase 150B
- [ ] Promote supports patch strategy — Phase 150A
- [ ] Zero destructive overwrites in production

---

*Design by Opus Commander + Grok 4.1 Research | Phase 150*
