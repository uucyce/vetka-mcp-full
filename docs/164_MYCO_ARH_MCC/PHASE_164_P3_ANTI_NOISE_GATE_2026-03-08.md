# PHASE 164 — P3 Anti-Noise Gate (2026-03-08)

Marker: `MARKER_164.P3.ANTI_NOISE_SILENCE_DEDUPE_GATE.V1`

## Gate Policy
1. No duplicate helper message for same normalized state key.
2. No helper echo in architect-only mode (`helperMode=off`).
3. Stale helper hint is purged when mode flips to architect.
4. Proactive helper hint only on meaningful context change.

## Runtime Hooks
- `MiniChat.tsx` compact/expanded dedupe and mode guards.
- `chat_routes.py` role-aware packet built from normalized context.

## Pass Criteria
- Switching helper off removes helper-only content from chat stream.
- Context changes produce one helper message per unique state key.
- Architect quick path does not leak helper phrasing.

