export interface DagLayoutBiasProfile {
  vertical_separation_bias: number;
  sibling_spacing_bias: number;
  branch_compactness_bias: number;
  focus_overlay_preference?: string;
  pin_persistence_preference?: string;
  confidence: number;
  sample_count: number;
  updated_at?: string;
}

const API_BASE = 'http://localhost:5001/api/mcc';
const PROFILE_CACHE = new Map<string, DagLayoutBiasProfile>();

function clamp(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v));
}

export async function fetchDagLayoutBiasProfile(
  scopeKey: string,
  userId = 'danila',
): Promise<DagLayoutBiasProfile | null> {
  if (!scopeKey) return null;
  if (PROFILE_CACHE.has(scopeKey)) return PROFILE_CACHE.get(scopeKey)!;

  const url = `${API_BASE}/layout/preferences?user_id=${encodeURIComponent(userId)}&scope_key=${encodeURIComponent(scopeKey)}`;
  const res = await fetch(url);
  if (!res.ok) return null;
  const json = await res.json();
  const profile = json?.profile;
  if (!profile || typeof profile !== 'object') return null;
  PROFILE_CACHE.set(scopeKey, profile);
  return profile as DagLayoutBiasProfile;
}

export async function updateDagLayoutBiasProfile(
  scopeKey: string,
  profile: Partial<DagLayoutBiasProfile>,
  userId = 'danila',
): Promise<DagLayoutBiasProfile | null> {
  if (!scopeKey) return null;
  const res = await fetch(`${API_BASE}/layout/preferences`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      scope_key: scopeKey,
      profile,
    }),
  });
  if (!res.ok) return null;
  const json = await res.json();
  const merged = json?.profile as DagLayoutBiasProfile | undefined;
  if (merged) PROFILE_CACHE.set(scopeKey, merged);
  return merged || null;
}

export function inferBiasFromPinnedPositions(
  positions: Record<string, { x: number; y: number }>,
): Partial<DagLayoutBiasProfile> {
  const points = Object.values(positions || {});
  if (points.length < 3) {
    return {
      confidence: 0.55,
      sample_count: 1,
    };
  }

  const xs = points.map(p => p.x);
  const ys = points.map(p => p.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const spreadX = Math.max(1, maxX - minX);
  const spreadY = Math.max(1, maxY - minY);
  const ratioYtoX = spreadY / spreadX;
  const compactness = points.length / (spreadX * spreadY);

  return {
    vertical_separation_bias: clamp((ratioYtoX - 0.75) * 1.2, -1, 1),
    sibling_spacing_bias: clamp((spreadX / Math.max(1, points.length * 55)) - 1, -1, 1),
    branch_compactness_bias: clamp((compactness * 120000) - 0.5, -1, 1),
    focus_overlay_preference: 'focus_only',
    pin_persistence_preference: 'pin_first',
    confidence: clamp(0.55 + Math.log10(points.length + 1) * 0.2, 0.55, 0.95),
    sample_count: 1,
    updated_at: new Date().toISOString(),
  };
}

