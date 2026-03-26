/**
 * MARKER_GAMMA-P2: PublishDialog — multi-step cross-platform publish dialog.
 *
 * Step 1: Select platforms → Step 2: Configure each → Step 3: Queue/Progress.
 * Triggered by File > Publish... (Cmd+Shift+P) or export submenu.
 * Monochrome: #1a1a1a/#222/#404040, no color.
 *
 * Architecture: RECON_CROSS_PLATFORM_PUBLISH_ARCHITECTURE_2026-03-25.md
 */
import { useState, useCallback, useEffect, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import type { Platform, PlatformTarget, PlatformMetadata, ReframeMode, PublishJob } from './types';
import { PLATFORM_LABELS, PLATFORM_CONSTRAINTS, createDefaultTarget } from './types';
import { PlatformCheckbox } from './PlatformCheckbox';
import { PublishPreviewCanvas } from './PublishPreviewCanvas';
import { PublishReframeControls } from './PublishReframeControls';
import { PublishMetadataForm } from './PublishMetadataForm';
import { PublishScheduler } from './PublishScheduler';
import { PublishQueue } from './PublishQueue';

// ─── Styles ───

const OVERLAY: CSSProperties = {
  position: 'fixed',
  inset: 0,
  zIndex: 9999,
  background: 'rgba(0,0,0,0.6)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
};

const DIALOG: CSSProperties = {
  background: '#1a1a1a',
  border: '1px solid #333',
  borderRadius: 8,
  width: 560,
  maxHeight: '85vh',
  overflow: 'auto',
  fontFamily: 'system-ui, -apple-system, sans-serif',
  color: '#ccc',
  fontSize: 12,
  display: 'flex',
  flexDirection: 'column',
};

const HEADER: CSSProperties = {
  padding: '14px 20px',
  borderBottom: '1px solid #222',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  flexShrink: 0,
};

const BODY: CSSProperties = {
  padding: '16px 20px',
  overflow: 'auto',
  flex: 1,
};

const FOOTER: CSSProperties = {
  padding: '12px 20px',
  borderTop: '1px solid #222',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  flexShrink: 0,
};

const BTN: CSSProperties = {
  background: '#333',
  border: '1px solid #444',
  borderRadius: 4,
  padding: '6px 16px',
  color: '#ccc',
  fontSize: 11,
  cursor: 'pointer',
  fontFamily: 'inherit',
};

const BTN_PRIMARY: CSSProperties = {
  ...BTN,
  background: '#555',
  border: '1px solid #666',
  color: '#fff',
};

const SECTION: CSSProperties = {
  marginBottom: 16,
};

const SECTION_TITLE: CSSProperties = {
  color: '#888',
  fontSize: 10,
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  marginBottom: 8,
};

const CARD: CSSProperties = {
  background: '#151515',
  border: '1px solid #2a2a2a',
  borderRadius: 6,
  padding: 12,
  marginBottom: 8,
};

const ALL_PLATFORMS: Platform[] = ['youtube', 'instagram', 'tiktok', 'x', 'telegram', 'file'];

type Step = 'platforms' | 'configure' | 'queue';

export function PublishDialog() {
  const show = useCutEditorStore((s) => s.showPublishDialog);
  const projectTitle = useCutEditorStore((s) => s.projectTitle) ?? '';

  const [step, setStep] = useState<Step>('platforms');
  const [targets, setTargets] = useState<Record<Platform, PlatformTarget>>(() => {
    const t: Partial<Record<Platform, PlatformTarget>> = {};
    for (const p of ALL_PLATFORMS) {
      t[p] = createDefaultTarget(p, projectTitle);
    }
    return t as Record<Platform, PlatformTarget>;
  });
  const [activePlatform, setActivePlatform] = useState<Platform>('youtube');
  const [jobs, setJobs] = useState<PublishJob[]>([]);

  // Reset when dialog opens
  useEffect(() => {
    if (show) {
      setStep('platforms');
      setJobs([]);
      // Refresh titles from project
      setTargets((prev) => {
        const next = { ...prev };
        for (const p of ALL_PLATFORMS) {
          next[p] = { ...next[p], metadata: { ...next[p].metadata, title: next[p].metadata.title || projectTitle } };
        }
        return next;
      });
    }
  }, [show, projectTitle]);

  const close = useCallback(() => {
    useCutEditorStore.getState().setShowPublishDialog(false);
  }, []);

  const onKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.stopPropagation();
      close();
    }
  }, [close]);

  const togglePlatform = useCallback((platform: Platform, enabled: boolean) => {
    setTargets((prev) => ({
      ...prev,
      [platform]: { ...prev[platform], enabled },
    }));
  }, []);

  const updateMetadata = useCallback((platform: Platform, metadata: PlatformMetadata) => {
    setTargets((prev) => ({
      ...prev,
      [platform]: { ...prev[platform], metadata },
    }));
  }, []);

  const updateReframe = useCallback((platform: Platform, mode: ReframeMode) => {
    setTargets((prev) => ({
      ...prev,
      [platform]: { ...prev[platform], reframeMode: mode },
    }));
  }, []);

  const enabledPlatforms = ALL_PLATFORMS.filter((p) => targets[p].enabled);

  const startPublish = useCallback(() => {
    // Create jobs for each enabled platform
    const newJobs: PublishJob[] = enabledPlatforms.map((p) => ({
      id: `pub_${p}_${Date.now()}`,
      platform: p,
      status: 'pending' as const,
      encodeProgress: 0,
      uploadProgress: 0,
      startedAt: Date.now(),
    }));
    setJobs(newJobs);
    setStep('queue');

    // Dispatch publish event for backend (Beta's encode worker will handle)
    window.dispatchEvent(new CustomEvent('cut:publish-start', {
      detail: {
        targets: enabledPlatforms.map((p) => targets[p]),
        jobs: newJobs,
      },
    }));
  }, [enabledPlatforms, targets]);

  // Compute duration warning
  const duration = useCutEditorStore((s) => {
    let maxEnd = 0;
    for (const lane of s.lanes) {
      for (const clip of lane.clips) {
        maxEnd = Math.max(maxEnd, clip.start_sec + clip.duration_sec);
      }
    }
    return maxEnd;
  });

  const durationWarnings = enabledPlatforms.filter((p) => {
    const max = PLATFORM_CONSTRAINTS[p].maxDurationSeconds;
    return isFinite(max) && duration > max;
  });

  if (!show) return null;

  return (
    <div style={OVERLAY} onClick={close} data-testid="publish-dialog-overlay">
      <div style={DIALOG} onClick={(e) => e.stopPropagation()} onKeyDown={onKeyDown} data-testid="publish-dialog">
        {/* Header */}
        <div style={HEADER}>
          <span style={{ fontSize: 13, color: '#eee' }}>
            Publish{step === 'configure' ? ` — ${enabledPlatforms.length} platforms` : ''}
          </span>
          <button onClick={close} style={{ ...BTN, padding: '2px 8px' }}>
            &times;
          </button>
        </div>

        {/* Body */}
        <div style={BODY}>
          {/* Duration warning banner */}
          {durationWarnings.length > 0 && step !== 'queue' && (
            <div style={{
              background: '#222',
              border: '1px solid #444',
              borderRadius: 4,
              padding: '8px 12px',
              marginBottom: 12,
              fontSize: 11,
              color: '#aaa',
            }} data-testid="publish-duration-warning">
              Timeline duration ({Math.round(duration)}s) exceeds limit for:{' '}
              {durationWarnings.map((p) => (
                <span key={p} style={{ color: '#eee' }}>
                  {PLATFORM_LABELS[p]} ({PLATFORM_CONSTRAINTS[p].maxDurationSeconds}s)
                  {p !== durationWarnings[durationWarnings.length - 1] ? ', ' : ''}
                </span>
              ))}
            </div>
          )}

          {/* Step 1: Platform Selection */}
          {step === 'platforms' && (
            <div style={SECTION}>
              <div style={SECTION_TITLE}>Select Platforms</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                {ALL_PLATFORMS.map((p) => (
                  <PlatformCheckbox
                    key={p}
                    platform={p}
                    checked={targets[p].enabled}
                    onChange={togglePlatform}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Step 2: Configure each platform */}
          {step === 'configure' && (
            <>
              {/* Platform tabs */}
              <div style={{ display: 'flex', gap: 2, marginBottom: 12, flexWrap: 'wrap' }}>
                {enabledPlatforms.map((p) => (
                  <button
                    key={p}
                    onClick={() => setActivePlatform(p)}
                    style={{
                      ...BTN,
                      background: activePlatform === p ? '#444' : '#222',
                      color: activePlatform === p ? '#fff' : '#888',
                      padding: '4px 12px',
                    }}
                    data-testid={`publish-tab-${p}`}
                  >
                    {PLATFORM_LABELS[p]}
                  </button>
                ))}
              </div>

              {/* Active platform config */}
              {enabledPlatforms.includes(activePlatform) && (() => {
                const target = targets[activePlatform];
                const constraints = PLATFORM_CONSTRAINTS[activePlatform];
                const needsReframe = !!constraints.requiresAspectRatio;

                return (
                  <div style={CARD} data-testid={`publish-config-${activePlatform}`}>
                    {/* Preview + Reframe (only for platforms that need aspect change) */}
                    {needsReframe && (
                      <div style={{ marginBottom: 12 }}>
                        <div style={SECTION_TITLE}>Preview ({constraints.requiresAspectRatio})</div>
                        <PublishPreviewCanvas
                          targetAspect={constraints.requiresAspectRatio!}
                          reframeMode={target.reframeMode}
                        />
                        <div style={{ marginTop: 8 }}>
                          <PublishReframeControls
                            mode={target.reframeMode}
                            onChange={(m) => updateReframe(activePlatform, m)}
                          />
                        </div>
                      </div>
                    )}

                    {/* Codec info */}
                    <div style={{ ...SECTION_TITLE, marginTop: needsReframe ? 0 : undefined }}>
                      Codec: {constraints.codec.join(' / ')} &middot;
                      Max: {isFinite(constraints.maxResolutionW) ? `${constraints.maxResolutionW}x${constraints.maxResolutionH}` : 'unlimited'}
                    </div>

                    {/* Metadata */}
                    <PublishMetadataForm
                      platform={activePlatform}
                      metadata={target.metadata}
                      onChange={updateMetadata}
                    />

                    {/* Scheduler */}
                    <PublishScheduler
                      value={target.metadata.scheduleAt ?? null}
                      onChange={(date) => updateMetadata(activePlatform, { ...target.metadata, scheduleAt: date })}
                    />
                  </div>
                );
              })()}
            </>
          )}

          {/* Step 3: Queue */}
          {step === 'queue' && (
            <PublishQueue jobs={jobs} />
          )}
        </div>

        {/* Footer */}
        <div style={FOOTER}>
          <div style={{ fontSize: 10, color: '#555' }}>
            {step === 'platforms' && `${enabledPlatforms.length} selected`}
            {step === 'configure' && 'Configure metadata & reframe per platform'}
            {step === 'queue' && `${jobs.filter((j) => j.status === 'done').length}/${jobs.length} complete`}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {step !== 'platforms' && step !== 'queue' && (
              <button style={BTN} onClick={() => setStep('platforms')}>Back</button>
            )}
            {step === 'platforms' && (
              <button
                style={enabledPlatforms.length > 0 ? BTN_PRIMARY : { ...BTN, opacity: 0.4 }}
                disabled={enabledPlatforms.length === 0}
                onClick={() => {
                  if (enabledPlatforms.length > 0) {
                    setActivePlatform(enabledPlatforms[0]);
                    setStep('configure');
                  }
                }}
              >
                Next
              </button>
            )}
            {step === 'configure' && (
              <button style={BTN_PRIMARY} onClick={startPublish}>
                Publish ({enabledPlatforms.length})
              </button>
            )}
            {step === 'queue' && (
              <button style={BTN} onClick={close}>Close</button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
