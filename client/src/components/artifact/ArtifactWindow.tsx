/**
 * ArtifactWindow - Floating window wrapper for ArtifactPanel.
 * Provides draggable/resizable container for file viewing.
 *
 * @status active
 * @phase 104.9
 * @depends FloatingWindow, ArtifactPanel, useStore
 * @used_by ChatPanel
 *
 * MARKER_104_VISUAL - Added L2 approval level and content change props
 */

import { FloatingWindow } from './FloatingWindow';
import { ArtifactPanel } from './ArtifactPanel';
import { useStore } from '../../store/useStore';

// Phase 68.2: Support for direct file/content passing
interface FileInfo {
  path: string;
  name: string;
  extension?: string;
}

interface RawContent {
  content: string;
  title: string;
  type?: 'text' | 'markdown' | 'code' | 'web';
  sourceUrl?: string;
}

// MARKER_104_VISUAL - Approval levels for artifact editing
type ApprovalLevel = 'L1' | 'L2' | 'L3';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  /** Phase 68.2: Direct file info (overrides store selection) */
  file?: FileInfo | null;
  /** Phase 68.2: Raw content for preview */
  rawContent?: RawContent | null;
  /** Phase 104.9: Approval level for L2 editing */
  approvalLevel?: ApprovalLevel;
  /** Phase 104.9: Artifact ID for approval events */
  artifactId?: string;
  /** Phase 104.9: Callback for L2 content changes */
  onContentChange?: (content: string) => void;
}

export function ArtifactWindow({ isOpen, onClose, file: propFile, rawContent, approvalLevel, artifactId, onContentChange }: Props) {
  const selectedId = useStore((state) => state.selectedId);
  const nodes = useStore((state) => state.nodes);
  const selectedNode = selectedId ? nodes[selectedId] : null;

  // Phase 68.2: Use prop file if provided, otherwise use store selection
  const storeFile = selectedNode && selectedNode.type === 'file' ? {
    path: selectedNode.path,
    name: selectedNode.name,
    extension: selectedNode.extension,
  } : null;

  const file = propFile || storeFile;

  // Determine title based on what we're showing
  const title = rawContent?.title || file?.name || 'Artifact Viewer';

  return (
    <FloatingWindow
      title={title}
      isOpen={isOpen}
      onClose={onClose}
      defaultWidth={700}
      defaultHeight={500}
    >
      {/* MARKER_104_VISUAL - Pass L2 approval props to ArtifactPanel */}
      <ArtifactPanel
        file={file}
        rawContent={rawContent}
        onClose={onClose}
        approvalLevel={approvalLevel}
        artifactId={artifactId}
        onContentChange={onContentChange}
      />
    </FloatingWindow>
  );
}
