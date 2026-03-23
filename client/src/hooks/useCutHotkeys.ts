/**
 * MARKER_185.7: Centralized Hotkey Registry for CUT NLE.
 *
 * Two built-in presets: Premiere Pro and Final Cut Pro 7.
 * User can override any binding via custom map (persisted in localStorage).
 *
 * Architecture:
 *   Preset (key -> action)  +  Handlers (action -> callback)  =  keydown listener
 *
 * Components register handlers via useCutHotkeys({ handlers }).
 * The hook resolves: keydown event -> active preset -> action name -> handler call.
 *
 * @phase 185
 * @wave 3
 * @status active
 */

// ─── Action names ───────────────────────────────────────────────────
// Every bindable action in CUT NLE. Add new actions here as features grow.

export type CutHotkeyAction =
  // Playback
  | 'playPause'
  | 'stop'
  | 'shuttleBack'
  | 'shuttleForward'
  | 'frameStepBack'
  | 'frameStepForward'
  | 'goToStart'
  | 'goToEnd'
  | 'cyclePlaybackRate'
  | 'fiveFrameStepBack'
  | 'fiveFrameStepForward'
  // Marking
  | 'markIn'
  | 'markOut'
  | 'clearIn'
  | 'clearOut'
  | 'clearInOut'
  | 'goToIn'
  | 'goToOut'
  // Editing
  | 'undo'
  | 'redo'
  | 'deleteClip'
  | 'splitClip'
  | 'rippleDelete'
  | 'selectAll'
  | 'copy'
  | 'cut'
  | 'paste'
  | 'pasteInsert'
  | 'nudgeLeft'
  | 'nudgeRight'
  // Tools
  | 'razorTool'
  | 'selectTool'
  | 'insertEdit'
  | 'overwriteEdit'
  | 'replaceEdit'
  | 'fitToFill'
  | 'superimpose'
  // MARKER_W5.TRIM: Trim tools (FCP7 Ch.44)
  | 'slipTool'
  | 'slideTool'
  | 'rippleTool'
  | 'rollTool'
  // Markers
  | 'addMarker'
  | 'addComment'
  | 'nextMarker'
  | 'prevMarker'
  // MARKER_KF67: Keyframe navigation
  | 'nextKeyframe'
  | 'prevKeyframe'
  | 'addKeyframe'
  // MARKER_B3.2: Record Mode
  | 'toggleRecordMode'
  // MARKER_FCP7.SPEED: Speed dialog
  | 'openSpeedControl'
  // Mark operations
  | 'markClip'
  | 'playInToOut'
  // Sequence operations
  | 'liftClip'
  | 'extractClip'
  | 'closeGap'
  | 'extendEdit'
  // MARKER_SPLIT-EDIT: L-cut / J-cut (FCP7 Ch.41)
  | 'splitEditLCut'
  | 'splitEditJCut'
  // MARKER_TRANSITION: Default transition
  | 'addDefaultTransition'
  // Navigation
  | 'prevEditPoint'
  | 'nextEditPoint'
  // MARKER_W5.MF: Match Frame + Q toggle (FCP7 Ch.50)
  | 'matchFrame'
  | 'toggleSourceProgram'
  // View
  | 'zoomIn'
  | 'zoomOut'
  | 'zoomToFit'
  | 'cycleTrackHeight'
  // Project
  | 'importMedia'
  | 'saveProject'
  // Panel focus
  | 'focusSource'
  | 'focusProgram'
  | 'focusTimeline'
  | 'focusProject'
  | 'focusEffects'
  // Linked selection + Snap
  | 'toggleLinkedSelection'
  | 'toggleSnap'
  // Subclip
  | 'makeSubclip'
  // CUT-specific
  | 'sceneDetect'
  | 'toggleViewMode'
  | 'escapeContext';

// ─── MARKER_FOCUS: Panel Focus Scoping ───────────────────────────────
// Defines which panels each action is allowed in.
// 'global' = fires regardless of focusedPanel.
// Array = fires only when focusedPanel is one of listed values.
// null/undefined in focusedPanel = treated as 'timeline' (default focus).

export type FocusPanelId = 'source' | 'program' | 'timeline' | 'project' | 'script' | 'dag' | 'effects';

