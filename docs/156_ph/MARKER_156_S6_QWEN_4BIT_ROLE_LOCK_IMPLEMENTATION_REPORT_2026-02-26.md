# MARKER_156.S6_QWEN_4BIT_ROLE_LOCK

Date: 2026-02-26
Phase: 156 / S6

## What was implemented

1. `MARKER_156.VOICE.S6_QWEN_PROFILE_SWITCH`
- File: `scripts/voice_tts_server.py`
- Added env-based model profile switch:
  - `QWEN_TTS_PROFILE=4bit|5bit|6bit|8bit`
  - default profile: `4bit`
  - direct override: `QWEN_TTS_MODEL=<hf_model_id>`
- Health payload now includes active `profile` and available profiles.

2. `MARKER_156.VOICE.S6_ROLE_LOCK`
- File: `src/voice/voice_assignment_registry.py`
- Added stable assignment API by group+role:
  - `get_or_assign_group_role(group_id, role, provider, model_id, tts_provider)`
- Assignment key format for team lock:
  - `group:{group_id}:role:{role}`

3. `MARKER_156.VOICE.S6_GROUP_HANDLER_INTEGRATION`
- File: `src/api/handlers/group_message_handler.py`
- Group voice pipeline now resolves assignments by role lock (not by model identity only).
- `voice_reason` for successful lock: `S6_role_voice_locked`.

4. `MARKER_156.VOICE.S6_ROLE_MAP`
- File: `data/agent_role_voice_map.json`
- Added configurable default role mapping:
  - `pm -> ryan`
  - `dev -> eric`
  - `qa -> aiden`
  - `architect -> uncle_fu`
  - `hostess -> vivian`
  - `researcher -> serena`
  - `jarvis -> dylan`

## Notes

- Existing fallback chain in `TTSEngine` remains intact (`qwen3 -> edge -> piper`).
- This step does not yet add emotion params to Qwen request contract.
- Current profile default is intentionally `4bit` for speed, with fast rollback to `8bit` via env.

## Suggested runtime env examples

- Fast default:
  - `QWEN_TTS_PROFILE=4bit`
- Rollback quality:
  - `QWEN_TTS_PROFILE=8bit`
- Explicit custom model:
  - `QWEN_TTS_MODEL=mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit`
