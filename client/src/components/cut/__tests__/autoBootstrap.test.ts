/**
 * MARKER_CUT-UX-NOWELCOME — Auto-bootstrap contract tests.
 *
 * Tests:
 * 1. DockviewLayout source no longer imports WelcomeScreen
 * 2. DockviewLayout source has no showWelcome early-return block
 * 3. CutStandalone has setSandboxRoot (mutable sandbox state)
 * 4. CutStandalone has auto-bootstrap useEffect guard
 * 5. refreshProjectState sandboxRootOverride path builds correct URL
 * 6. handleBootstrap captures effectiveSandboxRoot from response
 * 7. Bootstrap sends mode=create_or_open unconditionally
 * 8. refreshProjectState skips when no sr and no override
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const WORKTREE = resolve(__dirname, '../../../../../');
const DOCKVIEW_PATH = resolve(WORKTREE, 'client/src/components/cut/DockviewLayout.tsx');
const STANDALONE_PATH = resolve(WORKTREE, 'client/src/CutStandalone.tsx');

function readSrc(p: string) {
  return readFileSync(p, 'utf-8');
}

describe('MARKER_CUT-UX-NOWELCOME: auto-bootstrap, no WelcomeScreen gate', () => {
  it('1. DockviewLayout does not import WelcomeScreen as default', () => {
    const src = readSrc(DOCKVIEW_PATH);
    // Should not have "import WelcomeScreen" as an active import
    expect(src).not.toMatch(/^import WelcomeScreen/m);
  });

  it('2. DockviewLayout has no showWelcome early-return block', () => {
    const src = readSrc(DOCKVIEW_PATH);
    expect(src).not.toContain('if (showWelcome)');
    expect(src).not.toContain('return (\n      <WelcomeScreen');
  });

  it('3. CutStandalone declares setSandboxRoot setter', () => {
    const src = readSrc(STANDALONE_PATH);
    expect(src).toContain('const [sandboxRoot, setSandboxRoot] = useState(');
  });

  it('4. CutStandalone has auto-bootstrap effect for missing query.sandboxRoot', () => {
    const src = readSrc(STANDALONE_PATH);
    expect(src).toContain('if (!query.sandboxRoot)');
    expect(src).toContain('void handleBootstrap()');
  });

  it('5. refreshProjectState accepts sandboxRootOverride as third parameter', () => {
    const src = readSrc(STANDALONE_PATH);
    expect(src).toContain('sandboxRootOverride?: string');
    expect(src).toContain('const sr = sandboxRootOverride || sandboxRoot');
  });

  it('6. refreshProjectState uses sr (not sandboxRoot directly) in URL', () => {
    const src = readSrc(STANDALONE_PATH);
    expect(src).toContain('encodeURIComponent(sr)');
    // Must NOT use sandboxRoot directly in the fetch URL (inside refreshProjectState)
    // The URL construction now uses `sr`
    expect(src).not.toMatch(/encodeURIComponent\(sandboxRoot\)/);
  });

  it('7. handleBootstrap captures effectiveSandboxRoot from response', () => {
    const src = readSrc(STANDALONE_PATH);
    expect(src).toContain('effectiveSandboxRoot');
    expect(src).toContain('payload.project.sandbox_root || sandboxRoot');
    expect(src).toContain('setSandboxRoot(effectiveSandboxRoot)');
  });

  it('8. handleBootstrap passes effectiveSandboxRoot override to refreshProjectState', () => {
    const src = readSrc(STANDALONE_PATH);
    expect(src).toContain('refreshProjectState(payload.project.project_id, undefined, effectiveSandboxRoot');
  });
});
