# ARCHITECTURE: Scout + Sherpa + Verifier Chain
# Task Intelligence Pipeline for VETKA SPACE

**Phase:** 203
**Date:** 2026-04-04
**Author:** Captain Burnell (Joyce) + Commander
**Status:** Architecture draft, pending review

---

## 0. The Pulsar Metaphor

Jocelyn Bell Burnell found the pulsar because she had three things:
1. **A telescope** that pointed at the right part of the sky (Scout)
2. **Paper tape** that recorded the signal over time (Sherpa)
3. **Her own eyes** that separated signal from noise (Verifier)

Without the telescope, the tape records nothing useful.
Without the tape, you can't see patterns over time.
Without the eyes, every anomaly looks like garbage.

All three. In that order. After every observation.

---

## 1. Three Roles, One Chain

### Scout (local, synchronous, deterministic)
- **When:** At task creation (`action=add`) and task update (`action=update`)
- **What:** Finds exact code lines, injects markers into task
- **Speed:** 1-2 seconds
- **Engine:** ripgrep + ast.parse (Python) / tree-sitter (TS) — local only
- **Output:** `task.scout_context = [{file, start_line, end_line, symbol, snippet}]`
- **Status transition:** `pending` -> `scout_recon`

### Sherpa (external, asynchronous, probabilistic)
- **When:** Background loop, picks up `scout_recon` tasks
- **What:** Sends task + scout context to external AI, gets research back
- **Speed:** 1-3 minutes per task
- **Engine:** Playwright + DeepSeek/Kimi/Arena (free tier)
- **Output:** `docs/sherpa_recon/sherpa_{task_id}.md` + `task.recon_docs`
- **Status transition:** `scout_recon` -> `recon_done`
- **Key insight:** Scout's markers go INTO the prompt — AI gets exact code, not guesses

### Verifier (local, synchronous, gate)
- **When:** After EVERY status transition (middleware in TaskBoard)
- **What:** Validates the transition is legitimate, rollbacks garbage
- **Speed:** <1 second
- **Engine:** Path verification, hallucination detection, ast.parse, term overlap
- **Output:** `{accepted: bool, rollback_to: status, reason: str, confidence: float}`
- **Status transition:** Accept current or rollback to previous

---

## 2. Status Chain with Verifier Gates

```
                    ┌─── Verifier ───┐
                    │  paths exist?   │
                    │  lines valid?   │
pending ──Scout──▸ scout_recon ──────┤
   ▲                                 │ FAIL → pending
   └─────────────────────────────────┘

                    ┌─── Verifier ───────┐
                    │  hallucination <20% │
                    │  term overlap >15%  │
                    │  length >500 chars  │
scout_recon ──Sherpa──▸ recon_done ──────┤
   ▲                                     │ FAIL → scout_recon
   └─────────────────────────────────────┘  (Sherpa retries via different service)

                    ┌─── Verifier ──────────┐
                    │  files in allowed_paths │
                    │  syntax valid (ast)     │
                    │  no forbidden paths     │
recon_done ──Agent──▸ done_worktree ────────┤
   ▲                                        │ FAIL → recon_done
   └────────────────────────────────────────┘  (agent redoes work)

                    ┌─── Verifier ──────┐
                    │  tests pass?       │
                    │  no regressions?   │
done_worktree ──QA──▸ verified ─────────┤
   ▲                                    │ FAIL → needs_fix
   └────────────────────────────────────┘
```

**Every arrow has a Verifier gate. Every gate can rollback.**

---

## 3. Scout — Deep Design

### 3.1 What Scout Finds

For each task, Scout resolves `allowed_paths` + `domain` + title/description into specific code locations:

```python
@dataclass
class ScoutMarker:
    file: str           # "src/orchestration/task_board.py"
    start_line: int     # 45
    end_line: int       # 67
    symbol: str         # "class TaskBoard.update_status"
    snippet: str        # First 10 lines of the region
    relevance: float    # 0.0-1.0 (term overlap score)
```

### 3.2 How Scout Finds

```
Input: task (title, description, allowed_paths, domain, architecture_docs)

Step 1: Resolve search scope (same as improved search_codebase)
  → task_dirs from allowed_paths
  → domain_dirs from DOMAIN_PATHS mapping
  → global fallback

Step 2: Extract keywords (same as improved keyword extraction)
  → filter stop words, keep technical terms

Step 3: ripgrep with line numbers (-n) instead of just file names (-l)
  → For each match: capture file:line:content

Step 4: Expand to symbol boundaries
  → Python: ast.parse, find enclosing class/function for each line
  → TypeScript: tree-sitter (or simple regex for function/class/interface)
  → Result: start_line..end_line of the enclosing symbol

Step 5: Score by relevance
  → Count term matches in symbol name + surrounding code
  → Sort by relevance, take top 5-8 markers

Step 6: Inject into task
  → task.scout_context = [ScoutMarker, ...]
  → task.status = "scout_recon"
```

