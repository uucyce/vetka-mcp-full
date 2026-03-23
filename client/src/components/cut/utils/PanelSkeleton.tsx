/**
 * MARKER_GAMMA-APP1: Panel loading skeleton.
 * Shows pulsing placeholder bars while panel content loads.
 * Monochrome, minimal, no spinners.
 */

const PULSE_KEYFRAMES = `
@keyframes cut-skeleton-pulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.6; }
}
`;

// Inject keyframes once
let injected = false;
function injectKeyframes() {
  if (injected) return;
  const style = document.createElement('style');
  style.textContent = PULSE_KEYFRAMES;
  document.head.appendChild(style);
  injected = true;
}

interface PanelSkeletonProps {
  lines?: number;
  label?: string;
}

export default function PanelSkeleton({ lines = 5, label }: PanelSkeletonProps) {
  injectKeyframes();

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
      padding: 12,
      height: '100%',
      background: '#0a0a0a',
    }}>
      {label && (
        <div style={{
          fontSize: 9,
          color: '#444',
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
          marginBottom: 4,
        }}>
          Loading {label}...
        </div>
      )}
      {Array.from({ length: lines }, (_, i) => (
        <div
          key={i}
          style={{
            height: 8,
            background: '#1a1a1a',
            borderRadius: 3,
            width: `${60 + Math.random() * 40}%`,
            animation: 'cut-skeleton-pulse 1.5s ease-in-out infinite',
            animationDelay: `${i * 0.1}s`,
          }}
        />
      ))}
    </div>
  );
}
