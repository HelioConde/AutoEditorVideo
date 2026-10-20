import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/web',
  fullyParallel: false,
  timeout: 45_000,
  expect: { timeout: 8000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: { baseURL: 'http://127.0.0.1:5174', trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  projects: [
    { name: 'web-desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'web-mobile', use: { ...devices['Pixel 7'] } }
  ],
  webServer: {
    command: 'npm run dev:web',
    url: 'http://127.0.0.1:5174',
    reuseExistingServer: !process.env.CI,
    timeout: 60000
  }
});
