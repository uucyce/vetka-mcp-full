export const DETACHED_ARTIFACT_CHAT_STATE_KEY = 'vetka_detached_artifact_chat_state_v1';
export const DETACHED_ARTIFACT_PIN_REQUEST_KEY = 'vetka_detached_artifact_pin_request_v1';

export interface DetachedArtifactChatStateV1 {
  schema_version: 'detached_artifact_chat_state_v1';
  chat_open: boolean;
  current_chat_id: string | null;
  pinned_paths: string[];
  updated_at_ms: number;
}

export interface DetachedArtifactPinRequestV1 {
  schema_version: 'detached_artifact_pin_request_v1';
  action: 'toggle_pin';
  path: string;
  requested_at_ms: number;
  request_id: string;
}

function hasLocalStorage(): boolean {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
}

export function normalizeDetachedArtifactPath(path: string): string {
  const raw = String(path || '').trim();
  if (!raw) return '';
  const withoutScheme = raw.replace(/^file:\/\//, '');
  let decoded = withoutScheme;
  try {
    decoded = decodeURIComponent(withoutScheme);
  } catch {
    // Keep best-effort path when not URI encoded.
  }
  return decoded.replace(/\\/g, '/').replace(/\/+$/, '');
}

export function readDetachedArtifactChatState(): DetachedArtifactChatStateV1 | null {
  if (!hasLocalStorage()) return null;
  const raw = window.localStorage.getItem(DETACHED_ARTIFACT_CHAT_STATE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<DetachedArtifactChatStateV1>;
    if (parsed?.schema_version !== 'detached_artifact_chat_state_v1') return null;
    return {
      schema_version: 'detached_artifact_chat_state_v1',
      chat_open: Boolean(parsed.chat_open),
      current_chat_id: typeof parsed.current_chat_id === 'string' && parsed.current_chat_id.trim()
        ? parsed.current_chat_id.trim()
        : null,
      pinned_paths: Array.isArray(parsed.pinned_paths)
        ? parsed.pinned_paths.map((item) => normalizeDetachedArtifactPath(String(item || ''))).filter(Boolean)
        : [],
      updated_at_ms: Number(parsed.updated_at_ms || 0),
    };
  } catch {
    return null;
  }
}

export function writeDetachedArtifactChatState(state: DetachedArtifactChatStateV1): void {
  if (!hasLocalStorage()) return;
  window.localStorage.setItem(DETACHED_ARTIFACT_CHAT_STATE_KEY, JSON.stringify(state));
}

export function parseDetachedArtifactPinRequest(raw: string | null): DetachedArtifactPinRequestV1 | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<DetachedArtifactPinRequestV1>;
    if (parsed?.schema_version !== 'detached_artifact_pin_request_v1') return null;
    const path = normalizeDetachedArtifactPath(String(parsed.path || ''));
    if (!path || parsed.action !== 'toggle_pin') return null;
    return {
      schema_version: 'detached_artifact_pin_request_v1',
      action: 'toggle_pin',
      path,
      requested_at_ms: Number(parsed.requested_at_ms || 0),
      request_id: String(parsed.request_id || ''),
    };
  } catch {
    return null;
  }
}

export function writeDetachedArtifactPinRequest(request: DetachedArtifactPinRequestV1): void {
  if (!hasLocalStorage()) return;
  window.localStorage.setItem(DETACHED_ARTIFACT_PIN_REQUEST_KEY, JSON.stringify(request));
}
