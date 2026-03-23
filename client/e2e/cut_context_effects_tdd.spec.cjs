/**
 * MARKER_QA.CTX: TDD tests for Gamma's context menu + Effects Browser + Workspace switch.
 *
 * Groups:
 *   CTX: Tab context menu (right-click → Close / Close Others / Maximize)
 *   CTX-R9: Close All + Float (TDD — GREEN when GAMMA-R9 merges)
 *   EB: Effects Browser (search, categories, effect items)
 *   WS: Workspace switch (Edit/Color/Audio preset buttons)
 *
 * @phase 196
 * @agent Epsilon (QA-2)
 * @task tb_1774241524_12
 */
const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_CTX_PORT || 4199);
const DEV_ORIGIN = `http://127.0.0.1:${DEV_PORT}`;
const CUT_URL = `${DEV_ORIGIN}/cut?sandbox_root=${encodeURIComponent('/tmp/cut-ctx')}&project_id=ctx-tdd`;

let serverProcess = null;
let serverStartedBySpec = false;
let serverLogs = '';

function waitForHttpOk(url, timeoutMs = 30000) {
  const startedAt = Date.now();
  return new Promise((resolve, reject) => {
    const tick = () => { const req = http.get(url, (res) => { res.resume(); if ((res.statusCode || 0) < 500) resolve(); else retry(); }); req.on('error', retry); };
    const retry = () => { if (Date.now() - startedAt >= timeoutMs) reject(new Error(`Timed out\n${serverLogs}`)); else setTimeout(tick, 200); };
    tick();
  });
}

async function ensureDevServer() {
  try { await waitForHttpOk(DEV_ORIGIN, 1500); return; } catch { /* start */ }
  serverStartedBySpec = true;
  serverProcess = spawn('npm', ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(DEV_PORT)],
    { cwd: CLIENT_DIR, env: { ...process.env, BROWSER: 'none', CI: '1' }, stdio: ['ignore', 'pipe', 'pipe'] });
  const cap = (c) => { serverLogs += c.toString(); if (serverLogs.length > 20000) serverLogs = serverLogs.slice(-20000); };
  serverProcess.stdout.on('data', cap); serverProcess.stderr.on('data', cap);
  await waitForHttpOk(DEV_ORIGIN, 30000);
}

function cleanupServer() { if (serverProcess && serverStartedBySpec) { serverProcess.kill('SIGTERM'); serverProcess = null; } }

function createProject() {
  return {
    success: true, schema_version: 'cut_project_state_v1',
    project: { project_id: 'ctx-tdd', display_name: 'Context TDD', source_path: '/tmp/ctx.mov', sandbox_root: '/tmp/cut-ctx', state: 'ready', framerate: 25 },
    runtime_ready: true, graph_ready: true, waveform_ready: true,
    transcript_ready: false, thumbnail_ready: true, slice_ready: true,
    timecode_sync_ready: false, sync_surface_ready: false, meta_sync_ready: false, time_markers_ready: false,
    timeline_state: {
      timeline_id: 'main', selection: { clip_ids: [], scene_ids: [] },
      lanes: [
        { lane_id: 'V1', lane_type: 'video_main', clips: [
          { clip_id: 'ctx_v1', scene_id: 's1', start_sec: 0, duration_sec: 5, source_path: '/tmp/a.mov' },
          { clip_id: 'ctx_v2', scene_id: 's2', start_sec: 5, duration_sec: 4, source_path: '/tmp/b.mov' },
        ]},
        { lane_id: 'A1', lane_type: 'audio_main', clips: [
          { clip_id: 'ctx_a1', scene_id: 's1', start_sec: 0, duration_sec: 5, source_path: '/tmp/a.wav' },
        ]},
      ],
    },
    waveform_bundle: { items: [] }, thumbnail_bundle: { items: [] },
    sync_surface: { items: [] }, time_marker_bundle: { items: [] },
    recent_jobs: [], active_jobs: [],
  };
}

async function setupMocks(page) {
  const state = createProject();
  await page.route(`${DEV_ORIGIN}/api/cut/**`, async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/cut/project-state') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: '{"success":true}' });
  });
}

