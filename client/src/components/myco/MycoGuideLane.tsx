import { useEffect, useState } from 'react';
import type { MycoModeAHint } from './mycoModeATypes';
import mycoIdleQuestion from '../../assets/myco/myco_idle_question.png';
import mycoReadySmile from '../../assets/myco/myco_ready_smile.png';

interface Props {
  hint: MycoModeAHint | null;
  stateKey: string;
}

function InlineIcon({ token }: { token: string }) {
  const common = {
    width: 12,
    height: 12,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 2,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    style: { display: 'inline-block', verticalAlign: '-2px', marginRight: 6, color: '#f2f5f7' },
  };

  switch (token) {
    case 'pin':
      return (
        <svg {...common}>
          <path d="M12 17v5M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z" />
        </svg>
      );
    case 'history':
      return (
        <svg {...common}>
          <path d="M3 3v5h5" />
          <path d="M3.05 13A9 9 0 1 0 6 5.3L3 8" />
          <path d="M12 7v5l4 2" />
        </svg>
      );
    case 'phone':
      return (
        <svg {...common}>
          <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
        </svg>
      );
    case 'scanner':
      return (
        <svg {...common}>
          <path d="M3 7h18" />
          <path d="M7 12h10" />
          <path d="M10 17h4" />
        </svg>
      );
    case 'folder':
      return (
        <svg {...common}>
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
        </svg>
      );
    case 'chat':
      return (
        <svg {...common}>
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      );
    case 'web':
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="10" />
          <path d="M2 12h20" />
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
        </svg>
      );
    case 'file':
      return (
        <svg {...common}>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
      );
    case 'star':
      return (
        <svg {...common}>
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
        </svg>
      );
    case 'key':
      return (
        <svg {...common}>
          <path d="M21 2l-2 2m-7.61 7.61a4 4 0 1 1-5.66-5.66 4 4 0 0 1 5.66 5.66z" />
          <path d="M15.5 7.5L22 14l-4 4-1.5-1.5-2 2-1.5-1.5-2 2-2.5-2.5" />
        </svg>
      );
    default:
      return null;
  }
}

function renderTokenizedText(text: string) {
  const parts = text.split(/(\[\[[a-z]+\]\])/g).filter(Boolean);
  return parts.map((part, index) => {
    const match = part.match(/^\[\[([a-z]+)\]\]$/);
    if (match) {
      return <InlineIcon key={`${part}-${index}`} token={match[1]} />;
    }
    return <span key={`${part}-${index}`}>{part}</span>;
  });
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

      <div style={{ fontSize: 13, lineHeight: 1.45, color: '#dbe2e8', marginBottom: 10 }}>
        {renderTokenizedText(hint.body)}
      </div>

      <div style={{ display: 'grid', gap: 6 }}>
        {hint.nextActions.slice(0, 3).map((action) => (
          <div key={action} style={{ fontSize: 12, color: '#c8d4de' }}>
            {renderTokenizedText(`> ${action}`)}
          </div>
        ))}
      </div>

      {hint.shortcuts.length > 0 && (
        <div style={{ marginTop: 10, fontSize: 11, color: '#8fa0ad' }}>{hint.shortcuts.join('  |  ')}</div>
      )}
    </aside>
  );
}
