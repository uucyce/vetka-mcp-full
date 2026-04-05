/**
 * MARKER_155.WIZARD.001: WizardContainer — 5-step wizard flow manager.
 *
 * Shows ONLY ONE step at a time. Each step has max 3 options.
 * Steps: Launch → Playground → Keys → DAG → Drill
 *
 * @phase 155
 * @wave 4 (P2)
 * @status active
 */

import { useState, useCallback, useEffect } from 'react';
import { NOLAN_PALETTE } from '../../utils/dagLayout';
import { useMCCStore } from '../../store/useMCCStore';

export type WizardStep = 1 | 2 | 3 | 4 | 5;

interface WizardContainerProps {
  currentStep: WizardStep;
  onStepComplete: (step: WizardStep, data: any) => void;
  onStepBack?: () => void;
}

// Step configuration with titles and descriptions
const STEP_CONFIG: Record<WizardStep, { title: string; subtitle: string; icon: string }> = {
  1: { title: 'New Project', subtitle: 'How would you like to start?', icon: '🚀' },
  2: { title: 'Setup Workspace', subtitle: 'Choose your playground', icon: '📁' },
  3: { title: 'Configure Keys', subtitle: 'Set up your AI providers', icon: '🔑' },
  4: { title: 'Architecture', subtitle: 'Plan your project structure', icon: '🗺️' },
  5: { title: 'Execute', subtitle: 'Run and monitor tasks', icon: '🔍' },
};

// Simple step components inline (could be split into separate files)
function StepLaunch({ onComplete }: { onComplete: (data: any) => void }) {
  const [selectedMethod, setSelectedMethod] = useState<'folder' | 'git' | 'description' | null>(null);
  const [inputValue, setInputValue] = useState('');

  const handleSubmit = () => {
    if (!selectedMethod || !inputValue.trim()) return;
    onComplete({ method: selectedMethod, value: inputValue.trim() });
  };

  return (
    <div style={{ maxWidth: 600, margin: '0 auto', paddingTop: 40 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 32 }}>
        {[
          { id: 'folder' as const, icon: '📁', title: 'Select Folder', desc: 'Open existing project' },
          { id: 'git' as const, icon: '🔗', title: 'Clone Repository', desc: 'From Git URL' },
          { id: 'description' as const, icon: '✨', title: 'Create New', desc: 'Describe what to build' },
        ].map((opt) => (
          <button
            key={opt.id}
            onClick={() => { setSelectedMethod(opt.id); setInputValue(''); }}
            style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 32,
              background: selectedMethod === opt.id ? 'rgba(74, 158, 255, 0.1)' : 'rgba(255,255,255,0.03)',
              border: `1px solid ${selectedMethod === opt.id ? '#4a9eff' : 'rgba(255,255,255,0.1)'}`,
              borderRadius: 8, cursor: 'pointer', transition: 'all 0.2s',
            }}
          >
            <span style={{ fontSize: 40, marginBottom: 12 }}>{opt.icon}</span>
            <span style={{ fontSize: 14, fontWeight: 600, color: '#fff', marginBottom: 4 }}>{opt.title}</span>
            <span style={{ fontSize: 11, color: '#888' }}>{opt.desc}</span>
          </button>
        ))}
      </div>

      {selectedMethod && (
        <div style={{ animation: 'fadeIn 0.3s' }}>
          <input
            type={selectedMethod === 'git' ? 'url' : 'text'}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={
              selectedMethod === 'folder' ? '/path/to/project' :
              selectedMethod === 'git' ? 'https://github.com/user/repo.git' :
              'A Python web scraper that extracts product prices...'
            }
            style={{
              width: '100%', padding: 14, marginBottom: 16,
              background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 6, color: '#fff', fontFamily: 'monospace', fontSize: 13,
            }}
          />
          <button
            onClick={handleSubmit}
            disabled={!inputValue.trim()}
            style={{
              width: '100%', padding: 14, background: inputValue.trim() ? '#4a9eff' : '#333',
              border: 'none', borderRadius: 6, color: '#fff', fontFamily: 'monospace',
              fontSize: 13, fontWeight: 600, cursor: inputValue.trim() ? 'pointer' : 'default',
            }}
          >
            Continue →
          </button>
        </div>
      )}
    </div>
  );
}

