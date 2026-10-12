const { defineConfig, devices } = require('@playwright/test');
const path = require('path');

const rootDir = path.resolve(__dirname, '..');
const reportDir = process.env.PLAYWRIGHT_REPORT_DIR || path.join(rootDir, 'output/playwright');

/**
 * Playwright E2E configuration for Gold Price Dashboard.
 * See https://playwright.dev/docs/test-configuration
 */
module.exports = defineConfig({
  testDir: './e2e',
  timeout: 30 * 1000,
  expect: {
    timeout: 5000,
  },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  outputDir: path.join(reportDir, 'test-results'),
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: path.join(reportDir, 'html') }],
    ['json', { outputFile: path.join(reportDir, 'results.json') }],
    ['junit', { outputFile: path.join(reportDir, 'junit.xml') }],
  ],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],

  /* Run local dev server before starting the tests if not already running */
  webServer: {
    command: 'npm start',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});
