/**
 * MARKER_153.6D: ToastContainer — renders toast notifications.
 *
 * Positioned at top-right of MCC container. Stacks vertically.
 * Each toast shows type icon, message, and dismiss button.
 * Auto-dismisses based on type (5s info/success, sticky errors).
 *
 * @phase 153
 * @wave 6
 * @status active
 */

import { TOAST_COLORS, type Toast, type ToastType } from '../../hooks/useToast';

const TYPE_ICONS: Record<ToastType, string> = {
  info: 'ℹ',
  success: '✓',
  warning: '⚠',
  error: '✕',
};

interface ToastContainerProps {
  toasts: Toast[];
  onDismiss: (id: string) => void;
}

export function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  if (toasts.length === 0) return null;

  return (
    <div
      style={{
        position: 'absolute',
        top: 8,
        right: 8,
        zIndex: 300,
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
        maxWidth: 300,
        pointerEvents: 'none',
      }}
    >
      {toasts.map((toast) => {
        const colors = TOAST_COLORS[toast.type];
        return (
          <div
            key={toast.id}
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: 6,
              padding: '6px 10px',
              background: colors.bg,
              border: `1px solid ${colors.border}`,
              borderRadius: 4,
              fontSize: 9,
              fontFamily: 'monospace',
              color: colors.text,
              pointerEvents: 'auto',
              animation: 'fadeIn 0.2s ease-out',
            }}
          >
            <span style={{ flexShrink: 0, fontSize: 10 }}>
              {TYPE_ICONS[toast.type]}
            </span>
            <span style={{ flex: 1, lineHeight: 1.4, wordBreak: 'break-word' }}>
              {toast.message}
            </span>
            <button
              onClick={() => onDismiss(toast.id)}
              style={{
                background: 'transparent',
                border: 'none',
                color: colors.text,
                cursor: 'pointer',
                fontSize: 8,
                padding: '0 2px',
                opacity: 0.6,
                flexShrink: 0,
                fontFamily: 'monospace',
              }}
              title="Dismiss"
            >
              ×
            </button>
          </div>
        );
      })}
    </div>
  );
}
