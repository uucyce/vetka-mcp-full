/**
 * MARKER_154.16A: FirstRunView — clean welcome screen for first-time project setup.
 *
 * Shown at navLevel='first_run'. Three options:
 * 1. Folder — select local project directory
 * 2. URL — clone git repository
 * 3. Text — describe project idea (AI generates roadmap)
 *
 * After selection: scanning → roadmap → auto-transition to 'roadmap' level.
 *
 * @phase 154
 * @wave 5
 * @status active
 */

import { useState, useCallback, useRef } from 'react';
import { useMCCStore } from '../../store/useMCCStore';
import { NOLAN_PALETTE } from '../../utils/dagLayout';

const API_BASE = 'http://localhost:5001/api';

type Step = 'choose' | 'input' | 'scanning' | 'done' | 'error';
type SourceType = 'folder' | 'url' | 'text';

const OPTIONS = [
  {
    key: 'folder' as SourceType,
    icon: '📁',
    label: 'Local Folder',
    desc: 'Point to an existing project directory',
    shortcut: '1',
  },
  {
    key: 'url' as SourceType,
    icon: '🔗',
    label: 'Git URL',
    desc: 'Clone a repository and analyze',
    shortcut: '2',
  },
  {
    key: 'text' as SourceType,
    icon: '📝',
    label: 'Describe',
    desc: 'Tell us what you want to build',
    shortcut: '3',
  },
];

