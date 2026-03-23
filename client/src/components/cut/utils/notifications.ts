/**
 * MARKER_GAMMA-APP1: Notification system — toast queue with auto-dismiss.
 *
 * Usage: notify('Save complete') or notify('Render failed', 'error')
 * Types: 'info' (auto-dismiss 3s), 'error' (persistent until click)
 * Max 5 visible toasts. Older ones removed FIFO.
 */

export type NotificationType = 'info' | 'error' | 'success';

interface Toast {
  id: number;
  message: string;
  type: NotificationType;
  el: HTMLDivElement;
  timer?: ReturnType<typeof setTimeout>;
}

let container: HTMLDivElement | null = null;
let nextId = 0;
const toasts: Toast[] = [];
const MAX_TOASTS = 5;

function ensureContainer(): HTMLDivElement {
  if (container && document.body.contains(container)) return container;
  container = document.createElement('div');
  container.style.cssText =
    'position:fixed;top:8px;right:8px;z-index:99999;display:flex;flex-direction:column;gap:4px;pointer-events:none';
  document.body.appendChild(container);
  return container;
}

function removeToast(toast: Toast) {
  toast.el.style.opacity = '0';
  toast.el.style.transform = 'translateX(20px)';
  if (toast.timer) clearTimeout(toast.timer);
  setTimeout(() => {
    toast.el.remove();
    const idx = toasts.indexOf(toast);
    if (idx !== -1) toasts.splice(idx, 1);
  }, 200);
}

export function notify(message: string, type: NotificationType = 'info') {
  const c = ensureContainer();

  // Remove oldest if at max
  while (toasts.length >= MAX_TOASTS) {
    removeToast(toasts[0]);
  }

  const id = nextId++;
  const el = document.createElement('div');
  const borderColor = type === 'error' ? '#666' : type === 'success' ? '#555' : '#444';
  el.style.cssText =
    `padding:6px 14px;background:rgba(20,20,20,0.95);border:1px solid ${borderColor};` +
    'border-radius:4px;font-size:11px;font-family:system-ui,-apple-system,sans-serif;' +
    'color:#ccc;pointer-events:auto;cursor:pointer;max-width:320px;word-break:break-word;' +
    'transition:opacity 0.2s,transform 0.2s;opacity:0;transform:translateX(20px);' +
    'box-shadow:0 4px 12px rgba(0,0,0,0.5)';

  el.textContent = message;
  c.appendChild(el);

  // Animate in
  requestAnimationFrame(() => {
    el.style.opacity = '1';
    el.style.transform = 'translateX(0)';
  });

  const toast: Toast = { id, message, type, el };

  // Auto-dismiss for non-errors
  if (type !== 'error') {
    toast.timer = setTimeout(() => removeToast(toast), 3000);
  }

  // Click to dismiss
  el.addEventListener('click', () => removeToast(toast));

  toasts.push(toast);
}
