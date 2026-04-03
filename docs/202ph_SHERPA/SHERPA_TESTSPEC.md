# SHERPA Response Extraction Test Specification
**Phase:** 202 v1.1 (Stability)
**Date:** 2026-04-03
**Author:** Epsilon (QA)
**Target Agents:** Eta (DOM extraction fix), Zeta (service protocols)
**Related:** ARCHITECTURE_SHERPA.md, P0 issues in Copy extraction & Arena dual responses

---

## 1. Overview

This document defines test scenarios and acceptance criteria for Sherpa's response extraction and processing pipeline. The test spec enables DOM-based extraction implementation (replacing clipboard) with clear verification targets.

**Scope:** Response extraction from 3 working services (DeepSeek, Kimi, Arena), edge case handling, and dual-response processing.

**Not in Scope:** File attachment upload, email profile rotation, Ollama summarization (backend tests), service probe mode (40+ services).

---

## 2. Response Extraction Scenarios

### 2.1 DeepSeek Full Response Extraction

**Service:** DeepSeek (text-only mode)
**DOM Structure:** Single response container (div with response content + Copy button)
**Current State:** Copy button truncates to last code block (~333-1112 chars)
**Target:** Full response text (15K+ expected for typical 2-3 section recon)

#### Test Setup
```
1. Navigate to https://chat.deepseek.com (or configured service URL)
2. Authenticate via persistent Playwright profile (cookies from data/sherpa_profiles/deepseek_*)
3. Send test prompt via fill() + Enter
   Prompt: "List 5 Python file I/O patterns with example code"
4. Wait for response completion (text stability + Copy button visible)
```

#### Test Case: DS-01 — Full Response Content Extraction

**Input:**
- Service: DeepSeek
- Prompt: "List 5 Python file I/O patterns with example code"
- Response type: Multi-section (explanation + 5 code examples)

**Expected DOM Structure:**
```html
<!-- Response container (primary target) -->
<div class="response-container" id="chat-message-XXX">
  <div class="message-content">
    <!-- Header text -->
    <p>Here are 5 Python file I/O patterns...</p>

    <!-- Code block 1 -->
    <pre><code class="language-python">...</code></pre>
    <button class="copy-btn">Copy</button>

    <!-- Code block 2-5 -->
    ...

    <!-- Master Copy button (if exists) -->
    <button class="copy-all">Copy All</button>
  </div>
</div>
```

**Extraction Method (DOM-based, NOT clipboard):**
```
Option A (Primary): inner_text() on entire response-container div
  result = document.querySelector('#chat-message-XXX').innerText

Option B (Fallback): Concatenate all code blocks + text sections
  sections = []
  sections.push(intro_text)
  sections.push(code_block_1.textContent)
  sections.push(code_block_2.textContent)
  ...
  result = sections.join('\n\n')
```

**Acceptance Criteria (PASS):**
- [ ] Response length ≥ 8000 chars (includes all 5 patterns + explanations)
- [ ] Response contains all 5 Python patterns (count keywords: "with open", "read()", "write()", "append", "json")
- [ ] All code examples included (count "```" blocks: ≥ 5)
- [ ] No truncation at phrase boundaries (last sentence complete, not cut mid-word)
- [ ] Extracted text matches DOM content ±5% (verification via hash or token count)

**Failure Conditions (FAIL):**
- [ ] Response length < 4000 chars (truncated, missing examples)
- [ ] Only 1-2 code blocks extracted instead of 5 (clipboard bug recreated)
- [ ] Last section cut mid-sentence ("The fifth pattern is...") — indicates clipboard truncation
- [ ] DOM extraction failed (returned empty string or error)

---

### 2.2 Kimi Full Response Extraction

**Service:** Kimi (text-only mode, CN-based)
**DOM Structure:** Single response container (similar to DeepSeek, different CSS classes)
**Current State:** Same Copy button truncation as DeepSeek
**Target:** Full response extraction with DOM method (works across service variations)

