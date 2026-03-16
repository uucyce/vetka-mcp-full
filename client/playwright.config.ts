/**
 * MARKER_186.1: Playwright config for VETKA CUT client e2e tests.
 *
 * Tests self-manage their dev servers (each spec spawns vite on its own port),
 * so we do NOT configure webServer here.
 *
 * Usage:
 *   cd client && npx playwright test                     # all 24 specs
 *   cd client && npx playwright test e2e/cut_playback*   # single spec
 *   cd client && npx playwright test --workers=1         # sequential (less port contention)
 */
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.spec.{ts,cjs,js}",
  timeout: 60_000,
  retries: 1,
  workers: 3,
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/e2e-report.json" }],
  ],
  use: {
    headless: true,
    viewport: { width: 1440, height: 900 },
    screenshot: "only-on-failure",
    trace: "on-first-retry",
  },
});
