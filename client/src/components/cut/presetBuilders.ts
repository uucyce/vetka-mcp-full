/**
 * MARKER_GAMMA-28: Workspace preset layout builders.
 *
 * Extracted from DockviewLayout.tsx so MenuBar can also use them
 * for workspace switching without reload.
 *
 * Each builder creates a complete panel layout using the dockview addPanel API.
 */
import type { DockviewApi } from 'dockview-react';

export type PresetBuilder = (api: DockviewApi, scriptText: string) => void;

export function buildEditingLayout(api: DockviewApi, scriptText: string) {
  // Left column: Project (with Script and Graph as tabs)
  api.addPanel({ id: 'project', component: 'project', title: 'Project' });
  api.addPanel({ id: 'script', component: 'script', title: 'Script', params: { scriptText }, position: { referencePanel: 'project', direction: 'within' } });
  api.addPanel({ id: 'graph', component: 'graph', title: 'Graph', position: { referencePanel: 'project', direction: 'within' } });
  // Source Monitor (center) + Program Monitor (right)
  api.addPanel({ id: 'source', component: 'source', title: 'SOURCE', position: { referencePanel: 'project', direction: 'right' } });
  api.addPanel({ id: 'program', component: 'program', title: 'PROGRAM', position: { referencePanel: 'source', direction: 'right' } });
  // MARKER_GAMMA-22: Split analysis into 2 groups for better tab visibility
  // Group 1 (Editorial) — below Project
  api.addPanel({ id: 'inspector', component: 'inspector', title: 'Inspector', position: { referencePanel: 'project', direction: 'below' } });
  api.addPanel({ id: 'clip', component: 'clip', title: 'Clip', position: { referencePanel: 'inspector', direction: 'within' } });
  api.addPanel({ id: 'history', component: 'history', title: 'History', position: { referencePanel: 'inspector', direction: 'within' } });
  api.addPanel({ id: 'storyspace', component: 'storyspace', title: 'StorySpace', position: { referencePanel: 'inspector', direction: 'within' } });
  api.addPanel({ id: 'montage', component: 'montage', title: 'Montage', position: { referencePanel: 'inspector', direction: 'within' } });
  // MARKER_GAMMA-MKL1: Marker List in editorial group
  api.addPanel({ id: 'markers', component: 'markers', title: 'Markers', position: { referencePanel: 'inspector', direction: 'within' } });
  // MARKER_GAMMA-33: Split media into 2 groups for better panel visibility
  // Group 2a (Effects) — right of Editorial group
  api.addPanel({ id: 'effects', component: 'effects', title: 'Effects', position: { referencePanel: 'inspector', direction: 'right' } });
  api.addPanel({ id: 'colorcorrector', component: 'colorcorrector', title: 'Color', position: { referencePanel: 'effects', direction: 'within' } });
  api.addPanel({ id: 'scopes', component: 'scopes', title: 'Scopes', position: { referencePanel: 'effects', direction: 'within' } });
  api.addPanel({ id: 'lutbrowser', component: 'lutbrowser', title: 'LUTs', position: { referencePanel: 'effects', direction: 'within' } });
  // MARKER_GAMMA-AUDIT: Transitions moved INTO Effects group (FCP7 convention)
  api.addPanel({ id: 'transitions', component: 'transitions', title: 'Transitions', position: { referencePanel: 'effects', direction: 'within' } });
  // Group 2b (Audio) — right of Effects group (Speed removed — it's a modal dialog)
  api.addPanel({ id: 'mixer', component: 'mixer', title: 'Mixer', position: { referencePanel: 'effects', direction: 'right' } });
  // Timeline (full-width bottom)
  api.addPanel({ id: 'timeline', component: 'timeline', title: 'Timeline', params: { scriptText }, position: { direction: 'below' } });
  // Sizes
  try { api.getPanel('project')?.api.setSize({ width: 320 }); } catch { /* ok */ }
  try { api.getPanel('timeline')?.api.setSize({ height: 300 }); } catch { /* ok */ }
  // MARKER_GAMMA-R2.FIX: Ensure key panels are foreground in their groups
  // Group 1 (Editorial): inspector foreground
  try { api.getPanel('inspector')?.api.setActive(); } catch { /* ok */ }
  // Group 2a (Effects): effects foreground (CC tests switch to scopes via tab)
  try { api.getPanel('effects')?.api.setActive(); } catch { /* ok */ }
  // Group 2b (Tools): mixer foreground (AUD1/AUD6 tests need mixer visible)
  try { api.getPanel('mixer')?.api.setActive(); } catch { /* ok */ }
}

