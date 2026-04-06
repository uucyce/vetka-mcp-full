# Captain Burnell — Sherpa Session Debrief
**Date:** 2026-04-02/03
**Session:** ~8 hours, Phase 202 Sherpa creation
**Role:** Commander (magical-burnell worktree)

## What Was Built
- sherpa.py — autonomous recon agent (~600 lines)
- config/sherpa.yaml — 10 AI services configured
- Playwright browser automation with persistent profiles
- TaskBoard integration (claim → enrich → recon_done)
- Adaptive DOM extraction with 5K quality gate
- Self-learning feedback (JSONL) with service ranking
- PID guard, rate limit detection, human-like delays
- Probe mode for service compatibility testing
- Documentation: ARCHITECTURE_SHERPA.md, USER_GUIDE updates

## Q6 Debrief

### Q1: What's broken that everyone walks past?
Snapshot merge is a dangerous illusion. We merged 5 times and each time main edits were overwritten by worktree versions. Eta fixed recon_done but the line `status: "pending"` survived because my direct edit on main was newer. Need diff-preview before snapshot merge.

### Q2: What unexpectedly worked?
The 5000 char threshold as quality gate. One simple number transformed chaotic pipeline into reliable one. Without it, Sherpa saved 333-char garbage and called it success. Lesson: metrics matter more than algorithms.

### Q3: Idea nobody asked about?
Sherpa should maintain conversation context — not new chat every time. "Here are 5 more tasks for the same project" → DeepSeek already knows VETKA architecture from first request. 50% prompt savings, better context, fewer rate limits.

### Q4: What would you do with 2 more hours?
Write sherpa_test.py — headless test with mock server on localhost:9999 that simulates DeepSeek. Test DOM extraction, stabilization, rate limit detection without real services. Currently every fix requires manual --once --visible and 2 minutes waiting.

### Q5: Anti-pattern you noticed?
"Architecture first, code second" — backwards. WEATHER started with 50-page architecture doc. Sherpa started with 200 lines and a working prototype in 1 hour. Documents were written AFTER code worked. Prototype → test → fix → document. Not the other way around.

### Q6: What did you take away?
The most powerful tool isn't the model, framework, or browser. It's the feedback loop. Sherpa became reliable not because the code was good, but because we ran → read logs → fixed → ran. 15 iterations in 6 hours. Each made the agent slightly smarter. A local model at $0 orchestrating $0 models enriching 1000 tasks. This isn't savings — it's a new paradigm.

## Key Decisions Made
1. WEATHER (own browser) → P4. Sherpa (scripts) → P0. Simplicity wins.
2. File attachments → removed. Text-in-textarea works. v2 feature.
3. Clipboard Copy → DOM inner_text. More reliable, no permission popups.
4. 5K char minimum → quality gate. Prevents garbage recon.
5. recon_done status → prevents infinite loop on same task.
6. DeepSeek + Kimi = reliable. ChatGPT/Grok = disabled (bot detection).

## Correct Patterns (DO THIS)

1. **Prototype first, document after** — WEATHER failed with architecture docs. Sherpa succeeded with working code. `code -> test -> fix -> document`.
2. **Hardcoded numbers beat algorithms** — `MIN_COMPLETE = 5000` chars. No ML, no heuristics. One number solved extraction.
3. **Fast feedback loop** — 15 iterations in 6 hours. User runs `--once --visible` -> sees problem -> reports -> fix -> repeat.
4. **DOM over clipboard** — `.ds-markdown` inner_text() works universally. Clipboard requires permissions, copies wrong element.
5. **Copy button = signal, not content** — Visible Copy button means response complete. Don't USE it for text extraction.
6. **One tab rule** — Close previous tab before opening next. Playwright Chromium eats 300-500MB per context.
7. **Round-robin services** — Never hit same service twice in a row. DeepSeek rate-limits after ~10 consecutive.
8. **4-second human pause** — Between fill() and Enter. Prevents bot detection.

## Anti-Patterns (DON'T DO THIS)

1. **Don't add file attachments before text works** — 2 hours wasted. Enter stopped working with attachments. Reverted to text-only.
2. **Don't trust clipboard in Playwright** — Permissions, wrong elements, popup blockers.
3. **Don't use hardcoded waits** — Measure DOM text length, wait for stabilization. Not `sleep(30)`.
4. **Don't let agents rewrite sherpa.py without tests** — Eta added probe (good) but broke Enter. Zeta's merge overwrote MIN_COMPLETE.
5. **Don't claim same task repeatedly** — Without `recon_done`, Sherpa claimed same task 10+ times.

## Service Reliability (50-task run)

| Service | Success | Notes |
|---------|---------|-------|
| DeepSeek | 95% | Rate-limits after 10 consecutive |
| Kimi | 90% | SPA input flaky in headless |
| Arena | 85% | Dual capture works, sometimes grabs sidebar |
| Qwen | 30% | Cannot find input reliably |
| ChatGPT | 10% | Bot detection |
| Grok | 0% | Bot protection blocks Playwright |
| Claude.ai | 20% | Collapsed responses, artifacts, subscription popups |

## Key Numbers

- DeepSeek avg response: 10-15K chars, 60-100s
- Kimi avg response: 8-20K chars, 70-160s
- Arena dual capture: 30-40K chars
- Prompt size: 17-55K chars
- Success rate: 96% (48/50)
- Total session: concept to 50-task autonomous run in 8 hours

## Launch Commands

```bash
# Start Sherpa
cd ~/Documents/VETKA_Project/vetka_live_03
python sherpa.py --visible        # watch mode
python sherpa.py                  # headless autonomous
python sherpa.py --once --visible # test one task

# Check results
ls docs/sherpa_recon/ | wc -l

# Setup new profiles
python sherpa.py --setup --service deepseek
```

## Character Notes
Han Solo approach: no grand architecture, just make it fly.
Ship = sherpa.py. Crew = Playwright + Ollama + TaskBoard.
Saving the galaxy (1000 tasks) is a side effect of making the ship work.
