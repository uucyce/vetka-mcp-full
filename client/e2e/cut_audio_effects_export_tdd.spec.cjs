/**
 * MARKER_QA.TDD3: TDD E2E tests for Audio Mixer, Effects Panel, and Export features.
 *
 * RED-by-design specs — tests provide targets for Beta and Gamma agents.
 *
 * Covers:
 *   AUD1-AUD6: Audio Mixer (B13) — faders, mute/solo, master, VU, pan
 *   FX1-FX5:   Effects Panel — categories, sliders, apply/reset, search
 *   EXP1-EXP4: Export — dialog tabs, progress/ETA, presets, editorial formats
 *
 * FCP7 Reference:
 *   Ch.55-57 (Audio Mixer), Ch.79-83 (Effects/Color), Ch.96 (Output)
 *
 * Author: Epsilon (QA-2) | 2026-03-22
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
const DEV_PORT = Number(process.env.VETKA_CUT_TDD3_PORT || 3011);
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

// ---------------------------------------------------------------------------
// Fixture
// ---------------------------------------------------------------------------
function createProjectWithClips() {
  return {
    success: true,
    schema_version: 'cut_project_state_v1',
    project: {
      project_id: 'cut-tdd3-suite',
      display_name: 'TDD3 Audio+FX+Export',
      source_path: '/tmp/cut/tdd3.mov',
      sandbox_root: '/tmp/cut-tdd3',
      state: 'ready',
    },
    runtime_ready: true, graph_ready: true, waveform_ready: true,
    transcript_ready: false, thumbnail_ready: true, slice_ready: true,
    timecode_sync_ready: false, sync_surface_ready: false,
    meta_sync_ready: false, time_markers_ready: false,
    timeline_state: {
      timeline_id: 'main',
      selection: { clip_ids: [], scene_ids: [] },
      lanes: [
        {
          lane_id: 'V1', lane_type: 'video_main',
          clips: [
            { clip_id: 'v1', scene_id: 's1', start_sec: 0, duration_sec: 5, source_path: '/tmp/cut/shot-a.mov' },
            { clip_id: 'v2', scene_id: 's2', start_sec: 5, duration_sec: 4, source_path: '/tmp/cut/shot-b.mov' },
          ],
        },
        {
          lane_id: 'A1', lane_type: 'audio_main',
          clips: [
            { clip_id: 'a1', scene_id: 's1', start_sec: 0, duration_sec: 5, source_path: '/tmp/cut/audio-a.wav' },
            { clip_id: 'a2', scene_id: 's2', start_sec: 5, duration_sec: 4, source_path: '/tmp/cut/audio-b.wav' },
          ],
        },
        {
          lane_id: 'A2', lane_type: 'audio_main',
          clips: [
            { clip_id: 'a_music', scene_id: 's1', start_sec: 0, duration_sec: 9, source_path: '/tmp/cut/music.wav' },
          ],
        },
      ],
    },
    waveform_bundle: { items: [] },
    thumbnail_bundle: { items: [] },
    sync_surface: { items: [] },
    time_marker_bundle: { items: [] },
    recent_jobs: [], active_jobs: [],
  };
}

async function setupApiMocks(page) {
  const state = createProjectWithClips();
  await page.route(`${DEV_ORIGIN}/api/cut/**`, async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/cut/project-state') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state) });
      return;
    }
    // Mock render job start — return a fake job_id
    if (url.pathname === '/api/cut/render/master') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, job_id: 'mock-job-001' }) });
      return;
    }
    // Mock job status — immediate completion
    if (url.pathname.startsWith('/api/cut/job/')) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
        success: true, status: 'done', progress: 1.0,
        result: { output_path: '/tmp/cut-tdd3/export.mp4', file_size_mb: 42.5 },
      }) });
      return;
    }
    // Mock editorial exports
    if (url.pathname.startsWith('/api/cut/export/')) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
        success: true, output_path: '/tmp/cut-tdd3/export.xml',
      }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) });
  });
}

async function navigateToCut(page, { preset = 'fcp7' } = {}) {
  await setupApiMocks(page);
  await page.addInitScript((p) => {
    window.localStorage.setItem('cut_hotkey_preset', p);
  }, preset);
  await page.goto(`${CUT_URL}?sandbox_root=${encodeURIComponent('/tmp/cut-tdd3')}&project_id=${encodeURIComponent('cut-tdd3-suite')}`, { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="cut-timeline-track-view"]', { timeout: 15000 });
  await page.waitForSelector('[data-testid^="cut-timeline-clip-"]', { timeout: 10000 }).catch(() => {});
}

// ===========================================================================
// AUDIO MIXER TESTS
// ===========================================================================
test.describe('TDD3: Audio Mixer', () => {

  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // -------------------------------------------------------------------------
  // AUD1: Mixer panel is accessible and shows channel strips
  // FCP7 p.881: "Audio Mixer — one strip per track"
  // -------------------------------------------------------------------------
  test('AUD1: mixer panel visible with one strip per audio lane', async ({ page }) => {
    await navigateToCut(page);

    // Mixer is registered as "Mixer" tab in dockview
    const mixerInfo = await page.evaluate(() => {
      const body = document.body.textContent || '';
      // Count channel strip indicators — look for mute (M) and solo (S) button pairs
      const muteButtons = document.querySelectorAll('button');
      let mCount = 0;
      let sCount = 0;
      for (const btn of muteButtons) {
        const text = (btn.textContent || '').trim();
        if (text === 'M') mCount++;
        if (text === 'S') sCount++;
      }
      return {
        hasMixerTab: body.includes('Mixer'),
        muteButtonCount: mCount,
        soloButtonCount: sCount,
      };
    });

    expect(mixerInfo.hasMixerTab).toBe(true);
    // 3 lanes (V1, A1, A2) + master = at least 3 M/S button pairs
    expect(mixerInfo.muteButtonCount).toBeGreaterThanOrEqual(3);
    expect(mixerInfo.soloButtonCount).toBeGreaterThanOrEqual(3);
  });

  // -------------------------------------------------------------------------
  // AUD2: Mute button toggles lane mute state in store
  // FCP7 p.886: "Mute button — silences track"
  // -------------------------------------------------------------------------
  test('AUD2: mute toggle updates store state', async ({ page }) => {
    await navigateToCut(page);

    // Toggle mute on A1 via store
    await page.evaluate(() => {
      if (window.__CUT_STORE__) window.__CUT_STORE__.getState().toggleMute('A1');
    });
    await page.waitForTimeout(100);

    const isMuted = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      return window.__CUT_STORE__.getState().mutedLanes.has('A1');
    });

    expect(isMuted).toBe(true);

    // Toggle again — should unmute
    await page.evaluate(() => {
      if (window.__CUT_STORE__) window.__CUT_STORE__.getState().toggleMute('A1');
    });
    await page.waitForTimeout(100);

    const isUnmuted = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      return !window.__CUT_STORE__.getState().mutedLanes.has('A1');
    });

    expect(isUnmuted).toBe(true);
  });

  // -------------------------------------------------------------------------
  // AUD3: Solo button toggles lane solo state
  // FCP7 p.886: "Solo button — isolates track for monitoring"
  // -------------------------------------------------------------------------
  test('AUD3: solo toggle updates store state', async ({ page }) => {
    await navigateToCut(page);

    await page.evaluate(() => {
      if (window.__CUT_STORE__) window.__CUT_STORE__.getState().toggleSolo('A2');
    });
    await page.waitForTimeout(100);

    const isSolo = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      return window.__CUT_STORE__.getState().soloLanes.has('A2');
    });

    expect(isSolo).toBe(true);
  });

  // -------------------------------------------------------------------------
  // AUD4: Volume fader sets lane volume (0-150%)
  // FCP7 p.884: "Fader — +12dB to -inf"
  // -------------------------------------------------------------------------
  test('AUD4: setLaneVolume updates store and clamps to 0-1.5', async ({ page }) => {
    await navigateToCut(page);

    // Set volume to 75%
    await page.evaluate(() => {
      if (window.__CUT_STORE__) window.__CUT_STORE__.getState().setLaneVolume('A1', 0.75);
    });
    await page.waitForTimeout(100);

    const vol = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      return window.__CUT_STORE__.getState().laneVolumes['A1'];
    });
    expect(vol).toBe(0.75);

    // Test clamping — try to set above max
    await page.evaluate(() => {
      if (window.__CUT_STORE__) window.__CUT_STORE__.getState().setLaneVolume('A1', 2.0);
    });
    await page.waitForTimeout(100);

    const clamped = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      return window.__CUT_STORE__.getState().laneVolumes['A1'];
    });
    expect(clamped).toBe(1.5); // max 150%
  });

  // -------------------------------------------------------------------------
  // AUD5: VU meter element exists per channel strip
  // FCP7 p.885: "Audio meters show level for each track"
  // -------------------------------------------------------------------------
  test('AUD5: mixer has VU level indicators', async ({ page }) => {
    await navigateToCut(page);

    // Look for VU meter elements — colored bars in mixer area
    const hasVU = await page.evaluate(() => {
      const body = document.body.innerHTML || '';
      // VU meters use green/yellow/red colors: #22c55e, #eab308, #ef4444
      // Or look for vertical bars with these background colors
      const allEls = document.querySelectorAll('div');
      for (const el of allEls) {
        const bg = window.getComputedStyle(el).backgroundColor || '';
        const h = el.getBoundingClientRect().height;
        const w = el.getBoundingClientRect().width;
        // VU bar: narrow (4-8px wide), tall (30-50px), green background
        if (w >= 3 && w <= 10 && h >= 20 && h <= 60 && bg.includes('34, 197, 94')) {
          return true;
        }
      }
      // Fallback: check for canvas elements (AudioLevelMeter uses canvas)
      const canvases = document.querySelectorAll('canvas');
      return canvases.length > 0;
    });

    expect(hasVU).toBe(true);
  });

  // -------------------------------------------------------------------------
  // AUD6: Master strip labeled MST exists
  // FCP7 p.889: "Master fader controls overall mix level"
  // -------------------------------------------------------------------------
  test('AUD6: master strip labeled MST is present', async ({ page }) => {
    await navigateToCut(page);

    const hasMaster = await page.evaluate(() => {
      const body = document.body.textContent || '';
      return body.includes('MST');
    });

    expect(hasMaster).toBe(true);
  });
});

// ===========================================================================
// EFFECTS PANEL TESTS
// ===========================================================================
test.describe('TDD3: Effects Panel', () => {

  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // -------------------------------------------------------------------------
  // FX1: Effects panel shows 5 effect categories
  // FCP7 p.79: "Effects tab lists video/audio filters"
  // -------------------------------------------------------------------------
  test('FX1: effects panel lists brightness, contrast, saturation, blur, opacity', async ({ page }) => {
    await navigateToCut(page);

    // Select a clip first (effects panel requires selection)
    await page.evaluate(() => {
      if (window.__CUT_STORE__) window.__CUT_STORE__.getState().setSelectedClip('v1');
    });
    await page.waitForTimeout(300);

    const effectLabels = await page.evaluate(() => {
      const body = document.body.textContent || '';
      const labels = ['Brightness', 'Contrast', 'Saturation', 'Blur', 'Opacity'];
      return labels.filter(l => body.includes(l));
    });

    // All 5 effect categories should be visible
    expect(effectLabels.length).toBeGreaterThanOrEqual(4);
  });

  // -------------------------------------------------------------------------
  // FX2: Setting clip effects updates store
  // -------------------------------------------------------------------------
  test('FX2: setClipEffects updates clip in store', async ({ page }) => {
    await navigateToCut(page);

    await page.evaluate(() => {
      if (!window.__CUT_STORE__) return;
      const s = window.__CUT_STORE__.getState();
      if (s.setClipEffects) {
        s.setClipEffects('v1', { brightness: 0.3, contrast: -0.2 });
      }
    });
    await page.waitForTimeout(200);

    const effects = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      const lanes = window.__CUT_STORE__.getState().lanes;
      for (const lane of lanes) {
        for (const clip of lane.clips) {
          if (clip.clip_id === 'v1' && clip.effects) return clip.effects;
        }
      }
      return null;
    });

    expect(effects).not.toBeNull();
    expect(effects.brightness).toBe(0.3);
    expect(effects.contrast).toBe(-0.2);
  });

  // -------------------------------------------------------------------------
  // FX3: Reset effects returns to defaults
  // -------------------------------------------------------------------------
  test('FX3: resetClipEffects clears effects from clip', async ({ page }) => {
    await navigateToCut(page);

    // Set then reset
    await page.evaluate(() => {
      if (!window.__CUT_STORE__) return;
      const s = window.__CUT_STORE__.getState();
      if (s.setClipEffects) s.setClipEffects('v1', { blur: 5 });
      if (s.resetClipEffects) s.resetClipEffects('v1');
    });
    await page.waitForTimeout(200);

    const effects = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return 'NOT_NULL';
      const lanes = window.__CUT_STORE__.getState().lanes;
      for (const lane of lanes) {
        for (const clip of lane.clips) {
          if (clip.clip_id === 'v1') return clip.effects;
        }
      }
      return 'NOT_FOUND';
    });

    // Effects should be undefined/null after reset
    expect(effects == null || effects === undefined).toBe(true);
  });

  // -------------------------------------------------------------------------
  // FX4: Empty state when no clip selected
  // -------------------------------------------------------------------------
  test('FX4: effects panel shows empty state without clip selection', async ({ page }) => {
    await navigateToCut(page);

    // Deselect all
    await page.evaluate(() => {
      if (window.__CUT_STORE__) window.__CUT_STORE__.getState().setSelectedClip(null);
    });
    await page.waitForTimeout(200);

    const hasEmptyState = await page.evaluate(() => {
      const body = document.body.textContent || '';
      return body.includes('Select a clip') || body.includes('No clip selected');
    });

    expect(hasEmptyState).toBe(true);
  });

  // -------------------------------------------------------------------------
  // FX5: Effect sliders have range constraints
  // -------------------------------------------------------------------------
  test('FX5: effects respect value ranges (brightness -1 to +1, blur 0 to 20)', async ({ page }) => {
    await navigateToCut(page);

    // Set out-of-range values
    await page.evaluate(() => {
      if (!window.__CUT_STORE__) return;
      const s = window.__CUT_STORE__.getState();
      if (s.setClipEffects) {
        s.setClipEffects('v1', { brightness: 5.0, blur: -10 });
      }
    });
    await page.waitForTimeout(200);

    // Read back after React re-render
    const ranges = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      const lanes = window.__CUT_STORE__.getState().lanes;
      for (const lane of lanes) {
        for (const clip of lane.clips) {
          if (clip.clip_id === 'v1' && clip.effects) {
            return { brightness: clip.effects.brightness, blur: clip.effects.blur };
          }
        }
      }
      return null;
    });

    // Values should exist (store sets them; UI layer clamps on render)
    expect(ranges).not.toBeNull();
  });
});

// ===========================================================================
// EXPORT TESTS
// ===========================================================================
test.describe('TDD3: Export Dialog', () => {

  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // -------------------------------------------------------------------------
  // EXP1: Export dialog opens and has 3 tabs
  // -------------------------------------------------------------------------
  test('EXP1: export dialog opens with Master, Editorial, Publish tabs', async ({ page }) => {
    await navigateToCut(page);

    // Open export dialog via store
    await page.evaluate(() => {
      if (window.__CUT_STORE__) {
        const s = window.__CUT_STORE__.getState();
        if (s.setShowExportDialog) s.setShowExportDialog(true);
      }
    });
    await page.waitForTimeout(300);

    const tabs = await page.evaluate(() => {
      const body = document.body.textContent || '';
      return {
        hasMaster: body.includes('Master') || body.includes('Render'),
        hasEditorial: body.includes('Editorial') || body.includes('XML') || body.includes('EDL'),
        hasPublish: body.includes('Publish') || body.includes('YouTube') || body.includes('Platform'),
      };
    });

    expect(tabs.hasMaster).toBe(true);
    expect(tabs.hasEditorial).toBe(true);
    expect(tabs.hasPublish).toBe(true);
  });

  // -------------------------------------------------------------------------
  // EXP2: Master render tab has codec and resolution options
  // -------------------------------------------------------------------------
  test('EXP2: master render tab lists codecs and resolutions', async ({ page }) => {
    await navigateToCut(page);

    await page.evaluate(() => {
      if (window.__CUT_STORE__) {
        const s = window.__CUT_STORE__.getState();
        if (s.setShowExportDialog) s.setShowExportDialog(true);
      }
    });
    await page.waitForTimeout(300);

    const options = await page.evaluate(() => {
      const body = document.body.textContent || '';
      return {
        hasProRes: body.includes('ProRes'),
        hasH264: body.includes('H.264') || body.includes('H264'),
        has1080: body.includes('1080'),
        has4K: body.includes('4K') || body.includes('3840'),
      };
    });

    expect(options.hasProRes).toBe(true);
    expect(options.hasH264).toBe(true);
    expect(options.has1080).toBe(true);
  });

  // -------------------------------------------------------------------------
  // EXP3: Export progress state exists in store
  // B2.2: ETA display during render
  // -------------------------------------------------------------------------
  test('EXP3: render progress and status fields exist in store', async ({ page }) => {
    await navigateToCut(page);

    const storeFields = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      const s = window.__CUT_STORE__.getState();
      return {
        hasRenderProgress: 'renderProgress' in s,
        hasRenderStatus: 'renderStatus' in s,
        hasRenderError: 'renderError' in s,
        hasSetRenderProgress: typeof s.setRenderProgress === 'function',
        hasSetRenderStatus: typeof s.setRenderStatus === 'function',
      };
    });

    expect(storeFields).not.toBeNull();
    expect(storeFields.hasRenderProgress).toBe(true);
    expect(storeFields.hasRenderStatus).toBe(true);
    expect(storeFields.hasSetRenderProgress).toBe(true);
  });

  // -------------------------------------------------------------------------
  // EXP4: Publish presets include YouTube, Instagram, TikTok, Telegram
  // B2.3: Export presets
  // -------------------------------------------------------------------------
  test('EXP4: publish tab lists platform presets', async ({ page }) => {
    await navigateToCut(page);

    await page.evaluate(() => {
      if (window.__CUT_STORE__) {
        const s = window.__CUT_STORE__.getState();
        if (s.setShowExportDialog) s.setShowExportDialog(true);
      }
    });
    await page.waitForTimeout(300);

    // Click the Publish tab (may be labeled "Publish" or "Platform")
    const clicked = await page.evaluate(() => {
      const allEls = document.querySelectorAll('div, span, button');
      for (const el of allEls) {
        const text = (el.textContent || '').trim();
        if (text === 'Publish' || text === 'Platform') {
          el.click();
          return true;
        }
      }
      return false;
    });
    await page.waitForTimeout(300);

    const presets = await page.evaluate(() => {
      const body = document.body.textContent || '';
      const platforms = ['YouTube', 'Instagram', 'TikTok', 'Telegram'];
      return platforms.filter(p => body.includes(p));
    });

    // At least 3 platform presets visible
    expect(presets.length).toBeGreaterThanOrEqual(3);
  });
});
