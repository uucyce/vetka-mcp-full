/**
 * MARKER_GAMMA-ESC-HOOK: useOverlayEscapeClose
 *
 * DRY helper for overlay/modal Escape-to-close pattern.
 * Registers a bubble-phase keydown listener that calls onClose() on Escape.
 * Pairs with data-overlay="1" on the overlay root div so useCutHotkeys
 * ESC-GUARD skips escapeContext while the overlay is open.
 *
 * @param onClose - function to call when Escape is pressed
 * @param enabled - set to false to temporarily disable (e.g. HotkeyEditor capture mode)
 */
import { useEffect } from 'react';

export function useOverlayEscapeClose(onClose: () => void, enabled = true): void {
  useEffect(() => {
    if (!enabled) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [enabled, onClose]);
}
