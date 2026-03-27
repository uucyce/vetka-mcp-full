/**
 * MARKER_QA.DEBRIEF_AUDIT: Post-merge health checks for the /cut page.
 *
 * Automated debrief audit — runs after every merge to catch regressions
 * introduced by any agent before they propagate further:
 *   DA1: Zero uncaught page errors (dead imports, module crashes)
 *   DA2: Zero console.error calls (runtime warnings, missing resources)
 *   DA3: Monochrome compliance — no non-grey computed colors on visible UI
 *   DA4: No empty src attributes on media elements
 *
 * @phase 198
 * @agent epsilon
 * @verifies post-merge health (debrief audit)
 */
const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

// ---------------------------------------------------------------------------
// Server bootstrap
// ---------------------------------------------------------------------------
const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_DEBRIEF_AUDIT_PORT || 4196);
const DEV_ORIGIN = `http://127.0.0.1:${DEV_PORT}`;
const CUT_URL = `${DEV_ORIGIN}/cut`;

let serverProcess = null;
let serverStartedBySpec = false;
let serverLogs = '';

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
      if (Date.now() - startedAt >= timeoutMs) {
        reject(new Error(`Timed out waiting for ${url}\n${serverLogs}`));
        return;
      }
      setTimeout(tick, 200);
    };
    tick();
  });
}

async function ensureDevServer() {
  try { await waitForHttpOk(DEV_ORIGIN, 1500); return; } catch { /* start below */ }
  serverStartedBySpec = true;
  serverProcess = spawn(
    'npm', ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(DEV_PORT)],
    { cwd: CLIENT_DIR, env: { ...process.env, BROWSER: 'none', CI: '1' }, stdio: ['ignore', 'pipe', 'pipe'] }
  );
  const capture = (chunk) => {
    serverLogs += chunk.toString();
    if (serverLogs.length > 20000) serverLogs = serverLogs.slice(-20000);
  };
  serverProcess.stdout.on('data', capture);
  serverProcess.stderr.on('data', capture);
  await waitForHttpOk(DEV_ORIGIN, 30000);
}

function cleanupServer() {
  if (serverProcess && serverStartedBySpec) { serverProcess.kill('SIGTERM'); serverProcess = null; }
}

// ---------------------------------------------------------------------------
// Fixture
// ---------------------------------------------------------------------------
function createProjectState() {
  return {
    success: true,
    schema_version: 'cut_project_state_v1',
    project: {
      project_id: 'cut-debrief-audit',
      display_name: 'CUT Debrief Audit',
      source_path: '/tmp/cut/audit-source.mov',
      sandbox_root: '/tmp/cut-audit',
      state: 'ready',
    },
    runtime_ready: true,
    graph_ready: true,
    waveform_ready: true,
    transcript_ready: true,
    thumbnail_ready: true,
    slice_ready: true,
    timecode_sync_ready: false,
    sync_surface_ready: true,
    meta_sync_ready: false,
    time_markers_ready: false,
  };
}

async function setupApiMocks(page) {
  const state = createProjectState();
  await page.route(`${DEV_ORIGIN}/api/cut/**`, async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/cut/project-state') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) });
  });
}

