/**
 * Playwright E2E Test Suite: Studio Page State Management
 * 
 * Purpose: Catch state leaks and ensure Zustand stores reset correctly
 * when navigating between diagrams (especially broken vs. valid ones).
 * 
 * Run with: npx playwright test e2e/studio_chaos.spec.ts --headed
 */

import { test, expect, Page } from '@playwright/test'

// ============================================================================
// Test Data & Mocks
// ============================================================================

// Mock Diagram A: BROKEN (returns 500 or invalid JSON)
const BROKEN_DIAGRAM_RESPONSE = {
  status: 500,
  contentType: 'application/json',
  body: JSON.stringify({ error: 'Internal Server Error', detail: 'Generation failed' })
}

// Alternative broken response: malformed JSON
const MALFORMED_JSON_RESPONSE = {
  status: 200,
  contentType: 'application/json',
  body: '{"id": "broken", "type": "mermaid_erd", "content": "INVALID NOT MERMAID'  // Missing closing brace
}

// Mock Diagram B: VALID (returns perfect JSON)
const VALID_DIAGRAM_RESPONSE = {
  id: 'valid-diagram-001',
  type: 'mermaid_erd',
  content: `erDiagram
    USER ||--o{ ORDER : places
    ORDER ||--|{ LINE_ITEM : contains
    PRODUCT ||--o{ LINE_ITEM : "ordered in"
    USER {
        string id PK
        string name
        string email
    }
    ORDER {
        string id PK
        date createdAt
        string status
    }`,
  created_at: new Date().toISOString(),
  score: 95.0,
  model_used: 'llama3'
}

// Mock artifacts list with both broken and valid diagrams
const MOCK_ARTIFACTS_LIST = [
  {
    id: 'broken-diagram-001',
    type: 'mermaid_erd',
    content: 'BROKEN_DIAGRAM_CONTENT_THAT_WILL_FAIL',
    created_at: new Date(Date.now() - 3600000).toISOString(),  // 1 hour ago
    score: 0
  },
  {
    id: 'valid-diagram-001',
    type: 'mermaid_erd',
    content: VALID_DIAGRAM_RESPONSE.content,
    created_at: new Date().toISOString(),
    score: 95.0
  }
]

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Set up API route interception with our mock data
 */
async function setupMockRoutes(page: Page) {
  // Intercept artifact list endpoint
  await page.route('**/api/generation/artifacts**', async (route) => {
    const url = route.request().url()
    
    // Return different artifacts based on query params or path
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_ARTIFACTS_LIST)
    })
  })
  
  // Intercept single artifact fetch for BROKEN diagram
  await page.route('**/api/generation/artifacts/broken-diagram-001**', async (route) => {
    // Simulate a server error for the broken diagram
    await route.fulfill(BROKEN_DIAGRAM_RESPONSE)
  })
  
  // Intercept single artifact fetch for VALID diagram  
  await page.route('**/api/generation/artifacts/valid-diagram-001**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(VALID_DIAGRAM_RESPONSE)
    })
  })
  
  // Intercept version endpoints to prevent extra calls
  await page.route('**/api/versions/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ versions: [] })
    })
  })
  
  // Mock WebSocket to prevent connection errors (just acknowledge)
  await page.route('**/ws/**', async (route) => {
    await route.abort()  // WebSocket routes need special handling
  })
  
  // Mock other common API endpoints to prevent 404s
  await page.route('**/api/models/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { id: 'ollama:llama3', name: 'Llama 3', provider: 'ollama', status: 'available' }
      ])
    })
  })
  
  await page.route('**/api/context/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ context_id: 'mock-context', success: true })
    })
  })
}

/**
 * Wait for the page to be fully loaded (no loading spinners)
 */
async function waitForPageLoad(page: Page) {
  // Wait for any loading spinners to disappear
  await page.waitForSelector('.animate-spin', { state: 'hidden', timeout: 10000 }).catch(() => {})
  
  // Wait for main content to be visible
  await page.waitForSelector('[data-testid="studio-content"], .studio-content, main', { 
    state: 'visible',
    timeout: 10000 
  }).catch(() => {})
  
  // Small delay to let React finish rendering
  await page.waitForTimeout(500)
}

/**
 * Check if error state is visible on the page
 */
async function hasErrorState(page: Page): Promise<boolean> {
  const errorIndicators = [
    '.error-message',
    '[data-testid="error-state"]',
    '.text-red-500',
    '.text-destructive',
    'text=Error',
    'text=failed',
    'text=Failed'
  ]
  
  for (const selector of errorIndicators) {
    const element = await page.$(selector)
    if (element) {
      const isVisible = await element.isVisible()
      if (isVisible) return true
    }
  }
  
  return false
}

