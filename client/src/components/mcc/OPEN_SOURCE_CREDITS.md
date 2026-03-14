# Open Source Credits

This module builds on open source frontend/runtime libraries.

## Direct Dependencies (Code + Build)

### UI and Runtime

- React
  - https://github.com/facebook/react
  - License: MIT

- TypeScript
  - https://github.com/microsoft/TypeScript
  - License: Apache-2.0

- Framer Motion
  - https://github.com/framer/motion
  - License: MIT

- react-draggable
  - https://github.com/react-grid-layout/react-draggable
  - License: MIT

### Graph and Workspace Rendering

- React Flow (`@xyflow/react`)
  - https://github.com/xyflow/xyflow
  - License: MIT

## Inspired Patterns (Not Vendored Source Trees)

These references describe workflow/UX patterns adapted in VETKA ecosystem
templates and orchestration, not copied upstream source trees inside this
module:

- OpenHands-style collaborative loop
  - VETKA template reference:
    `data/templates/workflows/openhands_collab_stub.json`
- G3 critic-coder loop
  - VETKA template reference:
    `data/templates/workflows/g3_critic_coder.json`
- Ralph single-agent loop
  - VETKA template reference:
    `data/templates/workflows/ralph_loop.json`
- n8n / ComfyUI workflow mapping patterns (converter-side in monorepo backend)
  - `src/services/converters/n8n_converter.py`
  - `src/services/converters/comfyui_converter.py`
  - `src/orchestration/dag_executor.py` (architecture note)

## Notes

- Preserve upstream attribution and licenses in derivative work.
- Additional dependencies are documented in the host client package manifest.
- Full monorepo audit marker:
  `docs/160_git/MARKER_160_OPENSOURCE_USAGE_AUDIT_2026-03-06.md`
