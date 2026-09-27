import { expect, request as playwrightRequest, test } from '@playwright/test'

const ADMIN_TOKEN = process.env.API_ADMIN_TOKEN || 'test-admin-secret-e2e'
const API_URL = process.env.HARNESS_API_URL || 'http://localhost:8080'

test('admin manages global users, issues owner-bound tokens, and confirms cascading revocation', async ({
  page,
}) => {
  const suffix = `${Date.now()}`
  const originalName = `User Journey ${suffix}`
  const editedName = `Edited User ${suffix}`
  const email = `user-${suffix}@example.com`
  const editedEmail = `edited-${suffix}@example.com`
  const api = await playwrightRequest.newContext({
    baseURL: API_URL,
    extraHTTPHeaders: { Authorization: `Bearer ${ADMIN_TOKEN}` },
  })
  let userId: string | undefined
  const tokenIds: string[] = []

  try {
    await page.goto('/users')
    await expect(page).toHaveURL(/\/login/)
    await page.getByLabel('Admin Key (API_ADMIN_TOKEN)').fill(ADMIN_TOKEN)
    await page.getByRole('button', { name: 'Open Dashboard' }).click()
    await expect(page).toHaveURL('/')
    await page.getByRole('link', { name: 'Users' }).click()
    await expect(page).toHaveURL('/users')
    await expect(page.getByRole('heading', { name: 'Users' })).toBeVisible()

    await page.getByRole('button', { name: 'New User' }).click()
    await page.getByLabel('Name').fill(`  ${originalName}  `)
    await page.getByLabel('Email').fill(email.toUpperCase())
    await page.getByRole('button', { name: 'Create User' }).click()

    await page.getByPlaceholder('Search users by name or email...').fill(email)
    const userRow = page.getByRole('row').filter({ hasText: email })
    await expect(userRow).toContainText(originalName)

    const listedUsers = await api.get('/v1/users', { params: { q: email, limit: 20, offset: 0 } })
    expect(listedUsers.ok()).toBeTruthy()
    const [createdUser] = (await listedUsers.json()) as Array<{
      id: string
      name: string
      email: string
      tenant_id?: string
    }>
    expect(createdUser).toMatchObject({ name: originalName, email })
    expect(createdUser).not.toHaveProperty('tenant_id')
    userId = createdUser.id

    const tenantResponse = await api.get(`/v1/tenants/${userId}`)
    expect(tenantResponse.status()).toBe(404)

    await userRow.getByRole('button', { name: `Edit user ${originalName}` }).click()
    await page.getByLabel('Name').fill(editedName)
    await page.getByLabel('Email').fill(editedEmail)
    await page.getByRole('button', { name: 'Save Changes' }).click()
    await page.getByPlaceholder('Search users by name or email...').fill(editedEmail)
    const editedRow = page.getByRole('row').filter({ hasText: editedEmail })
    await expect(editedRow).toContainText(editedName)

    const expectedTokenIds: string[] = []
    for (const lifetime of ['30', '90', '365'] as const) {
      await editedRow.getByRole('button', { name: `Create token for ${editedName}` }).click()
      const tokenDialog = page.getByRole('dialog', { name: 'Issue New Access Token' })
      await expect(tokenDialog.getByText('Owner (User):')).toBeVisible()
      await expect(tokenDialog.getByText(editedName, { exact: true })).toBeVisible()
      await expect(tokenDialog.getByText('Never Expires', { exact: true })).toHaveCount(0)
      const tokenName = `user-${lifetime}-day-${suffix}`
      await tokenDialog.getByLabel('Token Name').fill(tokenName)
      if (lifetime === '90') await tokenDialog.getByRole('button', { name: '90 Days' }).click()
      if (lifetime === '365') await tokenDialog.getByRole('button', { name: '1 Year (365 Days)' }).click()
      await tokenDialog.getByRole('button', { name: 'Create Token' }).click()
      await expect(page.getByText('One-Time Reveal Notice')).toBeVisible()
      await page.getByRole('button', { name: 'Done and Close' }).click()

      const tokensResponse = await api.get('/v1/tokens')
      expect(tokensResponse.ok()).toBeTruthy()
      const createdToken = ((await tokensResponse.json()) as Array<{
        id: string
        name: string
        user_id: string | null
        service_account_id: string | null
        expires_at: string | null
        project_keys: string[]
      }>).find((token) => token.name === tokenName)
      expect(createdToken).toBeDefined()
      expect(createdToken).toMatchObject({
        user_id: userId,
        service_account_id: null,
        project_keys: ['*'],
      })
      expect(createdToken?.expires_at).toBeTruthy()
      expect(Math.round((Date.parse(createdToken!.expires_at!) - Date.now()) / 86_400_000)).toBe(
        Number(lifetime)
      )
      expectedTokenIds.push(createdToken!.id)
    }
    tokenIds.push(...expectedTokenIds)

    await editedRow.getByRole('button', { name: `Delete user ${editedName}` }).click()
    await expect(
      page.getByText(`Deleting ${editedName} will permanently revoke all tokens owned by this user.`)
    ).toBeVisible()
    await page.getByRole('button', { name: 'Cancel' }).click()
    expect((await api.get(`/v1/users/${userId}`)).status()).toBe(200)
    for (const tokenId of tokenIds) expect((await api.get(`/v1/tokens/${tokenId}`)).status()).toBe(200)

    await editedRow.getByRole('button', { name: `Delete user ${editedName}` }).click()
    await page.getByLabel('Confirmation key').fill(editedName)
    await page.getByRole('button', { name: 'Delete Permanently' }).click()
    await expect(page.getByRole('row').filter({ hasText: editedEmail })).toHaveCount(0)
    expect((await api.get(`/v1/users/${userId}`)).status()).toBe(404)
    for (const tokenId of tokenIds) expect((await api.get(`/v1/tokens/${tokenId}`)).status()).toBe(404)
  } finally {
    if (userId) await api.delete(`/v1/users/${userId}`).catch(() => undefined)
    await api.dispose()
  }
})
