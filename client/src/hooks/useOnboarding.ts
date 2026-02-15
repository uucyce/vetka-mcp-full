import { useCallback, useEffect, useState } from 'react';

type OnboardingStep = 0 | 1 | 2 | 3 | 4;

interface OnboardingState {
  step: OnboardingStep;
  completed: boolean;
  dismissed: boolean;
}

const KEY = 'vetka_onboarding';

const DEFAULT_STATE: OnboardingState = {
  step: 0,
  completed: false,
  dismissed: false,
};

function loadState(): OnboardingState {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return DEFAULT_STATE;
    const parsed = JSON.parse(raw) as Partial<OnboardingState>;
    return {
      step: (parsed.step ?? 0) as OnboardingStep,
      completed: Boolean(parsed.completed),
      dismissed: Boolean(parsed.dismissed),
    };
  } catch {
    return DEFAULT_STATE;
  }
}

export function useOnboarding() {
  const [state, setState] = useState<OnboardingState>(DEFAULT_STATE);

  useEffect(() => {
    const initial = loadState();
    if (!initial.completed && !initial.dismissed && initial.step === 0) {
      const started: OnboardingState = { ...initial, step: 1 };
      setState(started);
      localStorage.setItem(KEY, JSON.stringify(started));
      return;
    }
    setState(initial);
  }, []);

  useEffect(() => {
    localStorage.setItem(KEY, JSON.stringify(state));
  }, [state]);

  const advance = useCallback(() => {
    setState((prev) => {
      if (prev.completed || prev.dismissed) return prev;
      if (prev.step === 4) {
        return { ...prev, completed: true, dismissed: true };
      }
      const nextStep = (prev.step + 1) as OnboardingStep;
      return { ...prev, step: nextStep };
    });
  }, []);

  const dismiss = useCallback(() => {
    setState((prev) => ({ ...prev, dismissed: true }));
  }, []);

  const reset = useCallback(() => {
    setState({ step: 1, completed: false, dismissed: false });
  }, []);

  return {
    step: state.step,
    completed: state.completed,
    dismissed: state.dismissed,
    advance,
    dismiss,
    reset,
  };
}