type ActionScope = 'global' | FocusPanelId[];

export const ACTION_SCOPE: Record<CutHotkeyAction, ActionScope> = {
  // Playback — works in source, program, and timeline
  playPause:           'global',
  stop:                'global',
  shuttleBack:         'global',
  shuttleForward:      'global',
  frameStepBack:       'global',
  frameStepForward:    'global',
  goToStart:           'global',
  goToEnd:             'global',
  cyclePlaybackRate:   'global',
  fiveFrameStepBack:   'global',
  fiveFrameStepForward:'global',

  // Marking — source: source marks, program/timeline: sequence marks
  markIn:              'global',
  markOut:             'global',
  clearIn:             'global',
  clearOut:            'global',
  clearInOut:          'global',
  goToIn:              'global',
  goToOut:             'global',

  // Editing — timeline only
  deleteClip:          'global',
  splitClip:           'global',
  rippleDelete:        'global',
  nudgeLeft:           'global',
  nudgeRight:          'global',
  insertEdit:          'global',
  overwriteEdit:       'global',
  replaceEdit:         'global',
  fitToFill:           'global',
  superimpose:         'global',

  // Tools — global (tool switch applies to next timeline interaction regardless of focused panel)
  razorTool:           'global',
  selectTool:          'global',
  // MARKER_W5.TRIM: Trim tools — global
  slipTool:            'global',
  slideTool:           'global',
  rippleTool:          'global',
  rollTool:            'global',

  // Navigation — timeline/program
  prevEditPoint:       'global',
  nextEditPoint:       'global',
  // MARKER_W5.MF: Match Frame + Q toggle
  matchFrame:          'global',
  toggleSourceProgram: 'global',

  // Markers — source, program, timeline
  addMarker:           'global',
  addComment:          'global',
  nextMarker:          'global',
  prevMarker:          'global',
  nextKeyframe:        'global',
  prevKeyframe:        'global',
  addKeyframe:         'global',
  toggleRecordMode:    'global',  // MARKER_B3.2
  openSpeedControl:    'global',

  // Mark operations
  markClip:            'global',
  playInToOut:         'global',

  // Sequence operations — timeline only
  liftClip:            'global',
  extractClip:         'global',
  closeGap:            'global',
  extendEdit:          'global',
  splitEditLCut:       'global',
  splitEditJCut:       'global',
  addDefaultTransition:'global',

  // Global — always fire
  undo:                'global',
  redo:                'global',
  selectAll:           'global',
  copy:                'global',
  cut:                 'global',
  paste:               'global',
  pasteInsert:         'global',
  zoomIn:              'global',
  zoomOut:             'global',
  zoomToFit:           'global',
  cycleTrackHeight:    'global',
  importMedia:         'global',
  saveProject:         'global',
  focusSource:         'global',
  focusProgram:        'global',
  focusTimeline:       'global',
  focusProject:        'global',
  focusEffects:        'global',
  toggleLinkedSelection: 'global',
  toggleSnap:          'global',
  makeSubclip:         'global',
  sceneDetect:         'global',
  toggleViewMode:      'global',
  escapeContext:       'global',
};

// ─── Key notation ───────────────────────────────────────────────────
// Format: modifier+key or just key.
// Modifiers: Cmd, Ctrl, Shift, Alt (Cmd = Meta on Mac, Ctrl on Win).
// Key: Space, ArrowLeft, ArrowRight, Delete, Backspace, Home, End,
//      Enter, Escape, or single char (a-z, 0-9, +, -, =).
// Examples: 'Cmd+z', 'Shift+Delete', 'Space', 'b', 'Cmd+Shift+z'

export type HotkeyBinding = string;

export type HotkeyPresetName = 'premiere' | 'fcp7' | 'custom';

export type HotkeyMap = Partial<Record<CutHotkeyAction, HotkeyBinding>>;

// ─── Built-in presets ───────────────────────────────────────────────
// Populated with known defaults. Grok research will fill remaining gaps.

