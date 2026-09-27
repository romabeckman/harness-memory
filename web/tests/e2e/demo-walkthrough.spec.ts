import { test, expect } from '@playwright/test'

const ADMIN_TOKEN = process.env.API_ADMIN_TOKEN || 'test-admin-secret-e2e'

test('Credential review walkthrough', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveURL(/\/login/)

  await page.fill('input[name="token"]', ADMIN_TOKEN)
  await page.click('button[type="submit"]')
  await expect(page).toHaveURL('/')
  await expect(page.getByRole('button', { name: 'New Token' })).toHaveCount(0)

  const row = page.locator('tr:has-text("pre-existing-e2e-token")')
  await expect(row).toContainText(/User|Service Account/)
  await row.locator('button[title="Revoke token"]').click()
  await expect(row.locator('button:has-text("Confirm")')).toBeVisible()
  await row.locator('button:has-text("Cancel")').click()
  await expect(row).toBeVisible()

  await page.click('button:has-text("Sign Out")')
  await expect(page).toHaveURL(/\/login/)
})
