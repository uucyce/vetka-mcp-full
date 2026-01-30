/**
 * Artifact components barrel export.
 * Re-exports ArtifactPanel, ArtifactWindow, and FloatingWindow.
 *
 * @status active
 * @phase 96
 * @depends ./ArtifactPanel, ./ArtifactWindow, ./FloatingWindow
 * @used_by components/chat/ChatPanel
 */

export { ArtifactPanel } from './ArtifactPanel';
export { ArtifactWindow } from './ArtifactWindow';
export { FloatingWindow } from './FloatingWindow';