export const PREMIERE_PRESET: HotkeyMap = {
  // Playback
  playPause:         'Space',
  stop:              'k',
  shuttleBack:       'j',
  shuttleForward:    'l',
  frameStepBack:     'ArrowLeft',
  frameStepForward:  'ArrowRight',
  fiveFrameStepBack: 'Shift+ArrowLeft',
  fiveFrameStepForward: 'Shift+ArrowRight',
  goToStart:         'Home',
  goToEnd:           'End',
  cyclePlaybackRate: 'Cmd+Shift+r',
  // Marking
  markIn:            'i',
  markOut:           'o',
  clearIn:           'Alt+i',
  clearOut:          'Alt+o',
  clearInOut:        'Cmd+Shift+x',
  goToIn:            'Shift+i',
  goToOut:           'Shift+o',
  markClip:          'x',
  playInToOut:       'Shift+\\',
  // Sequence operations
  liftClip:          ';',
  extractClip:       "'",
  closeGap:          'Alt+Backspace',
  extendEdit:        'e',
  // MARKER_SPLIT-EDIT: L-cut / J-cut
  splitEditLCut:     'Alt+e',
  splitEditJCut:     'Alt+Shift+e',
  addDefaultTransition: 'Cmd+t',
  // Editing
  undo:              'Cmd+z',
  redo:              'Cmd+Shift+z',
  deleteClip:        'Delete',
  splitClip:         'Cmd+k',
  rippleDelete:      'Shift+Delete',
  selectAll:         'Cmd+a',
  copy:              'Cmd+c',
  cut:               'Cmd+x',
  paste:             'Cmd+v',
  pasteInsert:       'Cmd+Shift+v',
  nudgeLeft:         'Alt+ArrowLeft',
  nudgeRight:        'Alt+ArrowRight',
  // Tools
  razorTool:         'c',
  selectTool:        'v',
  insertEdit:        ',',
  overwriteEdit:     '.',
  replaceEdit:       'F11',
  fitToFill:         'Shift+F11',
  superimpose:       'F12',
  // MARKER_W5.TRIM: Premiere trim tools
  slipTool:          'y',
  slideTool:         'u',
  rippleTool:        'b',
  rollTool:          'n',
  // Markers
  addMarker:         'm',
  addComment:        'Shift+m',
  nextMarker:        'Shift+ArrowDown',
  prevMarker:        'Shift+ArrowUp',
  nextKeyframe:      'Shift+k',
  prevKeyframe:      'Alt+k',
  addKeyframe:       'Ctrl+k',
  toggleRecordMode:  'Cmd+Shift+k',  // MARKER_B3.2
  openSpeedControl:  'Cmd+j',
  // Navigation
  prevEditPoint:     'ArrowUp',
  nextEditPoint:     'ArrowDown',
  // MARKER_W5.MF: Match Frame + Q toggle
  matchFrame:        'f',
  toggleSourceProgram: 'q',
  // View
  zoomIn:            '=',
  zoomOut:           '-',
  zoomToFit:         '\\',
  cycleTrackHeight:  'Shift+t',
  // Project
  importMedia:       'Cmd+i',
  saveProject:       'Cmd+s',
  // Panel focus (Premiere: ⇧1-5, CUT: ⌘1-5)
  focusSource:       'Cmd+1',
  focusProgram:      'Cmd+2',
  focusTimeline:     'Cmd+3',
  focusProject:      'Cmd+4',
  focusEffects:      'Cmd+5',
  // Linked selection + Snap
  toggleLinkedSelection: 'Cmd+l',
  toggleSnap:        'n',
  makeSubclip:       'Cmd+u',
  // CUT-specific
  sceneDetect:       'Cmd+d',
  toggleViewMode:    'Cmd+\\',
  escapeContext:     'Escape',
};

