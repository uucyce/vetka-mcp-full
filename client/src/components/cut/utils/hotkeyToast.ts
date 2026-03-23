/**
 * MARKER_GAMMA-R5.1: Hotkey visual feedback — brief toast overlay on shortcut activation.
 *
 * Shows action name centered at bottom of viewport for 600ms.
 * Monochrome, non-interactive, auto-removes. Premiere Pro style.
 */

let activeEl: HTMLDivElement | null = null;
let hideTimer: ReturnType<typeof setTimeout> | null = null;

export function showHotkeyToast(actionLabel: string) {
  // Reuse or create element
  if (!activeEl) {
    activeEl = document.createElement('div');
    activeEl.style.cssText =
      'position:fixed;bottom:32px;left:50%;transform:translateX(-50%);' +
      'padding:4px 14px;background:rgba(30,30,30,0.92);border:1px solid #444;' +
      'border-radius:4px;font-size:11px;font-family:system-ui,-apple-system,sans-serif;' +
      'color:#ccc;pointer-events:none;z-index:99999;white-space:nowrap;' +
      'transition:opacity 0.15s ease-out;opacity:0';
    document.body.appendChild(activeEl);
  }

  activeEl.textContent = actionLabel;
  activeEl.style.opacity = '1';

  if (hideTimer) clearTimeout(hideTimer);
  hideTimer = setTimeout(() => {
    if (activeEl) activeEl.style.opacity = '0';
  }, 600);
}
