# SHERPA v2.0 — PULSAR Stack Architecture
# VETKA SPACE: Scout & Harvest Engine with Intelligence Layer

**Phase:** 203 (extends 202)
**Date:** 2026-04-03
**Author:** Captain Burnell (Джойс) + Commander
**Status:** Architecture approved, ready for implementation
**Codename:** PULSAR (Periodic Universal Lightweight Scout with Adaptive Reasoning)

---

## 0. WEATHER → VETKA SPACE

WEATHER (Phase 201) was designed as a separate browser project for agents.
Sherpa (Phase 202) proved the concept WITHOUT a separate browser — Playwright inside one script.

**VETKA SPACE** is the evolution: a cosmic workspace where agents interact with external AI services.
Not a browser. Not a framework. A **space** — open, infinite, agent-native.

| Old Name | New Name | Why |
|----------|----------|-----|
| WEATHER browser | VETKA SPACE | Agents don't need a browser — they need space to operate |
| Sherpa recon agent | SHERPA (unchanged) | The scout that walks the trails |
| WEATHER adapters | SPACE Protocols | Per-service behavioral configs, auto-learned |
| WEATHER profiles | SPACE Identities | Browser personas for service access |

The WEATHER worktrees (`weather-core`, `weather-mediator`, `weather-terminal`, `weather-mistral-*`) become **SPACE domain** worktrees. Same agents (Polaris, Theta, Iota, Kappa, Mistral-1/2/3), new mission.

---

## 1. Current State (v1.0 — Phase 202)

Sherpa v1.0 is a 1982-line Python script that:
- Claims pending tasks from TaskBoard
- Searches codebase with ripgrep
- Builds prompts from task context + code snippets
- Sends to free AI services via Playwright (DeepSeek, Kimi, Arena)
- Extracts responses via DOM inner_text()
- Saves recon docs to `docs/sherpa_recon/`
- Updates task with `recon_docs` + `implementation_hints`
- Logs feedback to `data/sherpa_feedback.jsonl`
- Auto-disables services after 3 consecutive failures

**What's missing (v2.0 scope):**
1. No intelligent service selection (just round-robin)
2. No rate-limit detection mid-session
3. No response quality verification
4. No Arena ethical voting
5. No retry through alternate service on failure

---

## 2. PULSAR Stack — Three New Modules

### 2.1 ServiceHealthMonitor (SHM)

**Purpose:** Replace dumb round-robin with health-aware service routing.

**Location:** Class `ServiceHealthMonitor` in `sherpa.py`, replaces `SherpaHarness.select_service()`

**Data source:** `data/sherpa_feedback.jsonl` (existing) + runtime state

**Algorithm:**
```
For each enabled service, compute health_score:
  base_reliability = success_count / total_count  (from JSONL, last 20 entries)
  recent_penalty   = -0.3 if last 3 entries are failures
  rate_limit_flag  = -1.0 if rate_limit detected in last 10 minutes
  slow_penalty     = -0.1 if avg_response_time > 120s
  cooldown_active  = -1.0 if service is in cooldown window

  health_score = base_reliability + recent_penalty + rate_limit_flag + slow_penalty + cooldown_active
  Clamp to [0.0, 1.0]

Service selection:
  1. Filter services with health_score > 0.0
  2. Sort by health_score descending
  3. Pick top service (not same as last used — anti-burst)
  4. If all scores <= 0.0 → enter RECOVERY mode:
     - Sleep 5 minutes
     - Reset cooldowns
     - Try service with highest base_reliability
```

**Rate-limit detection (runtime):**
```python
RATE_LIMIT_SIGNALS = [
    "rate limit", "too many requests", "429", "quota exceeded",
    "daily limit", "usage limit", "try again later",
    "upgrade to", "subscribe to", "out of messages",
    "лимит", "ограничение",  # Russian services
]

# Check in:
# 1. HTTP response status (429)
# 2. DOM body text after sending prompt
# 3. Response text if suspiciously short (<100 chars)
```

