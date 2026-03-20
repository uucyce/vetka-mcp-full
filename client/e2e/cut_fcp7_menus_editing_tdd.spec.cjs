/**
 * MARKER_QA.FCP7_MENUS: TDD E2E tests for FCP7 menu + editing compliance.
 *
 * Covers gaps found in FCP7 Ch.31-40 audit:
 *   SEQ1-4: Sequence menu items (Lift, Extract, Close Gap, Extend Edit)
 *   MARK1-3: Mark menu items (Mark Clip X, Markers navigation, Play In-to-Out)
 *   CLIP1-2: Clip menu items (Insert/Overwrite enabled, Link/Unlink)
 *   EDIT1-2: Clipboard ops (Cut/Copy/Paste functional)
 *   DND1: Drag-to-Timeline insert/overwrite zones
 *
 * Reference tasks:
 *   tb_1773995686_12 (Sequence menu)
 *   tb_1773995698_13 (Mark menu)
 *   tb_1773995706_14 (Clip menu)
 *   tb_1773995715_15 (drag-to-timeline)
 *   tb_1773995730_17 (clipboard)
 */
const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_MENUS_PORT || 3009);
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
  const capture = (chunk) => { serverLogs += chunk.toString(); if (serverLogs.length > 20000) serverLogs = serverLogs.slice(-20000); };
  serverProcess.stdout.on('data', capture);
  serverProcess.stderr.on('data', capture);
  await waitForHttpOk(DEV_ORIGIN, 30000);
}

function cleanupServer() {
  if (serverProcess && serverStartedBySpec) { serverProcess.kill('SIGTERM'); serverProcess = null; }
}