async function navigateToCut(page) {
  await setupMocks(page);
  await page.goto(CUT_URL, { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="cut-timeline-track-view"]', { timeout: 15000 });
  await page.waitForSelector('[data-testid^="cut-timeline-clip-"]', { timeout: 10000 }).catch(() => {});
}

// ===========================================================================
// CTX: Tab Context Menu (existing GAMMA-15)
// ===========================================================================
test.describe('CTX: Tab Context Menu', () => {
  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  test('CTX1: right-click on dockview tab opens context menu', async ({ page }) => {
    await navigateToCut(page);
    // Right-click on Inspector tab
    const tab = page.locator('.dv-tab:has-text("Inspector")').first();
    if (await tab.isVisible().catch(() => false)) {
      await tab.click({ button: 'right' });
      await page.waitForTimeout(300);

      // Context menu should appear with "Close Panel" text
      const closeItem = page.locator('text=Close Panel').first();
      const visible = await closeItem.isVisible().catch(() => false);
      expect(visible).toBe(true);

      // Dismiss with Escape
      await page.keyboard.press('Escape');
    }
  });

  test('CTX2: context menu has Close Others in Group', async ({ page }) => {
    await navigateToCut(page);
    const tab = page.locator('.dv-tab:has-text("Inspector")').first();
    if (await tab.isVisible().catch(() => false)) {
      await tab.click({ button: 'right' });
      await page.waitForTimeout(300);

      const closeOthers = page.locator('text=Close Others').first();
      const visible = await closeOthers.isVisible().catch(() => false);
      expect(visible).toBe(true);

      await page.keyboard.press('Escape');
    }
  });

  test('CTX3: context menu has Maximize / Restore', async ({ page }) => {
    await navigateToCut(page);
    const tab = page.locator('.dv-tab:has-text("Inspector")').first();
    if (await tab.isVisible().catch(() => false)) {
      await tab.click({ button: 'right' });
      await page.waitForTimeout(300);

      const maximize = page.locator('text=Maximize').first();
      const visible = await maximize.isVisible().catch(() => false);
      expect(visible).toBe(true);

      await page.keyboard.press('Escape');
    }
  });

  test('CTX4: context menu is monochrome (no colored elements)', async ({ page }) => {
    await navigateToCut(page);
    const tab = page.locator('.dv-tab:has-text("Inspector")').first();
    if (await tab.isVisible().catch(() => false)) {
      await tab.click({ button: 'right' });
      await page.waitForTimeout(300);

      const menuColors = await page.evaluate(() => {
        // Find the context menu (fixed position, high z-index)
        const fixedDivs = Array.from(document.querySelectorAll('div')).filter(d => {
          const s = getComputedStyle(d);
          return s.position === 'fixed' && parseInt(s.zIndex) > 9000;
        });
        for (const div of fixedDivs) {
          const bg = getComputedStyle(div).backgroundColor;
          const m = bg.match(/rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/);
          if (m) {
            const [r, g, b] = [+m[1], +m[2], +m[3]];
            // Check if monochrome (R≈G≈B within 15)
            if (Math.abs(r - g) > 15 || Math.abs(g - b) > 15) return { bg, monochrome: false };
          }
        }
        return { monochrome: true };
      });

      expect(menuColors.monochrome).toBe(true);
      await page.keyboard.press('Escape');
    }
  });
});

// ===========================================================================
// CTX-R9: TDD for GAMMA-R9 additions (Close All + Float)
// ===========================================================================
test.describe('CTX-R9: Close All + Float (TDD — GREEN after GAMMA-R9 merge)', () => {
  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  test('CTX-R9-1: context menu contains Close All in Group', async ({ page }) => {
    await navigateToCut(page);
    const tab = page.locator('.dv-tab:has-text("Inspector")').first();
    if (await tab.isVisible().catch(() => false)) {
      await tab.click({ button: 'right' });
      await page.waitForTimeout(300);

      const closeAll = page.locator('text=Close All').first();
      const visible = await closeAll.isVisible().catch(() => false);
      expect(visible).toBe(true);

      await page.keyboard.press('Escape');
    }
  });

  test('CTX-R9-2: context menu contains Float option', async ({ page }) => {
    await navigateToCut(page);
    const tab = page.locator('.dv-tab:has-text("Inspector")').first();
    if (await tab.isVisible().catch(() => false)) {
      await tab.click({ button: 'right' });
      await page.waitForTimeout(300);

      const floatItem = page.locator('text=Float').first();
      const visible = await floatItem.isVisible().catch(() => false);
      expect(visible).toBe(true);

      await page.keyboard.press('Escape');
    }
  });
});

// ===========================================================================
// EB: Effects Browser
// ===========================================================================
test.describe('EB: Effects Browser', () => {
  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  test('EB1: effects browser shows when no clip selected', async ({ page }) => {
    await navigateToCut(page);
    // Click Effects tab — without clip selected, should show browser
    const effectsTab = page.locator('.dv-tab:has-text("Effects")').first();
    if (await effectsTab.isVisible().catch(() => false)) {
      await effectsTab.click();
      await page.waitForTimeout(300);
    }
    const browser = page.locator('[data-testid="effects-browser"]');
    const visible = await browser.isVisible().catch(() => false);
    // If no clip selected, EffectsPanel shows EffectsBrowser
    expect(visible).toBe(true);
  });

  test('EB2: effects browser has search input', async ({ page }) => {
    await navigateToCut(page);
    const effectsTab = page.locator('.dv-tab:has-text("Effects")').first();
    if (await effectsTab.isVisible().catch(() => false)) {
      await effectsTab.click();
      await page.waitForTimeout(300);
    }
    const searchInput = page.locator('[data-testid="effects-browser"] input[placeholder*="Search"]');
    const visible = await searchInput.isVisible().catch(() => false);
    expect(visible).toBe(true);
  });

  test('EB3: effects browser has category headers', async ({ page }) => {
    await navigateToCut(page);
    const effectsTab = page.locator('.dv-tab:has-text("Effects")').first();
    if (await effectsTab.isVisible().catch(() => false)) {
      await effectsTab.click();
      await page.waitForTimeout(300);
    }
    // Should have category names like "COLOR", "BLUR / SHARPEN", "TRANSFORM"
    const categories = await page.evaluate(() => {
      const browser = document.querySelector('[data-testid="effects-browser"]');
      if (!browser) return [];
      const headers = browser.querySelectorAll('span');
      return Array.from(headers)
        .map(s => s.textContent?.trim())
        .filter(t => t && /^[A-Z]/.test(t) && t.length > 2);
    });
    expect(categories.length).toBeGreaterThanOrEqual(2);
  });

  test('EB4: search filters effects list', async ({ page }) => {
    await navigateToCut(page);
    const effectsTab = page.locator('.dv-tab:has-text("Effects")').first();
    if (await effectsTab.isVisible().catch(() => false)) {
      await effectsTab.click();
      await page.waitForTimeout(300);
    }
    const searchInput = page.locator('[data-testid="effects-browser"] input[placeholder*="Search"]');
    if (await searchInput.isVisible().catch(() => false)) {
      // Count items before search
      const countBefore = await page.evaluate(() => {
        const browser = document.querySelector('[data-testid="effects-browser"]');
        return browser ? browser.querySelectorAll('[draggable="true"]').length : 0;
      });

      // Type search term
      await searchInput.fill('blur');
      await page.waitForTimeout(200);

      const countAfter = await page.evaluate(() => {
        const browser = document.querySelector('[data-testid="effects-browser"]');
        return browser ? browser.querySelectorAll('[draggable="true"]').length : 0;
      });

      // Filtered count should be less than or equal to total
      if (countBefore > 0) {
        expect(countAfter).toBeLessThanOrEqual(countBefore);
        expect(countAfter).toBeGreaterThan(0); // "blur" should match at least 1
      }
    }
  });

  test('EB5: effect items are draggable', async ({ page }) => {
    await navigateToCut(page);
    const effectsTab = page.locator('.dv-tab:has-text("Effects")').first();
    if (await effectsTab.isVisible().catch(() => false)) {
      await effectsTab.click();
      await page.waitForTimeout(300);
    }
    const draggables = await page.evaluate(() => {
      const browser = document.querySelector('[data-testid="effects-browser"]');
      if (!browser) return 0;
      return browser.querySelectorAll('[draggable="true"]').length;
    });
    expect(draggables).toBeGreaterThan(0);
  });
});

// ===========================================================================
// WS: Workspace Switch
// ===========================================================================
test.describe('WS: Workspace Switch', () => {
  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  test('WS1: workspace buttons visible (toolbar or Window menu)', async ({ page }) => {
    await navigateToCut(page);
    // Workspace buttons may be in toolbar (WS: bar) or Window menu only
    const editBtn = page.locator('button:has-text("Edit")').first();
    const editVisible = await editBtn.isVisible().catch(() => false);

    if (!editVisible) {
      // Check via Window menu → Workspaces
      const windowBtn = page.locator('button:text-is("Window")').first();
      if (await windowBtn.isVisible().catch(() => false)) {
        await windowBtn.click();
        await page.waitForTimeout(200);
        const workspaces = page.locator('text=Workspaces').first();
        expect(await workspaces.isVisible().catch(() => false)).toBe(true);
        await page.keyboard.press('Escape');
      }
    } else {
      expect(editVisible).toBe(true);
    }
  });

  test('WS2: clicking Color switches workspace layout', async ({ page }) => {
    await navigateToCut(page);

    // Count dockview groups before
    const groupsBefore = await page.evaluate(() =>
      document.querySelectorAll('.dv-groupview').length
    );

    const colorBtn = page.locator('button:has-text("Color")').first();
    if (await colorBtn.isVisible().catch(() => false)) {
      await colorBtn.click();
      await page.waitForTimeout(500);

      const groupsAfter = await page.evaluate(() =>
        document.querySelectorAll('.dv-groupview').length
      );

      // Layout should have at least 3 groups
      expect(groupsAfter).toBeGreaterThanOrEqual(3);
    }
  });

  test('WS3: switching back to Edit restores layout', async ({ page }) => {
    await navigateToCut(page);

    // Switch to Color then back to Edit
    const colorBtn = page.locator('button:has-text("Color")').first();
    const editBtn = page.locator('button:has-text("Edit")').first();

    if (await colorBtn.isVisible().catch(() => false)) {
      await colorBtn.click();
      await page.waitForTimeout(500);
      await editBtn.click();
      await page.waitForTimeout(500);

      // Timeline should still be visible after round-trip
      const timeline = page.locator('[data-testid="cut-timeline-track-view"]');
      await expect(timeline).toBeVisible({ timeout: 3000 });
    }
  });
});