export const FCP7_PRESET: HotkeyMap = {
  // Playback
  playPause:         'Space',
  stop:              'k',
  shuttleBack:       'j',
  shuttleForward:    'l',
  frameStepBack:     'ArrowLeft',
  frameStepForward:  'ArrowRight',
  fiveFrameStepBack: 'Shift+ArrowLeft',
  fiveFrameStepForward: 'Shift+ArrowRight',
  goToStart:         'Home',
  goToEnd:           'End',
  cyclePlaybackRate: 'Cmd+Shift+r',
  // Marking
  markIn:            'i',
  markOut:           'o',
  clearIn:           'Alt+i',
  clearOut:          'Alt+o',
  goToIn:            'Shift+i',
  goToOut:           'Shift+o',
  clearInOut:        'Alt+x',
  markClip:          'x',
  playInToOut:       'Ctrl+\\',
  // Sequence operations (FCP7 Ch.32)
  liftClip:          ';',
  extractClip:       "'",
  closeGap:          'Alt+Backspace',
  extendEdit:        'e',
  splitEditLCut:     'Alt+e',
  splitEditJCut:     'Alt+Shift+e',
  addDefaultTransition: 'Cmd+t',
  // Editing
  undo:              'Cmd+z',
  redo:              'Cmd+Shift+z',
  deleteClip:        'Delete',
  // MARKER_CTRLV_FIX: FCP7 uses ⌘K for Add Edit, NOT Ctrl+V (collides with paste)
  splitClip:         'Cmd+k',
  rippleDelete:      'Shift+Delete',
  selectAll:         'Cmd+a',
  copy:              'Cmd+c',
  cut:               'Cmd+x',
  paste:             'Cmd+v',
  pasteInsert:       'Cmd+Shift+v',
  nudgeLeft:         'Alt+ArrowLeft',
  nudgeRight:        'Alt+ArrowRight',
  // Tools
  razorTool:         'b',
  selectTool:        'a',
  insertEdit:        ',',
  overwriteEdit:     '.',
  replaceEdit:       'F11',
  fitToFill:         'Shift+F11',
  superimpose:       'F12',
  // MARKER_W5.TRIM: FCP7 trim tools — Y=slip, U=slide (S conflicts with snap toggle)
  slipTool:          'y',
  slideTool:         'u',
  rippleTool:        'r',
  rollTool:          'Shift+r',
  // Markers
  addMarker:         'm',
  addComment:        'Shift+m',
  nextMarker:        'Shift+ArrowDown',
  prevMarker:        'Shift+ArrowUp',
  nextKeyframe:      'Shift+k',
  prevKeyframe:      'Alt+k',
  addKeyframe:       'Ctrl+k',
  toggleRecordMode:  'Cmd+Shift+k',  // MARKER_B3.2
  openSpeedControl:  'Cmd+j',
  // Navigation
  prevEditPoint:     'ArrowUp',
  nextEditPoint:     'ArrowDown',
  // MARKER_W5.MF: Match Frame + Q toggle (FCP7)
  matchFrame:        'f',
  toggleSourceProgram: 'q',
  // View
  zoomIn:            'Cmd+=',
  zoomOut:           'Cmd+-',
  zoomToFit:         'Shift+z',
  cycleTrackHeight:  'Shift+t',
  // Project
  importMedia:       'Cmd+i',
  saveProject:       'Cmd+s',
  // Panel focus (FCP7: ⌘1-4, CUT: ⌘1-5)
  focusSource:       'Cmd+1',
  focusProgram:      'Cmd+2',
  focusTimeline:     'Cmd+3',
  focusProject:      'Cmd+4',
  focusEffects:      'Cmd+5',
  // Linked selection (FCP7 standard: Shift+L) + Snap (N)
  toggleLinkedSelection: 'Shift+l',
  toggleSnap:        'n',
  makeSubclip:       'Cmd+u',
  // CUT-specific
  sceneDetect:       'Cmd+d',
  toggleViewMode:    'Cmd+\\',
  escapeContext:     'Escape',
};

export const PRESETS: Record<Exclude<HotkeyPresetName, 'custom'>, HotkeyMap> = {
  premiere: PREMIERE_PRESET,
  fcp7: FCP7_PRESET,
};

// ─── Persistence ────────────────────────────────────────────────────

const LS_PRESET_KEY = 'cut_hotkey_preset';
const LS_CUSTOM_KEY = 'cut_hotkey_custom';

export function loadPresetName(): HotkeyPresetName {
  try {
    const v = localStorage.getItem(LS_PRESET_KEY);
    if (v === 'premiere' || v === 'fcp7' || v === 'custom') return v;
  } catch { /* SSR / iframe sandbox */ }
  return 'premiere'; // default
}

