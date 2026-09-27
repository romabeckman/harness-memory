import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RestHarnessApiClient } from '@/infrastructure/api/rest-harness-api-client'
import { LinkedProjectDto } from '@/application/ports/harness-api-client.port'

describe('RestHarnessApiClient project links', () => {
  const client = new RestHarnessApiClient('http://api:8080', 'test_admin_token')

  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('should send authenticated GET request to /v1/projects/{key}/links', async () => {
    const linkedProjects: LinkedProjectDto[] = [
      {
        project_id: 'proj-1',
        key: 'send',
        name: 'Send Service',
        tenant_id: 'tenant-1',
      },
    ]

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => linkedProjects,
    } as Response)

    const result = await client.listProjectLinks('tenant-1', 'catalog')
    expect(result).toEqual(linkedProjects)
    expect(fetchSpy).toHaveBeenCalledWith(
      'http://api:8080/v1/projects/catalog/links?tenant_id=tenant-1',
      {
        method: 'GET',
        headers: {
          Authorization: 'Bearer test_admin_token',
          'Content-Type': 'application/json',
        },
      }
    )
  })

  it('should send POST request with JSON payload to /v1/projects/{key}/links', async () => {
    const payload = {
      target_project_key: 'send',
      target_tenant_id: 'tenant-2',
    }

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => ({
        id: 'link-1',
        linked_project: {
          project_id: 'proj-2',
          key: 'send',
          name: 'Send Service',
          tenant_id: 'tenant-2',
        },
        created_at: '2026-09-27T00:00:00Z',
      }),
    } as Response)

    await client.createProjectLink('tenant-1', 'catalog', payload)
    expect(fetchSpy).toHaveBeenCalledWith(
      'http://api:8080/v1/projects/catalog/links?tenant_id=tenant-1',
      {
        method: 'POST',
        headers: {
          Authorization: 'Bearer test_admin_token',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      }
    )
  })

  it('should throw descriptive error when server returns 409 Conflict', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 409,
      json: async () => ({ detail: 'project link already exists' }),
    } as Response)

    await expect(
      client.createProjectLink('tenant-1', 'catalog', { target_project_key: 'send' })
    ).rejects.toThrow('project link already exists')
  })

  it('should send DELETE request to /v1/projects/{key}/links/{targetKey}', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 204,
    } as Response)

    await client.deleteProjectLink('tenant-1', 'catalog', 'send', 'tenant-2')
    expect(fetchSpy).toHaveBeenCalledWith(
      'http://api:8080/v1/projects/catalog/links/send?tenant_id=tenant-1&target_tenant_id=tenant-2',
      {
        method: 'DELETE',
        headers: {
          Authorization: 'Bearer test_admin_token',
          'Content-Type': 'application/json',
        },
      }
    )
  })

  it('should send DELETE request without target_tenant_id when omitted', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 204,
    } as Response)

    await client.deleteProjectLink('tenant-1', 'catalog', 'send')
    expect(fetchSpy).toHaveBeenCalledWith(
      'http://api:8080/v1/projects/catalog/links/send?tenant_id=tenant-1',
      {
        method: 'DELETE',
        headers: {
          Authorization: 'Bearer test_admin_token',
          'Content-Type': 'application/json',
        },
      }
    )
  })
})
