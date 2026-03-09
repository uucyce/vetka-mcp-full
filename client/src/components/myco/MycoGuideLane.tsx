import { useEffect, useState } from 'react';
import type { MycoModeAHint } from './mycoModeATypes';
import mycoIdleQuestion from '../../assets/myco/myco_idle_question.png';
import mycoReadySmile from '../../assets/myco/myco_ready_smile.png';

interface Props {
  hint: MycoModeAHint | null;
  stateKey: string;
}

export function MycoGuideLane({ hint, stateKey }: Props) {
  const [dismissedKey, setDismissedKey] = useState<string | null>(null);

  useEffect(() => {
    if (dismissedKey && dismissedKey !== stateKey) {
      setDismissedKey(null);
    }
  }, [dismissedKey, stateKey]);

  if (!hint || dismissedKey === stateKey) return null;

  const toneBorder = hint.tone === 'warning' ? '#c78b52' : hint.tone === 'action' ? '#6ea58d' : '#4a6178';
  const avatarSrc = hint.tone === 'warning' ? mycoIdleQuestion : mycoReadySmile;

  return (
    <aside
      data-testid="myco-mode-a-guide"
      style={{
        position: 'fixed',
        left: 16,
        bottom: 16,
        width: 360,
        maxWidth: 'calc(100vw - 32px)',
        zIndex: 140,
        borderRadius: 14,
        border: `1px solid ${toneBorder}`,
        background: 'rgba(11, 13, 16, 0.92)',
        boxShadow: '0 18px 48px rgba(0,0,0,0.34)',
        backdropFilter: 'blur(10px)',
        color: '#f2f5f7',
        padding: '14px 14px 12px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          <img
            src={avatarSrc}
            alt="MYCO"
            style={{
              width: 44,
              height: 44,
              objectFit: 'contain',
              borderRadius: 12,
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.08)',
              padding: 4,
              flexShrink: 0,
            }}
          />
          <div>
            <div style={{ fontSize: 11, letterSpacing: 1.2, textTransform: 'uppercase', color: '#8ea4b5', marginBottom: 6 }}>
              MYCO
            </div>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>{hint.title}</div>
          </div>
        </div>
        <button
          aria-label="Dismiss MYCO hint"
          onClick={() => setDismissedKey(stateKey)}
          style={{
            border: 'none',
            background: 'transparent',
            color: '#89a0af',
            cursor: 'pointer',
            fontSize: 18,
            lineHeight: 1,
            padding: 0,
          }}
        >
          ×
        </button>
      </div>

      <div style={{ fontSize: 13, lineHeight: 1.45, color: '#dbe2e8', marginBottom: 10 }}>{hint.body}</div>

      <div style={{ display: 'grid', gap: 6 }}>
        {hint.nextActions.slice(0, 3).map((action) => (
          <div key={action} style={{ fontSize: 12, color: '#c8d4de' }}>
            {`> ${action}`}
          </div>
        ))}
      </div>

      {hint.shortcuts.length > 0 && (
        <div style={{ marginTop: 10, fontSize: 11, color: '#8fa0ad' }}>{hint.shortcuts.join('  |  ')}</div>
      )}
    </aside>
  );
}
