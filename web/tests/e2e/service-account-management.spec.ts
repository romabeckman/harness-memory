import { expect, request as playwrightRequest, test } from '@playwright/test'

const ADMIN_TOKEN = process.env.API_ADMIN_TOKEN || 'test-admin-secret-e2e'
const API_URL = process.env.HARNESS_API_URL || 'http://localhost:8080'

test('admin manages a service account and its locked non-expiring token', async ({ page }) => {
  const suffix = `${Date.now()}`
  const originalName = `Automation ${suffix}`
  const editedName = `Edited automation ${suffix}`
  const tokenName = `service-account-token-${suffix}`
  const api = await playwrightRequest.newContext({
    baseURL: API_URL,
    extraHTTPHeaders: { Authorization: `Bearer ${ADMIN_TOKEN}` },
  })
  let accountId: string | undefined
  let tokenId: string | undefined

  try {
    await page.goto('/service-accounts')
    await expect(page).toHaveURL(/\/login/)
    await page.getByLabel('Admin Key (API_ADMIN_TOKEN)').fill(ADMIN_TOKEN)
    await page.getByRole('button', { name: 'Open Dashboard' }).click()
    await page.getByRole('link', { name: 'Service Accounts' }).click()
    await expect(page).toHaveURL('/service-accounts')
    await expect(page.getByRole('heading', { name: 'Service Accounts', exact: true })).toBeVisible()

    await page.getByRole('button', { name: 'New Service Account' }).click()
    await page.getByLabel('Name').fill(`  ${originalName}  `)
    await page.getByLabel('Organization (required)').selectOption({ index: 1 })
    await page.getByRole('button', { name: 'Create Service Account' }).click()

    const accountRow = page.getByRole('row').filter({ hasText: originalName })
    await expect(accountRow).toBeVisible()
    const accountResponse = await api.get('/v1/service-accounts', {
      params: { q: originalName, limit: 20, offset: 0 },
    })
    expect(accountResponse.ok()).toBeTruthy()
    accountId = ((await accountResponse.json()) as Array<{ id: string }>)[0]?.id
    expect(accountId).toBeDefined()

    await accountRow.getByRole('button', { name: `Create token for ${originalName}` }).click()
    const tokenDialog = page.getByRole('dialog', { name: 'Issue New Access Token' })
    await expect(tokenDialog.getByText('Owner (Service Account):')).toBeVisible()
    await expect(tokenDialog.getByText(originalName, { exact: true })).toBeVisible()
    await tokenDialog.getByLabel('Token Name').fill(tokenName)
    await tokenDialog.getByRole('button', { name: 'Never Expires' }).click()
    await tokenDialog.getByRole('button', { name: 'Create Token' }).click()
    await expect(page.getByText('One-Time Reveal Notice')).toBeVisible()
    await page.getByRole('button', { name: 'Done and Close' }).click()

    const tokensResponse = await api.get('/v1/tokens')
    const createdToken = ((await tokensResponse.json()) as Array<{
      id: string
      name: string
      service_account_id: string | null
      expires_at: string | null
    }>).find((token) => token.name === tokenName)
    expect(createdToken).toMatchObject({
      service_account_id: accountId,
      expires_at: null,
    })
    tokenId = createdToken?.id

    await accountRow.getByRole('button', { name: `Edit service account ${originalName}` }).click()
    await page.getByLabel('Name').fill(editedName)
    await expect(page.getByText(/Organization:/)).toBeVisible()
    await page.getByRole('button', { name: 'Save Changes' }).click()
    await expect(page.getByRole('row').filter({ hasText: editedName })).toBeVisible()

    await page.getByRole('row').filter({ hasText: editedName }).getByRole('button', { name: `Delete service account ${editedName}` }).click()
    await expect(page.getByText(`Deleting ${editedName} will permanently revoke all tokens owned by this service account.`)).toBeVisible()
    await page.getByLabel('Confirmation key').fill(editedName)
    await page.getByRole('button', { name: 'Delete Permanently' }).click()
    await expect(page.getByRole('row').filter({ hasText: editedName })).toHaveCount(0)
    expect((await api.get(`/v1/service-accounts/${accountId}`)).status()).toBe(404)
    expect((await api.get(`/v1/tokens/${tokenId}`)).status()).toBe(404)
  } finally {
    if (accountId) await api.delete(`/v1/service-accounts/${accountId}`).catch(() => undefined)
    await api.dispose()
  }
})