async function navigateToCut(page) {
  await setupApiMocks(page);
  await page.goto(CUT_URL, { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="cut-editor-layout"]', { timeout: 15000 });
}

// ===========================================================================
// Debrief Audit — post-merge health checks
// ===========================================================================
test.describe.serial('Debrief Audit — post-merge health checks', () => {

  test.setTimeout(30000);

  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // -------------------------------------------------------------------------
  // DA1: Zero uncaught page errors
  // -------------------------------------------------------------------------
  test('DA1: zero uncaught page errors on /cut load', async ({ page }) => {
    const pageErrors = [];
    page.on('pageerror', (err) => { pageErrors.push(err.message); });

    await navigateToCut(page);
    await page.waitForTimeout(2000);

    if (pageErrors.length > 0) {
      const report = pageErrors.map((msg, i) => `[${i + 1}] ${msg}`).join('\n');
      test.info().annotations.push({ type: 'warning', description: `Page errors:\n${report}` });
    }

    expect(pageErrors).toHaveLength(0);
  });

  // -------------------------------------------------------------------------
  // DA2: Zero console.error calls
  // -------------------------------------------------------------------------
  test('DA2: zero console.error calls on /cut load', async ({ page }) => {
    const consoleErrors = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await navigateToCut(page);
    await page.waitForTimeout(2000);

    const filtered = consoleErrors.filter((msg) => {
      if (msg.includes('favicon')) return false;
      if (msg.includes('net::ERR')) return false;
      return true;
    });

    if (filtered.length > 0) {
      const report = filtered.map((msg, i) => `[${i + 1}] ${msg}`).join('\n');
      test.info().annotations.push({ type: 'warning', description: `Console errors:\n${report}` });
    }

    expect(filtered).toHaveLength(0);
  });

  // -------------------------------------------------------------------------
  // DA3: Monochrome compliance — no non-grey computed colors on visible UI
  // -------------------------------------------------------------------------
  test('DA3: monochrome compliance — no non-grey computed colors on visible UI', async ({ page }) => {
    await navigateToCut(page);

    const violations = await page.evaluate(() => {
      const found = [];
      const TOLERANCE = 20; // slightly relaxed for anti-aliasing

      // Allowed non-grey contexts: elements inside [data-color-exempt],
      // video/canvas elements, elements with opacity 0
      const isExempt = (el) => {
        if (el.closest('[data-color-exempt]')) return true;
        if (['VIDEO', 'CANVAS', 'IMG'].includes(el.tagName)) return true;
        if (getComputedStyle(el).opacity === '0') return true;
        return false;
      };

      const allEls = document.querySelectorAll('*');
      for (const el of allEls) {
        if (isExempt(el)) continue;
        const style = getComputedStyle(el);
        // Check backgroundColor and color
        for (const prop of ['backgroundColor', 'color', 'borderColor']) {
          const val = style[prop];
          if (!val || val === 'transparent' || val === 'rgba(0, 0, 0, 0)') continue;
          const match = val.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
          if (!match) continue;
          const [, rs, gs, bs] = match;
          const r = Number(rs), g = Number(gs), b = Number(bs);
          // Skip near-black (all < 30) and near-white (all > 225)
          if (r < 30 && g < 30 && b < 30) continue;
          if (r > 225 && g > 225 && b > 225) continue;
          // Skip transparent-ish
          const alphaMatch = val.match(/rgba\(\d+,\s*\d+,\s*\d+,\s*([\d.]+)\)/);
          if (alphaMatch && Number(alphaMatch[1]) < 0.1) continue;
          // Check grey: max diff between channels
          const maxDiff = Math.max(Math.abs(r - g), Math.abs(r - b), Math.abs(g - b));
          if (maxDiff > TOLERANCE) {
            // Allow red (playhead/error: R dominant, low G/B)
            if (r >= 150 && g <= 100 && b <= 100) continue;
            found.push({
              tag: el.tagName,
              testid: el.getAttribute('data-testid') || '',
              className: (el.className || '').toString().slice(0, 60),
              prop,
              value: val,
              rgb: { r, g, b },
            });
            if (found.length >= 20) break; // cap report size
          }
        }
        if (found.length >= 20) break;
      }
      return found;
    });

    if (violations.length > 0) {
      const report = violations.map((v, i) =>
        `[${i + 1}] <${v.tag}> testid="${v.testid}" class="${v.className}" ${v.prop}=${v.value} rgb(${v.rgb.r},${v.rgb.g},${v.rgb.b})`
      ).join('\n');
      test.info().annotations.push({ type: 'warning', description: `Monochrome violations:\n${report}` });
    }

    expect(violations.length).toBe(0);
  });

  // -------------------------------------------------------------------------
  // DA4: No empty src attributes
  // -------------------------------------------------------------------------
  test('DA4: no empty src attributes on media elements', async ({ page }) => {
    await navigateToCut(page);

    const emptySrcs = await page.evaluate(() => {
      const results = [];
      for (const tag of ['img', 'video', 'audio', 'iframe', 'source']) {
        document.querySelectorAll(tag).forEach(el => {
          const src = el.getAttribute('src');
          if (src !== null && src.trim() === '') {
            results.push({ tag: el.tagName, testid: el.getAttribute('data-testid') || '', parent: el.parentElement?.tagName || '' });
          }
        });
      }
      return results;
    });

    if (emptySrcs.length > 0) {
      const report = emptySrcs.map((e, i) =>
        `[${i + 1}] <${e.tag}> testid="${e.testid}" parent=<${e.parent}>`
      ).join('\n');
      test.info().annotations.push({ type: 'warning', description: `Empty src attributes:\n${report}` });
    }

    expect(emptySrcs).toHaveLength(0);
  });

});