function createProjectState() {
  return {
    success: true,
    schema_version: 'cut_project_state_v1',
    project: { project_id: 'cut-menu-tdd', display_name: 'Menu TDD', source_path: '/tmp/cut/menu.mov', sandbox_root: '/tmp/cut-menu', state: 'ready' },
    runtime_ready: true, graph_ready: true, waveform_ready: true, transcript_ready: false, thumbnail_ready: true,
    slice_ready: true, timecode_sync_ready: false, sync_surface_ready: false, meta_sync_ready: false, time_markers_ready: false,
    timeline_state: {
      timeline_id: 'main', selection: { clip_ids: [], scene_ids: [] },
      lanes: [
        { lane_id: 'V1', lane_type: 'video_main', clips: [
          { clip_id: 'v1', scene_id: 's1', start_sec: 0, duration_sec: 4, source_path: '/tmp/a.mov' },
          { clip_id: 'v2', scene_id: 's2', start_sec: 5, duration_sec: 3, source_path: '/tmp/b.mov' },
          { clip_id: 'v3', scene_id: 's3', start_sec: 9, duration_sec: 5, source_path: '/tmp/c.mov' },
        ]},
        { lane_id: 'A1', lane_type: 'audio_main', clips: [
          { clip_id: 'a1', scene_id: 's1', start_sec: 0, duration_sec: 4, source_path: '/tmp/a.wav' },
          { clip_id: 'a2', scene_id: 's2', start_sec: 5, duration_sec: 3, source_path: '/tmp/b.wav' },
        ]},
      ],
    },
    waveform_bundle: { items: [] }, thumbnail_bundle: { items: [] },
    sync_surface: { items: [] }, time_marker_bundle: { items: [] },
    recent_jobs: [], active_jobs: [],
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
  await page.waitForSelector('[data-testid="cut-timeline-track-view"]', { timeout: 15000 });
}

// Helper: open menu, check for item, close
async function menuContains(page, menuName, itemText) {
  await page.click(`button:text-is("${menuName}")`);
  await page.waitForTimeout(200);
  const found = await page.locator(`text=${itemText}`).first().isVisible().catch(() => false);
  await page.keyboard.press('Escape');
  return found;
}

// ===========================================================================
// SEQUENCE MENU
// ===========================================================================
test.describe.serial('FCP7 Menus: Sequence (TDD)', () => {
  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // FCP7: Sequence > Lift (;) — remove In-to-Out, leave gap
  test('SEQ1: Sequence menu contains Lift (;)', async ({ page }) => {
    await navigateToCut(page);
    const found = await menuContains(page, 'Sequence', 'Lift');
    expect(found).toBe(true);
  });

  // FCP7: Sequence > Extract (') — remove In-to-Out, close gap
  test('SEQ2: Sequence menu contains Extract (\')', async ({ page }) => {
    await navigateToCut(page);
    const found = await menuContains(page, 'Sequence', 'Extract');
    expect(found).toBe(true);
  });

  // FCP7: Sequence > Close Gap
  test('SEQ3: Sequence menu contains Close Gap', async ({ page }) => {
    await navigateToCut(page);
    const found = await menuContains(page, 'Sequence', 'Close Gap');
    expect(found).toBe(true);
  });

  // FCP7: Sequence > Extend Edit (E) — extend cut to playhead
  test('SEQ4: Sequence menu contains Extend Edit', async ({ page }) => {
    await navigateToCut(page);
    const found = await menuContains(page, 'Sequence', 'Extend Edit');
    expect(found).toBe(true);
  });

  // FCP7: Sequence > Add Video Transition (⌘T)
  test('SEQ5: Sequence menu contains Add Video Transition (⌘T)', async ({ page }) => {
    await navigateToCut(page);
    const found = await menuContains(page, 'Sequence', 'Video Transition');
    expect(found).toBe(true);
  });

  // FCP7: Sequence > Add Edit to All Tracks (⌘⇧K)
  test('SEQ6: Sequence menu contains Add Edit to All Tracks', async ({ page }) => {
    await navigateToCut(page);
    const found = await menuContains(page, 'Sequence', 'All Tracks');
    expect(found).toBe(true);
  });

  // Verify total item count >= 10 (currently 4)
  test('SEQ7: Sequence menu has 10+ items (not just 4)', async ({ page }) => {
    await navigateToCut(page);
    await page.click('button:text-is("Sequence")');
    await page.waitForTimeout(200);

    const itemCount = await page.evaluate(() => {
      // Count visible non-separator items in the open dropdown
      const items = document.querySelectorAll('div[style*="cursor: pointer"], div[style*="cursor: default"]');
      // Alternative: count direct children of dropdown
      const buttons = document.querySelectorAll('button');
      const seqBtn = Array.from(buttons).find(b => b.textContent === 'Sequence');
      if (!seqBtn) return 0;
      const dropdown = seqBtn.parentElement?.querySelector('div[style*="position: absolute"]');
      if (!dropdown) return 0;
      return dropdown.children.length;
    });

    await page.keyboard.press('Escape');
    expect(itemCount).toBeGreaterThanOrEqual(10);
  });
});

// ===========================================================================
// MARK MENU
// ===========================================================================
test.describe.serial('FCP7 Menus: Mark (TDD)', () => {
  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // FCP7: Mark > Mark Clip (X) — set In/Out to clip boundaries
  test('MARK1: Mark menu contains Mark Clip (X)', async ({ page }) => {
    await navigateToCut(page);
    const found = await menuContains(page, 'Mark', 'Mark Clip');
    expect(found).toBe(true);
  });

  // FCP7: Mark > Markers > Next (⇧M in Premiere / ⇧↓ in FCP7)
  test('MARK2: Mark menu contains Go to Next Marker', async ({ page }) => {
    await navigateToCut(page);
    await page.click('button:text-is("Mark")');
    await page.waitForTimeout(200);
    const hasNext = await page.locator('text=/Next Marker|Go to Next/').first().isVisible().catch(() => false);
    await page.keyboard.press('Escape');
    expect(hasNext).toBe(true);
  });

  // FCP7: Mark > Markers > Previous
  test('MARK3: Mark menu contains Go to Previous Marker', async ({ page }) => {
    await navigateToCut(page);
    await page.click('button:text-is("Mark")');
    await page.waitForTimeout(200);
    const hasPrev = await page.locator('text=/Previous Marker|Go to Prev/').first().isVisible().catch(() => false);
    await page.keyboard.press('Escape');
    expect(hasPrev).toBe(true);
  });

  // Add Marker should be ENABLED (currently disabled)
  test('MARK4: Add Marker (M) is enabled, not disabled', async ({ page }) => {
    await navigateToCut(page);
    await page.click('button:text-is("Mark")');
    await page.waitForTimeout(200);

    const isDisabled = await page.evaluate(() => {
      const items = document.querySelectorAll('div');
      for (const item of items) {
        if (item.textContent?.includes('Add Marker') && !item.textContent?.includes('Next') && !item.textContent?.includes('Prev')) {
          const style = window.getComputedStyle(item);
          // Disabled items typically have opacity < 1 or color #555/#666
          return style.opacity < '0.6' || style.color === 'rgb(85, 85, 85)' || style.color === 'rgb(102, 102, 102)';
        }
      }
      return true; // not found = effectively disabled
    });

    await page.keyboard.press('Escape');
    expect(isDisabled).toBe(false);
  });
});

// ===========================================================================
// CLIP MENU
// ===========================================================================
test.describe.serial('FCP7 Menus: Clip (TDD)', () => {
  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // Insert (,) should be ENABLED
  test('CLIP1: Clip > Insert (,) is enabled', async ({ page }) => {
    await navigateToCut(page);
    await page.click('button:text-is("Clip")');
    await page.waitForTimeout(200);

    const isEnabled = await page.evaluate(() => {
      const items = document.querySelectorAll('div');
      for (const item of items) {
        if (item.textContent?.trim().startsWith('Insert') && item.textContent?.includes(',')) {
          const style = window.getComputedStyle(item);
          return style.opacity >= '0.8' && style.pointerEvents !== 'none';
        }
      }
      return false;
    });

    await page.keyboard.press('Escape');
    expect(isEnabled).toBe(true);
  });

  // Make Subclip (⌘U) — FCP7 Ch.31
  test('CLIP2: Clip menu contains Make Subclip', async ({ page }) => {
    await navigateToCut(page);
    const found = await menuContains(page, 'Clip', 'Subclip');
    expect(found).toBe(true);
  });

  // Scale to Sequence — FCP7 Modify menu
  test('CLIP3: Clip menu contains Scale to Sequence', async ({ page }) => {
    await navigateToCut(page);
    const found = await menuContains(page, 'Clip', 'Scale to Sequence');
    expect(found).toBe(true);
  });
});

// ===========================================================================
// EDIT MENU — Clipboard
// ===========================================================================
test.describe.serial('FCP7 Menus: Edit Clipboard (TDD)', () => {
  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // Cut/Copy/Paste should be ENABLED (currently disabled)
  test('EDIT1: Edit > Cut (⌘X) is enabled', async ({ page }) => {
    await navigateToCut(page);

    // Select a clip first
    const clip = page.locator('[data-testid^="cut-timeline-clip-"]').first();
    await clip.click();
    await page.waitForTimeout(200);

    await page.click('button:text-is("Edit")');
    await page.waitForTimeout(200);

    const isEnabled = await page.evaluate(() => {
      const items = document.querySelectorAll('div');
      for (const item of items) {
        const text = item.textContent?.trim() || '';
        if (text === 'Cut⌘X' || (text.startsWith('Cut') && text.includes('⌘X'))) {
          const style = window.getComputedStyle(item);
          return style.opacity >= '0.8' && style.pointerEvents !== 'none';
        }
      }
      return false;
    });

    await page.keyboard.press('Escape');
    expect(isEnabled).toBe(true);
  });

  // Find (⌘F) should exist
  test('EDIT2: Edit menu contains Find (⌘F)', async ({ page }) => {
    await navigateToCut(page);
    const found = await menuContains(page, 'Edit', 'Find');
    expect(found).toBe(true);
  });

  // Paste Attributes (⌥V) — FCP7 Modify
  test('EDIT3: Edit menu contains Paste Attributes', async ({ page }) => {
    await navigateToCut(page);
    const found = await menuContains(page, 'Edit', 'Paste Attributes');
    expect(found).toBe(true);
  });
});

// ===========================================================================
// DRAG-TO-TIMELINE — Insert/Overwrite zones
// ===========================================================================
test.describe('FCP7: Drag-to-Timeline Zones (TDD)', () => {
  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // FCP7 Ch.35 p.517: Track split into insert zone (upper 1/3) and overwrite zone (lower 2/3)
  test('DND1: timeline tracks have insert/overwrite drop zones', async ({ page }) => {
    await navigateToCut(page);

    // This tests that the track visually or functionally splits during drag
    // We can't fully test drag behavior without source, but we can check for
    // zone indicators or cursor changes
    const hasZoneSupport = await page.evaluate(() => {
      const lanes = document.querySelectorAll('[data-testid^="cut-timeline-lane-"]');
      for (const lane of lanes) {
        // Check for data attributes indicating zones
        if (lane.querySelector('[data-drop-zone="insert"]') || lane.querySelector('[data-drop-zone="overwrite"]')) {
          return true;
        }
        // Check for zone divider elements
        if (lane.querySelector('[class*="insert-zone"], [class*="overwrite-zone"], [data-testid*="drop-zone"]')) {
          return true;
        }
      }
      return false;
    });

    expect(hasZoneSupport).toBe(true);
  });
});

// ===========================================================================
// FILE MENU
// ===========================================================================
test.describe.serial('FCP7 Menus: File (TDD)', () => {
  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  test('FILE1: File menu contains New Sequence (⌘N)', async ({ page }) => {
    await navigateToCut(page);
    const found = await menuContains(page, 'File', 'New Sequence');
    expect(found).toBe(true);
  });

  test('FILE2: File menu contains Close (⌘W)', async ({ page }) => {
    await navigateToCut(page);
    const found = await menuContains(page, 'File', 'Close');
    expect(found).toBe(true);
  });

  test('FILE3: File menu contains Revert', async ({ page }) => {
    await navigateToCut(page);
    const found = await menuContains(page, 'File', 'Revert');
    expect(found).toBe(true);
  });
});
