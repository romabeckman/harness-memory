import { describe, it, expect, vi, beforeEach } from 'vitest'
import { RestHarnessApiClient } from '@/infrastructure/api/rest-harness-api-client'

describe('RestHarnessApiClient', () => {
  const BASE_URL = 'http://api:8080'
  const ADMIN_TOKEN = 'test_admin_token'
  let client: RestHarnessApiClient

  beforeEach(() => {
    vi.restoreAllMocks()
    client = new RestHarnessApiClient(BASE_URL, ADMIN_TOKEN)
  })

  it('SCN-13: should forward API_ADMIN_TOKEN in Bearer header and return parsed data', async () => {
    const mockTenants = [{ id: 'tenant-1', name: 'default' }]
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockTenants,
    } as Response)

    const result = await client.listTenants()

    expect(fetchSpy).toHaveBeenCalledWith('http://api:8080/v1/tenants', {
      method: 'GET',
      headers: {
        Authorization: 'Bearer test_admin_token',
        'Content-Type': 'application/json',
      },
    })
    expect(result).toEqual(mockTenants)
  })

  it('SCN-14: should map 401/403 API responses to clean sanitized BFF application errors', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      text: async () => '{"detail": "invalid_token"}',
    } as Response)

    await expect(client.listTenants()).rejects.toThrow(
      'Harness API authorization failed: unauthorized administrative request'
    )
  })

  it('should post and return created token payload', async () => {
    const mockCreated = {
      id: 'token-123',
      name: 'ci-runner',
      token: 'hm_secret_key_abc',
      service_account_id: 'sa-456',
      scopes: ['memory:publish'],
      created_at: '2026-09-23T20:00:00Z',
    }

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => mockCreated,
    } as Response)

    const result = await client.createToken({
      name: 'ci-runner',
      service_account_id: 'sa-456',
      scopes: ['memory:publish'],
    })

    expect(result).toEqual(mockCreated)
  })

  it('should send DELETE request to revoke token', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 204,
      text: async () => '',
    } as Response)

    await client.revokeToken('token-123')

    expect(fetchSpy).toHaveBeenCalledWith('http://api:8080/v1/tokens/token-123', {
      method: 'DELETE',
      headers: {
        Authorization: 'Bearer test_admin_token',
        'Content-Type': 'application/json',
      },
    })
  })

  it('should list bounded token pages with limit and offset', async () => {
    const tokens = [{ id: 'token-123', name: 'release-token' }]
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => tokens,
    } as Response)

    await expect(client.listTokens(20, 40)).resolves.toEqual(tokens)

    expect(fetchSpy).toHaveBeenCalledWith('http://api:8080/v1/tokens?limit=20&offset=40', {
      method: 'GET',
      headers: {
        Authorization: 'Bearer test_admin_token',
        'Content-Type': 'application/json',
      },
    })
  })
})
