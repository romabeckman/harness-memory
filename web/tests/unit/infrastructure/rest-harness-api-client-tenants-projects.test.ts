import { describe, it, expect, vi, beforeEach } from 'vitest'
import { RestHarnessApiClient } from '@/infrastructure/api/rest-harness-api-client'

describe('RestHarnessApiClient - Tenants and Projects Management', () => {
  const BASE_URL = 'http://api:8080'
  const ADMIN_TOKEN = 'test_admin_token'
  let client: RestHarnessApiClient

  beforeEach(() => {
    vi.restoreAllMocks()
    client = new RestHarnessApiClient(BASE_URL, ADMIN_TOKEN)
  })

  it('should call PATCH /v1/tenants/:id to update tenant', async () => {
    const updated = { id: 't-1', key: 'tenant-1', name: 'New Name', status: 'disabled' }
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => updated,
    } as Response)

    const res = await client.updateTenant('t-1', { name: 'New Name', status: 'disabled' })
    expect(res).toEqual(updated)
    expect(fetchSpy).toHaveBeenCalledWith('http://api:8080/v1/tenants/t-1', {
      method: 'PATCH',
      headers: {
        Authorization: 'Bearer test_admin_token',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ name: 'New Name', status: 'disabled' }),
    })
  })

  it('should call DELETE /v1/tenants/:id to delete tenant', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 204,
      text: async () => '',
    } as Response)

    await client.deleteTenant('t-1')
    expect(fetchSpy).toHaveBeenCalledWith('http://api:8080/v1/tenants/t-1', {
      method: 'DELETE',
      headers: {
        Authorization: 'Bearer test_admin_token',
        'Content-Type': 'application/json',
      },
    })
  })

  it('should call GET /v1/tenants with query, limit and offset', async () => {
    const mockTenants = [{ id: 't-1', key: 'tenant-1', name: 'Tenant 1' }]
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockTenants,
    } as Response)

    const res = await client.listTenants('acme', 20, 40)
    expect(res).toEqual(mockTenants)
    expect(fetchSpy).toHaveBeenCalledWith('http://api:8080/v1/tenants?q=acme&limit=20&offset=40', {
      method: 'GET',
      headers: {
        Authorization: 'Bearer test_admin_token',
        'Content-Type': 'application/json',
      },
    })
  })

  it('should call GET /v1/projects with tenant_id filter, query and pagination', async () => {
    const mockProjects = [{ id: 'p-1', tenant_id: 't-1', key: 'proj-a', name: 'Alpha' }]
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockProjects,
    } as Response)

    const res = await client.listProjects('t-1', 'alpha', 20, 0)
    expect(res).toEqual(mockProjects)
    expect(fetchSpy).toHaveBeenCalledWith(
      'http://api:8080/v1/projects?tenant_id=t-1&q=alpha&limit=20&offset=0',
      {
        method: 'GET',
        headers: {
          Authorization: 'Bearer test_admin_token',
          'Content-Type': 'application/json',
        },
      }
    )
  })

  it('should call POST /v1/projects to create a project', async () => {
    const mockProject = { id: 'p-1', tenant_id: 't-1', key: 'proj-a', name: 'Alpha' }
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => mockProject,
    } as Response)

    const res = await client.createProject({ tenant_id: 't-1', key: 'proj-a', name: 'Alpha' })
    expect(res).toEqual(mockProject)
    expect(fetchSpy).toHaveBeenCalledWith('http://api:8080/v1/projects', {
      method: 'POST',
      headers: {
        Authorization: 'Bearer test_admin_token',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ tenant_id: 't-1', key: 'proj-a', name: 'Alpha' }),
    })
  })

  it('should call DELETE /v1/projects/:key?tenant_id=:id to delete a project', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 204,
      text: async () => '',
    } as Response)

    await client.deleteProject('t-1', 'proj-a')
    expect(fetchSpy).toHaveBeenCalledWith('http://api:8080/v1/projects/proj-a?tenant_id=t-1', {
      method: 'DELETE',
      headers: {
        Authorization: 'Bearer test_admin_token',
        'Content-Type': 'application/json',
      },
    })
  })

  it('should list environments using both tenant and project filters', async () => {
    const environments = [{ id: 'e-1', name: 'staging', type: 'staging' }]
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => environments,
    } as Response)

    const result = await client.listProjectEnvironments({
      tenantId: 'tenant-1',
      projectKey: 'catalog',
    })

    expect(result).toEqual(environments)
    expect(fetchSpy).toHaveBeenCalledWith(
      'http://api:8080/v1/environments?tenant_id=tenant-1&project_key=catalog&limit=100&offset=0',
      {
        method: 'GET',
        headers: {
          Authorization: 'Bearer test_admin_token',
          'Content-Type': 'application/json',
        },
      }
    )
  })

  it('should create an environment through the tenant-scoped administrator route', async () => {
    const environment = { id: 'e-1', name: 'qa-canary', type: 'other' }
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => environment,
    } as Response)

    const result = await client.addProjectEnvironment(
      { tenantId: 'tenant-1', projectKey: 'catalog' },
      'qa-canary'
    )

    expect(result).toEqual(environment)
    expect(fetchSpy).toHaveBeenCalledWith(
      'http://api:8080/v1/projects/catalog/environments?tenant_id=tenant-1',
      {
        method: 'POST',
        headers: {
          Authorization: 'Bearer test_admin_token',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: 'qa-canary' }),
      }
    )
  })
})
