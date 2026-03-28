/**
 * MARKER_C4.1: Panel wrappers barrel export for dockview integration.
 * Each panel wraps an existing CUT component with focus handling and dark bg.
 */

// Monitor panels
export { default as SourceMonitorPanel } from './SourceMonitorPanel';
export { default as ProgramMonitorPanel } from './ProgramMonitorPanel';

// Timeline panel
export { default as TimelinePanel } from './TimelinePanel';

// Navigation panels (left column tabs)
export { default as ProjectPanelDock } from './ProjectPanelDock';
export { default as ScriptPanelDock } from './ScriptPanelDock';
export { default as GraphPanelDock } from './GraphPanelDock';

// Analysis panels (left column bottom tabs)
export { default as InspectorPanelDock } from './InspectorPanelDock';
export { default as ClipPanelDock } from './ClipPanelDock';
export { default as StorySpacePanelDock } from './StorySpacePanelDock';
export { default as HistoryPanelDock } from './HistoryPanelDock';

// MARKER_C14: Auto-Montage panel
export { default as AutoMontagePanelDock } from './AutoMontagePanelDock';

// MARKER_B13: Audio Mixer panel
export { default as AudioMixerPanelDock } from './AudioMixerPanelDock';

// MARKER_GAMMA-MKL1: Marker List panel
export { default as MarkerListPanel } from './MarkerListPanel';

// MARKER_GAMMA-C12.2: Timeline Instance panel (multi-timeline navigator)
export { default as TimelineInstancePanel } from './TimelineInstancePanel';

// MARKER_GAMMA-W6.3: Social Crosspost / Publish panel
export { default as PublishPanel } from './PublishPanel';

// MARKER_GAMMA-MULTICAM-PANEL: Multicam angle grid panel (FCP7 Ch.42)
export { default as MulticamPanel } from './MulticamPanel';

// MARKER_SOURCE_ACQUIRE: Source Acquire panel (FCP7 Log & Capture)
export { default as SourceAcquirePanelDock } from './SourceAcquirePanelDock';

// MARKER_GAMMA-LAYERUI: Layer Stack & Depth Inspector panel
export { default as LayerStackPanel } from './LayerStackPanel';
