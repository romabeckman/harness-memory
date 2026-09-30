import { beforeEach, describe, expect, it, vi } from 'vitest'
import { listAllTenantsAction } from '@/app/actions/tenants'
import { ClientFactory } from '@/infrastructure/api/client-factory'

describe('tenant retrieval for service-account management', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('retrieves organizations beyond the first 100 records', async () => {
    const firstPage = Array.from({ length: 100 }, (_, index) => ({
      id: `tenant-${index}`,
      name: `Tenant ${index}`,
      status: 'active' as const,
    }))
    const finalPage = [{ id: 'tenant-100', name: 'Tenant 100', status: 'active' as const }]
    const listTenants = vi.fn().mockResolvedValueOnce(firstPage).mockResolvedValueOnce(finalPage)
    vi.spyOn(ClientFactory, 'getHarnessClient').mockReturnValue({ listTenants } as never)

    const result = await listAllTenantsAction()

    expect(result.data).toHaveLength(101)
    expect(result.data?.[100].name).toBe('Tenant 100')
    expect(listTenants).toHaveBeenNthCalledWith(2, undefined, 100, 100)
  })
})
