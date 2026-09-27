import { beforeEach, describe, expect, it, vi } from 'vitest'
import { listTenantProjectsAction } from '@/app/actions/projects'
import { ClientFactory } from '@/infrastructure/api/client-factory'

vi.mock('next/cache', () => ({ revalidatePath: vi.fn() }))

describe('tenant project listing for token grants', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('loads projects beyond the first page', async () => {
    const firstPage = Array.from({ length: 100 }, (_, index) => ({ id: `${index}`, key: `project-${index}` }))
    const finalPage = [{ id: '100', key: 'project-100' }]
    const listProjects = vi.fn().mockResolvedValueOnce(firstPage).mockResolvedValueOnce(finalPage)
    vi.spyOn(ClientFactory, 'getHarnessClient').mockReturnValue({ listProjects } as never)

    const result = await listTenantProjectsAction('user-1')

    expect(result.data).toHaveLength(101)
    expect(result.data?.[100].key).toBe('project-100')
    expect(listProjects).toHaveBeenNthCalledWith(2, 'user-1', undefined, 100, 100)
  })
})