export function FirstRunView() {
  const [step, setStep] = useState<Step>('choose');
  const [source, setSource] = useState<SourceType | null>(null);
  const [inputValue, setInputValue] = useState('');
  const [progress, setProgress] = useState('');
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);
  const drillDown = useMCCStore(s => s.drillDown);

  const handleSelect = useCallback((type: SourceType) => {
    setSource(type);
    setStep('input');
    setTimeout(() => inputRef.current?.focus(), 100);
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!source || !inputValue.trim()) return;
    setStep('scanning');
    setError(null);
    setProgress('Initializing project...');

    try {
      // Map source type for API
      const sourceType = source === 'folder' ? 'local' : source === 'url' ? 'git' : 'text';

      setProgress('Scanning project structure...');
      const res = await fetch(`${API_BASE}/mcc/project/init`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_type: sourceType,
          source_path: inputValue.trim(),
          quota_gb: 10,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || data.message || `HTTP ${res.status}`);
      }

      setProgress('Building roadmap...');
      // Trigger roadmap generation
      await fetch(`${API_BASE}/mcc/roadmap/generate`, { method: 'POST' }).catch(() => {});

      setProgress('Ready!');
      setStep('done');

      // Auto-navigate to roadmap after short delay
      setTimeout(() => {
        drillDown('roadmap');
      }, 800);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setStep('error');
    }
  }, [source, inputValue, drillDown]);

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'monospace',
        background: NOLAN_PALETTE.bg,
      }}
    >
      {/* Logo / Title */}
      <div style={{ textAlign: 'center', marginBottom: 32 }}>
        <div style={{ fontSize: 28, marginBottom: 8 }}>🌳</div>
        <div style={{
          color: NOLAN_PALETTE.text,
          fontSize: 16,
          fontWeight: 700,
          letterSpacing: 2,
        }}>
          VETKA
        </div>
        <div style={{
          color: NOLAN_PALETTE.textMuted,
          fontSize: 10,
          marginTop: 4,
        }}>
          What project are we building?
        </div>
      </div>

      {/* Step: Choose */}
      {step === 'choose' && (
        <div style={{ display: 'flex', gap: 12 }}>
          {OPTIONS.map(opt => (
            <button
              key={opt.key}
              onClick={() => handleSelect(opt.key)}
              style={{
                width: 140,
                padding: '16px 12px',
                background: 'rgba(20,20,20,0.9)',
                border: `1px solid ${NOLAN_PALETTE.border}`,
                borderRadius: 8,
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 8,
                transition: 'all 0.15s',
                fontFamily: 'monospace',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = NOLAN_PALETTE.text;
                e.currentTarget.style.transform = 'translateY(-2px)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = NOLAN_PALETTE.border;
                e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              <span style={{ fontSize: 20 }}>{opt.icon}</span>
              <span style={{ color: NOLAN_PALETTE.text, fontSize: 11, fontWeight: 600 }}>
                {opt.label}
              </span>
              <span style={{ color: '#555', fontSize: 8, textAlign: 'center', lineHeight: 1.3 }}>
                {opt.desc}
              </span>
              <span style={{ color: '#333', fontSize: 7 }}>
                Press {opt.shortcut}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Step: Input */}
      {step === 'input' && source && (
        <div style={{ width: 360, textAlign: 'center' }}>
          <div style={{ color: NOLAN_PALETTE.textMuted, fontSize: 10, marginBottom: 8 }}>
            {source === 'folder' && 'Enter project directory path:'}
            {source === 'url' && 'Enter git repository URL:'}
            {source === 'text' && 'Describe your project idea:'}
          </div>

          {source === 'text' ? (
            <textarea
              ref={inputRef as any}
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit();
                if (e.key === 'Escape') { setStep('choose'); setSource(null); }
              }}
              placeholder="A React dashboard for managing AI pipelines..."
              rows={4}
              style={{
                width: '100%',
                background: NOLAN_PALETTE.bgDim,
                border: `1px solid ${NOLAN_PALETTE.border}`,
                borderRadius: 6,
                color: NOLAN_PALETTE.text,
                fontFamily: 'monospace',
                fontSize: 11,
                padding: '8px 12px',
                outline: 'none',
                resize: 'none',
              }}
            />
          ) : (
            <input
              ref={inputRef as any}
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') handleSubmit();
                if (e.key === 'Escape') { setStep('choose'); setSource(null); }
              }}
              placeholder={
                source === 'folder'
                  ? '/Users/me/projects/my-app'
                  : 'https://github.com/org/repo.git'
              }
              style={{
                width: '100%',
                background: NOLAN_PALETTE.bgDim,
                border: `1px solid ${NOLAN_PALETTE.border}`,
                borderRadius: 6,
                color: NOLAN_PALETTE.text,
                fontFamily: 'monospace',
                fontSize: 11,
                padding: '8px 12px',
                outline: 'none',
              }}
            />
          )}

          <div style={{ display: 'flex', gap: 8, marginTop: 12, justifyContent: 'center' }}>
            <button
              onClick={() => { setStep('choose'); setSource(null); setInputValue(''); }}
              style={{
                padding: '6px 16px',
                background: NOLAN_PALETTE.bg,
                border: `1px solid ${NOLAN_PALETTE.border}`,
                borderRadius: 4,
                color: NOLAN_PALETTE.textMuted,
                fontSize: 10,
                cursor: 'pointer',
                fontFamily: 'monospace',
              }}
            >
              ← Back
            </button>
            <button
              onClick={handleSubmit}
              disabled={!inputValue.trim()}
              style={{
                padding: '6px 20px',
                background: inputValue.trim() ? '#1a1a1a' : NOLAN_PALETTE.bg,
                border: `1px solid ${inputValue.trim() ? NOLAN_PALETTE.text : NOLAN_PALETTE.border}`,
                borderRadius: 4,
                color: inputValue.trim() ? NOLAN_PALETTE.text : '#555',
                fontSize: 10,
                fontWeight: 600,
                cursor: inputValue.trim() ? 'pointer' : 'default',
                fontFamily: 'monospace',
              }}
            >
              Initialize →
            </button>
          </div>
        </div>
      )}

      {/* Step: Scanning */}
      {step === 'scanning' && (
        <div style={{ textAlign: 'center' }}>
          <div style={{
            color: NOLAN_PALETTE.text,
            fontSize: 12,
            marginBottom: 8,
          }}>
            ⏳ {progress}
          </div>
          <div style={{
            width: 200,
            height: 2,
            background: 'rgba(255,255,255,0.05)',
            borderRadius: 1,
            overflow: 'hidden',
            margin: '0 auto',
          }}>
            <div
              style={{
                height: '100%',
                width: '60%',
                background: NOLAN_PALETTE.text,
                borderRadius: 1,
                animation: 'progressPulse 1.5s ease-in-out infinite',
              }}
            />
          </div>
          <style>{`
            @keyframes progressPulse {
              0% { width: 20%; opacity: 0.5; }
              50% { width: 80%; opacity: 1; }
              100% { width: 20%; opacity: 0.5; }
            }
          `}</style>
        </div>
      )}

      {/* Step: Done */}
      {step === 'done' && (
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>✓</div>
          <div style={{ color: '#8a8', fontSize: 12 }}>
            Project initialized! Entering roadmap...
          </div>
        </div>
      )}

      {/* Step: Error */}
      {step === 'error' && (
        <div style={{ textAlign: 'center', maxWidth: 360 }}>
          <div style={{ color: '#a66', fontSize: 12, marginBottom: 8 }}>
            ⚠ {error}
          </div>
          <button
            onClick={() => { setStep('choose'); setError(null); }}
            style={{
              padding: '6px 16px',
              background: NOLAN_PALETTE.bg,
              border: `1px solid ${NOLAN_PALETTE.border}`,
              borderRadius: 4,
              color: NOLAN_PALETTE.textMuted,
              fontSize: 10,
              cursor: 'pointer',
              fontFamily: 'monospace',
            }}
          >
            ← Try again
          </button>
        </div>
      )}
    </div>
  );
}
