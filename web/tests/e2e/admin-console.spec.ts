import { test, expect } from '@playwright/test'

const ADMIN_TOKEN = process.env.API_ADMIN_TOKEN || 'test-admin-secret-e2e'

test.describe('Harness Memory Admin Console — credential review', () => {
  async function authenticate(page: import('@playwright/test').Page) {
    await page.goto('/login')
    await page.fill('input[name="token"]', ADMIN_TOKEN)
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/')
  }

  test('redirects unauthenticated users and accepts the admin session', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveURL(/\/login/)
    await expect(page.locator('h1')).toContainText('Harness Memory')

    await page.fill('input[name="token"]', 'invalid-token-123')
    await page.click('button[type="submit"]')
    await expect(page.locator('text=Invalid credential')).toBeVisible()

    await page.fill('input[name="token"]', ADMIN_TOKEN)
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/')
    await expect(page.locator('text=Access Tokens & Credentials')).toBeVisible()
  })

  test('shows owner context and no aggregate issuance control', async ({ page }) => {
    await authenticate(page)

    await expect(page.getByRole('button', { name: 'New Token' })).toHaveCount(0)
    await expect(page.locator('tbody tr').first()).toContainText(/User|Service Account/)
  })

  test('cancels revocation without changing the credential list', async ({ page }) => {
    await authenticate(page)

    const row = page.locator('tr:has-text("pre-existing-e2e-token")')
    await expect(row).toBeVisible()
    await row.locator('button[title="Revoke token"]').click()
    await expect(row.locator('button:has-text("Confirm")')).toBeVisible()
    await row.locator('button:has-text("Cancel")').click()
    await expect(row.locator('button[title="Revoke token"]')).toBeVisible()
    await expect(row).toBeVisible()
  })

  test('revokes a selected token after confirmation', async ({ page }) => {
    await authenticate(page)

    const row = page.locator('tr:has-text("pre-existing-e2e-token")')
    await expect(row).toBeVisible()
    await row.locator('button[title="Revoke token"]').click()
    await row.locator('button:has-text("Confirm")').click()
    await expect(page.locator('tr:has-text("pre-existing-e2e-token")')).not.toBeVisible()
  })

  test('logs out and protects the dashboard', async ({ page }) => {
    await authenticate(page)
    await page.click('button:has-text("Sign Out")')
    await expect(page).toHaveURL(/\/login/)
    await page.goto('/')
    await expect(page).toHaveURL(/\/login/)
  })
})
