import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  createServiceAccountAction,
  deleteServiceAccountAction,
  listServiceAccountsAction,
  updateServiceAccountAction,
  ensureServiceAccountAction,
} from '@/app/actions/service-accounts'
import { ClientFactory } from '@/infrastructure/api/client-factory'
import { HarnessApiClientPort } from '@/application/ports/harness-api-client.port'

vi.mock('next/cache', () => ({ revalidatePath: vi.fn() }))

describe('Service Accounts Server Actions', () => {
  const mockClient: Partial<HarnessApiClientPort> = {
    listServiceAccounts: vi.fn(),
    createServiceAccount: vi.fn(),
    updateServiceAccount: vi.fn(),
    deleteServiceAccount: vi.fn(),
  }

  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(ClientFactory, 'getHarnessClient').mockReturnValue(
      mockClient as HarnessApiClientPort
    )
  })

  it('should list service accounts for a specific tenant', async () => {
    const mockAccounts = [
      { id: 'sa-1', tenant_id: 't-1', name: 'ci-publisher' },
    ]
    vi.mocked(mockClient.listServiceAccounts!).mockResolvedValueOnce(mockAccounts)

    const result = await listServiceAccountsAction('t-1')

    expect(result.data).toEqual(mockAccounts)
    expect(mockClient.listServiceAccounts).toHaveBeenCalledWith('t-1')
  })

  it('should return existing service account if found during ensure', async () => {
    const mockAccounts = [
      { id: 'sa-1', tenant_id: 't-1', name: 'ci-publisher' },
    ]
    vi.mocked(mockClient.listServiceAccounts!).mockResolvedValueOnce(mockAccounts)

    const result = await ensureServiceAccountAction('t-1')

    expect(result.data).toEqual(mockAccounts[0])
    expect(mockClient.createServiceAccount).not.toHaveBeenCalled()
  })

  it('should automatically provision a service account if none exists for tenant', async () => {
    vi.mocked(mockClient.listServiceAccounts!).mockResolvedValueOnce([])
    const newlyCreated = {
      id: 'sa-new',
      tenant_id: 't-1',
      name: 'default-automation',
    }
    vi.mocked(mockClient.createServiceAccount!).mockResolvedValueOnce(newlyCreated)

    const result = await ensureServiceAccountAction('t-1')

    expect(result.data).toEqual(newlyCreated)
    expect(mockClient.createServiceAccount).toHaveBeenCalledWith({
      tenant_id: 't-1',
      name: 'default-automation',
    })
  })

  it('lists global service accounts with the default page', async () => {
    vi.mocked(mockClient.listServiceAccounts!).mockResolvedValueOnce([])

    await expect(listServiceAccountsAction()).resolves.toEqual({ data: [] })
    expect(mockClient.listServiceAccounts).toHaveBeenCalledWith({ limit: 100, offset: 0 })
  })

  it('lists service accounts for the selected organization and forwards pagination', async () => {
    vi.mocked(mockClient.listServiceAccounts!).mockResolvedValueOnce([])

    await listServiceAccountsAction({ tenantId: 't-1', query: 'release', limit: 20, offset: 20 })

    expect(mockClient.listServiceAccounts).toHaveBeenCalledWith({
      tenantId: 't-1',
      query: 'release',
      limit: 20,
      offset: 20,
    })
  })

  it('requires organization and valid name before creating an account', async () => {
    await expect(createServiceAccountAction({ name: 'Release bot' })).resolves.toEqual({
      success: false,
      error: 'Organization is required',
    })
    await expect(createServiceAccountAction({ name: ' '.repeat(2), tenantId: 't-1' })).resolves.toEqual({
      success: false,
      error: 'Service account name is required',
    })
    expect(mockClient.createServiceAccount).not.toHaveBeenCalled()
  })

  it('trims create and update input, then revalidates the page', async () => {
    const account = { id: 'sa-1', tenant_id: 't-1', name: 'Release bot' }
    vi.mocked(mockClient.createServiceAccount!).mockResolvedValueOnce(account)
    vi.mocked(mockClient.updateServiceAccount!).mockResolvedValueOnce(account)
    vi.mocked(mockClient.deleteServiceAccount!).mockResolvedValueOnce()

    await expect(
      createServiceAccountAction({ name: '  Release bot  ', tenantId: 't-1' })
    ).resolves.toEqual({ success: true, data: account })
    await expect(updateServiceAccountAction('sa-1', { name: '  Release bot 2  ' })).resolves.toEqual({
      success: true,
      data: account,
    })
    await expect(deleteServiceAccountAction('sa-1')).resolves.toEqual({ success: true })

    expect(mockClient.createServiceAccount).toHaveBeenCalledWith({
      name: 'Release bot',
      tenant_id: 't-1',
    })
    expect(mockClient.updateServiceAccount).toHaveBeenCalledWith('sa-1', { name: 'Release bot 2' })
    expect(mockClient.deleteServiceAccount).toHaveBeenCalledWith('sa-1')
  })

  it('returns safe failures for list and mutation errors', async () => {
    vi.mocked(mockClient.listServiceAccounts!).mockRejectedValueOnce(
      new Error('API_ADMIN_TOKEN=secret Authorization: Bearer secret')
    )
    vi.mocked(mockClient.createServiceAccount!).mockRejectedValueOnce(new Error('upstream failed'))

    const listResult = await listServiceAccountsAction({ limit: 20, offset: 0 })
    const createResult = await createServiceAccountAction({ name: 'Release bot', tenantId: 't-1' })

    expect(listResult.error).not.toContain('API_ADMIN_TOKEN')
    expect(listResult.error).not.toContain('Authorization')
    expect(createResult).toEqual({ success: false, error: 'upstream failed' })
  })
})
