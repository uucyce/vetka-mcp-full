/**
 * MARKER_155.FLOW.STEPS: Step Indicator — 5-step progress for user flow.
 *
 * Shows current step in the user journey:
 * 1. 🚀 Launch — Select project
 * 2. 📁 Playground — Setup workspace
 * 3. 🔑 Keys — API configuration
 * 4. 🗺️ DAG — Plan architecture
 * 5. 🔍 Drill — Execute tasks
 *
 * @phase 155
 * @wave 4 (P2)
 * @status active
 */

import { useMCCStore } from '../../store/useMCCStore';
import { NOLAN_PALETTE } from '../../utils/dagLayout';

interface Step {
  id: number;
  label: string;
  description: string;
  icon: string;
}

const STEPS: Step[] = [
  { id: 1, label: 'Launch', description: 'Select project', icon: '🚀' },
  { id: 2, label: 'Playground', description: 'Setup workspace', icon: '📁' },
  { id: 3, label: 'Keys', description: 'API configuration', icon: '🔑' },
  { id: 4, label: 'DAG', description: 'Plan architecture', icon: '🗺️' },
  { id: 5, label: 'Drill', description: 'Execute tasks', icon: '🔍' },
];

export function StepIndicator() {
  const { navLevel, hasProject } = useMCCStore();

  const currentStep =
    navLevel === 'roadmap'
      ? 4
      : ['tasks', 'workflow', 'running', 'results'].includes(navLevel)
        ? 5
        : 4;

  // MARKER_155A.P0.STEP_VISIBILITY:
  // Hide the phase strip during first-run setup to avoid showing inactive drill stages.
  if (!hasProject || navLevel === 'first_run') {
    return null;
  }

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 4,
        padding: '8px 16px',
        background: NOLAN_PALETTE.bgLight,
        borderBottom: `1px solid ${NOLAN_PALETTE.border}`,
        fontFamily: 'monospace',
      }}
    >
      {STEPS.map((step, index) => {
        const isActive = step.id === currentStep;
        const isCompleted = step.id < currentStep;
        const isLast = index === STEPS.length - 1;

        return (
          <div key={step.id} style={{ display: 'flex', alignItems: 'center' }}>
            {/* Step circle */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '4px 10px',
                borderRadius: 4,
                background: isActive
                  ? 'rgba(74, 158, 255, 0.15)'
                  : isCompleted
                    ? 'rgba(136, 136, 136, 0.1)'
                    : 'transparent',
                border: `1px solid ${
                  isActive
                    ? 'rgba(74, 158, 255, 0.5)'
                    : isCompleted
                      ? 'rgba(136, 136, 136, 0.3)'
                      : 'transparent'
                }`,
                opacity: isActive || isCompleted ? 1 : 0.5,
                transition: 'all 0.2s ease',
                cursor: isCompleted ? 'pointer' : 'default',
              }}
              title={`${step.icon} ${step.label}: ${step.description}`}
            >
              {/* Icon */}
              <span style={{ fontSize: 12 }}>{step.icon}</span>

              {/* Label (only for active step on small screens, always on larger) */}
              <span
                style={{
                  fontSize: 9,
                  fontWeight: isActive ? 600 : 400,
                  color: isActive
                    ? NOLAN_PALETTE.text
                    : isCompleted
                      ? NOLAN_PALETTE.textDim
                      : '#444',
                  textTransform: 'uppercase',
                  letterSpacing: 0.5,
                }}
              >
                {step.label}
              </span>

              {/* Step number badge */}
              <span
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: '50%',
                  background: isActive
                    ? '#4a9eff'
                    : isCompleted
                      ? '#666'
                      : '#333',
                  color: '#fff',
                  fontSize: 7,
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {step.id}
              </span>
            </div>

            {/* Connector line */}
            {!isLast && (
              <div
                style={{
                  width: 16,
                  height: 1,
                  background:
                    isCompleted || (isActive && currentStep > step.id)
                      ? 'rgba(136, 136, 136, 0.5)'
                      : 'rgba(68, 68, 68, 0.3)',
                  margin: '0 4px',
                }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