**Fallback chain (configurable in sherpa.yaml):**
```yaml
fallback_chain:
  - [deepseek, kimi, arena]       # Primary rotation
  - [deepseek_2, kimi_2]          # Secondary accounts
  - [huggingchat, mistral]        # Tertiary (if logged in)
recovery_sleep_seconds: 300        # 5 min when all services down
max_retries_per_task: 2            # Try 2 different services before giving up
```

**Interface:**
```python
class ServiceHealthMonitor:
    def __init__(self, feedback_path: Path, services: List[ServiceConfig])
    def select_service(self, exclude: Optional[str] = None) -> Optional[ServiceConfig]
    def report_success(self, service_name: str, chars: int, time_s: float)
    def report_failure(self, service_name: str, error_type: str)
    def report_rate_limit(self, service_name: str)
    def get_health_report(self) -> dict  # For logging/debugging
    def is_all_down(self) -> bool
```

**Complexity:** Medium
**Lines estimate:** ~150
**Dependencies:** Existing FeedbackCollector, ServiceProtocol

---

### 2.2 ArenaVoter (AV)

**Purpose:** Ethically participate in LLM Arena by voting for the better response, then using it.

**Location:** Class `ArenaVoter` in `sherpa.py`, called after response extraction for Arena service.

**Why this matters:**
- Arena.ai gives us TWO free responses per query (side-by-side blind comparison)
- Currently we grab both and leave — this is extractive, not participatory
- Voting gives Arena real evaluation data — we become a contributor, not a leech
- Better response = better recon quality

**Algorithm:**
```
Input: response_a (str), response_b (str), task (dict)

Step 1: Volume score
  vol_a = len(response_a)
  vol_b = len(response_b)
  # Normalize: 0-1 range where 1 = longer
  vol_score_a = vol_a / max(vol_a, vol_b, 1)
  vol_score_b = vol_b / max(vol_a, vol_b, 1)

Step 2: Relevance score (term overlap)
  # Extract key terms from task title + description
  task_terms = extract_terms(task["title"] + " " + task.get("description", ""))
  # Count unique term matches in each response (case-insensitive)
  rel_a = count_term_matches(response_a, task_terms) / max(len(task_terms), 1)
  rel_b = count_term_matches(response_b, task_terms) / max(len(task_terms), 1)

Step 3: Code presence score (for build/fix tasks)
  code_a = count_code_blocks(response_a)  # regex: ```...```
  code_b = count_code_blocks(response_b)
  code_score_a = min(code_a / 3, 1.0)  # Cap at 3 blocks
  code_score_b = min(code_b / 3, 1.0)

Step 4: Composite score
  weights = {volume: 0.3, relevance: 0.5, code: 0.2}
  score_a = vol_score_a * 0.3 + rel_a * 0.5 + code_score_a * 0.2
  score_b = vol_score_b * 0.3 + rel_b * 0.5 + code_score_b * 0.2

Step 5: Vote
  if abs(score_a - score_b) < 0.05:
      vote = "tie"  # Too close to call
  elif score_a > score_b:
      vote = "a"
  else:
      vote = "b"

Step 6: Click vote button in Arena UI
  # Arena has: "A is better" / "B is better" / "Tie" / "Both bad"
  click_vote_button(vote)

Return: winner_response (the response with higher score)
```

**Arena DOM structure (observed):**
```
div.chat-container
  div.response-a  (left panel)
    div.markdown-body  → response A text
  div.response-b  (right panel)
    div.markdown-body  → response B text
  div.vote-buttons
    button "A is better"
    button "B is better"
    button "Tie"
    button "Both are bad"
```

**Term extraction:**
```python
def extract_terms(text: str) -> set:
    """Extract meaningful terms from task description."""
    # Remove common stop words
    stop = {"the", "a", "an", "is", "are", "for", "to", "in", "on", "of", "and", "or", "not", "with"}
    # Split on non-alphanumeric, keep words 3+ chars
    words = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]{2,}', text.lower())
    # Prioritize: file names, function names, class names, technical terms
    return {w for w in words if w not in stop}
```

