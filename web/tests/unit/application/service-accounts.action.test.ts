import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  listServiceAccountsAction,
  ensureServiceAccountAction,
} from '@/app/actions/service-accounts'
import { ClientFactory } from '@/infrastructure/api/client-factory'
import { HarnessApiClientPort } from '@/application/ports/harness-api-client.port'

describe('Service Accounts Server Actions', () => {
  const mockClient: Partial<HarnessApiClientPort> = {
    listServiceAccounts: vi.fn(),
    createServiceAccount: vi.fn(),
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
})
