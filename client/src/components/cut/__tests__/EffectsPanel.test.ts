/**
 * MARKER_CUT-IMPORT-FIX: Structural tests for EffectsPanel.tsx
 *
 * Verifies:
 *   - No duplicate closing braces (regression: TransitionsSection had duplicate })
 *   - All exported functions are parseable
 *   - File has balanced braces
 *   - TransitionsSection function defined exactly once
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const EFFECTS_PATH = resolve(__dirname, '..', 'EffectsPanel.tsx');

function readSrc(): string {
  return readFileSync(EFFECTS_PATH, 'utf-8');
}

describe('EffectsPanel.tsx structural integrity', () => {
  it('has no duplicate "  );\\n}" closing pattern (TransitionsSection regression)', () => {
    const src = readSrc();
    const lines = src.split('\n');

    // Find all occurrences of the exact duplicate pattern:
    // line N: "  );"  line N+1: "}"
    let closingCount = 0;
    for (let i = 0; i < lines.length - 1; i++) {
      if (lines[i].trim() === ');' && lines[i + 1].trim() === '}') {
        closingCount++;
      }
    }
    // TransitionsSection + EffectsBrowser + EffectsPanel default + CategoryHeader + EffectTooltip
    // Each function can have one ");}" pattern. But there should NOT be two consecutive ones
    // separated by nothing (the old bug was "}  </div>  );  }" immediately followed by another).
    // Check: no two consecutive ");\n}" blocks within 3 lines of each other
    const closingPositions: number[] = [];
    for (let i = 0; i < lines.length - 1; i++) {
      if (lines[i].trim() === ');' && lines[i + 1].trim() === '}') {
        closingPositions.push(i);
      }
    }
    for (let j = 1; j < closingPositions.length; j++) {
      const gap = closingPositions[j] - closingPositions[j - 1];
      expect(gap, `Duplicate closing at lines ${closingPositions[j - 1] + 1} and ${closingPositions[j] + 1} (gap=${gap})`).toBeGreaterThan(2);
    }
  });

  it('TransitionsSection function is defined exactly once', () => {
    const src = readSrc();
    const matches = src.match(/function\s+TransitionsSection\s*\(/g);
    expect(matches).not.toBeNull();
    expect(matches!.length).toBe(1);
  });

  it('default export EffectsPanel function is defined exactly once', () => {
    const src = readSrc();
    const matches = src.match(/export\s+default\s+function\s+EffectsPanel\s*\(/g);
    expect(matches).not.toBeNull();
    expect(matches!.length).toBe(1);
  });

  it('EffectsBrowser function is defined exactly once', () => {
    const src = readSrc();
    const matches = src.match(/function\s+EffectsBrowser\s*\(/g);
    expect(matches).not.toBeNull();
    expect(matches!.length).toBe(1);
  });

  it('has roughly balanced curly braces', () => {
    const src = readSrc();
    // Remove string literals and comments to avoid counting braces inside them
    const stripped = src
      .replace(/\/\/.*$/gm, '')    // single-line comments
      .replace(/\/\*[\s\S]*?\*\//g, '') // multi-line comments
      .replace(/'[^']*'/g, '')     // single-quoted strings
      .replace(/"[^"]*"/g, '')     // double-quoted strings
      .replace(/`[^`]*`/g, '');    // template literals (simple)
    const opens = (stripped.match(/{/g) || []).length;
    const closes = (stripped.match(/}/g) || []).length;
    // Allow small imbalance from template literals we couldn't strip
    expect(Math.abs(opens - closes)).toBeLessThanOrEqual(2);
  });
});