export function savePresetName(name: HotkeyPresetName): void {
  try { localStorage.setItem(LS_PRESET_KEY, name); } catch { /* noop */ }
}

export function loadCustomOverrides(): HotkeyMap {
  try {
    const raw = localStorage.getItem(LS_CUSTOM_KEY);
    if (raw) return JSON.parse(raw) as HotkeyMap;
  } catch { /* corrupt data */ }
  return {};
}

export function saveCustomOverrides(map: HotkeyMap): void {
  try { localStorage.setItem(LS_CUSTOM_KEY, JSON.stringify(map)); } catch { /* noop */ }
}

// ─── Key matching engine ────────────────────────────────────────────

interface ParsedBinding {
  cmd: boolean;
  ctrl: boolean;
  shift: boolean;
  alt: boolean;
  key: string; // lowercase
}

function parseBinding(binding: HotkeyBinding): ParsedBinding {
  const parts = binding.split('+');
  const result: ParsedBinding = { cmd: false, ctrl: false, shift: false, alt: false, key: '' };
  for (const p of parts) {
    const lower = p.toLowerCase().trim();
    if (lower === 'cmd' || lower === 'meta') result.cmd = true;
    else if (lower === 'ctrl') result.ctrl = true;
    else if (lower === 'shift') result.shift = true;
    else if (lower === 'alt' || lower === 'opt' || lower === 'option') result.alt = true;
    else result.key = lower;
  }
  return result;
}

function normalizeEventKey(e: KeyboardEvent): string {
  // Map event.key / event.code to our binding notation
  if (e.code === 'Space') return 'space';
  if (e.key === 'ArrowLeft' || e.code === 'ArrowLeft') return 'arrowleft';
  if (e.key === 'ArrowRight' || e.code === 'ArrowRight') return 'arrowright';
  if (e.key === 'ArrowUp' || e.code === 'ArrowUp') return 'arrowup';
  if (e.key === 'ArrowDown' || e.code === 'ArrowDown') return 'arrowdown';
  if (e.key === 'Delete') return 'delete';
  if (e.key === 'Backspace') return 'backspace';
  if (e.key === 'Home') return 'home';
  if (e.key === 'End') return 'end';
  if (e.key === 'Enter') return 'enter';
  if (e.key === 'Escape') return 'escape';
  if (e.key === 'Tab') return 'tab';
  // Function keys
  if (/^F\d+$/i.test(e.key)) return e.key.toLowerCase();
  // Regular keys
  return e.key.toLowerCase();
}

function matchesEvent(parsed: ParsedBinding, e: KeyboardEvent): boolean {
  const wantCmd = parsed.cmd;
  const wantCtrl = parsed.ctrl;
  const hasMetaOrCtrl = e.metaKey || e.ctrlKey;

  // Cmd means metaKey on Mac, ctrlKey on non-Mac
  if (wantCmd && !hasMetaOrCtrl) return false;
  if (!wantCmd && !wantCtrl && hasMetaOrCtrl) return false;
  if (wantCtrl && !e.ctrlKey) return false;

  if (parsed.shift !== e.shiftKey) return false;
  if (parsed.alt !== e.altKey) return false;

  const eventKey = normalizeEventKey(e);
  return eventKey === parsed.key;
}

// ─── Resolved map builder ───────────────────────────────────────────

export type ResolvedHotkeyMap = Map<CutHotkeyAction, ParsedBinding>;

export function resolveMap(presetName: HotkeyPresetName, customOverrides: HotkeyMap): ResolvedHotkeyMap {
  // Start with selected preset (or premiere as base for custom)
  const base: HotkeyMap = presetName === 'custom'
    ? { ...PREMIERE_PRESET }
    : { ...(PRESETS[presetName] || PREMIERE_PRESET) };

  // Apply custom overrides on top
  const merged = { ...base, ...customOverrides };

  const map = new Map<CutHotkeyAction, ParsedBinding>();
  for (const [action, binding] of Object.entries(merged)) {
    if (binding) {
      map.set(action as CutHotkeyAction, parseBinding(binding));
    }
  }
  return map;
}

// ─── Reverse lookup (for UI labels: action -> "Cmd+D") ─────────────