### 3.3 Integration with TaskBoard

Scout runs as a **hook** inside TaskBoard `action=add`:

```python
# In task_board_tools.py, after task creation:
if new_task.status == "pending" and new_task.allowed_paths:
    scout_result = scout.analyze(new_task)
    if scout_result.markers:
        new_task.scout_context = scout_result.markers
        new_task.status = "scout_recon"
        log.info(f"Scout: {len(scout_result.markers)} markers for {new_task.id}")
```

**Also runs on task update** — if `allowed_paths` or `description` changes, re-scout.

### 3.4 Scout Output in Task (what agents see)

```json
{
  "id": "tb_xxx",
  "title": "Fix cutignore scanning",
  "status": "scout_recon",
  "scout_context": [
    {
      "file": "src/scanners/local_scanner.py",
      "start_line": 45,
      "end_line": 67,
      "symbol": "LocalScanner.scan_directory",
      "snippet": "def scan_directory(self, root: Path):\n    ...",
      "relevance": 0.85
    },
    {
      "file": "src/scanners/base_scanner.py",
      "start_line": 12,
      "end_line": 30,
      "symbol": "BaseScanner (class)",
      "snippet": "class BaseScanner:\n    IGNORE_PATTERNS = ...",
      "relevance": 0.72
    }
  ]
}
```

### 3.5 Scout Context in Sherpa Prompt

When Sherpa picks up a `scout_recon` task, it injects scout_context directly:

```
## Pre-scouted Code Locations (VERIFIED — these files and lines EXIST)

### src/scanners/local_scanner.py:45-67 (LocalScanner.scan_directory)
```python
def scan_directory(self, root: Path):
    for entry in root.iterdir():
        if self._should_ignore(entry):
            continue
        ...
```

### src/scanners/base_scanner.py:12-30 (BaseScanner class)
```python
class BaseScanner:
    IGNORE_PATTERNS = ['.git', 'node_modules', '__pycache__']
    ...
```
```

This makes AI responses **dramatically more accurate** because:
1. AI sees real code, real function names, real line numbers
2. AI can reference specific lines instead of inventing file names
3. The "VERIFIED" label signals these are ground truth, not suggestions

---

## 4. Verifier — Deep Design

### 4.1 Verifier as TaskBoard Middleware

Verifier is NOT a separate script. It's a **hook that fires on every status transition**:

```python
class TaskVerifier:
    """Middleware gate in TaskBoard. Checks every status transition."""

    # Define what each transition requires
    TRANSITION_CHECKS = {
        ("pending", "scout_recon"): ["check_scout_markers_valid"],
        ("scout_recon", "recon_done"): ["check_hallucination", "check_term_overlap", "check_min_length"],
        ("recon_done", "claimed"): [],  # Agent can always claim
        ("claimed", "done_worktree"): ["check_files_in_allowed_paths", "check_syntax_valid"],
        ("done_worktree", "verified"): ["check_tests_pass"],
        ("done_worktree", "needs_fix"): [],  # QA can always reject
    }

    def check_transition(self, task: dict, old_status: str, new_status: str) -> VerifyResult:
        checks = self.TRANSITION_CHECKS.get((old_status, new_status), [])
        for check_name in checks:
            check_fn = getattr(self, check_name)
            result = check_fn(task)
            if not result.accepted:
                return VerifyResult(
                    accepted=False,
                    rollback_to=old_status,  # Back to where we were
                    reason=f"{check_name}: {result.reason}",
                    confidence=result.confidence,
                )
        return VerifyResult(accepted=True, rollback_to=None, reason="ok", confidence=1.0)
```

### 4.2 Check Functions

