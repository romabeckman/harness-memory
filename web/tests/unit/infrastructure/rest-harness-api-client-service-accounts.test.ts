import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RestHarnessApiClient } from '@/infrastructure/api/rest-harness-api-client'

describe('RestHarnessApiClient service-account management', () => {
  const client = new RestHarnessApiClient('http://api:8080', 'test_admin_token')

  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('lists global and organization-filtered pages through the REST contract', async () => {
    const accounts = [{ id: 'sa-1', tenant_id: 'tenant-1', name: 'Release bot' }]
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => accounts,
    } as Response)

    await expect(client.listServiceAccounts({ limit: 20, offset: 20 })).resolves.toEqual(accounts)
    await expect(
      client.listServiceAccounts({ tenantId: 'tenant/1', limit: 20, offset: 0 })
    ).resolves.toEqual(accounts)

    expect(fetchSpy).toHaveBeenNthCalledWith(
      1,
      'http://api:8080/v1/service-accounts?limit=20&offset=20',
      expect.objectContaining({ method: 'GET' })
    )
    expect(fetchSpy).toHaveBeenNthCalledWith(
      2,
      'http://api:8080/v1/service-accounts?tenant_id=tenant%2F1&limit=20&offset=0',
      expect.objectContaining({ method: 'GET' })
    )
  })

  it('maps create, name-only update, and delete operations', async () => {
    const account = { id: 'sa-1', tenant_id: 'tenant-1', name: 'Release bot' }
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => account } as Response)
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => account } as Response)
      .mockResolvedValueOnce({ ok: true, status: 204 } as Response)

    await expect(
      client.createServiceAccount({ name: 'Release bot', tenant_id: 'tenant-1' })
    ).resolves.toEqual(account)
    await expect(client.updateServiceAccount('sa-1', { name: 'Release bot 2' })).resolves.toEqual(
      account
    )
    await expect(client.deleteServiceAccount('sa-1')).resolves.toBeUndefined()

    expect(fetchSpy).toHaveBeenNthCalledWith(
      1,
      'http://api:8080/v1/service-accounts',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ name: 'Release bot', tenant_id: 'tenant-1' }),
      })
    )
    expect(fetchSpy).toHaveBeenNthCalledWith(
      2,
      'http://api:8080/v1/service-accounts/sa-1',
      expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ name: 'Release bot 2' }) })
    )
    expect(fetchSpy).toHaveBeenNthCalledWith(
      3,
      'http://api:8080/v1/service-accounts/sa-1',
      expect.objectContaining({ method: 'DELETE' })
    )
  })

  it('does not expose response bodies from authorization failures', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 401,
      text: async () => 'API_ADMIN_TOKEN=secret request headers',
    } as Response)

    await expect(client.listServiceAccounts({ limit: 20, offset: 0 })).rejects.toThrow(
      'Harness API authorization failed: unauthorized administrative request'
    )
  })
})