export function getBindingLabel(
  action: CutHotkeyAction,
  presetName: HotkeyPresetName = 'premiere',
  customOverrides: HotkeyMap = {}
): string {
  const base = presetName === 'custom' ? PREMIERE_PRESET : (PRESETS[presetName] || PREMIERE_PRESET);
  const merged = { ...base, ...customOverrides };
  return merged[action] || '';
}

// ─── All actions list (for settings UI) ─────────────────────────────

export const ALL_ACTIONS: { action: CutHotkeyAction; label: string; group: string }[] = [
  // Playback
  { action: 'playPause', label: 'Play / Pause', group: 'Playback' },
  { action: 'stop', label: 'Stop', group: 'Playback' },
  { action: 'shuttleBack', label: 'Shuttle Back (5s)', group: 'Playback' },
  { action: 'shuttleForward', label: 'Shuttle Forward (5s)', group: 'Playback' },
  { action: 'frameStepBack', label: 'Frame Step Back', group: 'Playback' },
  { action: 'frameStepForward', label: 'Frame Step Forward', group: 'Playback' },
  { action: 'goToStart', label: 'Go to Start', group: 'Playback' },
  { action: 'goToEnd', label: 'Go to End', group: 'Playback' },
  { action: 'cyclePlaybackRate', label: 'Cycle Playback Rate', group: 'Playback' },
  { action: 'fiveFrameStepBack', label: '5-Frame Step Back', group: 'Playback' },
  { action: 'fiveFrameStepForward', label: '5-Frame Step Forward', group: 'Playback' },
  // Marking
  { action: 'markIn', label: 'Set Mark In', group: 'Marking' },
  { action: 'markOut', label: 'Set Mark Out', group: 'Marking' },
  { action: 'clearIn', label: 'Clear Mark In', group: 'Marking' },
  { action: 'clearOut', label: 'Clear Mark Out', group: 'Marking' },
  { action: 'clearInOut', label: 'Clear In/Out', group: 'Marking' },
  { action: 'goToIn', label: 'Go to Mark In', group: 'Marking' },
  { action: 'goToOut', label: 'Go to Mark Out', group: 'Marking' },
  // Editing
  { action: 'undo', label: 'Undo', group: 'Editing' },
  { action: 'redo', label: 'Redo', group: 'Editing' },
  { action: 'deleteClip', label: 'Delete Clip', group: 'Editing' },
  { action: 'splitClip', label: 'Split / Razor', group: 'Editing' },
  { action: 'rippleDelete', label: 'Ripple Delete', group: 'Editing' },
  { action: 'selectAll', label: 'Select All', group: 'Editing' },
  { action: 'copy', label: 'Copy', group: 'Editing' },
  { action: 'cut', label: 'Cut', group: 'Editing' },
  { action: 'paste', label: 'Paste', group: 'Editing' },
  { action: 'pasteInsert', label: 'Paste Insert', group: 'Editing' },
  { action: 'nudgeLeft', label: 'Nudge Left', group: 'Editing' },
  { action: 'nudgeRight', label: 'Nudge Right', group: 'Editing' },
  // Tools
  { action: 'razorTool', label: 'Razor / Blade Tool', group: 'Tools' },
  { action: 'selectTool', label: 'Selection Tool', group: 'Tools' },
  { action: 'insertEdit', label: 'Insert Edit', group: 'Tools' },
  { action: 'overwriteEdit', label: 'Overwrite Edit', group: 'Tools' },
  { action: 'replaceEdit', label: 'Replace Edit (F11)', group: 'Tools' },
  { action: 'fitToFill', label: 'Fit to Fill (Shift+F11)', group: 'Tools' },
  { action: 'superimpose', label: 'Superimpose (F12)', group: 'Tools' },
  // MARKER_W5.TRIM: Trim tools
  { action: 'slipTool', label: 'Slip Tool', group: 'Tools' },
  { action: 'slideTool', label: 'Slide Tool', group: 'Tools' },
  { action: 'rippleTool', label: 'Ripple Edit Tool', group: 'Tools' },
  { action: 'rollTool', label: 'Roll Edit Tool', group: 'Tools' },
  // Markers
  { action: 'addMarker', label: 'Add Marker', group: 'Markers' },
  { action: 'addComment', label: 'Add Comment Marker', group: 'Markers' },
  { action: 'nextMarker', label: 'Next Marker', group: 'Markers' },
  { action: 'prevMarker', label: 'Previous Marker', group: 'Markers' },
  { action: 'nextKeyframe', label: 'Next Keyframe', group: 'Keyframes' },
  { action: 'prevKeyframe', label: 'Previous Keyframe', group: 'Keyframes' },
  { action: 'addKeyframe', label: 'Add Keyframe', group: 'Keyframes' },
  { action: 'toggleRecordMode', label: 'Toggle Record Mode', group: 'Keyframes' },
  { action: 'openSpeedControl', label: 'Change Speed (⌘J)', group: 'Tools' },
  // Mark operations
  { action: 'markClip', label: 'Mark Clip (X)', group: 'Marking' },
  { action: 'playInToOut', label: 'Play In to Out', group: 'Marking' },
  // Sequence operations
  { action: 'liftClip', label: 'Lift (leave gap)', group: 'Sequence' },
  { action: 'extractClip', label: 'Extract (close gap)', group: 'Sequence' },
  { action: 'closeGap', label: 'Close Gap', group: 'Sequence' },
  { action: 'extendEdit', label: 'Extend Edit', group: 'Sequence' },
  { action: 'splitEditLCut', label: 'L-Cut (video ends, audio continues)', group: 'Sequence' },
  { action: 'splitEditJCut', label: 'J-Cut (audio starts, video later)', group: 'Sequence' },
  { action: 'addDefaultTransition', label: 'Add Default Transition (⌘T)', group: 'Sequence' },
  // Navigation
  { action: 'prevEditPoint', label: 'Previous Edit Point', group: 'Navigation' },
  { action: 'nextEditPoint', label: 'Next Edit Point', group: 'Navigation' },
  // MARKER_W5.MF
  { action: 'matchFrame', label: 'Match Frame (F)', group: 'Navigation' },
  { action: 'toggleSourceProgram', label: 'Toggle Source/Program (Q)', group: 'Navigation' },
  // View
  { action: 'zoomIn', label: 'Zoom In', group: 'View' },
  { action: 'zoomOut', label: 'Zoom Out', group: 'View' },
  { action: 'zoomToFit', label: 'Zoom to Fit', group: 'View' },
  { action: 'cycleTrackHeight', label: 'Cycle Track Height (S/M/L)', group: 'View' },
  // Project
  { action: 'importMedia', label: 'Import Media', group: 'Project' },
  { action: 'saveProject', label: 'Save Project', group: 'Project' },
  // Panel focus
  { action: 'focusSource', label: 'Focus Source Monitor', group: 'Window' },
  { action: 'focusProgram', label: 'Focus Program Monitor', group: 'Window' },
  { action: 'focusTimeline', label: 'Focus Timeline', group: 'Window' },
  { action: 'focusProject', label: 'Focus Project Panel', group: 'Window' },
  { action: 'focusEffects', label: 'Focus Effects Panel', group: 'Window' },
  { action: 'toggleLinkedSelection', label: 'Toggle Linked Selection', group: 'Timeline' },
  { action: 'toggleSnap', label: 'Toggle Snap (N)', group: 'Timeline' },
  { action: 'makeSubclip', label: 'Make Subclip (Cmd+U)', group: 'Editing' },
  // CUT
  { action: 'sceneDetect', label: 'Detect Scenes', group: 'CUT' },
  { action: 'toggleViewMode', label: 'Toggle NLE / Debug', group: 'CUT' },
  { action: 'escapeContext', label: 'Cancel / Close', group: 'CUT' },
];

