# PHASE 170 — CUT Scene Graph NLE Pane Compact Card

## Goal
Expose one compact media-native graph card in the NLE Scene Graph pane so users get richer graph context without opening the full shell surface.

## Rules
- Use the primary selected graph card when available.
- Show label, node type, display mode, modality, marker count, optional duration, sync badge, and visual bucket.
- Keep it summary-only and subordinate to the DAG viewport.

## Visible Signals
- `Compact Graph Card`
- `no primary graph card` fallback
- sync/bucket summary line
