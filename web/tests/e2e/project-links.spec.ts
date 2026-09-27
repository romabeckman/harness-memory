import { test, expect } from '@playwright/test'

const ADMIN_TOKEN = process.env.API_ADMIN_TOKEN || 'test-admin-secret-e2e'

test.describe('Harness Memory Admin Console — Project Links E2E Suite', () => {
  const login = async (page: any) => {
    await page.goto('/login')
    await page.fill('input[name="token"]', ADMIN_TOKEN)
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/')
  }

  test('SCN-E2E-LINK-01: should manage project links via web UI', async ({ page }) => {
    await login(page)
    await page.click('aside a[href="/projects"]')
    await expect(page).toHaveURL('/projects')
    await expect(page.locator('h1')).toContainText('Software Projects')

    // Find any project link button if projects exist
    const linkButton = page.locator('button[aria-label^="Manage links for"]').first()
    if (await linkButton.isVisible()) {
      await linkButton.click()
      await expect(page.locator('section[aria-label^="Links for"]')).toBeVisible()
    }
  })
})
