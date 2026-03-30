import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 0,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'python -m azure_migrate_simulations.web.app',
    url: 'http://localhost:5000',
    reuseExistingServer: true,
    timeout: 30_000,
    env: {
      PYTHONPATH: 'src',
      PYTHONIOENCODING: 'utf-8',
    },
  },
});
