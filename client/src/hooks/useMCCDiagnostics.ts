import { useCallback, useEffect, useRef, useState } from 'react';
// MARKER_176.15: Centralized MCC API config import.
import { MCC_API } from '../config/api.config';

const MIN_RUNTIME_FETCH_INTERVAL_MS = 2000;
const MIN_BUILD_FETCH_INTERVAL_MS = 15000;
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

  const lastRuntimeFetchRef = useRef(0);
  const lastBuildFetchRef = useRef(0);
  const inFlightRef = useRef(false);
  const queuedRef = useRef(false);
  const aliveRef = useRef(true);

  const pushEvent = useCallback((event: DiagnosticsEvent) => {
    setState(prev => ({
      ...prev,
      eventLog: [event, ...prev.eventLog].slice(0, MAX_EVENT_LOG),
    }));
  }, []);

  const doFetch = useCallback(async (
    source: TriggerSource,
    forceRuntime = false,
    includeBuild = false
  ) => {
    const now = Date.now();
    const shouldFetchRuntime =
      forceRuntime || now - lastRuntimeFetchRef.current >= MIN_RUNTIME_FETCH_INTERVAL_MS;
    const shouldFetchBuild = includeBuild &&
      (now - lastBuildFetchRef.current >= MIN_BUILD_FETCH_INTERVAL_MS);

    if (!shouldFetchRuntime && !shouldFetchBuild) {
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
    if (shouldFetchRuntime) {
      lastRuntimeFetchRef.current = now;
    }
    if (shouldFetchBuild) {
      lastBuildFetchRef.current = now;
    }
    pushEvent({
      ts: now,
      source,
      action: 'fetch',
      note: `${forceRuntime ? 'force-runtime' : 'normal'}${shouldFetchBuild ? '+build' : ''}`,
    });

    setState(prev => ({ ...prev, loading: true, error: null }));

    try {
      const runtimePromise = shouldFetchRuntime
        ? fetch(`${MCC_API}/graph/predict/runtime-health?force=${forceRuntime ? 'true' : 'false'}`)
        : Promise.resolve(null);
      const buildPromise = shouldFetchBuild
        ? fetch(`${MCC_API}/graph/build-design`, {
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
          })
        : Promise.resolve(null);

      const [healthRes, buildRes] = await Promise.all([runtimePromise, buildPromise]);

      if (!aliveRef.current) return;

      const healthJson = healthRes && healthRes.ok ? await healthRes.json() : null;
      const buildJson = buildRes && buildRes.ok ? await buildRes.json() : null;
      const errors: string[] = [];
      if (healthRes && !healthRes.ok) errors.push(`health=${healthRes.status}`);
      if (buildRes && !buildRes.ok) errors.push(`build=${buildRes.status}`);

      setState(prev => ({
        ...prev,
        loading: false,
        error: errors.length > 0 ? errors.join(' ') : null,
        lastUpdatedAt: Date.now(),
        lastReason: source,
        runtimeHealth: shouldFetchRuntime
          ? ((healthJson as RuntimeHealthData | null) || null)
          : prev.runtimeHealth,
        buildDesign: shouldFetchBuild
          ? ((buildJson as BuildDesignData | null) || null)
          : prev.buildDesign,
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
        void doFetch(source, false, false);
      }
    }
  }, [pushEvent]);

  useEffect(() => {
    aliveRef.current = true;
    void doFetch('init', true, false);

    const onTaskBoard = () => { void doFetch('task-board-updated', false, false); };
    const onPipelineActivity = () => { void doFetch('pipeline-activity', false, false); };
    const onFocus = () => { void doFetch('focus', true, false); };
    const onVisibility = () => {
      if (document.visibilityState === 'visible') {
        void doFetch('visibility', true, false);
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
    void doFetch('manual', forceRuntime, true);
  }, [doFetch]);

  return {
    ...state,
    refresh,
  };
}
