/**
 * MARKER_GAMMA-28 + LAYOUT-AUDIT: Workspace preset layout builders.
 *
 * Aligned with CUT_UNIFIED_VISION.md §1.1-1.3:
 * - Editing: Navigation + Analysis + Source/Program + Effects + Timeline
 * - Color: Scopes + ColorCorrector + LUTs prominent
 * - Audio: Mixer dominant, timeline tall
 *
 * Each builder creates a complete panel layout using the dockview addPanel API.
 */
import type { DockviewApi } from 'dockview-react';

export type PresetBuilder = (api: DockviewApi, scriptText: string) => void;

/**
 * EDITING workspace — lean NLE baseline per Unified Vision §1.1
 *
 * Navigation group: Project / Script / Graph
 * Analysis group: Inspector / Clip / History / StorySpace
 * Monitors: Source + Program
 * Effects group: Effects panel (Transitions = category inside Effects, not separate tab)
 * Timeline: full-width bottom
 *
 * NOT in editing default: Montage (AI), Markers (Window menu), Mixer (Audio ws),
 * Scopes/ColorCorrector/LutBrowser (Color ws)
 */
export function buildEditingLayout(api: DockviewApi, scriptText: string) {
  // Navigation tabs (left column top)
  api.addPanel({ id: 'project', component: 'project', title: 'Project' });
  api.addPanel({ id: 'script', component: 'script', title: 'Script', params: { scriptText }, position: { referencePanel: 'project', direction: 'within' } });
  api.addPanel({ id: 'graph', component: 'graph', title: 'Graph', position: { referencePanel: 'project', direction: 'within' } });
  // Source Monitor (center) + Program Monitor (right)
  api.addPanel({ id: 'source', component: 'source', title: 'SOURCE', position: { referencePanel: 'project', direction: 'right' } });
  api.addPanel({ id: 'program', component: 'program', title: 'PROGRAM', position: { referencePanel: 'source', direction: 'right' } });
  // Analysis tabs (left column bottom) — per Unified Vision §1.3
  api.addPanel({ id: 'inspector', component: 'inspector', title: 'Inspector', position: { referencePanel: 'project', direction: 'below' } });
  api.addPanel({ id: 'clip', component: 'clip', title: 'Clip', position: { referencePanel: 'inspector', direction: 'within' } });
  api.addPanel({ id: 'history', component: 'history', title: 'History', position: { referencePanel: 'inspector', direction: 'within' } });
  api.addPanel({ id: 'storyspace', component: 'storyspace', title: 'StorySpace', position: { referencePanel: 'inspector', direction: 'within' } });
  // Effects (right of Analysis) — Transitions is a category inside EffectsPanel (GAMMA-LAYOUT1)
  api.addPanel({ id: 'effects', component: 'effects', title: 'Effects', position: { referencePanel: 'inspector', direction: 'right' } });
  // Timeline (full-width bottom)
  api.addPanel({ id: 'timeline', component: 'timeline', title: 'Timeline', params: { scriptText }, position: { direction: 'below' } });
  // Sizes
  try { api.getPanel('project')?.api.setSize({ width: 320 }); } catch { /* ok */ }
  try { api.getPanel('timeline')?.api.setSize({ height: 300 }); } catch { /* ok */ }
  // Foreground panels
  try { api.getPanel('inspector')?.api.setActive(); } catch { /* ok */ }
  try { api.getPanel('effects')?.api.setActive(); } catch { /* ok */ }
}

/**
 * COLOR workspace — color grading focused
 * Scopes + ColorCorrector + LUTs prominent, Program Monitor large
 */
export function buildColorLayout(api: DockviewApi, scriptText: string) {
  api.addPanel({ id: 'source', component: 'source', title: 'SOURCE' });
  // Left column: minimal navigation
  api.addPanel({ id: 'project', component: 'project', title: 'Project', position: { referencePanel: 'source', direction: 'below' } });
  api.addPanel({ id: 'inspector', component: 'inspector', title: 'Inspector', position: { referencePanel: 'project', direction: 'within' } });
  api.addPanel({ id: 'clip', component: 'clip', title: 'Clip', position: { referencePanel: 'project', direction: 'within' } });
  api.addPanel({ id: 'history', component: 'history', title: 'History', position: { referencePanel: 'project', direction: 'within' } });
  // Center: Program Monitor
  api.addPanel({ id: 'program', component: 'program', title: 'PROGRAM', position: { referencePanel: 'source', direction: 'right' } });
  // Right: Color Corrector + LUTs
  api.addPanel({ id: 'colorcorrector', component: 'colorcorrector', title: 'Color', position: { referencePanel: 'program', direction: 'right' } });
  api.addPanel({ id: 'lutbrowser', component: 'lutbrowser', title: 'LUTs', position: { referencePanel: 'colorcorrector', direction: 'within' } });
  // Below Color: Scopes
  api.addPanel({ id: 'scopes', component: 'scopes', title: 'Scopes', position: { referencePanel: 'colorcorrector', direction: 'below' } });
  // Effects below left — Transitions is a category inside EffectsPanel (GAMMA-LAYOUT1)
  api.addPanel({ id: 'effects', component: 'effects', title: 'Effects', position: { referencePanel: 'project', direction: 'below' } });
  // Timeline
  api.addPanel({ id: 'timeline', component: 'timeline', title: 'Timeline', params: { scriptText }, position: { direction: 'below' } });
  try { api.getPanel('source')?.api.setSize({ width: 260 }); } catch { /* ok */ }
  try { api.getPanel('colorcorrector')?.api.setSize({ width: 300 }); } catch { /* ok */ }
  try { api.getPanel('timeline')?.api.setSize({ height: 240 }); } catch { /* ok */ }
  try { api.getPanel('colorcorrector')?.api.setActive(); } catch { /* ok */ }
  try { api.getPanel('scopes')?.api.setActive(); } catch { /* ok */ }
}