**Interface:**
```python
class ArenaVoter:
    def __init__(self)
    async def extract_dual_responses(self, page) -> Tuple[str, str]
    def score_responses(self, resp_a: str, resp_b: str, task: dict) -> Tuple[float, float, str]
    async def cast_vote(self, page, vote: str)  # "a", "b", "tie"
    async def process_arena(self, page, task: dict) -> str  # Returns winner response
```

**Complexity:** Medium
**Lines estimate:** ~120
**Dependencies:** Playwright page object, task dict

---

### 2.3 ReconVerifier (RV)

**Purpose:** Quality gate between response extraction and recon save. Catches garbage, hallucinations, and off-topic responses.

**Location:** Class `ReconVerifier` in `sherpa.py`, called after step 5 (response extraction) and before step 6 (save).

**Algorithm:**
```
Input: response (str), task (dict), service_name (str)

CHECK 1: Minimum length
  if len(response) < 500:
      return REJECT("too_short", f"{len(response)} chars < 500 minimum")

CHECK 2: Hallucination markers
  HALLUCINATION_MARKERS = [
      "I don't have access to",
      "I cannot access",
      "as an AI language model",
      "as an AI assistant",
      "I'm not able to browse",
      "I cannot browse the internet",
      "I don't have the ability to",
      "I can't view files",
      "I cannot execute code",
      "I apologize, but I cannot",
      "unfortunately, I cannot",
  ]
  for marker in HALLUCINATION_MARKERS:
      if marker.lower() in response.lower():
          # Check if it's in a quote or example (not the AI refusing)
          context = response[max(0, response.lower().index(marker.lower())-50):
                            response.lower().index(marker.lower())+len(marker)+50]
          if not is_in_code_block(context):
              return REJECT("hallucination", f"Found: '{marker}'")

CHECK 3: Term relevance
  task_terms = extract_terms(task["title"] + " " + task.get("description", ""))
  response_terms = extract_terms(response)
  overlap = task_terms & response_terms
  overlap_ratio = len(overlap) / max(len(task_terms), 1)
  if overlap_ratio < 0.15:
      return REJECT("off_topic", f"Only {len(overlap)}/{len(task_terms)} terms matched ({overlap_ratio:.0%})")

CHECK 4: Code presence for build/fix tasks
  phase_type = task.get("phase_type", "")
  code_blocks = re.findall(r'```[\s\S]*?```', response)
  if phase_type in ("build", "fix") and len(code_blocks) == 0:
      return WARN("no_code", "Build/fix task but no code blocks in response")
      # WARN doesn't reject, just logs

CHECK 5: Repetition detection
  # Some services loop when confused
  paragraphs = [p.strip() for p in response.split('\n\n') if len(p.strip()) > 50]
  if len(paragraphs) > 3:
      unique = set(paragraphs)
      if len(unique) < len(paragraphs) * 0.6:
          return REJECT("repetitive", f"{len(paragraphs) - len(unique)} repeated paragraphs")

All checks passed → return ACCEPT(confidence_score)
```

**Confidence scoring:**
```
confidence = 1.0
- response < 2000 chars: -0.2
- no code blocks for build: -0.1
- overlap_ratio < 0.3: -0.1
- response > 10000 chars: +0.1 (bonus for thorough response)

Final confidence in [0.0, 1.0]
Saved to feedback JSONL for learning
```

**Retry logic (integrated into sherpa_loop):**
```python
MAX_RETRIES = 2

for attempt in range(MAX_RETRIES + 1):
    service = health_monitor.select_service(exclude=last_failed_service)
    response = await browser.send_prompt(service.name, prompt)
    verdict = verifier.verify(response, task, service.name)

    if verdict.accepted:
        health_monitor.report_success(service.name, len(response), elapsed)
        break
    else:
        health_monitor.report_failure(service.name, verdict.reason)
        log.warning(f"Attempt {attempt+1}: {verdict.reason} from {service.name}")
        last_failed_service = service.name

if not verdict.accepted:
    # All retries exhausted — save what we have with low confidence
    log.error(f"All {MAX_RETRIES+1} attempts failed for {task_id}")
    # Still save partial recon with confidence=0.0 marker
```

