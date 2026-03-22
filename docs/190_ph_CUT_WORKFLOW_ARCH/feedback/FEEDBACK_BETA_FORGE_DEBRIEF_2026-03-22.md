# Beta-Forge Debrief — 2026-03-22

## Q1: What's broken?

`compile_video_filters()` in cut_effects_engine.py assumes all effects are `EffectParam` objects (accesses `.enabled`, `.type`, `.params` as attributes). But `apply_mixer_to_plan()` injects raw dicts. This works today because mixer effects go into `audio_effects` (compiled by `compile_audio_filters` which handles both). But if anyone puts a dict into `video_effects` — crash. Also noticed: `_run_master_render_job` doesn't check `cancel_requested` flag before starting render — only during Popen poll loop. A cancel request between job creation and FFmpeg launch is silently ignored (race window ~200ms).

## Q2: What unexpectedly worked?

The "check-before-build" pattern: every task started with `action=get` on the original roadmap task_id. Found 6/11 tasks already done — saved hours of duplicate work. The existing code was high quality and well-structured, so my role shifted from "build" to "wire + test + cleanup". This is actually the highest-leverage mode: find gaps between existing modules and connect them. One `import` + 3 lines of wiring = entire feature works. The render pipeline went from "effects work in preview only" to "everything renders to FFmpeg" in 6 targeted edits.

## Q3: Unrealized idea

**FFmpeg `-progress` pipe for real render progress.** Current Popen poll loop estimates progress linearly from elapsed/timeout — this is fake. FFmpeg has a `-progress pipe:1` flag that outputs `out_time_us=`, `speed=`, `frame=` every 500ms. Parsing this would give real % progress (current_time / total_duration), accurate ETA, and actual encoding speed. Implementation: add `"-progress", "pipe:1"` to cmd, read stdout lines in poll loop, parse `out_time_us` → compute real progress. ~30 lines of code, massive UX improvement for long renders.

## Session stats

Commits: 15 | Tests: 235 | Modules: 4 new | Endpoints: 8 new | Effects: 38 total
