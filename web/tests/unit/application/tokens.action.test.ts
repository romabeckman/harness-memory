import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  createTokenAction,
  loadAllCredentialReviewCatalogs,
  loadDashboardDataAction,
  revokeTokenAction,
} from '@/app/actions/tokens'
import { HarnessApiClientPort } from '@/application/ports/harness-api-client.port'
import { ClientFactory } from '@/infrastructure/api/client-factory'

import { revalidatePath } from 'next/cache'

vi.mock('next/cache', () => ({ revalidatePath: vi.fn() }))

describe('token server action', () => {
  const mockClient: Partial<HarnessApiClientPort> = {
    createToken: vi.fn(),
  }

  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(ClientFactory, 'getHarnessClient').mockReturnValue(mockClient as HarnessApiClientPort)
    vi.mocked(mockClient.createToken!).mockReset()
  })

  it('rejects a request that includes a second owner identifier', async () => {
    const result = await createTokenAction({
      name: 'release-token',
      owner: { kind: 'user', id: 'user-1', name: 'Ada' },
      scopes: ['memory:read'],
      projectKeys: [],
      lifetimeDays: 30,
      serviceAccountId: 'sa-1',
    } as Parameters<typeof createTokenAction>[0] & { serviceAccountId: string })

    expect(result).toEqual({
      success: false,
      error: 'Exactly one token owner must be selected',
    })
    expect(mockClient.createToken).not.toHaveBeenCalled()
  })

  it('loads every bounded catalog page exactly once', async () => {
    const client = {
      listTokens: vi.fn(async (_limit: number, offset: number) =>
        offset === 0 ? [{ id: 'token-1' }, { id: 'token-2' }] : [{ id: 'token-3' }]
      ),
      listUsers: vi.fn(async (_query: string | undefined, _limit: number, offset: number) =>
        offset === 0
          ? [{ id: 'user-1' }, { id: 'user-2' }]
          : [{ id: 'user-3' }]
      ),
      listServiceAccounts: vi.fn(async (query: { offset?: number }) =>
        query.offset === 0 ? [{ id: 'sa-1' }, { id: 'sa-2' }] : [{ id: 'sa-3' }]
      ),
      listTenants: vi.fn(async (_query: string | undefined, _limit: number, offset: number) =>
        offset === 0 ? [{ id: 'tenant-1' }, { id: 'tenant-2' }] : [{ id: 'tenant-3' }]
      ),
    } as unknown as HarnessApiClientPort

    const result = await loadAllCredentialReviewCatalogs(client, 2)

    expect(result.tokens).toHaveLength(3)
    expect(result.users).toHaveLength(3)
    expect(result.serviceAccounts).toHaveLength(3)
    expect(result.tenants).toHaveLength(3)
    expect(vi.mocked(client.listTokens)).toHaveBeenNthCalledWith(1, 2, 0)
    expect(vi.mocked(client.listTokens)).toHaveBeenNthCalledWith(2, 2, 2)
    expect(vi.mocked(client.listUsers)).toHaveBeenNthCalledWith(1, undefined, 2, 0)
    expect(vi.mocked(client.listUsers)).toHaveBeenNthCalledWith(2, undefined, 2, 2)
    expect(vi.mocked(client.listServiceAccounts)).toHaveBeenNthCalledWith(1, { limit: 2, offset: 0 })
    expect(vi.mocked(client.listServiceAccounts)).toHaveBeenNthCalledWith(2, { limit: 2, offset: 2 })
  })

  it('returns review-ready rows without per-credential owner requests', async () => {
    const client = {
      listTenants: vi.fn().mockResolvedValue([{ id: 'tenant-1', name: 'Platform' }]),
      listServiceAccounts: vi.fn().mockResolvedValue([{ id: 'sa-1', tenant_id: 'tenant-1', name: 'release-bot' }]),
      listTokens: vi.fn().mockResolvedValueOnce([
        { id: 'token-1', name: 'user-token', user_id: 'user-1', service_account_id: null, scopes: [], project_keys: [], created_at: '', is_active: true },
        { id: 'token-2', name: 'service-token', user_id: null, service_account_id: 'sa-1', scopes: [], project_keys: [], created_at: '', is_active: true },
      ]),
      listUsers: vi.fn().mockResolvedValueOnce([{ id: 'user-1', name: 'Ada', email: 'ada@example.com' }]),
    } as unknown as HarnessApiClientPort
    vi.spyOn(ClientFactory, 'getHarnessClient').mockReturnValue(client)

    const result = await loadDashboardDataAction()

    expect(result.data?.credentials).toHaveLength(2)
    expect(result.data?.credentials[0].ownerName).toBe('Ada')
    expect(result.data?.credentials[1].ownerName).toBe('release-bot')
    expect(client.listUsers).toHaveBeenCalledTimes(1)
    expect(client.listTokens).toHaveBeenCalledTimes(1)
  })

  it('returns a safe dashboard error without partial credentials', async () => {
    const client = {
      listTenants: vi.fn().mockResolvedValue([{ id: 'tenant-1', name: 'Platform' }]),
      listServiceAccounts: vi.fn().mockResolvedValue([{ id: 'sa-1', tenant_id: 'tenant-1', name: 'release-bot' }]),
      listTokens: vi.fn().mockRejectedValue(new Error('API_ADMIN_TOKEN=secret Authorization: Bearer hm_secret')),
    } as unknown as HarnessApiClientPort
    vi.spyOn(ClientFactory, 'getHarnessClient').mockReturnValue(client)

    const result = await loadDashboardDataAction()

    expect(result.data).toBeUndefined()
    expect(result.error).toBe('Failed to load credential review data')
    expect(result.error).not.toContain('secret')
  })

  it('does not bootstrap identity records when review catalogs are empty', async () => {
    const client = {
      listTokens: vi.fn().mockResolvedValue([]),
      listUsers: vi.fn().mockResolvedValue([]),
      listServiceAccounts: vi.fn().mockResolvedValue([]),
      listTenants: vi.fn().mockResolvedValue([]),
      createTenant: vi.fn(),
      createServiceAccount: vi.fn(),
    } as unknown as HarnessApiClientPort
    vi.spyOn(ClientFactory, 'getHarnessClient').mockReturnValue(client)

    const result = await loadDashboardDataAction()

    expect(result.data?.credentials).toEqual([])
    expect(client.createTenant).not.toHaveBeenCalled()
    expect(client.createServiceAccount).not.toHaveBeenCalled()
  })

  it('loads only one bounded token review page', async () => {
    const client = {
      listTokens: vi.fn().mockResolvedValue([]),
      listUsers: vi.fn().mockResolvedValue([]),
      listServiceAccounts: vi.fn().mockResolvedValue([]),
      listTenants: vi.fn().mockResolvedValue([]),
    } as unknown as HarnessApiClientPort
    vi.spyOn(ClientFactory, 'getHarnessClient').mockReturnValue(client)

    await loadDashboardDataAction(2)

    expect(client.listTokens).toHaveBeenCalledTimes(1)
    expect(client.listTokens).toHaveBeenCalledWith(51, 100)
  })

  it('revalidates only after successful revocation', async () => {
    mockClient.revokeToken = vi.fn().mockResolvedValue(undefined)

    await expect(revokeTokenAction('token-1')).resolves.toEqual({ success: true })

    expect(mockClient.revokeToken).toHaveBeenCalledOnce()
    expect(revalidatePath).toHaveBeenCalledWith('/')
  })

  it('keeps revocation failures retryable and safe', async () => {
    mockClient.revokeToken = vi.fn().mockRejectedValue(new Error('request headers API_ADMIN_TOKEN=secret'))

    await expect(revokeTokenAction('token-1')).resolves.toEqual({
      success: false,
      error: 'Failed to revoke token',
    })
    expect(revalidatePath).not.toHaveBeenCalled()
  })
})