**Interface:**
```python
@dataclass
class VerifyResult:
    accepted: bool
    reason: str       # "ok" | "too_short" | "hallucination" | "off_topic" | "repetitive"
    confidence: float  # 0.0 - 1.0
    details: str       # Human-readable explanation

class ReconVerifier:
    HALLUCINATION_MARKERS: List[str]
    MIN_CHARS: int = 500
    MIN_TERM_OVERLAP: float = 0.15

    def verify(self, response: str, task: dict, service_name: str) -> VerifyResult
    def extract_terms(self, text: str) -> set
    def is_in_code_block(self, text: str) -> bool
```

**Complexity:** Medium
**Lines estimate:** ~130
**Dependencies:** None (pure logic, no I/O)

---

## 3. Integration into sherpa_loop

Current flow (v1.0):
```
1. Get pending tasks → 2. Claim → 3. Search codebase → 4. Build prompt
→ 5. Send to service (round-robin) → 6. Save recon → 7. Update task → 8. Cooldown
```

New flow (v2.0 PULSAR):
```
1. Get pending tasks → 2. Claim → 3. Search codebase → 4. Build prompt
→ 5a. [SHM] Select healthiest service
→ 5b. Send to service
→ 5c. [AV]  If Arena: extract dual, score, vote, pick winner
→ 5d. [RV]  Verify response quality
→ 5e. [SHM] Report success/failure
→ 5f. [RV]  If REJECT: retry via different service (max 2)
→ 6. Save recon (with confidence score) → 7. Update task → 8. Cooldown
```

**Code changes in sherpa_loop:**
```python
# Replace lines 1603-1618 in current sherpa.py

# NEW: Initialize PULSAR stack
health_monitor = ServiceHealthMonitor(FEEDBACK_FILE, active_services)
verifier = ReconVerifier()
arena_voter = ArenaVoter()

# ...inside the loop...

# 5a. Select service (health-aware)
last_failed = None
response = ""
verdict = VerifyResult(accepted=False, reason="not_attempted", confidence=0.0, details="")

for attempt in range(MAX_RETRIES + 1):
    svc = health_monitor.select_service(exclude=last_failed)
    if not svc:
        log.error("All services down — entering recovery mode")
        await asyncio.sleep(cfg.recovery_sleep_seconds)
        break

    # 5b. Send
    t0 = time.time()
    try:
        response = await browser.send_prompt(svc.profile_name, prompt)
    except Exception as e:
        health_monitor.report_failure(svc.name, f"browser_error:{type(e).__name__}")
        last_failed = svc.name
        continue

    elapsed = time.time() - t0

    # 5c. Arena special handling
    if svc.name == "arena" and response:
        page = browser._pages.get(svc.profile_name)
        if page:
            response = await arena_voter.process_arena(page, task)

    # 5d. Verify
    if response:
        verdict = verifier.verify(response, task, svc.name)
        if verdict.accepted:
            health_monitor.report_success(svc.name, len(response), elapsed)
            break
        else:
            health_monitor.report_failure(svc.name, verdict.reason)
            log.warning(f"Attempt {attempt+1}/{MAX_RETRIES+1}: {verdict.reason}")
            last_failed = svc.name
    else:
        health_monitor.report_failure(svc.name, "empty_response")
        last_failed = svc.name
```

---

## 4. Config Changes (sherpa.yaml)

