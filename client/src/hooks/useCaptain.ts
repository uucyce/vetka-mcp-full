/**
 * MARKER_153.7C: useCaptain — hook for Architect Captain recommendations.
 *
 * Fetches recommendation from GET /api/mcc/captain/recommend.
 * Provides accept/reject actions that call corresponding endpoints.
 * Auto-fetches on mount when enabled.
 *
 * @phase 153
 * @wave 7
 * @status active
 */

import { useState, useCallback, useEffect } from 'react';
import { API_BASE } from '../config/api.config';

export interface Recommendation {
  has_recommendation: boolean;
  module_id: string;
  module_label: string;
  task_title: string;
  description: string;
  priority: number;
  workflow_id: string;
  preset: string;
  reason: string;
  confidence: number;
  alternatives: string[];
  message?: string;  // when no recommendation
}

export interface ProjectProgress {
  total: number;
  completed: number;
  active: number;
  pending: number;
  percent: number;
  completed_ids: string[];
}

interface CaptainState {
  recommendation: Recommendation | null;
  progress: ProjectProgress | null;
  loading: boolean;
  error: string | null;
}

export function useCaptain(autoFetch: boolean = false) {
  const [state, setState] = useState<CaptainState>({
    recommendation: null,
    progress: null,
    loading: false,
    error: null,
  });

  const fetchRecommendation = useCallback(async () => {
    setState(s => ({ ...s, loading: true, error: null }));
    try {
      const res = await fetch(`${API_BASE}/mcc/captain/recommend`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: Recommendation = await res.json();
      setState(s => ({ ...s, recommendation: data, loading: false }));
      return data;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setState(s => ({ ...s, error: msg, loading: false }));
      return null;
    }
  }, []);

  const fetchProgress = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/mcc/captain/progress`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: ProjectProgress = await res.json();
      setState(s => ({ ...s, progress: data }));
      return data;
    } catch {
      return null;
    }
  }, []);

  const acceptRecommendation = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/mcc/captain/accept`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      // Refresh recommendation after accept
      await fetchRecommendation();
      return data;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setState(s => ({ ...s, error: msg }));
      return null;
    }
  }, [fetchRecommendation]);

  const rejectRecommendation = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/mcc/captain/reject`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return data;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setState(s => ({ ...s, error: msg }));
      return null;
    }
  }, []);

  // Auto-fetch on mount if enabled
  useEffect(() => {
    if (autoFetch) {
      fetchRecommendation();
      fetchProgress();
    }
  }, [autoFetch, fetchRecommendation, fetchProgress]);

  return {
    ...state,
    fetchRecommendation,
    fetchProgress,
    acceptRecommendation,
    rejectRecommendation,
  };
}
