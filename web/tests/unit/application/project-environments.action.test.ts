import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  addProjectEnvironmentAction,
  listProjectEnvironmentsAction,
} from '@/app/actions/projects'
import { ClientFactory } from '@/infrastructure/api/client-factory'

vi.mock('next/cache', () => ({ revalidatePath: vi.fn() }))

describe('project environment actions', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('lists environments with the tenant and project reference', async () => {
    const environments = [{ id: 'env-1', name: 'staging', type: 'staging' as const }]
    const listProjectEnvironments = vi.fn().mockResolvedValue(environments)
    vi.spyOn(ClientFactory, 'getHarnessClient').mockReturnValue(
      { listProjectEnvironments } as never
    )

    const result = await listProjectEnvironmentsAction({
      tenantId: 'tenant-1',
      projectKey: 'catalog',
    })

    expect(result.data).toEqual(environments)
    expect(listProjectEnvironments).toHaveBeenCalledWith({
      tenantId: 'tenant-1',
      projectKey: 'catalog',
    })
  })

  it('trims environment names before submitting and refreshes Projects', async () => {
    const created = { id: 'env-1', name: 'qa-canary', type: 'other' as const }
    const addProjectEnvironment = vi.fn().mockResolvedValue(created)
    vi.spyOn(ClientFactory, 'getHarnessClient').mockReturnValue(
      { addProjectEnvironment } as never
    )
    const { revalidatePath } = await import('next/cache')

    const result = await addProjectEnvironmentAction(
      { tenantId: 'tenant-1', projectKey: 'catalog' },
      '  qa-canary  '
    )

    expect(result).toEqual({ success: true, data: created })
    expect(addProjectEnvironment).toHaveBeenCalledWith(
      { tenantId: 'tenant-1', projectKey: 'catalog' },
      'qa-canary'
    )
    expect(revalidatePath).toHaveBeenCalledWith('/projects')
  })

  it.each(['', ' '.repeat(2), 'x'.repeat(65), 'qa canary', 'qa.canary'])(
    'rejects invalid environment name %j before making an API request',
    async (name) => {
      const addProjectEnvironment = vi.fn()
      vi.spyOn(ClientFactory, 'getHarnessClient').mockReturnValue(
        { addProjectEnvironment } as never
      )

      const result = await addProjectEnvironmentAction(
        { tenantId: 'tenant-1', projectKey: 'catalog' },
        name
      )

      expect(result.success).toBe(false)
      expect(addProjectEnvironment).not.toHaveBeenCalled()
    }
  )

  it('keeps API create failures visible to the panel caller', async () => {
    const addProjectEnvironment = vi.fn().mockRejectedValue(new Error('conflict'))
    vi.spyOn(ClientFactory, 'getHarnessClient').mockReturnValue(
      { addProjectEnvironment } as never
    )

    const result = await addProjectEnvironmentAction(
      { tenantId: 'tenant-1', projectKey: 'catalog' },
      'staging'
    )

    expect(result).toEqual({ success: false, error: 'conflict' })
  })
})