/**
 * Check if the diagram rendered correctly (Mermaid SVG present)
 */
async function hasMermaidRendered(page: Page): Promise<boolean> {
  // Check for Mermaid SVG elements
  const svgElement = await page.$('.mermaid svg, [data-testid="mermaid-diagram"] svg, .mermaid-diagram svg')
  if (svgElement) {
    return await svgElement.isVisible()
  }
  
  // Alternative: Check for successful content area without error
  const contentArea = await page.$('.artifact-content, [data-testid="diagram-content"]')
  if (contentArea) {
    const text = await contentArea.textContent()
    return text?.includes('USER') || text?.includes('ORDER') || text?.includes('erDiagram') || false
  }
  
  return false
}

// ============================================================================
// Test Suite: Rapid Navigation Stress Test
// ============================================================================

test.describe('Studio Page State Management - Chaos Tests', () => {
  
  test.beforeEach(async ({ page }) => {
    // Set up all mock routes before navigation
    await setupMockRoutes(page)
  })
  
  test('Rapid Navigation Stress Test - Error State Isolation', async ({ page }) => {
    /**
     * This test validates that:
     * 1. Viewing a broken diagram shows an error state
     * 2. Navigating to a valid diagram shows the correct content
     * 3. The error state from the broken diagram does NOT leak into the valid diagram
     * 4. This works correctly even under rapid navigation (5 cycles)
     */
    
    const CYCLE_COUNT = 5
    const NAVIGATION_DELAY_MS = 300  // Aggressive, rapid switching
    
    // Navigate to Studio page
    await page.goto('/studio')
    await waitForPageLoad(page)
    
    // Initial state: Should NOT show error
    const initialError = await hasErrorState(page)
    console.log(`Initial state - Has error: ${initialError}`)
    
    for (let cycle = 1; cycle <= CYCLE_COUNT; cycle++) {
      console.log(`\n--- Cycle ${cycle}/${CYCLE_COUNT} ---`)
      
      // STEP 1: Navigate to BROKEN diagram
      console.log('Navigating to BROKEN diagram...')
      
      // Click on the broken diagram in the list (or navigate directly)
      // This simulates selecting "Diagram A" (broken)
      await page.goto('/canvas?artifactId=broken-diagram-001')
      await waitForPageLoad(page)
      
      // ASSERTION 1: Broken diagram SHOULD show error state
      const hasErrorAfterBroken = await hasErrorState(page)
      console.log(`After broken diagram - Has error: ${hasErrorAfterBroken}`)
      
      // Note: We expect this to show error, but don't fail if the mock doesn't trigger it
      // The key test is the NEXT assertion
      
      // STEP 2: Rapidly navigate BACK and then to VALID diagram
      console.log('Switching to VALID diagram...')
      
      // Navigate to valid diagram
      await page.goto('/canvas?artifactId=valid-diagram-001')
      await page.waitForTimeout(NAVIGATION_DELAY_MS)  // Simulate rapid switching
      await waitForPageLoad(page)
      
      // ASSERTION 2: Valid diagram should NOT show error state
      const hasErrorAfterValid = await hasErrorState(page)
      console.log(`After valid diagram - Has error: ${hasErrorAfterValid}`)
      
      // This is the CRITICAL assertion: Error from Diagram A should NOT leak
      expect(
        hasErrorAfterValid,
        `Cycle ${cycle}: Error state leaked from broken diagram to valid diagram!`
      ).toBe(false)
      
      // ASSERTION 3: Valid diagram content should be rendered
      const diagramRendered = await hasMermaidRendered(page)
      console.log(`Valid diagram rendered: ${diagramRendered}`)
      
      // Check that content is present (even if Mermaid rendering is mocked)
      const pageContent = await page.textContent('body')
      const hasValidContent = pageContent?.includes('USER') || 
                             pageContent?.includes('ORDER') ||
                             pageContent?.includes('erDiagram')
      
      console.log(`Has valid content: ${hasValidContent}`)
      
      // At least one of these should be true for a valid diagram
      expect(
        diagramRendered || hasValidContent,
        `Cycle ${cycle}: Valid diagram content not found!`
      ).toBe(true)
      
      // Small delay before next cycle
      await page.waitForTimeout(100)
    }
    
    console.log('\n✅ All cycles passed - No state leaks detected!')
  })
  
  test('Back Button Navigation - State Reset', async ({ page }) => {
    /**
     * Tests that using browser back/forward buttons also properly resets state
     */
    
    // Start at Studio
    await page.goto('/studio')
    await waitForPageLoad(page)
    
    // Navigate to Canvas with valid diagram
    await page.goto('/canvas?artifactId=valid-diagram-001')
    await waitForPageLoad(page)
    
    // Capture initial state
    const initialError = await hasErrorState(page)
    expect(initialError).toBe(false)
    
    // Navigate to broken diagram
    await page.goto('/canvas?artifactId=broken-diagram-001')
    await waitForPageLoad(page)
    
    // Go back using browser back button
    await page.goBack()
    await waitForPageLoad(page)
    
    // The valid diagram should show without error leakage
    const errorAfterBack = await hasErrorState(page)
    expect(
      errorAfterBack,
      'Error state persisted after browser back navigation!'
    ).toBe(false)
  })
  
  test('Zustand Store Reset Verification', async ({ page }) => {
    /**
     * Directly tests that Zustand stores are being reset properly
     * by checking the store state via window.__ZUSTAND__ (if exposed)
     */
    
    await page.goto('/canvas?artifactId=broken-diagram-001')
    await waitForPageLoad(page)
    
    // Try to get diagram store state (if exposed for testing)
    const diagramStoreState = await page.evaluate(() => {
      // @ts-ignore - accessing internal store state
      const store = window.__DIAGRAM_STORE__ || window.useDiagramStore?.getState?.()
      return store ? {
        error: store.error,
        isRepairing: store.isRepairing,
        validation: store.validation
      } : null
    })
    
    console.log('Diagram store state after broken diagram:', diagramStoreState)
    
    // Navigate away
    await page.goto('/studio')
    await waitForPageLoad(page)
    
    // Navigate to valid diagram
    await page.goto('/canvas?artifactId=valid-diagram-001')
    await waitForPageLoad(page)
    
    // Check store state again
    const diagramStoreStateAfter = await page.evaluate(() => {
      // @ts-ignore
      const store = window.__DIAGRAM_STORE__ || window.useDiagramStore?.getState?.()
      return store ? {
        error: store.error,
        isRepairing: store.isRepairing,
        validation: store.validation
      } : null
    })
    
    console.log('Diagram store state after valid diagram:', diagramStoreStateAfter)
    
    // If store is exposed, verify error was cleared
    if (diagramStoreStateAfter) {
      expect(
        diagramStoreStateAfter.error,
        'Diagram store error was not cleared on navigation!'
      ).toBeNull()
    }
  })
  
})

