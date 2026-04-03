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

## Character Notes
Han Solo approach: no grand architecture, just make it fly.
Ship = sherpa.py. Crew = Playwright + Ollama + TaskBoard.
Saving the galaxy (1000 tasks) is a side effect of making the ship work.
