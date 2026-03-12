import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:1434",
    headless: true,
  },
  webServer: {
    command: "npm run dev -- --host 127.0.0.1",
    port: 1434,
    reuseExistingServer: true,
    cwd: "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground"
  },
});
