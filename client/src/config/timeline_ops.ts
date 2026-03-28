/**
 * MARKER_OP-REGISTRY: Canonical timeline op-type registry.
 *
 * Single source of truth for all timeline op type strings.
 * Both frontend (TypeScript) and backend (Python) must stay in sync with this list.
 *
 * Backend mirror: src/api/routes/cut_routes.py → VALID_TIMELINE_OPS (frozenset)
 * Backend validation: _apply_timeline_ops() raises ValueError on unknown ops.
 *
 * Usage:
 *   import { type TimelineOpType } from '../config/timeline_ops';
 *   // applyTimelineOps receives Array<{ op: TimelineOpType; [key: string]: unknown }>
 *
 * @phase ENGINE_OPS
 * @task tb_1774424877_1
 */

export const TIMELINE_OP_TYPES = [
  // ─── Selection / view ───
  'set_selection',
  'set_view',

  // ─── Clip positioning ───
  'move_clip',
  'trim_clip',
  'slip_clip',
  'ripple_trim',
  'ripple_trim_to_playhead',
  'roll_edit',
  'slide_clip',
  'swap_clips',

  // ─── Clip lifecycle ───
  'insert_at',
  'overwrite_at',
  'split_at',
  'remove_clip',
  'ripple_delete',
  'replace_media',

  // ─── Clip properties ───
  'set_clip_color',
  'set_clip_meta',
  'set_transition',
  'set_effects',
  'reset_effects',
  'set_prop',
  'add_keyframe',
  'remove_keyframe',

  // ─── Sync ───
  'apply_sync_offset',

  // ─── Markers ───
  'delete_marker',

  // ─── Async / dedicated-endpoint proxies ───
  'run_pulse_analysis',
  'run_automontage_favorites',
] as const;

export type TimelineOpType = typeof TIMELINE_OP_TYPES[number];

/**
 * Runtime set for O(1) frontend validation before network round-trip.
 * Prevents "unsupported timeline op" 500s from unknown op strings.
 */
export const TIMELINE_OPS_SET: ReadonlySet<string> = new Set(TIMELINE_OP_TYPES);
