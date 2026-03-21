const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_DEBUG_INSPECTOR_PORT || 4182);
const DEV_ORIGIN = `http://127.0.0.1:${DEV_PORT}`;

let serverProcess = null;
let serverStartedBySpec = false;
let serverLogs = '';

function waitForHttpOk(url, timeoutMs = 30000) {
  const startedAt = Date.now();
  return new Promise((resolve, reject) => {
    const tick = () => {
      const req = http.get(url, (res) => {
        res.resume();
        if ((res.statusCode || 0) < 500) {
          resolve();
          return;
        }
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
  try {
    await waitForHttpOk(DEV_ORIGIN, 1500);
    return;
  } catch {
    // Start local server below.
  }

  serverStartedBySpec = true;
  serverProcess = spawn(
    'npm',
    ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(DEV_PORT)],
    {
      cwd: CLIENT_DIR,
      env: { ...process.env, BROWSER: 'none', CI: '1' },
      stdio: ['ignore', 'pipe', 'pipe'],
    }
  );

  const capture = (chunk) => {
    serverLogs += chunk.toString();
    if (serverLogs.length > 20000) {
      serverLogs = serverLogs.slice(-20000);
    }
  };
  serverProcess.stdout.on('data', capture);
  serverProcess.stderr.on('data', capture);

  await waitForHttpOk(DEV_ORIGIN, 30000);
}

function cleanupServer() {
  if (serverProcess && serverStartedBySpec) {
    serverProcess.kill('SIGTERM');
    serverProcess = null;
  }
}

function createProjectState(lastStats) {
  return {
    success: true,
    schema_version: 'cut_project_state_v1',
    project: {
      project_id: 'proj_inspector_smoke',
      display_name: 'CUT Inspector Smoke',
      source_path: '/tmp/cut/source.mov',
      sandbox_root: '/tmp/cut-smoke',
      state: 'ready',
    },
    bootstrap_state: { last_stats: lastStats },
    timeline_state: { timeline_id: 'main', selection: { clip_ids: [], scene_ids: [] }, lanes: [] },
    scene_graph: { nodes: [] },
    waveform_bundle: { items: [] },
    transcript_bundle: { items: [] },
    thumbnail_bundle: { items: [] },
    audio_sync_result: { items: [] },
    slice_bundle: { items: [] },
    timecode_sync_result: { items: [] },
    sync_surface: { schema_version: 'cut_sync_surface_v1', items: [] },
    time_marker_bundle: { items: [] },
    recent_jobs: [],
    active_jobs: [],
    runtime_ready: false,
    graph_ready: false,
    waveform_ready: false,
    transcript_ready: false,
    thumbnail_ready: false,
    audio_sync_ready: false,
    slice_ready: false,
    timecode_sync_ready: false,
    sync_surface_ready: false,
    meta_sync_ready: false,
    time_markers_ready: false,
  };
}

async function installInspectorQuestionMocks(page, requestLog) {
  const snapshots = [
    createProjectState({
      fallback_questions: ['Need language', 'Need pacing'],
      source_count: 2,
      mode: 'guided_bootstrap',
      missing_fields: ['language', 'duration_sec'],
    }),
    createProjectState({
      fallback_questions: ['Need audience'],
      source_count: 2,
      mode: 'guided_bootstrap',
      missing_fields: ['audience'],
      recovery_hint: 'ask one short clarifier',
    }),
  ];
  let projectStateIndex = 0;

  await page.route(`${DEV_ORIGIN}/api/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    requestLog.push({ method: request.method(), pathname: url.pathname });

    if (url.pathname === '/api/cut/project-state') {
      const payload = snapshots[Math.min(projectStateIndex, snapshots.length - 1)];
      projectStateIndex += 1;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(payload),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true }),
    });
  });
}

test.describe.serial('phase170 cut debug inspector/questions smoke', () => {
  test.setTimeout(90000);

  test.beforeAll(async ({}, testInfo) => {
    testInfo.setTimeout(90000);
    await ensureDevServer();
  });

  test.afterAll(async () => {
    cleanupServer();
  });

  test('renders bootstrap stats JSON and updates after refresh safely', async ({ page }) => {
    const pageErrors = [];
    const requestLog = [];
    await installInspectorQuestionMocks(page, requestLog);
    page.on('pageerror', (error) => pageErrors.push(String(error)));

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(
      `${DEV_ORIGIN}/cut?sandbox_root=${encodeURIComponent('/tmp/cut-smoke')}&project_id=${encodeURIComponent('proj_inspector_smoke')}`,
      { waitUntil: 'domcontentloaded' }
    );

    await expect(page.getByText('Project').first()).toBeVisible();
    await page.locator('button[title="Toggle NLE / Debug view"]').click();
    await expect(page.getByText('VETKA CUT')).toBeVisible();
    await expect(page.getByText('Inspector / Questions')).toBeVisible();
    await expect(page.getByText('Bootstrap stats')).toBeVisible();
    const inspectorPre = page.locator('pre').last();
    await expect(inspectorPre).toContainText('fallback_questions');
    await expect(inspectorPre).toContainText('guided_bootstrap');
    await expect(inspectorPre).toContainText('missing_fields');

    await page.getByRole('button', { name: 'Refresh Project State' }).click();
    await expect.poll(() => requestLog.filter((entry) => entry.pathname === '/api/cut/project-state').length).toBeGreaterThan(1);
    await expect(page.getByText('Project loaded')).toBeVisible();
    await expect(inspectorPre).toContainText('recovery_hint');
    await expect(inspectorPre).toContainText('ask one short clarifier');
    await expect(inspectorPre).toContainText('Need audience');

    await expect(page.locator('text=MCC Runtime Error')).toHaveCount(0);
    await expect(pageErrors).toEqual([]);
    expect(await page.evaluate(() => window.localStorage.getItem('vetka_last_runtime_error'))).toBeNull();
    expect(requestLog.filter((entry) => entry.pathname === '/api/cut/project-state').length).toBeGreaterThan(1);
  });
});