```python
def check_scout_markers_valid(self, task) -> VerifyResult:
    """Verify scout markers point to real files and valid line ranges."""
    markers = task.get("scout_context", [])
    if not markers:
        return VerifyResult(accepted=False, reason="no scout markers")
    for m in markers:
        full_path = PROJECT_ROOT / m["file"]
        if not full_path.is_file():
            return VerifyResult(accepted=False, reason=f"file not found: {m['file']}")
        line_count = len(full_path.read_text().split("\n"))
        if m["end_line"] > line_count:
            return VerifyResult(accepted=False, reason=f"line {m['end_line']} > {line_count} in {m['file']}")
    return VerifyResult(accepted=True, reason="ok")

def check_hallucination(self, task) -> VerifyResult:
    """Check recon response for hallucinated file paths."""
    # Uses detect_hallucinated_paths() from sherpa.py
    recon_docs = task.get("recon_docs", [])
    for doc_path in recon_docs:
        resolved = PROJECT_ROOT / doc_path
        if resolved.exists():
            response_text = resolved.read_text()
            result = detect_hallucinated_paths(response_text, [])
            if result["score"] < 0.5:  # More than 50% paths are fake
                return VerifyResult(accepted=False,
                    reason=f"hallucination score {result['score']:.0%} — {result['hallucinated'][:3]}")
    return VerifyResult(accepted=True, reason="ok")

def check_term_overlap(self, task) -> VerifyResult:
    """Check that recon is actually about this task."""
    # ... (uses extract_terms from PULSAR)

def check_min_length(self, task) -> VerifyResult:
    """Check recon response has minimum substance."""
    # ... (500 char minimum)

def check_files_in_allowed_paths(self, task) -> VerifyResult:
    """Check that agent only modified files in allowed_paths."""
    # ... (git diff --name-only vs allowed_paths)

def check_syntax_valid(self, task) -> VerifyResult:
    """Check modified Python/TS files parse without errors."""
    # ... (ast.parse for .py, basic check for .ts)
```

### 4.3 Rollback Behavior

When Verifier rejects a transition:

```python
# In task_board update_status:
verdict = verifier.check_transition(task, old_status, new_status)

if not verdict.accepted:
    # Rollback to previous status
    task["status"] = verdict.rollback_to
    # Add verification note so agent/Sherpa knows what failed
    task["verification_notes"] = verdict.reason
    # Increment retry counter
    task["verify_retries"] = task.get("verify_retries", 0) + 1
    # If too many retries, flag for human review
    if task["verify_retries"] >= 3:
        task["status"] = "needs_fix"
        task["verification_notes"] += " [MAX_RETRIES — needs human review]"
    log.warning(f"Verifier rejected {old_status}→{new_status} for {task['id']}: {verdict.reason}")
```

### 4.4 Verifier is Silent

Verifier never asks questions. Never creates tasks. Never sends notifications.
It just says YES or NO. If NO, it writes the reason and rolls back.
Agents see the reason in `verification_notes` and fix.
Sherpa sees the rollback and retries via different service.
Scout sees the rollback and re-analyzes with broader scope.

**Silent. Automatic. Invisible until it catches garbage.**

---

## 5. The Full Chain — Example Walkthrough

**Task: "Fix .cutignore not filtering media files"**

```
1. Commander creates task:
   action=add, title="Fix .cutignore...", allowed_paths=["src/scanners/"], domain="engine"
   Status: pending

2. Scout triggers (sync, <2s):
   → rg -n "cutignore\|ignore\|filter" src/scanners/
   → Finds: local_scanner.py:45 (scan_directory), base_scanner.py:12 (IGNORE_PATTERNS)
   → ast.parse → expands to function/class boundaries
   → Injects scout_context with 3 markers
   → Requests: pending → scout_recon

3. Verifier gate (sync, <1s):
   → check_scout_markers_valid: all 3 files exist, line ranges valid
   → ACCEPTED
   → Status: scout_recon

4. Sherpa picks up task (async, ~2min):
   → Reads scout_context → injects REAL code into prompt
   → Sends to DeepSeek with exact lines and function names
   → DeepSeek response: "Modify LocalScanner.scan_directory at line 52,
     add .cutignore glob pattern to IGNORE_PATTERNS..."
   → No hallucinated paths (AI saw real code!)
   → Saves recon doc
   → Requests: scout_recon → recon_done

5. Verifier gate (sync, <1s):
   → check_hallucination: 0/4 paths hallucinated, score=1.0
   → check_term_overlap: "cutignore", "scanner", "filter" all present
   → check_min_length: 8500 chars
   → ACCEPTED
   → Status: recon_done

6. Agent Alpha claims and implements:
   → Sees scout_context: exact files and lines to modify
   → Sees recon_doc: DeepSeek's approach + example code
   → Makes changes
   → Requests: recon_done → done_worktree

7. Verifier gate (sync, <1s):
   → check_files_in_allowed_paths: all modified files in src/scanners/
   → check_syntax_valid: ast.parse passes
   → ACCEPTED
   → Status: done_worktree

8. Delta verifies → verified → merge
```

