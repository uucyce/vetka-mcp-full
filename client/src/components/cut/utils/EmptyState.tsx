/**
 * MARKER_GAMMA-POLISH1: Shared empty state component for panels.
 * Shows centered message with optional hint. Monochrome.
 */

interface EmptyStateProps {
  message: string;
  hint?: string;
}

export default function EmptyState({ message, hint }: EmptyStateProps) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
      color: '#444',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      fontSize: 11,
      gap: 4,
      padding: 20,
      textAlign: 'center',
      userSelect: 'none',
    }}>
      <span style={{ color: '#555' }}>{message}</span>
      {hint && <span style={{ fontSize: 9, color: '#333' }}>{hint}</span>}
    </div>
  );
}
