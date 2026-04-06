/**
 * MARKER_GAMMA-MENU-WIRE: Structural tests for MenuBar menu item wiring.
 *
 * Verifies that menu items with existing store handlers are wired (not disabled).
 * Catches regressions where working store actions get disconnected from the UI.
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const MENUBAR_PATH = resolve(__dirname, '..', 'MenuBar.tsx');
const STORE_PATH = resolve(__dirname, '..', '..', '..', 'store', 'useCutEditorStore.ts');

function readMenuBar(): string {
  return readFileSync(MENUBAR_PATH, 'utf-8');
}

function readStore(): string {
  return readFileSync(STORE_PATH, 'utf-8');
}

describe('MenuBar: wired menu items must not be disabled', () => {
  it('Render All is wired to store.renderAll()', () => {
    const src = readMenuBar();
    // Must have Render All with an action, not disabled
    expect(src).toMatch(/label:\s*'Render All'.*action:/);
    expect(src).not.toMatch(/label:\s*'Render All'.*disabled:\s*true/);
  });

  it('store has renderAll implementation', () => {
    const src = readStore();
    expect(src).toMatch(/renderAll:\s*async\s*\(\)/);
  });
});

describe('MenuBar: disabled items inventory', () => {
  it('counts remaining disabled items (regression guard)', () => {
    const src = readMenuBar();
    // Count items with `disabled: true` (not conditional disables like `disabled: !selectedClipId`)
    const hardDisabled = src.match(/disabled:\s*true\b/g) || [];
    // Current known count: Freeze Frame, Scale to Sequence, Group,
    // 7 Composite Mode items, Trim Edit, Nest Items, Save As, Save All = 14
    // Allow some tolerance but catch large regressions
    expect(hardDisabled.length).toBeLessThanOrEqual(15);
    expect(hardDisabled.length).toBeGreaterThanOrEqual(5); // guard against false "all wired" claims
  });
});