**Compare with today (no Scout, no Verifier gates):**
- Sherpa sends "fix cutignore scanning media files" to DeepSeek
- DeepSeek invents `file_scanner.py`, `ignore_parser.py` (don't exist)
- Recon saved with 50% hallucinated paths
- Agent wastes time looking for files that don't exist
- 40% recon value instead of 90%+

---

## 6. Implementation Plan

### What exists today (Phase 202 + PULSAR improvements):
- search_codebase with domain + allowed_paths + arch_docs seed
- detect_hallucinated_paths (hallucination detector)
- Anti-hallucination prompt grounding
- FeedbackCollector + ServiceProtocol

### What needs building:

| Component | Where | Lines | Who | Depends on |
|-----------|-------|-------|-----|------------|
| **scout.py** | New file | ~200 | Polaris + Theta | Nothing |
| `ScoutMarker` dataclass | scout.py | ~20 | Theta | Nothing |
| `Scout.analyze()` — rg + ast | scout.py | ~100 | Polaris | ScoutMarker |
| `Scout.expand_to_symbol()` — ast.parse | scout.py | ~60 | Iota | Nothing |
| Scout hook in task_board_tools.py | Existing file | ~15 | Burnell | scout.py |
| **TaskVerifier** class | task_board.py or new verifier.py | ~200 | Polaris + Burnell | Nothing |
| Transition checks (6 functions) | verifier | ~150 | Theta + Iota | TaskVerifier |
| Verifier middleware in task_board | task_board_tools.py | ~20 | Burnell | TaskVerifier |
| `scout_recon` status in TaskBoard | task_board.py | ~5 | Kappa | Nothing |
| Scout context in Sherpa prompt | sherpa.py | ~20 | Burnell | Scout |
| Unit tests for Scout | tests/ | ~150 | Mistral-2 | scout.py |
| Unit tests for Verifier | tests/ | ~150 | Mistral-2 | verifier |

**Total new code:** ~500 lines across 2-3 files
**Parallel tracks:** Scout and Verifier can be built simultaneously

### Parallel execution map:
```
Track A (Scout):          Track B (Verifier):
  Theta: ScoutMarker        Polaris: TaskVerifier class
  Polaris: Scout.analyze    Theta: check functions
  Iota: expand_to_symbol    Iota: check functions
  ────────────────────      ─────────────────────────
  Burnell: hook in TB       Burnell: middleware in TB
  ────────────────────      ─────────────────────────
         ╰────── Burnell: integrate + Sherpa prompt ──────╯
                            │
                     Mistral-2: tests
                     Delta: E2E verification
```

---

## 7. New Task Status: `scout_recon`

Add to TaskBoard valid statuses:

```python
VALID_STATUSES = [
    "pending",          # Created, no context
    "scout_recon",      # Scout found code locations, ready for Sherpa or agent
    "recon_done",       # Sherpa enriched with external research
    "queued",           # In queue for agent
    "claimed",          # Agent working
    "running",          # Agent actively executing
    "done",             # Completed (non-worktree)
    "done_worktree",    # Completed in worktree, awaiting merge
    "need_qa",          # Needs QA verification
    "verified",         # QA passed
    "needs_fix",        # QA failed or Verifier rejected too many times
    "done_main",        # Merged to main
    "failed",           # Failed permanently
    "cancelled",        # Cancelled
]
```

Valid transitions with Verifier gates:
```python
VALID_TRANSITIONS = {
    "pending":       ["scout_recon", "claimed", "cancelled"],  # Scout or direct claim
    "scout_recon":   ["recon_done", "claimed", "pending"],     # Sherpa or direct claim or rollback
    "recon_done":    ["claimed", "scout_recon"],               # Agent claim or rollback
    "claimed":       ["done_worktree", "done", "recon_done"],  # Complete or rollback
    "done_worktree": ["verified", "needs_fix", "recon_done"],  # QA or rollback
    # ... existing transitions
}
```

---

## 8. MCC Integration (Future)

In MCC (Multi-Context Commander), the DAG view shows task status visually:

| Status | Color in DAG | Meaning |
|--------|-------------|---------|
| `pending` | Grey | No context, raw task |
| `scout_recon` | Blue | Code locations found, contextualized |
| `recon_done` | Green | Fully researched, ready for agent |
| `claimed` | Yellow | Agent working |
| `done_worktree` | Orange | Done, awaiting QA |
| `verified` | Bright green | QA passed |
| `needs_fix` | Red | Failed verification |

When user clicks a file in DAG → tasks linked to that file (via `scout_context.file`) highlight. Scout creates this linkage automatically.

---

## 9. Design Decisions

| Decision | Why |
|----------|-----|
| Scout is synchronous hook, not async loop | Must be instant at task creation — user shouldn't wait |
| Verifier is middleware, not separate script | Must catch EVERY transition, not just some |
| Verifier is silent (no notifications) | Noise reduction — it just works |
| Rollback to PREVIOUS status, not pending | Preserves work — don't lose recon when code fails |
| 3 retries then needs_fix | Prevent infinite loops |
| scout_recon is optional — agents can claim pending too | Not all tasks need scouting (docs, research tasks) |
| Scout runs on update too, not just add | allowed_paths might change — re-scout needed |

---

*The telescope points. The tape records. The eyes see.*
*Scout. Sherpa. Verifier.*
*Three instruments, one truth: find the signal in the noise.*