function StepPlayground({ onComplete, onBack }: { onComplete: (data: any) => void; onBack?: () => void }) {
  const [selectedAction, setSelectedAction] = useState<'new' | 'copy' | 'continue' | null>(null);

  return (
    <div style={{ maxWidth: 600, margin: '0 auto', paddingTop: 40 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 32 }}>
        {[
          { id: 'new' as const, icon: '🆕', title: 'Fresh Start', desc: 'New clean playground' },
          { id: 'copy' as const, icon: '📋', title: 'Copy Existing', desc: 'Duplicate project' },
          { id: 'continue' as const, icon: '▶️', title: 'Continue', desc: 'Resume workspace' },
        ].map((opt) => (
          <button
            key={opt.id}
            onClick={() => setSelectedAction(opt.id)}
            style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 32,
              background: selectedAction === opt.id ? 'rgba(74, 158, 255, 0.1)' : 'rgba(255,255,255,0.03)',
              border: `1px solid ${selectedAction === opt.id ? '#4a9eff' : 'rgba(255,255,255,0.1)'}`,
              borderRadius: 8, cursor: 'pointer',
            }}
          >
            <span style={{ fontSize: 40, marginBottom: 12 }}>{opt.icon}</span>
            <span style={{ fontSize: 14, fontWeight: 600, color: '#fff' }}>{opt.title}</span>
            <span style={{ fontSize: 11, color: '#888' }}>{opt.desc}</span>
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 12 }}>
        {onBack && (
          <button
            onClick={onBack}
            style={{
              flex: 1, padding: 14, background: 'transparent',
              border: '1px solid rgba(255,255,255,0.2)', borderRadius: 6,
              color: '#888', fontFamily: 'monospace', fontSize: 13, cursor: 'pointer',
            }}
          >
            ← Back
          </button>
        )}
        <button
          onClick={() => selectedAction && onComplete({ action: selectedAction })}
          disabled={!selectedAction}
          style={{
            flex: 2, padding: 14, background: selectedAction ? '#4a9eff' : '#333',
            border: 'none', borderRadius: 6, color: '#fff', fontFamily: 'monospace',
            fontSize: 13, fontWeight: 600, cursor: selectedAction ? 'pointer' : 'default',
          }}
        >
          Continue →
        </button>
      </div>
    </div>
  );
}

