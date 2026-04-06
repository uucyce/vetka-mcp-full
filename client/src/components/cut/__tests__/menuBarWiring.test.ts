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
    expect(src).toMatch(/label:\s*'Render All'.*action:/);
    expect(src).not.toMatch(/label:\s*'Render All'.*disabled:\s*true/);
  });

  it('Save As is wired with action (not disabled)', () => {
    const src = readMenuBar();
    expect(src).toMatch(/label:\s*'Save As\.\.\.'.*action:/);
    expect(src).not.toMatch(/label:\s*'Save As\.\.\.'.*disabled:\s*true/);
  });

  it('Trim Edit is wired to setTrimEditActive (not disabled)', () => {
    const src = readMenuBar();
    expect(src).toMatch(/label:\s*'Trim Edit'.*action:/);
    expect(src).not.toMatch(/label:\s*'Trim Edit'.*disabled:\s*true/);
    expect(src).toContain('setTrimEditActive');
  });

  it('store has renderAll implementation', () => {
    const src = readStore();
    expect(src).toMatch(/renderAll:\s*async\s*\(\)/);
  });

  it('store has setTrimEditActive implementation', () => {
    const src = readStore();
    expect(src).toMatch(/setTrimEditActive:/);
  });
});

describe('MenuBar: disabled items inventory', () => {
  it('counts remaining disabled items (regression guard)', () => {
    const src = readMenuBar();
    const hardDisabled = src.match(/disabled:\s*true\b/g) || [];
    // After wiring Render All + Save As + Trim Edit: remaining =
    // Save All, Freeze Frame, Scale to Sequence, Group, 7 Composite Mode, Nest Items = 12
    // + 1 tolerance for edge cases
    expect(hardDisabled.length).toBeLessThanOrEqual(13);
    expect(hardDisabled.length).toBeGreaterThanOrEqual(5);
  });
});