/**
 * AUDIO workspace — Mixer dominant, tall timeline for waveforms
 */
export function buildAudioLayout(api: DockviewApi, scriptText: string) {
  api.addPanel({ id: 'project', component: 'project', title: 'Project' });
  api.addPanel({ id: 'script', component: 'script', title: 'Script', params: { scriptText }, position: { referencePanel: 'project', direction: 'within' } });
  // Source/Program stacked
  api.addPanel({ id: 'source', component: 'source', title: 'SOURCE', position: { referencePanel: 'project', direction: 'right' } });
  api.addPanel({ id: 'program', component: 'program', title: 'PROGRAM', position: { referencePanel: 'source', direction: 'within' } });
  // Mixer — own group, wide
  api.addPanel({ id: 'mixer', component: 'mixer', title: 'Mixer', position: { referencePanel: 'source', direction: 'right' } });
  // Analysis below left
  api.addPanel({ id: 'inspector', component: 'inspector', title: 'Inspector', position: { referencePanel: 'project', direction: 'below' } });
  api.addPanel({ id: 'clip', component: 'clip', title: 'Clip', position: { referencePanel: 'inspector', direction: 'within' } });
  api.addPanel({ id: 'history', component: 'history', title: 'History', position: { referencePanel: 'inspector', direction: 'within' } });
  // Effects right of analysis — Transitions is a category inside EffectsPanel (GAMMA-LAYOUT1)
  api.addPanel({ id: 'effects', component: 'effects', title: 'Effects', position: { referencePanel: 'inspector', direction: 'right' } });
  // Timeline — tall for waveform visibility
  api.addPanel({ id: 'timeline', component: 'timeline', title: 'Timeline', params: { scriptText }, position: { direction: 'below' } });
  try { api.getPanel('project')?.api.setSize({ width: 260 }); } catch { /* ok */ }
  try { api.getPanel('mixer')?.api.setSize({ width: 280 }); } catch { /* ok */ }
  try { api.getPanel('timeline')?.api.setSize({ height: 380 }); } catch { /* ok */ }
  try { api.getPanel('mixer')?.api.setActive(); } catch { /* ok */ }
  try { api.getPanel('effects')?.api.setActive(); } catch { /* ok */ }
}

/**
 * MULTICAM workspace — multi-angle viewer + wide timeline (FCP7 Ch.42)
 * Program Monitor large, Source stacked with angle grid concept
 */
export function buildMulticamLayout(api: DockviewApi, scriptText: string) {
  // Source (left) — will show multicam angle grid when MulticamViewer is ready
  api.addPanel({ id: 'source', component: 'source', title: 'SOURCE' });
  // Program (center, large) — shows switched output
  api.addPanel({ id: 'program', component: 'program', title: 'PROGRAM', position: { referencePanel: 'source', direction: 'right' } });
  // Right: Project + Clip inspector stacked
  api.addPanel({ id: 'project', component: 'project', title: 'Project', position: { referencePanel: 'program', direction: 'right' } });
  api.addPanel({ id: 'clip', component: 'clip', title: 'Clip', position: { referencePanel: 'project', direction: 'within' } });
  // Below Source: Mixer (audio monitoring during multicam)
  api.addPanel({ id: 'mixer', component: 'mixer', title: 'Mixer', position: { referencePanel: 'source', direction: 'below' } });
  // Timeline — wide, for multicam cutting
  api.addPanel({ id: 'timeline', component: 'timeline', title: 'Timeline', params: { scriptText }, position: { direction: 'below' } });
  // Sizes: program large, timeline tall
  try { api.getPanel('source')?.api.setSize({ width: 300 }); } catch { /* ok */ }
  try { api.getPanel('project')?.api.setSize({ width: 240 }); } catch { /* ok */ }
  try { api.getPanel('timeline')?.api.setSize({ height: 340 }); } catch { /* ok */ }
  try { api.getPanel('program')?.api.setActive(); } catch { /* ok */ }
}

export const PRESET_BUILDERS: Record<string, PresetBuilder> = {
  editing: buildEditingLayout,
  color: buildColorLayout,
  audio: buildAudioLayout,
  multicam: buildMulticamLayout,
  custom: buildEditingLayout,
};
