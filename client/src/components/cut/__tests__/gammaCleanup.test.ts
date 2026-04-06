/**
 * MARKER_GAMMA-TS-CLEAN: Structural regression tests for Gamma-owned files.
 *
 * Verifies:
 *   - No unused type imports (LayerManifestMeta, AcquireJob)
 *   - No `as any` casts in EditMarkerDialog (marker field access)
 *   - DockviewLayout uses DockviewLayoutJSON instead of `as any`
 *   - MenuBar uses explicit union type instead of `as any`
 *   - TimeMarker type includes `notes` field
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const BASE = resolve(__dirname, '..');
const PANELS = resolve(BASE, 'panels');
const STORE = resolve(__dirname, '..', '..', '..', 'store');

function read(path: string): string {
  return readFileSync(path, 'utf-8');
}

describe('Gamma cleanup: unused imports removed', () => {
  it('LayerStackPanel does not import LayerManifestMeta', () => {
    const src = read(resolve(PANELS, 'LayerStackPanel.tsx'));
    expect(src).not.toContain('LayerManifestMeta');
  });

  it('SourceAcquirePanelDock does not import AcquireJob', () => {
    const src = read(resolve(PANELS, 'SourceAcquirePanelDock.tsx'));
    expect(src).not.toMatch(/import.*AcquireJob/);
  });
});

describe('Gamma cleanup: as-any casts eliminated', () => {
  it('EditMarkerDialog has no `as any` casts', () => {
    const src = read(resolve(PANELS, 'EditMarkerDialog.tsx'));
    expect(src).not.toContain('as any');
  });

  it('DockviewLayout uses DockviewLayoutJSON type (no raw `as any` for panel dedup)', () => {
    const src = read(resolve(BASE, 'DockviewLayout.tsx'));
    // Should have the typed interface
    expect(src).toContain('interface DockviewLayoutJSON');
    // Should use it instead of `as any` in dedup guards
    expect(src).toContain('as DockviewLayoutJSON');
    // Panel map should not use `: any` parameter type
    const panelMapMatches = src.match(/panels\.map\(\(p:\s*any\)/g);
    expect(panelMapMatches).toBeNull();
  });

  it('MenuBar does not use bare `as any` for setFocusedPanel', () => {
    const src = read(resolve(BASE, 'MenuBar.tsx'));
    // Should not have `targetFocus as any`
    expect(src).not.toMatch(/targetFocus\s+as\s+any/);
  });
});

describe('Gamma cleanup: TimeMarker type has notes field', () => {
  it('useCutEditorStore TimeMarker type includes notes', () => {
    const src = read(resolve(STORE, 'useCutEditorStore.ts'));
    // Find TimeMarker type definition and check for notes field
    const markerTypeMatch = src.match(/export type TimeMarker\s*=\s*\{[\s\S]*?\};/);
    expect(markerTypeMatch).not.toBeNull();
    expect(markerTypeMatch![0]).toContain('notes?:');
  });
});
