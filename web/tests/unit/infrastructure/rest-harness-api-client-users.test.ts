import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RestHarnessApiClient } from '@/infrastructure/api/rest-harness-api-client'

describe('RestHarnessApiClient user management', () => {
  const client = new RestHarnessApiClient('http://api:8080', 'test_admin_token')

  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('lists global users with search and pagination', async () => {
    const users = [{ id: 'user-1', name: 'Ada', email: 'ada@example.com' }]
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => users,
    } as Response)

    await expect(client.listUsers('ada', 20, 40)).resolves.toEqual(users)
    expect(fetchSpy).toHaveBeenCalledWith('http://api:8080/v1/users?q=ada&limit=20&offset=40', {
      method: 'GET',
      headers: {
        Authorization: 'Bearer test_admin_token',
        'Content-Type': 'application/json',
      },
    })
  })

  it('maps user CRUD to existing REST contracts', async () => {
    const user = { id: 'user-1', name: 'Ada', email: 'ada@example.com' }
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => user } as Response)
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => user } as Response)
      .mockResolvedValueOnce({ ok: true, status: 204 } as Response)

    await expect(client.createUser({ name: 'Ada', email: 'ada@example.com' })).resolves.toEqual(user)
    await expect(client.updateUser('user-1', { name: 'Ada Lovelace' })).resolves.toEqual(user)
    await expect(client.deleteUser('user-1')).resolves.toBeUndefined()

    expect(fetchSpy).toHaveBeenNthCalledWith(1, 'http://api:8080/v1/users', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ name: 'Ada', email: 'ada@example.com' }),
    }))
    expect(fetchSpy).toHaveBeenNthCalledWith(2, 'http://api:8080/v1/users/user-1', expect.objectContaining({
      method: 'PATCH',
      body: JSON.stringify({ name: 'Ada Lovelace' }),
    }))
    expect(fetchSpy).toHaveBeenNthCalledWith(3, 'http://api:8080/v1/users/user-1', expect.objectContaining({
      method: 'DELETE',
    }))
  })

  it('sanitizes authorization failures without exposing credentials or response bodies', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 403,
      text: async () => 'API_ADMIN_TOKEN=secret backend details',
    } as Response)

    await expect(client.listUsers()).rejects.toThrow(
      'Harness API authorization failed: unauthorized administrative request'
    )
  })
})
