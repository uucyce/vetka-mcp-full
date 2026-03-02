# MARKER_156: JARVIS (USER-FACING "VETKA") VOICE MODE MASTER PLAN

Date: 2026-02-26
Phase: 156
Scope: Dedicated live voice dialog mode (separate from group/solo chat voice messages)

## 1. Goal
Create a stable live dialog mode where user talks to VETKA by voice and receives voice replies with minimal delay.

Hard separation:
- Group/Solo chats: only full voice messages (no early kickoff chunks).
- Jarvis/VETKA live mode: interactive listen -> think -> speak loop.

## 2. Product constraints
- Activation surface should be in top Tauri header zone:
  - preferred: clickable `VETKA` label toggles listen state;
  - fallback: compact control row directly below header if native titlebar layout constraints block it.
- Controls: simple monochrome icons only (white eye + white mic/speech), no "space" style widgets.
- Visual feedback:
  - passive mode: calm, near-static indicator;
  - speaking mode: animated waveform/light reacts to real output audio energy;
  - no always-running aggressive wave.

## 3. Current status audit
- Frontend has Jarvis hook/state machine (`idle/listening/thinking/speaking`) and waveform component.
- Browser STT fallback was added (`SpeechRecognition`) and sends `transcript_hint`.
- Backend now accepts `transcript_hint` fallback when local Whisper is unavailable.
- Out-of-state audio chunk warnings were reduced from warning-level spam to debug.
- Regression package currently green on smoke profile.

## 4. Marker-based implementation backlog

### MARKER_156_JARVIS_S2_9_UI_HEADER_CONTROLS
- Move/normalize controls into top-center header experience.
- Keep only minimal row: eye, VETKA trigger, mic/speech mode.
- Add compact `Auto/Favorite` selector without noisy panel behavior.
- Acceptance: click VETKA -> state toggles listening, visual state reflected.

### MARKER_156_JARVIS_S3_1_STT_RELIABILITY
- Finalize dual STT path:
  - local Whisper when available;
  - browser transcript fallback via `transcript_hint` when Whisper absent/fails.
- Add telemetry field in logs: `stt_source = whisper|browser_hint|none`.
- Acceptance: no dead-end `No STT engine` dialog when browser transcript exists.

### MARKER_156_JARVIS_S3_2_STATE_MACHINE_HARDENING
- Enforce strict transitions to avoid chunk/state race:
  - listening -> thinking -> speaking -> idle.
- Ignore late chunks silently or debug-only (already partially done).
- Add tests for fast toggle and auto-stop race.
- Acceptance: no warning storms, no stuck THINKING/IDLE loops.

### MARKER_156_JARVIS_S4_AUDIO_VISUALIZATION
- Drive wave/light from actual outbound TTS chunk amplitude (RMS/peak), not synthetic idle oscillator.
- Render animation only during `speaking`.
- Passive mode should be near-static.
- Acceptance: visible sync between spoken voice and visual pulses.

### MARKER_156_JARVIS_S5_MODEL_ROUTING
- Clarify text-generation source for Jarvis responses:
  - `Auto`: best available low-latency local or API model.
  - `Favorite`: user’s favorite list order.
  - fallback policy: free API models from unified provider registry/phonebook.
- Add explicit metadata internal-only (not noisy in main UI): selected model/provider/latency.
- Acceptance: deterministic model selection with graceful fallback.

### MARKER_156_JARVIS_S6_TEST_PACKAGE
- Add/extend tests:
  - jarvis listen-stop with `transcript_hint` fallback;
  - state transition race cases;
  - model routing (`auto/favorite/fallback`);
  - speaking-only waveform visibility contract.
- Keep included in stable smoke profile.
- Acceptance: green tests and marker report.

## 5. Open research items (targeted)
1. Tauri header integration options by window mode:
- native titlebar vs custom titlebar/webview overlay compatibility;
- click/drag regions without breaking controls.

2. Best local STT for low-latency RU/EN on Apple Silicon:
- Whisper base/small vs alternative MLX STT footprints;
- expected first-text latency under live conditions.

3. TTS visualization signal source:
- use emitted PCM chunks from current stream path vs WebAudio analyser from playback element;
- choose lower overhead and tighter A/V sync.

## 6. Execution order
1. S2.9 UI header controls
2. S3.1 STT reliability
3. S3.2 state machine hardening
4. S4 audio visualization
5. S5 model routing
6. S6 tests + report

## 7. Done in this iteration
- Backend `transcript_hint` fallback integrated in Jarvis listen-stop pipeline.
- Wrong-state audio chunk warning noise reduced.
- Regression smoke and targeted voice tests passed.