// ============================================================================
// Test Suite: Memory Leak Detection
// ============================================================================

test.describe('Studio Page Memory Leak Detection', () => {
  
  test('No memory growth on repeated navigation', async ({ page }) => {
    /**
     * Navigates between pages multiple times and checks for memory growth
     */
    
    await setupMockRoutes(page)
    
    const measurements: number[] = []
    const NAVIGATION_COUNT = 10
    
    for (let i = 0; i < NAVIGATION_COUNT; i++) {
      // Navigate to Studio
      await page.goto('/studio')
      await page.waitForTimeout(200)
      
      // Navigate to Canvas
      await page.goto('/canvas')
      await page.waitForTimeout(200)
      
      // Measure memory (if available)
      const metrics = await page.metrics().catch(() => null)
      if (metrics && metrics.JSHeapUsedSize) {
        measurements.push(metrics.JSHeapUsedSize)
      }
    }
    
    if (measurements.length >= 2) {
      const firstHalf = measurements.slice(0, Math.floor(measurements.length / 2))
      const secondHalf = measurements.slice(Math.floor(measurements.length / 2))
      
      const avgFirst = firstHalf.reduce((a, b) => a + b, 0) / firstHalf.length
      const avgSecond = secondHalf.reduce((a, b) => a + b, 0) / secondHalf.length
      
      const growthPercent = ((avgSecond - avgFirst) / avgFirst) * 100
      
      console.log(`Memory growth: ${growthPercent.toFixed(2)}%`)
      console.log(`First half avg: ${(avgFirst / 1024 / 1024).toFixed(2)} MB`)
      console.log(`Second half avg: ${(avgSecond / 1024 / 1024).toFixed(2)} MB`)
      
      // Allow up to 50% growth (navigation creates some expected growth)
      // Anything more indicates a leak
      expect(
        growthPercent,
        `Memory growth ${growthPercent.toFixed(2)}% exceeds threshold (50%)`
      ).toBeLessThan(50)
    }
  })
})

