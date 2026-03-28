/**
 * MARKER_GEN-COST: Generation Cost Badge — estimated + session spend.
 * Monochrome. Updates live (debounced 500ms from store).
 *
 * @phase GENERATION_CONTROL
 * @task tb_1774432024_1
 */
import type { CSSProperties } from 'react';
import { useGenerationControlStore } from '../../store/useGenerationControlStore';

const BADGE: CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 10,
  padding: '3px 8px',
  fontSize: 9, fontFamily: 'monospace', color: '#666',
  borderTop: '1px solid #111',
};

const LABEL: CSSProperties = {
  fontSize: 8, textTransform: 'uppercase', letterSpacing: 0.5, color: '#444',
  marginRight: 3,
};

export default function GenerationCostBadge() {
  const estimatedCostUsd = useGenerationControlStore((s) => s.estimatedCostUsd);
  const sessionSpendUsd = useGenerationControlStore((s) => s.sessionSpendUsd);

  return (
    <div style={BADGE} data-testid="generation-cost-badge">
      <span>
        <span style={LABEL}>Est</span>
        {estimatedCostUsd !== null ? `$${estimatedCostUsd.toFixed(3)}` : '—'}
      </span>
      <span style={{ color: '#333' }}>|</span>
      <span>
        <span style={LABEL}>Session</span>
        ${sessionSpendUsd.toFixed(3)}
      </span>
    </div>
  );
}
