/**
 * Run this once to save your Microsoft login session:
 *   npx playwright test --project=setup
 *
 * A browser window opens. Sign in with tf@upgrade.net.gr (or any Microsoft account).
 * After the dashboard loads, auth state is saved to e2e/auth.json.
 * All subsequent test runs reuse that session — no login prompt.
 */
import { test as setup } from '@playwright/test'
import path from 'path'

const AUTH_FILE = path.join(__dirname, 'auth.json')

setup('authenticate via Microsoft login', async ({ page }) => {
  await page.goto('/')

  // SWA redirects to Microsoft login — wait up to 2 minutes for user to complete
  await page.waitForURL('**/gentle-sky-08574a603.7.azurestaticapps.net/**', { timeout: 120_000 })

  // Confirm we're past auth (dashboard title visible)
  await page.waitForSelector('text=Archon', { timeout: 30_000 })

  await page.context().storageState({ path: AUTH_FILE })
  console.log(`Auth state saved to ${AUTH_FILE}`)
})
