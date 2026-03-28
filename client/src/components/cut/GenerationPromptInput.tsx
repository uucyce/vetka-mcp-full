/**
 * MARKER_GEN-PROMPT: Generation Prompt Input + param grid.
 * Renders textarea + provider param schema grid.
 * Reads/writes useGenerationControlStore.
 *
 * @phase GENERATION_CONTROL
 * @task tb_1774432024_1
 */
import { useCallback, useEffect, useRef, type CSSProperties } from 'react';
import { useGenerationControlStore } from '../../store/useGenerationControlStore';
import { PROVIDER_MAP, type ParamSchema } from '../../config/generation.config';
import { API_BASE } from '../../config/api.config';

// ─── Styles ───

const CONTAINER: CSSProperties = {
  display: 'flex', flexDirection: 'column', gap: 8,
  padding: '8px 10px',
};

const LABEL: CSSProperties = {
  fontSize: 8, textTransform: 'uppercase', letterSpacing: 0.5,
  color: '#555', marginBottom: 2,
};

const TEXTAREA: CSSProperties = {
  width: '100%', minHeight: 64, padding: '6px 8px',
  background: '#111', border: '1px solid #333', borderRadius: 3,
  color: '#ccc', fontSize: 10, fontFamily: 'system-ui',
  resize: 'vertical', outline: 'none', boxSizing: 'border-box',
  lineHeight: 1.5,
};

const PARAMS_GRID: CSSProperties = {
  display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 8px',
};

const PARAM_FIELD: CSSProperties = {
  display: 'flex', flexDirection: 'column',
};

const INPUT: CSSProperties = {
  padding: '3px 6px', background: '#111',
  border: '1px solid #333', borderRadius: 3, color: '#ccc',
  fontSize: 10, fontFamily: 'system-ui', outline: 'none',
};

const REF_ROW: CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 6,
};

const REF_BTN: CSSProperties = {
  padding: '3px 8px', background: '#111', border: '1px solid #333',
  borderRadius: 3, color: '#888', fontSize: 9, cursor: 'pointer',
  fontFamily: 'system-ui',
};

const REF_THUMB: CSSProperties = {
  width: 36, height: 20, borderRadius: 2, objectFit: 'cover',
  border: '1px solid #333',
};

// ─── Component ───

export default function GenerationPromptInput() {
  const machineState = useGenerationControlStore((s) => s.machineState);
  const activeProviderId = useGenerationControlStore((s) => s.activeProviderId);
  const prompt = useGenerationControlStore((s) => s.prompt);
  const params = useGenerationControlStore((s) => s.params);
  const referenceFrameDataUrl = useGenerationControlStore((s) => s.referenceFrameDataUrl);
  const setPrompt = useGenerationControlStore((s) => s.setPrompt);
  const setParam = useGenerationControlStore((s) => s.setParam);
  const setEstimatedCost = useGenerationControlStore((s) => s.setEstimatedCost);
  const setReferenceFrame = useGenerationControlStore((s) => s.setReferenceFrame);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const disabled = !['IDLE', 'CONFIGURING', 'REJECTED'].includes(machineState);

  const provider = activeProviderId ? PROVIDER_MAP.get(activeProviderId) : null;

  // Debounced cost estimate — 500ms after prompt/param change
  useEffect(() => {
    if (!activeProviderId || !prompt.trim()) {
      setEstimatedCost(null);
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${API_BASE}/cut/generate/estimate-cost`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ provider_id: activeProviderId, prompt, params }),
        });
        if (res.ok) {
          const data = await res.json() as { estimated_usd: number };
          setEstimatedCost(data.estimated_usd);
        }
      } catch {
        // Estimate failed — show null gracefully
        setEstimatedCost(null);
      }
    }, 500);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [prompt, params, activeProviderId, setEstimatedCost]);

  const captureReferenceFrame = useCallback(() => {
    // Cmd+F: capture from source monitor <video> element
    const video = document.querySelector<HTMLVideoElement>('[data-source-monitor-video]');
    if (!video) return;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 320;
    canvas.height = video.videoHeight || 180;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    setReferenceFrame(canvas.toDataURL('image/jpeg', 0.8));
  }, [setReferenceFrame]);

  const clearReferenceFrame = useCallback(() => setReferenceFrame(null), [setReferenceFrame]);

  const renderParam = (schema: ParamSchema) => {
    const value = params[schema.key] ?? schema.default;
    return (
      <div key={schema.key} style={PARAM_FIELD} data-testid={`param-${schema.key}`}>
        <div style={LABEL}>{schema.label}</div>
        {schema.type === 'select' ? (
          <select
            style={INPUT}
            value={String(value)}
            disabled={disabled}
            onChange={(e) => setParam(schema.key, e.target.value)}
          >
            {schema.options?.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        ) : (
          <input
            style={INPUT}
            type={schema.type === 'number' ? 'number' : 'text'}
            value={String(value)}
            min={schema.min}
            max={schema.max}
            step={schema.step}
            disabled={disabled}
            onChange={(e) => setParam(schema.key, schema.type === 'number' ? parseFloat(e.target.value) : e.target.value)}
          />
        )}
      </div>
    );
  };

  return (
    <div style={CONTAINER} data-testid="generation-prompt-input">
      {/* Prompt textarea */}
      <div>
        <div style={LABEL}>Prompt</div>
        <textarea
          style={{ ...TEXTAREA, opacity: disabled ? 0.5 : 1 }}
          value={prompt}
          disabled={disabled}
          placeholder={disabled ? '—' : 'Describe what to generate…'}
          onChange={(e) => setPrompt(e.target.value)}
          data-testid="prompt-textarea"
        />
      </div>

      {/* Reference frame */}
      <div style={REF_ROW}>
        <button
          style={REF_BTN}
          onClick={captureReferenceFrame}
          disabled={disabled}
          title="Capture reference frame from Source Monitor (⌘F)"
          data-testid="btn-capture-ref"
        >
          Ref Frame
        </button>
        {referenceFrameDataUrl && (
          <>
            <img
              src={referenceFrameDataUrl}
              style={REF_THUMB}
              alt="Reference frame"
              data-testid="ref-frame-thumb"
            />
            <button
              style={{ ...REF_BTN, color: '#555' }}
              onClick={clearReferenceFrame}
              data-testid="btn-clear-ref"
            >
              ×
            </button>
          </>
        )}
      </div>

      {/* Provider param grid */}
      {provider && provider.paramSchema.length > 0 && (
        <div>
          <div style={LABEL}>Parameters</div>
          <div style={PARAMS_GRID}>
            {provider.paramSchema.map(renderParam)}
          </div>
        </div>
      )}
    </div>
  );
}