#### Test Case: KM-01 — Full Response Content Extraction

**Input:**
- Service: Kimi
- Prompt: "Explain async/await in JavaScript with 3 examples"
- Response type: Multi-section explanation + code examples

**Expected DOM Structure:** (Kimi-specific classes)
```html
<div class="message-row" data-role="assistant">
  <div class="message-text" id="message-content-YYY">
    <p>Async/await is syntactic sugar over Promises...</p>
    <pre class="code-block"><code>...</code></pre>
    ... (2 more code blocks)
    <button class="copy-icon">复制</button> <!-- Chinese "Copy" -->
  </div>
</div>
```

**Extraction Method:**
```
Same as DeepSeek (Option A/B above)
result = document.querySelector('[data-role="assistant"] .message-text').innerText
```

**Acceptance Criteria (PASS):**
- [ ] Response length ≥ 5000 chars (explanation + 3 complete examples)
- [ ] Contains "async", "await", "Promise" keywords (≥ 5 occurrences each)
- [ ] All 3 code examples extracted (count "```" blocks: ≥ 3)
- [ ] No truncation; last example fully included
- [ ] Works even if Kimi uses different CSS selectors than DeepSeek

**Failure Conditions (FAIL):**
- [ ] Response < 2500 chars (truncated)
- [ ] Only 1 code block extracted (clipboard bug)
- [ ] Chinese text mangled or missing (encoding issue)
- [ ] Selector mismatch (data-role="assistant" doesn't exist)

---

### 2.3 Arena.ai Dual Response Extraction

**Service:** Arena.ai (benchmark mode)
**DOM Structure:** TWO independent response containers (left & right panels)
**Current State:** Only capturing one response; missing comparative analysis
**Target:** Extract both responses separately with clear left/right labels

#### Test Case: AR-01 — Left Response Extraction

**Input:**
- Service: Arena.ai
- Prompt: "What is the Halting Problem?"
- Response type: Dual response (Model A on left, Model B on right)

**Expected DOM Structure:** (Arena-specific)
```html
<div class="arena-container">
  <!-- Left panel: Model A -->
  <div class="response-panel left" id="response-left">
    <div class="model-header">Model A (e.g., GPT-4)</div>
    <div class="response-content">
      <p>The Halting Problem is a classic problem in computability theory...</p>
      ... (explanation + code if applicable)
    </div>
    <button class="copy-btn">Copy</button>
  </div>

  <!-- Right panel: Model B -->
  <div class="response-panel right" id="response-right">
    <div class="model-header">Model B (e.g., Claude)</div>
    <div class="response-content">
      <p>The Halting Problem asks whether a program can determine...</p>
      ... (different explanation, different approach)
    </div>
    <button class="copy-btn">Copy</button>
  </div>
</div>
```

**Extraction Method:**
```
Left response:
  left_content = document.querySelector('#response-left .response-content').innerText
  left_model = document.querySelector('#response-left .model-header').innerText

Right response:
  right_content = document.querySelector('#response-right .response-content').innerText
  right_model = document.querySelector('#response-right .model-header').innerText

Result structure:
  {
    "left": {
      "model": left_model,
      "content": left_content,
      "chars": left_content.length
    },
    "right": {
      "model": right_model,
      "content": right_content,
      "chars": right_content.length
    }
  }
```

**Acceptance Criteria (PASS):**
- [ ] Left response extracted (length ≥ 2000 chars)
- [ ] Right response extracted (length ≥ 2000 chars)
- [ ] Both responses are DIFFERENT (Levenshtein distance > 30%, not duplicates)
- [ ] Model names captured correctly (left_model ≠ right_model)
- [ ] Both responses address same question (share key terms: "Halting", "Problem", "computability")
- [ ] No crosstalk (left response doesn't contain right model's name, vice versa)

**Failure Conditions (FAIL):**
- [ ] Only left response extracted, right is empty (original bug)
- [ ] Only right response extracted
- [ ] Both responses identical (scraper error, same content twice)
- [ ] Response lengths < 1000 chars (truncated)
- [ ] Model header extraction failed (returns "Model A", not actual name)

#### Test Case: AR-02 — Arena Response Persistence & Comparison

**Input:**
- Service: Arena.ai
- Prompt: "Compare REST vs GraphQL"
- Response type: Dual response with code examples

**Acceptance Criteria (PASS):**
- [ ] Left response includes REST explanation + code example (expect 3000+ chars)
- [ ] Right response includes GraphQL explanation + code example (expect 3000+ chars)
- [ ] Both responses mention the key terms from prompt ("REST", "GraphQL")
- [ ] Code blocks preserved in both responses (count "```" blocks: ≥ 2 per response)
- [ ] Comparison-style structure detected (both responses acknowledge the alternative)

---

## 3. Edge Cases & Error Handling

### 3.1 Timeout Handling

**Scenario:** Service takes longer than expected (network lag, server busy), or never responds.

#### Test Case: TO-01 — Response Timeout

**Setup:**
```
1. Configure timeout threshold: 30 seconds
2. Send prompt to service
3. Simulate timeout by:
   - Option A: Intentionally close tab (simulate network disconnect)
   - Option B: Network throttle (Chrome DevTools: slow 3G)
   - Option C: Wait past timeout without response completion
```

**Expected Behavior:**
```
After 30 seconds without response or Copy button:
  status = "timeout"
  message = "DeepSeek did not respond within 30 seconds"
  result = null
  timestamp = ISO 8601
```

**Acceptance Criteria (PASS):**
- [ ] Timeout detected after 30 seconds
- [ ] No exception thrown (graceful failure)
- [ ] Status recorded as "timeout" (not "error")
- [ ] Sherpa can retry with next service in fallback chain
- [ ] Task status remains pending (ready for retry)

**Failure Conditions (FAIL):**
- [ ] Timeout not detected, script hangs indefinitely
- [ ] Exception raised (should be caught, handled gracefully)
- [ ] Task marked as failed (should retry, not fail immediately)

---

### 3.2 Empty Response Handling

**Scenario:** Service responds but returns empty content (user gets blank page, or error page instead of response).

#### Test Case: ER-01 — Empty Response

**Setup:**
```
1. Manually delete all response content from page (simulate service error)
2. Or navigate to error page (403/500)
3. Attempt response extraction
```

**Expected Structure:**
```html
<!-- Error page or empty response -->
<div id="chat-message-XXX">
  <!-- Empty or error message -->
  <p>Error: Response unavailable</p>
  <!-- No Copy button, or disabled -->
  <button class="copy-btn" disabled>Copy</button>
</div>
```

**Extraction Method:**
```
result = document.querySelector('#chat-message-XXX').innerText.trim()
if (!result || result.length < 100) {
  return { status: "empty_response", message: "Service returned no content", result: null }
}
```

**Acceptance Criteria (PASS):**
- [ ] Empty response detected (innerText.length < 100)
- [ ] Status set to "empty_response" (not "success")
- [ ] No exception thrown (graceful failure)
- [ ] Fallback triggered (try next service)
- [ ] Task remains claimable (not marked as failed)

**Failure Conditions (FAIL):**
- [ ] Empty response treated as success (saved as blank recon)
- [ ] Exception raised instead of graceful null return
- [ ] Task marked as failed instead of retryable

---

### 3.3 Malformed HTML / Selector Mismatch

**Scenario:** Service UI changes, CSS classes/IDs no longer match expected structure.

#### Test Case: ML-01 — Service UI Changed

**Setup:**
```
1. Simulate CSS class name change:
   Old: <div class="response-container">
   New: <div class="message-box" data-testid="assistant-response">
2. Attempt extraction with original selector
```

**Extraction Method (with fallback):**
```
// Try primary selector
let response = document.querySelector('#chat-message-XXX')?.innerText

// If not found, try alternative selectors
if (!response) {
  response = document.querySelector('[data-testid="assistant-response"]')?.innerText
}
if (!response) {
  response = document.querySelector('.message-box')?.innerText
}
if (!response) {
  response = document.querySelector('[role="article"]')?.innerText
}

if (!response) {
  return { status: "selector_mismatch", message: "Could not find response element", fallbacks_tried: 4 }
}
```

**Acceptance Criteria (PASS):**
- [ ] Primary selector fails (old CSS class)
- [ ] Fallback selectors tried (alternative: data-testid, .message-box, role attribute)
- [ ] Response found via fallback selector
- [ ] Status = "success" (even via fallback)
- [ ] Recovery logged for future selector updates

**Failure Conditions (FAIL):**
- [ ] All selectors fail, no fallback recovery attempted
- [ ] Exception raised (should catch and try alternatives)
- [ ] Task marked failed instead of retryable

---

### 3.4 Partial Response / Streaming Interrupted

**Scenario:** Response is being streamed (typical for modern AI services), but extraction happens mid-stream.

#### Test Case: PS-01 — Incomplete Streaming Response

**Setup:**
```
1. Send prompt to service
2. Wait for response to START (first paragraph visible)
3. Attempt extraction BEFORE completion (before Copy button stable)
```

**Expected Behavior:**
```
Before completion:
  innerText = "The first paragraph is... [INCOMPLETE]"
  Copy button present but not yet stable (text still updating)
  Should WAIT instead of extracting

After completion:
  text stability detected (no changes for 2 seconds)
  Copy button clickable
  Extract complete response
```

**Acceptance Criteria (PASS):**
- [ ] Waits for text stability (no character changes in 2 seconds)
- [ ] Copy button becomes clickable before extraction
- [ ] Full response extracted after stability detected
- [ ] Partial extraction avoided (no mid-sentence truncation)

**Failure Conditions (FAIL):**
- [ ] Extracts during streaming (incomplete content saved)
- [ ] Doesn't wait for Copy button stability
- [ ] Response includes "[INCOMPLETE]" markers

---

### 3.5 Malformed HTML Recovery

**Scenario:** HTML structure is corrupted or nested differently (e.g., response inside wrong container, extra wrappers).

#### Test Case: MH-01 — Corrupted HTML Structure

**Setup:**
```html
<!-- Malformed: response content is wrapped in unexpected nesting -->
<div id="chat-XXX">
  <div class="wrapper">
    <div class="inner-wrapper">
      <div class="content-container">
        <p>Actual response content here...</p>
      </div>
    </div>
  </div>
</div>
```

**Extraction Method (robustness):**
```
// Strategy: search for actual text content, not specific structure
const searchText = (element, depth = 0) => {
  if (depth > 5) return null; // prevent infinite recursion

  let text = element.innerText?.trim();
  if (text && text.length > 500) return text; // found substantial content

  // Try all children
  for (const child of element.children) {
    let result = searchText(child, depth + 1);
    if (result) return result;
  }
  return null;
}

const response = searchText(document.getElementById('chat-XXX'));
```

**Acceptance Criteria (PASS):**
- [ ] Response extracted despite unexpected nesting (depth-first search works)
- [ ] Extracts actual paragraph text (≥ 500 chars)
- [ ] No specific CSS selectors required (flexible)
- [ ] Status = "success_degraded" (recovered from malformed HTML)

---

## 4. Test Scenarios Summary Table

| # | Test ID | Service | Scenario | Input | Expected Length | PASS Criteria | Agent |
|---|---------|---------|----------|-------|-----------------|---------------|-------|
| 1 | DS-01 | DeepSeek | Full response, 5 examples | "5 Python I/O patterns" | ≥8000 chars | All 5 patterns extracted, ≥5 code blocks | Eta |
| 2 | KM-01 | Kimi | Full response, 3 examples | "async/await examples" | ≥5000 chars | 3 examples extracted, no truncation | Eta |
| 3 | AR-01 | Arena | Left response (Model A) | "What is Halting Problem?" | ≥2000 chars | Left extracted, model name captured | Eta |
| 4 | AR-02 | Arena | Dual response comparison | "REST vs GraphQL" | ≥3000 chars each | Both responses extracted, ≥2 code blocks each | Eta |
| 5 | TO-01 | Any | Timeout (30s threshold) | (wait without response) | null | Timeout detected, status="timeout" | Zeta |
| 6 | ER-01 | Any | Empty response | (error page) | null | Status="empty_response", no exception | Zeta |
| 7 | ML-01 | Any | CSS selector mismatch | (changed HTML structure) | ≥1000 chars via fallback | Fallback selectors work, recovery logged | Zeta |
| 8 | PS-01 | Any | Partial/streaming response | (extract mid-stream) | ≥1000 chars | Waits for stability, no incomplete content | Eta |
| 9 | MH-01 | Any | Malformed HTML nesting | (deep nesting) | ≥500 chars | Depth-first search extracts content | Eta |

---

## 5. Implementation Notes for Eta/Zeta

### 5.1 DOM Extraction Pseudocode (Eta — sherpa.py update)

```python
def extract_response_dom(service_name: str) -> dict:
    """Extract response via DOM, not clipboard."""

    try:
        # Service-specific primary selectors
        selectors = {
            "deepseek": "#chat-message-*",  # dynamic ID
            "kimi": "[data-role='assistant'] .message-text",
            "arena": ["#response-left .response-content", "#response-right .response-content"]
        }

        # Get primary selector
        primary = selectors.get(service_name)
        if not primary:
            return {"status": "unknown_service"}

        # Extract based on service
        if service_name == "arena":
            # Dual response
            left = page.evaluate(f"document.querySelector('{primary[0]}').innerText")
            right = page.evaluate(f"document.querySelector('{primary[1]}').innerText")
            return {
                "status": "success",
                "left": left,
                "right": right,
                "chars_total": len(left) + len(right)
            }
        else:
            # Single response
            # Wait for text stability first
            wait_for_text_stability(page, timeout=30)

            content = page.evaluate(f"document.querySelector('{primary}').innerText")

            if not content or len(content) < 100:
                return {"status": "empty_response"}

            return {
                "status": "success",
                "content": content,
                "chars": len(content)
            }

    except TimeoutError:
        return {"status": "timeout"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

### 5.2 Fallback Chain (Zeta — sherpa.py retry logic)

```python
def extract_with_fallback(service_name: str, task_id: str):
    """Extract response, with fallback to next service if failed."""

    result = extract_response_dom(service_name)

    if result["status"] == "success":
        return result

    if result["status"] in ["timeout", "empty_response", "error"]:
        # Log failure for self-learning
        log_service_feedback(service_name, result["status"], 0)

        # Try next service in fallback chain
        next_service = get_fallback_service(service_name)
        if next_service:
            return extract_with_fallback(next_service, task_id)

    # All fallbacks exhausted
    return {
        "status": "failed",
        "task_id": task_id,
        "message": "All services exhausted, returning to pending"
    }
```

### 5.3 Self-Learning Log Format (Zeta — feedback.jsonl)

```jsonl
{"timestamp": "2026-04-03T16:30:00Z", "service": "deepseek", "task_id": "tb_123", "status": "success", "chars": 8456, "time_sec": 12.3}
{"timestamp": "2026-04-03T16:31:00Z", "service": "deepseek", "task_id": "tb_124", "status": "success", "chars": 5200, "time_sec": 9.8}
{"timestamp": "2026-04-03T16:32:00Z", "service": "arena", "task_id": "tb_125", "status": "success", "chars_left": 3100, "chars_right": 2900, "time_sec": 18.5}
{"timestamp": "2026-04-03T16:33:00Z", "service": "kimi", "task_id": "tb_126", "status": "timeout", "time_sec": 30.0}
```

---

## 6. Test Execution Protocol

### 6.1 Phase 1: Manual Verification (Before Eta/Zeta Implementation)

```
1. QA sets up local DeepSeek, Kimi, Arena profiles
2. QA manually runs each test case (DS-01, KM-01, AR-01/02, etc.)
3. QA documents CURRENT behavior (baseline):
   - Does Copy button truncate? (expected: YES, current bug)
   - Does Arena capture both responses? (expected: NO, current bug)
   - What are actual response lengths?
4. QA signs off on baseline
```

### 6.2 Phase 2: Implementation (Eta's DOM Extraction)

```
1. Eta implements DOM extraction (replace clipboard)
2. Eta runs manual tests again against new code
3. Eta documents actual behavior (should match PASS criteria)
4. QA verifies results, signs off
```

### 6.3 Phase 3: Automation (Zeta's Fallback Chain)

```
1. Zeta implements fallback logic + self-learning
2. Zeta runs full test suite (all 9 scenarios)
3. Zeta logs results to feedback.jsonl
4. QA verifies feedback log format
5. QA signs off on complete pipeline
```

---

## 7. Success Metrics

| Metric | Baseline | Target (Phase 201.1) |
|--------|----------|----------------------|
| DeepSeek full response extraction | 333-1112 chars (truncated) | ≥8000 chars (complete) |
| Kimi full response extraction | Similar truncation | ≥5000 chars (complete) |
| Arena dual response capture | 1 response only | Both responses extracted |
| Average response chars across 3 services | ~3000 | ≥6000 |
| Timeout detection | N/A (hangs) | ≥30 sec threshold |
| Error recovery (empty/malformed) | Fails task | Retries with fallback service |
| Self-learning feedback log | N/A | 100% of extraction attempts logged |

---

## 8. Risk Mitigation

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Service UI changes require constant selector updates | MEDIUM | Use fallback selectors + depth-first search; log failures for alerting |
| Copy button behavior changes (service update) | MEDIUM | Switch to DOM extraction (this spec) removes Copy button dependency |
| Arena model names not consistent | LOW | Extract from `model-header` class (stable), fallback to generic "Model A/B" |
| Timeout too short (30s), legitimate slow responses | LOW | Configurable threshold in sherpa.yaml (default 30s, override per service) |
| Text stability detection (streaming responses) | MEDIUM | Wait for 2-second silence before extracting (configurable) |

---

## 9. Questions for Implementation Review

1. **DOM Selector Standardization:** Should all services be mapped to unified selector patterns in sherpa.yaml, or keep service-specific selectors?
2. **Fallback Selector Chain:** Is the 4-level fallback chain (primary → data-testid → class → role) sufficient, or add more?
3. **Text Stability Detection:** Is 2 seconds of no-change sufficient, or should this be service-specific?
4. **Dual Response (Arena):** Should we label responses as "response_1/response_2" or "left/right" or "model_a/model_b"?
5. **Self-Learning Feedback:** Should feedback.jsonl include response hash (to detect duplicates), or just metadata?

---

## Appendix A: DOM Selector Reference

| Service | Primary Selector | Fallback 1 | Fallback 2 | Fallback 3 |
|---------|------------------|-----------|-----------|-----------|
| DeepSeek | `#chat-message-*` (dynamic) | `.response-container` | `[role="article"]` | Last `<p>` element |
| Kimi | `[data-role="assistant"] .message-text` | `.message-box` | `[data-testid="response"]` | `.content` |
| Arena (left) | `#response-left .response-content` | `.panel.left .content` | `[data-panel="left"]` | First `.response-panel` |
| Arena (right) | `#response-right .response-content` | `.panel.right .content` | `[data-panel="right"]` | Last `.response-panel` |
| Generic fallback | (service-specific) | `[role="article"]` | `.message-content` | Last text-heavy `<div>` |

---

*Document Status: READY FOR IMPLEMENTATION*
*Approval Path: Epsilon (QA design) → Eta (DOM extraction) → Zeta (fallback chain) → TaskBoard update*
*Version: 1.0*
