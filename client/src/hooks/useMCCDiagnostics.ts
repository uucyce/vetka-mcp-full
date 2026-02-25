import { useCallback, useEffect, useRef, useState } from 'react';

const API_BASE = 'http://localhost:5001/api';
const MIN_FETCH_INTERVAL_MS = 2000;
const MAX_EVENT_LOG = 30;

type TriggerSource =
  | 'init'
  | 'manual'
  | 'task-board-updated'
  | 'pipeline-activity'
  | 'focus'
  | 'visibility';

interface RuntimeHealthData {
  ok: boolean;
  enabled: boolean;
  embed_url: string;
  health_url: string;
  detail: string;
  backend: string;
  backend_detail: string;
  runtime_module: string;
}

interface VerifierSpectralData {
  lambda2?: number;
  eigengap?: number;
  component_count?: number;
  status?: string;
}

interface VerifierData {
  decision?: 'pass' | 'warn' | 'fail' | string;
  acyclic?: boolean;
  monotonic_knowledge_y?: boolean;
  orphan_rate?: number;
  spectral?: VerifierSpectralData;
}

interface BuildDesignData {
  verifier?: VerifierData;
  design_graph?: {
    nodes?: Array<unknown>;
    edges?: Array<unknown>;
  };
  runtime_graph?: {
    signature?: string;
  };
}

export interface DiagnosticsEvent {
  ts: number;
  source: TriggerSource;
  action: 'fetch' | 'skip' | 'queue';
  note: string;
}

export interface MCCDiagnosticsState {
  loading: boolean;
  error: string | null;
  lastUpdatedAt: number | null;
  lastReason: TriggerSource | null;
  runtimeHealth: RuntimeHealthData | null;
  buildDesign: BuildDesignData | null;
  eventLog: DiagnosticsEvent[];
}

export function useMCCDiagnostics() {
  const [state, setState] = useState<MCCDiagnosticsState>({
    loading: true,
    error: null,
    lastUpdatedAt: null,
    lastReason: null,
    runtimeHealth: null,
    buildDesign: null,
    eventLog: [],
  });

  const lastFetchRef = useRef(0);
  const inFlightRef = useRef(false);
  const queuedRef = useRef(false);
  const aliveRef = useRef(true);

  const pushEvent = useCallback((event: DiagnosticsEvent) => {
    setState(prev => ({
      ...prev,
      eventLog: [event, ...prev.eventLog].slice(0, MAX_EVENT_LOG),
    }));
  }, []);

  const doFetch = useCallback(async (source: TriggerSource, forceRuntime = false) => {
    const now = Date.now();
    if (now - lastFetchRef.current < MIN_FETCH_INTERVAL_MS) {
      pushEvent({
        ts: now,
        source,
        action: 'skip',
        note: 'debounced',
      });
      return;
    }

    if (inFlightRef.current) {
      queuedRef.current = true;
      pushEvent({
        ts: now,
        source,
        action: 'queue',
        note: 'in-flight',
      });
      return;
    }

    inFlightRef.current = true;
    lastFetchRef.current = now;
    pushEvent({
      ts: now,
      source,
      action: 'fetch',
      note: forceRuntime ? 'force-runtime' : 'normal',
    });

    setState(prev => ({ ...prev, loading: true, error: null }));

    try {
      const [healthRes, buildRes] = await Promise.all([
        fetch(`${API_BASE}/mcc/graph/predict/runtime-health?force=${forceRuntime ? 'true' : 'false'}`),
        fetch(`${API_BASE}/mcc/graph/build-design`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            scope_path: '',
            max_nodes: 260,
            include_artifacts: false,
            use_predictive_overlay: false,
            max_predicted_edges: 0,
            min_confidence: 0.55,
            problem_statement: '',
            target_outcome: '',
          }),
        }),
      ]);

      if (!aliveRef.current) return;

      const healthJson = healthRes.ok ? await healthRes.json() : null;
      const buildJson = buildRes.ok ? await buildRes.json() : null;

      setState(prev => ({
        ...prev,
        loading: false,
        error: (!healthRes.ok || !buildRes.ok)
          ? `health=${healthRes.status} build=${buildRes.status}`
          : null,
        lastUpdatedAt: Date.now(),
        lastReason: source,
        runtimeHealth: (healthJson as RuntimeHealthData | null) || null,
        buildDesign: (buildJson as BuildDesignData | null) || null,
      }));
    } catch (err) {
      if (!aliveRef.current) return;
      setState(prev => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : 'Diagnostics fetch failed',
      }));
    } finally {
      inFlightRef.current = false;
      if (queuedRef.current && aliveRef.current && document.visibilityState === 'visible') {
        queuedRef.current = false;
        void doFetch(source, false);
      }
    }
  }, [pushEvent]);

  useEffect(() => {
    aliveRef.current = true;
    void doFetch('init', true);

    const onTaskBoard = () => { void doFetch('task-board-updated'); };
    const onPipelineActivity = () => { void doFetch('pipeline-activity'); };
    const onFocus = () => { void doFetch('focus'); };
    const onVisibility = () => {
      if (document.visibilityState === 'visible') {
        void doFetch('visibility');
      }
    };

    window.addEventListener('task-board-updated', onTaskBoard as EventListener);
    window.addEventListener('pipeline-activity', onPipelineActivity as EventListener);
    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      aliveRef.current = false;
      window.removeEventListener('task-board-updated', onTaskBoard as EventListener);
      window.removeEventListener('pipeline-activity', onPipelineActivity as EventListener);
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [doFetch]);

  const refresh = useCallback((forceRuntime = false) => {
    void doFetch('manual', forceRuntime);
  }, [doFetch]);

  return {
    ...state,
    refresh,
  };
}
