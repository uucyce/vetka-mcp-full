/**
 * MARKER_DOCK-FIX-TAURI: Verify WebKit drag fix for dockview panels.
 *
 * Tauri uses WKWebView (Safari engine) on macOS. Safari requires
 * -webkit-user-drag: element for draggable="true" elements to fire
 * dragstart events. Without this CSS, dockview tabs are stuck.
 *
 * These tests verify:
 * 1. The CSS fix is present in dockview-cut-theme.css
 * 2. The dockview library sets draggable=true on tabs and void containers
 * 3. The CSS selector matches elements with draggable="true"
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const THEME_CSS_PATH = resolve(
  __dirname,
  '../dockview-cut-theme.css'
);

const DOCKVIEW_TAB_PATH = resolve(
  __dirname,
  '../../../../node_modules/dockview-core/dist/esm/dockview/components/tab/tab.js'
);

const DOCKVIEW_VOID_PATH = resolve(
  __dirname,
  '../../../../node_modules/dockview-core/dist/esm/dockview/components/titlebar/voidContainer.js'
);

describe('MARKER_DOCK-FIX-TAURI: WebKit drag fix', () => {
  const themeCSS = readFileSync(THEME_CSS_PATH, 'utf-8');

  it('dockview-cut-theme.css contains -webkit-user-drag: element rule', () => {
    expect(themeCSS).toContain('-webkit-user-drag: element');
  });

  it('CSS rule targets [draggable="true"] inside .dockview-theme-dark', () => {
    // The rule must be scoped to .dockview-theme-dark to avoid global side-effects
    const pattern = /\.dockview-theme-dark\s+\[draggable="true"\]\s*\{[^}]*-webkit-user-drag:\s*element/;
    expect(themeCSS).toMatch(pattern);
  });

  it('dockview tab.js sets element.draggable based on disableDnd', () => {
    const tabJS = readFileSync(DOCKVIEW_TAB_PATH, 'utf-8');
    expect(tabJS).toContain('.draggable');
    // Verify the tab element is created with draggable attribute
    expect(tabJS).toMatch(/this\._element\.draggable\s*=/);
  });

  it('dockview voidContainer.js sets element.draggable based on disableDnd', () => {
    const voidJS = readFileSync(DOCKVIEW_VOID_PATH, 'utf-8');
    expect(voidJS).toContain('.draggable');
    expect(voidJS).toMatch(/this\._element\.draggable\s*=/);
  });

  it('CSS does NOT set -webkit-user-drag on drag ghost (must stay pointer-events: none)', () => {
    // The drag ghost should NOT have -webkit-user-drag as it needs pointer-events: none
    const ghostRulePattern = /\.dv-tab-drag-ghost[^{]*\{[^}]*-webkit-user-drag/;
    expect(themeCSS).not.toMatch(ghostRulePattern);
  });

  it('drag ghost retains pointer-events: none', () => {
    expect(themeCSS).toMatch(/\.dv-tab-drag-ghost[\s\S]*?pointer-events:\s*none/);
  });

  it('sash resize retains pointer-events: auto (not broken by drag fix)', () => {
    expect(themeCSS).toMatch(/\.dv-sash[\s\S]*?pointer-events:\s*auto/);
  });
});
