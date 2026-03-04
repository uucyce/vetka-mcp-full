# vetka-chat-ui

Chat interface module for VETKA focused on agent-first collaboration:
solo chat, team chat, model-aware mentions, persistent chat history, and
voice-first interaction in one runtime panel.

## Why This Is Different
- Agent-native UX: chats are designed around agents/models, not only users.
- Team chat as a first-class mode: create/manage multi-agent groups and route
  mentions to specific participants.
- Memory-aware continuity: chat history, pinned context, and model usage are
  surfaced directly in the interaction loop.
- Voice as a real interface: realtime voice states, auto-send, and playback
  controls are integrated into the same input and message flow.

## Core Capabilities
- Persistent chat history sidebar with:
  - Search
  - Pagination / lazy loading
  - Favorites
  - Inline rename and delete controls
- Rich message timeline:
  - Reply-to message threading
  - Compound workflow message rendering
  - Artifact open actions from chat messages
  - Emoji/CAM reaction hooks
- Smart input pipeline:
  - `@mention` popup for agents/models
  - Solo-mode model suggestions from real chat usage
  - Group-mode dynamic participant mentions
  - Voice-model detection and automatic mic/send behavior
- Group creation and management:
  - Role slots for agents
  - Model assignment and update flows
  - Participant role/model update controls
- Voice interaction:
  - Realtime voice state machine (listening/speaking/model-speaking)
  - Visual waveform feedback
  - Voice message playback with rate control

## Architecture Snapshot
- `ChatPanel.tsx`: composition root and state orchestration for chat modes.
- `ChatSidebar.tsx`: persistent history panel (search/pagination/rename/favorites).
- `MessageInput.tsx`: text+voice input state machine with mention routing.
- `MessageBubble.tsx`: message rendering, reactions, artifact actions, voice playback.
- `MentionPopup.tsx`: mention UX for solo model tracking and group participants.
- `GroupCreatorPanel.tsx`: multi-agent group creation/editing surface.

## Open Source Attribution
This module uses and builds on open-source libraries. See
[OPEN_SOURCE_CREDITS.md](OPEN_SOURCE_CREDITS.md) for direct links and licenses.

If you reuse this module, please keep attribution intact and contribute fixes
back through pull requests.

## Status
- Source of truth: monorepo `danilagoleen/vetka`
- Mirror sync: automated via subtree publish workflow
- Stability: experimental / fast-moving

## Development
1. Fork this repository.
2. Create a branch: `feature/short-name` or `fix/short-name`.
3. Use Conventional Commits.
4. Open a PR with validation notes.

## Security
Please report vulnerabilities using `SECURITY.md`.

## License
MIT. See `LICENSE`.
