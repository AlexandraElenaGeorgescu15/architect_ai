import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright configuration for Architect.AI E2E tests
 * 
 * Run tests:
 *   npx playwright test                        # Run all tests
 *   npx playwright test --headed               # Run with browser visible
 *   npx playwright test e2e/studio_chaos.spec.ts --headed  # Specific test, headed
 *   npx playwright test --ui                   # Interactive UI mode
 */
export default defineConfig({
  // Test directory
  testDir: './e2e',
  
  // Test file pattern
  testMatch: '**/*.spec.ts',
  
  // Timeout for each test (ms)
  timeout: 60000,
  
  // Timeout for each expect() assertion (ms)
  expect: {
    timeout: 10000
  },
  
  // Run tests in parallel (set to 1 for debugging)
  fullyParallel: true,
  workers: process.env.CI ? 1 : undefined,
  
  // Fail the build on CI if test.only is accidentally left in
  forbidOnly: !!process.env.CI,
  
  // Retry on CI only
  retries: process.env.CI ? 2 : 0,
  
  // Reporter configuration
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list']
  ],
  
  // Shared settings for all projects
  use: {
    // Base URL for the frontend
    baseURL: 'http://localhost:3000',
    
    // Collect trace on first retry only
    trace: 'on-first-retry',
    
    // Screenshot on failure
    screenshot: 'only-on-failure',
    
    // Video recording
    video: 'retain-on-failure',
    
    // Browser viewport
    viewport: { width: 1920, height: 1080 },
    
    // Action timeout
    actionTimeout: 15000,
    
    // Navigation timeout
    navigationTimeout: 30000,
  },
  
  // Configure projects for cross-browser testing
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    
    // Uncomment to test on Firefox
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    
    // Uncomment to test on Safari
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],
  
  // Run your local dev server before starting the tests
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,  // 2 minutes for dev server to start
  },
})