export function buildColorLayout(api: DockviewApi, scriptText: string) {
  // Color grading: Program Monitor dominant, Scopes + Color Corrector + LUTs prominent
  api.addPanel({ id: 'source', component: 'source', title: 'SOURCE' });
  api.addPanel({ id: 'project', component: 'project', title: 'Project', position: { referencePanel: 'source', direction: 'below' } });
  api.addPanel({ id: 'script', component: 'script', title: 'Script', params: { scriptText }, position: { referencePanel: 'project', direction: 'within' } });
  api.addPanel({ id: 'inspector', component: 'inspector', title: 'Inspector', position: { referencePanel: 'project', direction: 'within' } });
  api.addPanel({ id: 'clip', component: 'clip', title: 'Clip', position: { referencePanel: 'project', direction: 'within' } });
  api.addPanel({ id: 'history', component: 'history', title: 'History', position: { referencePanel: 'project', direction: 'within' } });
  api.addPanel({ id: 'graph', component: 'graph', title: 'Graph', position: { referencePanel: 'project', direction: 'within' } });
  api.addPanel({ id: 'storyspace', component: 'storyspace', title: 'StorySpace', position: { referencePanel: 'project', direction: 'within' } });
  api.addPanel({ id: 'montage', component: 'montage', title: 'Montage', position: { referencePanel: 'project', direction: 'within' } });
  // MARKER_GAMMA-33: Split tools from effects group
  api.addPanel({ id: 'effects', component: 'effects', title: 'Effects', position: { referencePanel: 'project', direction: 'below' } });
  api.addPanel({ id: 'mixer', component: 'mixer', title: 'Mixer', position: { referencePanel: 'effects', direction: 'within' } });
  // MARKER_GAMMA-AUDIT: Transitions in Effects group, Speed removed (modal)
  api.addPanel({ id: 'transitions', component: 'transitions', title: 'Transitions', position: { referencePanel: 'effects', direction: 'within' } });
  api.addPanel({ id: 'program', component: 'program', title: 'PROGRAM', position: { referencePanel: 'source', direction: 'right' } });
  api.addPanel({ id: 'colorcorrector', component: 'colorcorrector', title: 'Color', position: { referencePanel: 'program', direction: 'right' } });
  api.addPanel({ id: 'lutbrowser', component: 'lutbrowser', title: 'LUTs', position: { referencePanel: 'colorcorrector', direction: 'within' } });
  api.addPanel({ id: 'scopes', component: 'scopes', title: 'Scopes', position: { referencePanel: 'colorcorrector', direction: 'below' } });
  api.addPanel({ id: 'timeline', component: 'timeline', title: 'Timeline', params: { scriptText }, position: { direction: 'below' } });
  try { api.getPanel('source')?.api.setSize({ width: 260 }); } catch { /* ok */ }
  try { api.getPanel('colorcorrector')?.api.setSize({ width: 300 }); } catch { /* ok */ }
  try { api.getPanel('timeline')?.api.setSize({ height: 240 }); } catch { /* ok */ }
  // MARKER_GAMMA-R2.FIX: Ensure key panels foreground per color preset purpose
  try { api.getPanel('colorcorrector')?.api.setActive(); } catch { /* ok */ }
  try { api.getPanel('scopes')?.api.setActive(); } catch { /* ok */ }
  try { api.getPanel('effects')?.api.setActive(); } catch { /* ok */ }
  try { api.getPanel('transitions')?.api.setActive(); } catch { /* ok */ }
}

export function buildAudioLayout(api: DockviewApi, scriptText: string) {
  api.addPanel({ id: 'project', component: 'project', title: 'Project' });
  api.addPanel({ id: 'script', component: 'script', title: 'Script', params: { scriptText }, position: { referencePanel: 'project', direction: 'within' } });
  api.addPanel({ id: 'source', component: 'source', title: 'SOURCE', position: { referencePanel: 'project', direction: 'right' } });
  api.addPanel({ id: 'program', component: 'program', title: 'PROGRAM', position: { referencePanel: 'source', direction: 'within' } });
  api.addPanel({ id: 'mixer', component: 'mixer', title: 'Mixer', position: { referencePanel: 'source', direction: 'right' } });
  api.addPanel({ id: 'inspector', component: 'inspector', title: 'Inspector', position: { referencePanel: 'project', direction: 'below' } });
  api.addPanel({ id: 'clip', component: 'clip', title: 'Clip', position: { referencePanel: 'inspector', direction: 'within' } });
  api.addPanel({ id: 'history', component: 'history', title: 'History', position: { referencePanel: 'inspector', direction: 'within' } });
  api.addPanel({ id: 'graph', component: 'graph', title: 'Graph', position: { referencePanel: 'inspector', direction: 'within' } });
  api.addPanel({ id: 'storyspace', component: 'storyspace', title: 'StorySpace', position: { referencePanel: 'inspector', direction: 'within' } });
  api.addPanel({ id: 'montage', component: 'montage', title: 'Montage', position: { referencePanel: 'inspector', direction: 'within' } });
  // MARKER_GAMMA-33: Split tools from effects group
  api.addPanel({ id: 'effects', component: 'effects', title: 'Effects', position: { referencePanel: 'inspector', direction: 'right' } });
  api.addPanel({ id: 'colorcorrector', component: 'colorcorrector', title: 'Color', position: { referencePanel: 'effects', direction: 'within' } });
  api.addPanel({ id: 'scopes', component: 'scopes', title: 'Scopes', position: { referencePanel: 'effects', direction: 'within' } });
  api.addPanel({ id: 'lutbrowser', component: 'lutbrowser', title: 'LUTs', position: { referencePanel: 'effects', direction: 'within' } });
  // MARKER_GAMMA-AUDIT: Transitions in Effects group, Speed removed (modal)
  api.addPanel({ id: 'transitions', component: 'transitions', title: 'Transitions', position: { referencePanel: 'effects', direction: 'within' } });
  api.addPanel({ id: 'timeline', component: 'timeline', title: 'Timeline', params: { scriptText }, position: { direction: 'below' } });
  try { api.getPanel('project')?.api.setSize({ width: 260 }); } catch { /* ok */ }
  try { api.getPanel('mixer')?.api.setSize({ width: 280 }); } catch { /* ok */ }
  try { api.getPanel('timeline')?.api.setSize({ height: 380 }); } catch { /* ok */ }
  // MARKER_GAMMA-R2.FIX: Ensure key panels foreground per audio preset purpose
  try { api.getPanel('inspector')?.api.setActive(); } catch { /* ok */ }
  try { api.getPanel('mixer')?.api.setActive(); } catch { /* ok */ }
  try { api.getPanel('effects')?.api.setActive(); } catch { /* ok */ }
}

export const PRESET_BUILDERS: Record<string, PresetBuilder> = {
  editing: buildEditingLayout,
  color: buildColorLayout,
  audio: buildAudioLayout,
  custom: buildEditingLayout,
};
