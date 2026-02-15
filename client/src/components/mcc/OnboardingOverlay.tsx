import { useEffect, useMemo, useState } from 'react';

interface OnboardingOverlayProps {
  step: 0 | 1 | 2 | 3 | 4;
  onAdvance: () => void;
  onDismiss: () => void;
}

interface StepConfig {
  target: string;
  message: string;
}

const STEPS: Record<number, StepConfig> = {
  1: { target: 'key-dropdown', message: 'Select your API key to get started.' },
  2: { target: 'team-dropdown', message: 'Choose your team preset. Dragon Silver is recommended.' },
  3: { target: 'sandbox-dropdown', message: 'Select or create a sandbox for safe experimentation.' },
  4: { target: 'architect-chat', message: 'Type a task and press Enter, or click Execute.' },
};

export function OnboardingOverlay({ step, onAdvance, onDismiss }: OnboardingOverlayProps) {
  const [rect, setRect] = useState<DOMRect | null>(null);

  const config = useMemo(() => STEPS[step], [step]);

  useEffect(() => {
    if (!config) return;
    const updateRect = () => {
      const target = document.querySelector(`[data-onboarding=\"${config.target}\"]`) as HTMLElement | null;
      setRect(target ? target.getBoundingClientRect() : null);
    };
    updateRect();
    window.addEventListener('resize', updateRect);
    window.addEventListener('scroll', updateRect, true);
    const t = setInterval(updateRect, 500);
    return () => {
      window.removeEventListener('resize', updateRect);
      window.removeEventListener('scroll', updateRect, true);
      clearInterval(t);
    };
  }, [config]);

  if (!config || step === 0) return null;

  const tooltipTop = rect ? Math.min(window.innerHeight - 160, rect.bottom + 10) : 120;
  const tooltipLeft = rect
    ? Math.max(16, Math.min(window.innerWidth - 320, rect.left))
    : 24;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1200,
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(0,0,0,0.6)',
        }}
      />

      {rect && (
        <div
          style={{
            position: 'absolute',
            left: rect.left - 4,
            top: rect.top - 4,
            width: rect.width + 8,
            height: rect.height + 8,
            border: '1px solid #4ecdc4',
            borderRadius: 6,
            boxShadow: '0 0 0 9999px rgba(0,0,0,0.6), 0 0 12px rgba(78,205,196,0.6)',
            animation: 'onboarding-pulse 1.3s ease-in-out infinite',
          }}
        />
      )}

      <div
        style={{
          position: 'absolute',
          top: tooltipTop,
          left: tooltipLeft,
          width: 300,
          background: '#111',
          border: '1px solid #333',
          borderRadius: 6,
          padding: 12,
          color: '#ddd',
          fontFamily: 'monospace',
          pointerEvents: 'auto',
        }}
      >
        <div style={{ fontSize: 9, color: '#666', textTransform: 'uppercase', marginBottom: 6 }}>
          onboarding {step}/4
        </div>
        <div style={{ fontSize: 11, lineHeight: 1.45, marginBottom: 10 }}>
          {config.message}
        </div>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: 4 }}>
            {[1, 2, 3, 4].map((s) => (
              <span key={s} style={{ color: s === step ? '#4ecdc4' : '#444', fontSize: 10 }}>
                ●
              </span>
            ))}
          </div>
          <button
            onClick={onDismiss}
            style={{
              marginLeft: 'auto',
              background: 'transparent',
              border: 'none',
              color: '#777',
              fontSize: 10,
              fontFamily: 'monospace',
              cursor: 'pointer',
            }}
          >
            skip
          </button>
          <button
            onClick={onAdvance}
            style={{
              marginLeft: 8,
              background: 'rgba(78,205,196,0.16)',
              border: '1px solid #4ecdc4',
              borderRadius: 3,
              color: '#c6ffff',
              fontSize: 10,
              fontFamily: 'monospace',
              padding: '4px 10px',
              cursor: 'pointer',
            }}
          >
            {step === 4 ? 'done' : 'next'}
          </button>
        </div>
      </div>

      <style>{`
        @keyframes onboarding-pulse {
          0%, 100% { box-shadow: 0 0 0 9999px rgba(0,0,0,0.6), 0 0 6px rgba(78,205,196,0.4); }
          50% { box-shadow: 0 0 0 9999px rgba(0,0,0,0.6), 0 0 14px rgba(78,205,196,0.75); }
        }
      `}</style>
    </div>
  );
}
