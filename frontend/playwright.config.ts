import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  expect: { timeout: 5_000 },
  workers: 1,
  use: {
    baseURL: "http://localhost:3000",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: [
    {
      command: "LIVEO_TEST_MODE=1 ../.venv/bin/python -m backend --serve",
      url: "http://localhost:8000/api/stream/status",
      reuseExistingServer: !process.env.CI,
      timeout: 15_000,
    },
    {
      command: "NEXT_PUBLIC_TEST_MODE=1 NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npm run dev",
      url: "http://localhost:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
  ],
});
