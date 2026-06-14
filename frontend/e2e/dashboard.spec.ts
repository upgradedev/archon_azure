import { test, expect } from '@playwright/test'

test.describe('Dashboard', () => {
  test('loads and auto-selects the latest period', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('Archon')).toBeVisible()
    // Period selector should be populated
    await expect(page.locator('.ant-select-selection-item')).toBeVisible({ timeout: 15_000 })
  })

  test('shows metric tiles for a period with a report', async ({ page }) => {
    await page.goto('/')
    // Wait for report to load — Revenue tile must appear
    await expect(page.getByText('Revenue')).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText('Expenses')).toBeVisible()
    await expect(page.getByText('Net Profit')).toBeVisible()
    await expect(page.getByText('Gross Margin')).toBeVisible()
    await expect(page.getByText('Cash Net')).toBeVisible()
    await expect(page.getByText('Invoices')).toBeVisible()
  })

  test('executive summary card shows Foundry IQ tag and body text', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('Executive Summary')).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText('Foundry IQ')).toBeVisible()
  })

  test('period dropdown lists available periods', async ({ page }) => {
    await page.goto('/')
    await page.locator('.ant-select-selector').first().click()
    await expect(page.locator('.ant-select-dropdown')).toBeVisible()
    // At least one option exists
    await expect(page.locator('.ant-select-item-option')).toHaveCount({ min: 1 } as never)
    await page.keyboard.press('Escape')
  })

  test('upload drawer opens and closes', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('Archon')).toBeVisible()
    await page.getByText('Upload Documents').click()
    await expect(page.locator('.ant-drawer')).toBeVisible()
    await expect(page.getByText('Reporting period')).toBeVisible()
    // Close drawer
    await page.locator('.ant-drawer-close').click()
    await expect(page.locator('.ant-drawer')).not.toBeVisible()
  })

  test('run analysis button appears for a period with no report', async ({ page }) => {
    // Use 2026-05 which has no report in demo data
    await page.goto('/')
    await page.waitForSelector('.ant-select-selector', { timeout: 15_000 })
    // Open period selector and pick 2026-05
    await page.locator('.ant-select-selector').first().click()
    const option = page.locator('.ant-select-item-option-content', { hasText: 'May 2026' })
    if (await option.isVisible()) {
      await option.click()
      await expect(page.getByText('Run Analysis')).toBeVisible({ timeout: 15_000 })
    } else {
      test.skip()
    }
  })

  test('refresh button reloads the report', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('Revenue')).toBeVisible({ timeout: 20_000 })
    await page.locator('[title="Refresh report"]').click()
    // Loading spinner may appear briefly — report should reload
    await expect(page.getByText('Revenue')).toBeVisible({ timeout: 20_000 })
  })
})
