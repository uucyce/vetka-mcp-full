/**
 * MARKER_W4.3: Save status indicator — minimal overlay in top-right.
 * Shows: "Saved", "Saving...", "Unsaved", or error state.
 * Fades out after 3 seconds when status is 'saved'.
 */
import { useEffect, useState, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';

const FADE_DELAY_MS = 3000;

export default function SaveIndicator() {
  const saveStatus = useCutEditorStore((s) => s.saveStatus);
  const hasUnsavedChanges = useCutEditorStore((s) => s.hasUnsavedChanges);
  const saveError = useCutEditorStore((s) => s.saveError);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (saveStatus === 'saving' || saveStatus === 'error') {
      setVisible(true);
    } else if (saveStatus === 'saved') {
      setVisible(true);
      const t = setTimeout(() => setVisible(false), FADE_DELAY_MS);
      return () => clearTimeout(t);
    } else {
      setVisible(false);
    }
  }, [saveStatus]);

  if (!visible && !hasUnsavedChanges) return null;

  let text = '';
  let color = '#888';
  if (saveStatus === 'saving') { text = 'Saving...'; color = '#ccc'; }
  else if (saveStatus === 'saved') { text = 'Saved'; color = '#aaa'; }
  else if (saveStatus === 'error') { text = saveError || 'Save failed'; color = '#777'; }
  else if (hasUnsavedChanges) { text = 'Unsaved'; color = '#888'; }

  if (!text) return null;

  const style: CSSProperties = {
    position: 'fixed',
    top: 4,
    right: 8,
    fontSize: 9,
    color,
    fontFamily: 'system-ui, -apple-system, sans-serif',
    letterSpacing: '0.3px',
    textTransform: 'uppercase',
    opacity: visible ? 1 : 0.5,
    transition: 'opacity 0.3s',
    zIndex: 9999,
    pointerEvents: 'none',
  };

  return <div data-testid="save-indicator" style={style}>{text}</div>;
}