// ─── Hook ───────────────────────────────────────────────────────────

import { useEffect, useRef, useCallback, useState } from 'react';
import { useCutEditorStore } from '../store/useCutEditorStore';

export type CutHotkeyHandlers = Partial<Record<CutHotkeyAction, () => void | Promise<void>>>;

interface UseCutHotkeysOptions {
  /** Action handlers. Only provided actions will fire. */
  handlers: CutHotkeyHandlers;
  /** Override preset (default: read from localStorage). */
  preset?: HotkeyPresetName;
  /** Disable all hotkeys (e.g. when modal is open). */
  disabled?: boolean;
}

interface UseCutHotkeysReturn {
  /** Current active preset name. */
  presetName: HotkeyPresetName;
  /** Switch to a different preset. */
  setPreset: (name: HotkeyPresetName) => void;
  /** Get human-readable binding for an action. */
  labelFor: (action: CutHotkeyAction) => string;
  /** Custom overrides map (for settings UI). */
  customOverrides: HotkeyMap;
  /** Update a single custom override. */
  setCustomBinding: (action: CutHotkeyAction, binding: HotkeyBinding) => void;
  /** Reset custom overrides. */
  resetCustom: () => void;
}

export function useCutHotkeys(options: UseCutHotkeysOptions): UseCutHotkeysReturn {
  const { handlers, disabled = false } = options;

  const [presetName, setPresetNameState] = useState<HotkeyPresetName>(
    () => options.preset || loadPresetName()
  );
  const [customOverrides, setCustomOverrides] = useState<HotkeyMap>(loadCustomOverrides);

  // MARKER_C6.2: Sync preset when changed from HotkeyPresetSelector
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === 'cut_hotkey_preset' && e.newValue) {
        const v = e.newValue as HotkeyPresetName;
        if (v === 'premiere' || v === 'fcp7' || v === 'custom') {
          setPresetNameState(v);
        }
      }
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  // Keep handlers in a ref so the keydown listener always sees latest
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  const resolvedRef = useRef<ResolvedHotkeyMap>(resolveMap(presetName, customOverrides));

  // Rebuild resolved map when preset or overrides change
  useEffect(() => {
    resolvedRef.current = resolveMap(presetName, customOverrides);
  }, [presetName, customOverrides]);

  // Keydown listener
  useEffect(() => {
    if (disabled) return;

    const onKeyDown = (e: KeyboardEvent) => {
      // Skip if typing in form elements
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      // Also skip if contentEditable
      if ((e.target as HTMLElement)?.isContentEditable) return;

      const resolved = resolvedRef.current;
      // MARKER_FOCUS: Read current focused panel for scope check
      const focusedPanel = useCutEditorStore.getState().focusedPanel ?? 'timeline';

      for (const [action, parsed] of resolved) {
        if (matchesEvent(parsed, e)) {
          // MARKER_FOCUS: Check panel scope before dispatching
          const scope = ACTION_SCOPE[action];
          if (scope !== 'global') {
            if (!scope.includes(focusedPanel as FocusPanelId)) {
              return; // action not allowed in this panel — swallow silently
            }
          }

          const handler = handlersRef.current[action];
          if (handler) {
            e.preventDefault();
            e.stopPropagation();
            const result = handler();
            if (result instanceof Promise) {
              result.catch((err) => console.error(`[CUT Hotkey] ${action} failed:`, err));
            }
          }
          return; // first match wins
        }
      }
    };

    // MARKER_HOTKEY_CAPTURE: Use capture phase to intercept before dockview stopPropagation
    window.addEventListener('keydown', onKeyDown, { capture: true });
    return () => window.removeEventListener('keydown', onKeyDown, { capture: true });
  }, [disabled]);

  // Preset switcher
  const setPreset = useCallback((name: HotkeyPresetName) => {
    setPresetNameState(name);
    savePresetName(name);
  }, []);

  // Label lookup
  const labelFor = useCallback(
    (action: CutHotkeyAction) => getBindingLabel(action, presetName, customOverrides),
    [presetName, customOverrides]
  );

  // Custom binding editor
  const setCustomBinding = useCallback((action: CutHotkeyAction, binding: HotkeyBinding) => {
    setCustomOverrides((prev) => {
      const next = { ...prev, [action]: binding };
      saveCustomOverrides(next);
      return next;
    });
  }, []);

  const resetCustom = useCallback(() => {
    setCustomOverrides({});
    saveCustomOverrides({});
  }, []);

  return {
    presetName,
    setPreset,
    labelFor,
    customOverrides,
    setCustomBinding,
    resetCustom,
  };
}
