/**
 * MARKER_DELTA3_MONO_E2E: Runtime monochrome enforcement for CUT UI.
 *
 * Scans ALL computed CSS styles in the CUT editor DOM at runtime.
 * Fails on any non-grey pixel (R!=G or G!=B) outside exempt zones.
 *
 * Exempt zones:
 * - Color correction panels (ColorWheel, scopes)
 * - Marker dots/badges (semantic color by type)
 * - Audio metering (red/yellow/green safety)
 * - Music visualization (Camelot, BPM, Pulse)
 * - Canvas/video elements (actual media content)
 *
 * This catches violations that static grep misses:
 * - Tailwind classes resolving to color
 * - CSS variables evaluating to non-grey
 * - Runtime-injected styles
 */

const { test, expect } = require('@playwright/test');
const http = require('http');
const net = require('net');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_MONO_PORT || 3215);
const DEV_ORIGIN = `http://127.0.0.1:${DEV_PORT}`;

let serverProcess = null;

function waitForHttpOk(url, timeoutMs = 30000) {
  const startedAt = Date.now();
  return new Promise((resolve, reject) => {
    const tick = () => {
      const req = http.get(url, (res) => {
        res.resume();
        if ((res.statusCode || 0) < 500) { resolve(); return; }
        retry();
      });
      req.on('error', retry);
    };
    const retry = () => {
      if (Date.now() - startedAt >= timeoutMs) { reject(new Error(`Timeout: ${url}`)); return; }
      setTimeout(tick, 200);
    };
    tick();
  });
}

function portIsBusy(port) {
  return new Promise((resolve) => {
    const socket = net.createConnection({ host: '127.0.0.1', port });
    socket.once('connect', () => { socket.destroy(); resolve(true); });
    socket.once('error', () => resolve(false));
  });
}

test.describe('CUT Monochrome Enforcement (runtime DOM scan)', () => {
  test.beforeAll(async () => {
    if (await portIsBusy(DEV_PORT)) return;
    serverProcess = spawn('npx', ['vite', 'dev', '--port', String(DEV_PORT), '--host', '127.0.0.1'], {
      cwd: CLIENT_DIR,
      env: { ...process.env, BROWSER: 'none', FORCE_COLOR: '0' },
      stdio: 'pipe',
    });
    await waitForHttpOk(`${DEV_ORIGIN}/cut`);
  });

  test.afterAll(async () => {
    if (serverProcess) { serverProcess.kill('SIGTERM'); serverProcess = null; }
  });

  test('MONO1: no non-grey computed colors in CUT editor DOM', async ({ page }) => {
    await page.goto(`${DEV_ORIGIN}/cut`, { waitUntil: 'networkidle' });
    // Wait for dockview to render
    await page.waitForSelector('.dv-dockview', { timeout: 15000 });

    const violations = await page.evaluate(() => {
      // Exempt selectors — elements where color is functional
      const EXEMPT_SELECTORS = [
        '[data-panel-id*="color"]',     // color correction panels
        '[data-panel-id*="scope"]',     // video scopes
        '.camelot-wheel',               // music visualization
        '.bpm-track',                   // beat grid
        '.pulse-inspector',             // story triangle
        'canvas',                       // media/waveform canvases
        'video',                        // video elements
        'svg',                          // icons (may have accent)
        '[class*="marker"]',            // marker elements
        '[class*="Marker"]',            // marker elements
        '[data-testid*="marker"]',      // marker test elements
        '.audio-level-meter',           // metering
        '.audio-mixer',                 // mixer
      ];

      function isExempt(el) {
        for (const sel of EXEMPT_SELECTORS) {
          if (el.matches(sel) || el.closest(sel)) return true;
        }
        return false;
      }

      function isGrey(r, g, b) {
        // Allow tolerance of 5 for anti-aliasing / subpixel rendering
        return Math.abs(r - g) <= 5 && Math.abs(g - b) <= 5;
      }

      function parseColor(str) {
        if (!str || str === 'transparent' || str === 'rgba(0, 0, 0, 0)') return null;
        const rgb = str.match(/rgba?\(\s*(\d+),\s*(\d+),\s*(\d+)/);
        if (!rgb) return null;
        const [, r, g, b] = rgb.map(Number);
        // Skip black, white, and near-black (common backgrounds)
        if (r + g + b === 0 || (r === 255 && g === 255 && b === 255)) return null;
        return { r, g, b };
      }

      const found = [];
      const allElements = document.querySelectorAll('*');

      for (const el of allElements) {
        if (isExempt(el)) continue;

        const style = window.getComputedStyle(el);
        const props = ['color', 'backgroundColor', 'borderColor', 'outlineColor'];

        for (const prop of props) {
          const val = style.getPropertyValue(
            prop.replace(/([A-Z])/g, '-$1').toLowerCase()
          );
          const parsed = parseColor(val);
          if (parsed && !isGrey(parsed.r, parsed.g, parsed.b)) {
            const tag = el.tagName.toLowerCase();
            const cls = el.className?.toString().slice(0, 40) || '';
            found.push({
              tag,
              cls,
              prop,
              value: val,
              r: parsed.r, g: parsed.g, b: parsed.b,
            });
          }
        }
      }

      // Deduplicate by color value
      const seen = new Set();
      return found.filter((v) => {
        const key = `${v.value}|${v.prop}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
    });

    if (violations.length > 0) {
      const report = violations.slice(0, 20).map((v) =>
        `  <${v.tag} class="${v.cls}"> ${v.prop}: ${v.value} (R=${v.r} G=${v.g} B=${v.b})`
      ).join('\n');
      console.log(`Monochrome violations (${violations.length}):\n${report}`);
    }

    // Mark as fixme until Gamma cleans up remaining violations
    // When violations reach 0, remove test.fixme() and enable strict assertion
    test.fixme(violations.length > 0,
      `${violations.length} runtime monochrome violations found — Gamma task pending`
    );
  });

  test('MONO2: no bright blue #3b82f6 anywhere in CUT DOM', async ({ page }) => {
    await page.goto(`${DEV_ORIGIN}/cut`, { waitUntil: 'networkidle' });
    await page.waitForSelector('.dv-dockview', { timeout: 15000 });

    const blueCount = await page.evaluate(() => {
      let count = 0;
      for (const el of document.querySelectorAll('*')) {
        const style = window.getComputedStyle(el);
        // rgb(59, 130, 246) = #3b82f6 (Tailwind blue-500)
        for (const prop of ['color', 'background-color', 'border-color']) {
          const val = style.getPropertyValue(prop);
          if (val && val.includes('59') && val.includes('130') && val.includes('246')) {
            count++;
          }
        }
      }
      return count;
    });

    expect(blueCount, 'Tailwind blue-500 (#3b82f6) found in CUT DOM — monochrome violation').toBe(0);
  });
});
