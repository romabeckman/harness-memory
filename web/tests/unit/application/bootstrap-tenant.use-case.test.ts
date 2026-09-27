import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BootstrapTenantUseCase } from '@/application/use-cases/bootstrap-tenant.use-case'
import { HarnessApiClientPort, TenantDto, ServiceAccountDto } from '@/application/ports/harness-api-client.port'

describe('BootstrapTenantUseCase', () => {
  let mockClient: HarnessApiClientPort
  let useCase: BootstrapTenantUseCase

  beforeEach(() => {
    mockClient = {
      listUsers: vi.fn(),
      createUser: vi.fn(),
      updateUser: vi.fn(),
      deleteUser: vi.fn(),
      listTenants: vi.fn(),
      createTenant: vi.fn(),
      listServiceAccounts: vi.fn(),
      createServiceAccount: vi.fn(),
      updateServiceAccount: vi.fn(),
      deleteServiceAccount: vi.fn(),
      listTokens: vi.fn(),
      createToken: vi.fn(),
      revokeToken: vi.fn(),
    }
    useCase = new BootstrapTenantUseCase(mockClient)
  })

  it('SCN-10: should auto-provision default tenant and service account when tenant catalog is empty', async () => {
    vi.mocked(mockClient.listTenants).mockResolvedValueOnce([])
    vi.mocked(mockClient.createTenant).mockResolvedValueOnce({
      id: 'new-tenant-id-123',
      name: 'default',
    })
    vi.mocked(mockClient.listServiceAccounts).mockResolvedValueOnce([])
    vi.mocked(mockClient.createServiceAccount).mockResolvedValueOnce({
      id: 'new-sa-id-456',
      tenant_id: 'new-tenant-id-123',
      name: 'default-automation',
    })

    const result = await useCase.execute()

    expect(mockClient.listTenants).toHaveBeenCalled()
    expect(mockClient.createTenant).toHaveBeenCalledWith({ name: 'default' })
    expect(mockClient.createServiceAccount).toHaveBeenCalledWith({
      tenant_id: 'new-tenant-id-123',
      name: 'default-automation',
    })
    expect(result).toEqual({
      tenantId: 'new-tenant-id-123',
      tenantName: 'default',
      serviceAccountId: 'new-sa-id-456',
      serviceAccountName: 'default-automation',
      isNewBootstrap: true,
    })
  })

  it('SCN-11: should reuse existing tenant and existing service account when tenant catalog is not empty', async () => {
    const existingTenant: TenantDto = { id: 'existing-tenant-999', name: 'acme-corp' }
    const existingSa: ServiceAccountDto = {
      id: 'existing-sa-888',
      tenant_id: 'existing-tenant-999',
      name: 'ci-runner',
    }

    vi.mocked(mockClient.listTenants).mockResolvedValueOnce([existingTenant])
    vi.mocked(mockClient.listServiceAccounts).mockResolvedValueOnce([existingSa])

    const result = await useCase.execute()

    expect(mockClient.createTenant).not.toHaveBeenCalled()
    expect(mockClient.createServiceAccount).not.toHaveBeenCalled()
    expect(result).toEqual({
      tenantId: 'existing-tenant-999',
      tenantName: 'acme-corp',
      serviceAccountId: 'existing-sa-888',
      serviceAccountName: 'ci-runner',
      isNewBootstrap: false,
    })
  })

  it('should create service account if tenant exists but has no service accounts', async () => {
    const existingTenant: TenantDto = { id: 'existing-tenant-999', name: 'acme-corp' }
    vi.mocked(mockClient.listTenants).mockResolvedValueOnce([existingTenant])
    vi.mocked(mockClient.listServiceAccounts).mockResolvedValueOnce([])
    vi.mocked(mockClient.createServiceAccount).mockResolvedValueOnce({
      id: 'created-sa-111',
      tenant_id: 'existing-tenant-999',
      name: 'default-automation',
    })

    const result = await useCase.execute()

    expect(mockClient.createTenant).not.toHaveBeenCalled()
    expect(mockClient.createServiceAccount).toHaveBeenCalledWith({
      tenant_id: 'existing-tenant-999',
      name: 'default-automation',
    })
    expect(result.serviceAccountId).toBe('created-sa-111')
  })
})
