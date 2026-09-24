import { test, expect } from '@playwright/test'

const ADMIN_TOKEN = process.env.API_ADMIN_TOKEN || 'test-admin-secret-e2e'

test.describe('Harness Memory Admin Console — E2E Suite', () => {
  test('SCN-E2E-01: should redirect unauthenticated users to /login and handle gatekeeper login', async ({
    page,
  }) => {
    // 1. Unauthenticated redirect
    await page.goto('/')
    await expect(page).toHaveURL(/\/login/)
    await expect(page.locator('h1')).toContainText('Harness Memory')

    // 2. Submit invalid token
    await page.fill('input[name="token"]', 'invalid-token-123')
    await page.click('button[type="submit"]')
    await expect(page.locator('text=Credencial inválida')).toBeVisible()

    // 3. Submit valid admin token
    await page.fill('input[name="token"]', ADMIN_TOKEN)
    await page.click('button[type="submit"]')

    // 4. Redirect to dashboard
    await expect(page).toHaveURL('/')
    await expect(page.locator('text=Tokens de Acesso & Credenciais')).toBeVisible()
  })

  test('SCN-E2E-02: should display active tenant and pre-existing seeded tokens', async ({ page }) => {
    // Authenticate
    await page.goto('/login')
    await page.fill('input[name="token"]', ADMIN_TOKEN)
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/')

    // Verify seeded token in table
    await expect(page.locator('text=pre-existing-e2e-token')).toBeVisible()
    await expect(page.locator('text=read').first()).toBeVisible()
    await expect(page.locator('text=Ativo').first()).toBeVisible()
  })

  test('SCN-E2E-03 & 04: should issue new token with scopes and display one-time reveal modal with copy', async ({
    page,
  }) => {
    // Authenticate
    await page.goto('/login')
    await page.fill('input[name="token"]', ADMIN_TOKEN)
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/')

    // Click "Novo Token"
    await page.click('button:has-text("Novo Token")')

    // Fill form in dialog
    const tokenName = `playwright-e2e-${Date.now()}`
    await page.fill('input[placeholder*="github-actions"]', tokenName)

    // Ensure memory:publish and memory:read are checked
    const publishCheckbox = page.locator('label:has-text("memory:publish") input[type="checkbox"]')
    if (!(await publishCheckbox.isChecked())) {
      await publishCheckbox.check()
    }

    // Select 30 days lifetime
    await page.click('button:has-text("30 Dias")')

    // Submit
    await page.click('button:has-text("Criar Token")')

    // Verify One-Time Reveal Modal
    await expect(page.locator('text=Token Emitido com Sucesso!')).toBeVisible()
    await expect(page.locator('text=Aviso de Exibição Única')).toBeVisible()

    const secretInput = page.locator('input[readonly]')
    const secretValue = await secretInput.inputValue()
    expect(secretValue).toMatch(/^hm_/)

    // Click Copiar
    await page.click('button:has-text("Copiar")')
    await expect(page.locator('text=Copiado!')).toBeVisible()

    // Close modal
    await page.click('button:has-text("Concluir e Fechar")')
    await expect(page.locator('text=Token Emitido com Sucesso!')).not.toBeVisible()

    // Verify new token exists in table
    await expect(page.locator(`text=${tokenName}`)).toBeVisible()
  })

  test('SCN-E2E-05: should revoke a token and update its status immediately', async ({ page }) => {
    // Authenticate
    await page.goto('/login')
    await page.fill('input[name="token"]', ADMIN_TOKEN)
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/')

    // Find row with pre-existing token and click trash button
    const row = page.locator('tr:has-text("pre-existing-e2e-token")')
    await expect(row).toBeVisible()

    await row.locator('button[title="Revogar token"]').click()
    await expect(row.locator('button:has-text("Confirmar")')).toBeVisible()

    // Confirm revocation
    await row.locator('button:has-text("Confirmar")').click()

    // The revoked token is removed from the active tokens list
    await expect(page.locator('tr:has-text("pre-existing-e2e-token")')).not.toBeVisible()
  })

  test('SCN-E2E-06: should logout and prevent further access without re-authenticating', async ({ page }) => {
    // Authenticate
    await page.goto('/login')
    await page.fill('input[name="token"]', ADMIN_TOKEN)
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/')

    // Click Sair
    await page.click('button:has-text("Sair")')
    await expect(page).toHaveURL(/\/login/)

    // Try going to / directly
    await page.goto('/')
    await expect(page).toHaveURL(/\/login/)
  })
})
