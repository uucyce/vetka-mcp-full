/**
 * MARKER_A3.2 — Tests for BPM marker kind visibility toggle + localStorage persistence.
 *
 * Tests:
 * 1. All 4 BPM kinds visible by default
 * 2. toggleMarkerKind hides a visible kind
 * 3. toggleMarkerKind re-shows a hidden kind
 * 4. isMarkerKindVisible returns correct value
 * 5. Persistence: toggleMarkerKind writes to localStorage
 * 6. Init: visibleMarkerKinds reads from localStorage on store creation
 * 7. Init: falls back to defaults when localStorage is empty
 * 8. Init: falls back to defaults when localStorage has invalid JSON
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// ---------------------------------------------------------------------------
// localStorage mock
// ---------------------------------------------------------------------------

const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: vi.fn((key: string) => { delete store[key]; }),
    clear: vi.fn(() => { store = {}; }),
  };
})();

Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock, writable: true });

const LS_KEY = 'cut_visible_marker_kinds';

// ---------------------------------------------------------------------------
// Helper: fresh store import per test (reset module registry)
// ---------------------------------------------------------------------------
async function freshStore() {
  vi.resetModules();
  const { useDockviewStore } = await import('../useDockviewStore');
  return useDockviewStore;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('MARKER_A3.2: BPM marker kind visibility', () => {
  beforeEach(() => {
    localStorageMock.clear();
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();
  });

  it('1. all 4 BPM kinds visible by default', async () => {
    const store = await freshStore();
    const { visibleMarkerKinds } = store.getState();
    expect(visibleMarkerKinds.has('bpm_audio')).toBe(true);
    expect(visibleMarkerKinds.has('bpm_visual')).toBe(true);
    expect(visibleMarkerKinds.has('bpm_script')).toBe(true);
    expect(visibleMarkerKinds.has('sync_point')).toBe(true);
  });

  it('2. toggleMarkerKind hides a visible kind', async () => {
    const store = await freshStore();
    store.getState().toggleMarkerKind('bpm_audio');
    expect(store.getState().visibleMarkerKinds.has('bpm_audio')).toBe(false);
  });

  it('3. toggleMarkerKind re-shows a hidden kind', async () => {
    const store = await freshStore();
    store.getState().toggleMarkerKind('bpm_audio');
    store.getState().toggleMarkerKind('bpm_audio');
    expect(store.getState().visibleMarkerKinds.has('bpm_audio')).toBe(true);
  });

  it('4. isMarkerKindVisible returns correct value', async () => {
    const store = await freshStore();
    expect(store.getState().isMarkerKindVisible('bpm_visual')).toBe(true);
    store.getState().toggleMarkerKind('bpm_visual');
    expect(store.getState().isMarkerKindVisible('bpm_visual')).toBe(false);
  });

  it('5. persistence: toggleMarkerKind writes to localStorage', async () => {
    const store = await freshStore();
    store.getState().toggleMarkerKind('bpm_audio');
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      LS_KEY,
      expect.any(String),
    );
    const saved = JSON.parse(localStorageMock.setItem.mock.calls.at(-1)![1] as string) as string[];
    expect(saved).not.toContain('bpm_audio');
    expect(saved).toContain('bpm_visual');
  });

  it('6. init: restores kinds from localStorage', async () => {
    const kinds = ['bpm_visual', 'sync_point'];
    localStorageMock.getItem.mockImplementation((key: string) =>
      key === LS_KEY ? JSON.stringify(kinds) : null,
    );
    const store = await freshStore();
    localStorageMock.getItem.mockReset();
    expect(store.getState().visibleMarkerKinds.has('bpm_visual')).toBe(true);
    expect(store.getState().visibleMarkerKinds.has('sync_point')).toBe(true);
    expect(store.getState().visibleMarkerKinds.has('bpm_audio')).toBe(false);
  });

  it('7. init: falls back to defaults when localStorage empty', async () => {
    // localStorageMock returns null (cleared in beforeEach)
    const store = await freshStore();
    expect(store.getState().visibleMarkerKinds.size).toBeGreaterThanOrEqual(4);
  });

  it('8. init: falls back to defaults when localStorage has invalid JSON', async () => {
    localStorageMock.getItem.mockImplementation((key: string) =>
      key === LS_KEY ? 'not-json' : null,
    );
    const store = await freshStore();
    localStorageMock.getItem.mockReset();
    expect(store.getState().visibleMarkerKinds.has('bpm_audio')).toBe(true);
  });
});