function StepKeys({ onComplete, onBack }: { onComplete: (data: any) => void; onBack?: () => void }) {
  const [selectedMethod, setSelectedMethod] = useState<'existing' | 'new' | 'local' | null>(null);

  return (
    <div style={{ maxWidth: 600, margin: '0 auto', paddingTop: 40 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 32 }}>
        {[
          { id: 'existing' as const, icon: '🔑', title: 'Use Existing', desc: 'Select saved key' },
          { id: 'new' as const, icon: '➕', title: 'Add New Key', desc: 'Configure provider' },
          { id: 'local' as const, icon: '🖥️', title: 'Local Model', desc: 'Use Ollama' },
        ].map((opt) => (
          <button
            key={opt.id}
            onClick={() => setSelectedMethod(opt.id)}
            style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 28,
              background: selectedMethod === opt.id ? 'rgba(74, 158, 255, 0.1)' : 'rgba(255,255,255,0.03)',
              border: `1px solid ${selectedMethod === opt.id ? '#4a9eff' : 'rgba(255,255,255,0.1)'}`,
              borderRadius: 8, cursor: 'pointer',
            }}
          >
            <span style={{ fontSize: 36, marginBottom: 8 }}>{opt.icon}</span>
            <span style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>{opt.title}</span>
            <span style={{ fontSize: 10, color: '#888' }}>{opt.desc}</span>
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 12 }}>
        {onBack && (
          <button onClick={onBack} style={{ flex: 1, padding: 14, background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', borderRadius: 6, color: '#888', fontFamily: 'monospace', fontSize: 13 }}>
            ← Back
          </button>
        )}
        <button
          onClick={() => selectedMethod && onComplete({ method: selectedMethod })}
          disabled={!selectedMethod}
          style={{ flex: 2, padding: 14, background: selectedMethod ? '#4a9eff' : '#333', border: 'none', borderRadius: 6, color: '#fff', fontFamily: 'monospace', fontSize: 13, fontWeight: 600 }}
        >
          Continue →
        </button>
      </div>
    </div>
  );
}

// DAG and Drill steps are more complex and use the main app components
// For now, we'll show a message that these require the full app
function StepDAGPlaceholder({ onComplete, onBack }: { onComplete: (data: any) => void; onBack?: () => void }) {
  return (
    <div style={{ padding: 40, textAlign: 'center' }}>
      <div style={{ fontSize: 48, marginBottom: 16 }}>🗺️</div>
      <h2 style={{ fontSize: 18, marginBottom: 8 }}>DAG View Active</h2>
      <p style={{ color: '#888', marginBottom: 24 }}>Use the main interface to create tasks</p>
      <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
        {onBack && <button onClick={onBack} style={{ padding: '12px 24px', background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', borderRadius: 6, color: '#888' }}>← Back</button>}
        <button onClick={() => onComplete({ action: 'ready' })} style={{ padding: '12px 24px', background: '#4a9eff', border: 'none', borderRadius: 6, color: '#fff', fontWeight: 600 }}>Continue →</button>
      </div>
    </div>
  );
}

export function WizardContainer({ currentStep, onStepComplete, onStepBack }: WizardContainerProps) {
  const config = STEP_CONFIG[currentStep];
  const { setNavLevel, navLevel } = useMCCStore();

  // Handle step completions
  const handleStep1 = (data: any) => {
    // Initialize project with selected method
    onStepComplete(1, data);
    // Move to step 2
  };

  const handleStep2 = (data: any) => {
    onStepComplete(2, data);
  };

  const handleStep3 = (data: any) => {
    onStepComplete(3, data);
  };

  const handleStep4 = (data: any) => {
    onStepComplete(4, data);
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: '#0a0a0a',
        fontFamily: 'monospace',
      }}
    >
      {/* MARKER_155.WIZARD.002: Step header with title/subtitle */}
      <div
        style={{
          padding: '24px 32px',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
          display: 'flex',
          alignItems: 'center',
          gap: 16,
        }}
      >
        <span style={{ fontSize: 32 }}>{config.icon}</span>
        <div>
          <h1 style={{ margin: 0, fontSize: 20, fontWeight: 600, color: '#fff' }}>
            {config.title}
          </h1>
          <p style={{ margin: '4px 0 0 0', fontSize: 12, color: '#888' }}>
            {config.subtitle}
          </p>
        </div>
      </div>

      {/* MARKER_155.WIZARD.003: Step content area - only current step renders here */}
      <div style={{ flex: 1, padding: 24, overflow: 'auto' }}>
        {currentStep === 1 && <StepLaunch onComplete={handleStep1} />}
        {currentStep === 2 && <StepPlayground onComplete={handleStep2} onBack={onStepBack} />}
        {currentStep === 3 && <StepKeys onComplete={handleStep3} onBack={onStepBack} />}
        {currentStep === 4 && <StepDAGPlaceholder onComplete={handleStep4} onBack={onStepBack} />}
        {currentStep === 5 && (
          <div style={{ padding: 40, textAlign: 'center' }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>🔍</div>
            <h2 style={{ fontSize: 18 }}>Ready to Execute</h2>
          </div>
        )}
      </div>
    </div>
  );
}