```yaml
# ── PULSAR Stack (v2.0) ─────────────────────────────────────────────
pulsar:
  # ServiceHealthMonitor
  health:
    window_size: 20              # Last N feedback entries per service
    consecutive_fail_threshold: 3 # Auto-disable after N failures
    rate_limit_cooldown_s: 600   # 10 min cooldown on rate limit
    slow_threshold_s: 120        # Mark "slow" if avg > 120s
    recovery_sleep_s: 300        # 5 min when all services down

  # Fallback chains (tried in order)
  fallback_chain:
    primary: [deepseek, kimi, arena]
    secondary: [deepseek_2, kimi_2]
    tertiary: [huggingchat, mistral]

  # ReconVerifier
  verifier:
    min_chars: 500
    min_term_overlap: 0.15
    max_retries: 2
    hallucination_action: reject  # reject | warn
    confidence_threshold: 0.3     # Below this = save with warning

  # ArenaVoter
  arena:
    enabled: true
    vote_weights:
      volume: 0.3
      relevance: 0.5
      code_presence: 0.2
    tie_threshold: 0.05           # Score diff < this = tie vote
```

---

## 5. File Structure

```
sherpa.py                          # Main script (grows ~400 lines to ~2400)
  class ServiceHealthMonitor       # NEW: Health-aware service selection
  class ArenaVoter                 # NEW: Arena dual-response scoring + voting
  class ReconVerifier              # NEW: Response quality gate
  class VerifyResult               # NEW: Dataclass for verification results
  class FeedbackCollector          # EXISTING: JSONL logging (unchanged)
  class ServiceProtocol            # EXISTING: Auto-generated protocols (unchanged)
  class SherpaHarness              # EXISTING: Task filtering (updated to use SHM)
  class BrowserClient              # EXISTING: Playwright automation (minor update for Arena)
  class TaskBoardClient            # EXISTING: HTTP API (unchanged)
  class OllamaClient              # EXISTING: Local model (unchanged)

config/sherpa.yaml                 # Updated with pulsar: section
data/sherpa_feedback.jsonl         # Existing, gets new fields (confidence, verify_result)
```

---

## 6. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| All three modules in sherpa.py | Single file = simple deploy, no import issues for free-tier agents |
| No ML/embedding for verification | Pure heuristics — works offline, zero dependencies, deterministic |
| Arena voting is opt-in | `pulsar.arena.enabled: true` — can disable if Arena changes UI |
| Confidence stored in JSONL | Future: Qwen can learn which services give best results per task type |
| Retry via different service | Not same service retry — avoids rate limit cascade |
| WARN vs REJECT distinction | Some issues (no code in research task) aren't fatal |

---

## 7. Testing Strategy

| Module | Test Type | Who | How |
|--------|-----------|-----|-----|
| ServiceHealthMonitor | Unit | Theta/Iota | Mock JSONL, test scoring, fallback chain |
| ArenaVoter.score_responses | Unit | Kappa | Mock responses, verify scoring math |
| ArenaVoter.cast_vote | Integration | Burnell | Real Playwright against Arena |
| ReconVerifier | Unit | Mistral-2 (QA) | Fixture responses: good/bad/hallucinated/short |
| Full PULSAR loop | Integration | Delta (QA) | sherpa.py --once with real service |
| Config parsing | Unit | Mistral-1 | Load sherpa.yaml, verify defaults |

---

## 8. Metrics (Post-Deploy)

Track in `data/sherpa_feedback.jsonl`:
- `verify_result`: accepted/rejected per response
- `confidence`: 0.0-1.0 per response
- `retry_count`: how many retries were needed
- `selected_by`: "health_monitor" (vs old "round_robin")
- `arena_vote`: a/b/tie (Arena only)
- `arena_score_a`, `arena_score_b`: composite scores

**Success criteria:**
- Reject rate < 20% (most responses should pass verification)
- Retry success rate > 60% (retry on different service should work)
- Arena vote cast > 90% of Arena interactions
- No service stuck in permanent cooldown (recovery works)

---

*PULSAR: the signal in the noise. Found by Burnell, operationalized by SPACE.*
