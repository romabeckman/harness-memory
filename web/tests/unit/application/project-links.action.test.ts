import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  listProjectLinksAction,
  createProjectLinkAction,
  deleteProjectLinkAction,
} from '@/app/actions/project-links'
import { ClientFactory } from '@/infrastructure/api/client-factory'
import { LinkedProjectDto } from '@/application/ports/harness-api-client.port'

vi.mock('next/cache', () => ({ revalidatePath: vi.fn() }))

describe('project link server actions', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  describe('listProjectLinksAction', () => {
    it('should return data array when API client returns linked projects', async () => {
      const projectA: LinkedProjectDto = {
        project_id: 'proj-a',
        key: 'send',
        name: 'Send Service',
        tenant_id: 'tenant-1',
      }
      const projectB: LinkedProjectDto = {
        project_id: 'proj-b',
        key: 'billing',
        name: 'Billing API',
        tenant_id: 'tenant-2',
      }
      const listProjectLinks = vi.fn().mockResolvedValue([projectA, projectB])
      vi.spyOn(ClientFactory, 'getHarnessClient').mockReturnValue({
        listProjectLinks,
      } as never)

      const result = await listProjectLinksAction('tenant-1', 'catalog')

      expect(result).toEqual({ data: [projectA, projectB] })
      expect(result.error).toBeUndefined()
      expect(listProjectLinks).toHaveBeenCalledWith('tenant-1', 'catalog')
    })

    it('should return error message when API client throws an error', async () => {
      const listProjectLinks = vi.fn().mockRejectedValue(new Error('Network error'))
      vi.spyOn(ClientFactory, 'getHarnessClient').mockReturnValue({
        listProjectLinks,
      } as never)

      const result = await listProjectLinksAction('tenant-1', 'catalog')

      expect(result).toEqual({ error: 'Network error' })
      expect(result.data).toBeUndefined()
    })
  })

  describe('createProjectLinkAction', () => {
    it('should invoke client and trigger revalidatePath when payload is valid', async () => {
      const createProjectLink = vi.fn().mockResolvedValue(undefined)
      vi.spyOn(ClientFactory, 'getHarnessClient').mockReturnValue({
        createProjectLink,
      } as never)
      const { revalidatePath } = await import('next/cache')

      const result = await createProjectLinkAction('tenant-1', 'catalog', {
        target_project_key: 'send',
        target_tenant_id: 'tenant-2',
      })

      expect(result).toEqual({ success: true })
      expect(createProjectLink).toHaveBeenCalledWith('tenant-1', 'catalog', {
        target_project_key: 'send',
        target_tenant_id: 'tenant-2',
      })
      expect(revalidatePath).toHaveBeenCalledWith('/projects')
    })

    it('should forward created_by to client when provided', async () => {
      const createProjectLink = vi.fn().mockResolvedValue(undefined)
      vi.spyOn(ClientFactory, 'getHarnessClient').mockReturnValue({
        createProjectLink,
      } as never)

      const result = await createProjectLinkAction('tenant-1', 'catalog', {
        target_project_key: 'send',
        target_tenant_id: 'tenant-2',
        created_by: 'user-uuid-123',
      })

      expect(result).toEqual({ success: true })
      expect(createProjectLink).toHaveBeenCalledWith('tenant-1', 'catalog', {
        target_project_key: 'send',
        target_tenant_id: 'tenant-2',
        created_by: 'user-uuid-123',
      })
    })

    it('should return error string when backend returns conflict error', async () => {
      const createProjectLink = vi
        .fn()
        .mockRejectedValue(new Error('project link already exists'))
      vi.spyOn(ClientFactory, 'getHarnessClient').mockReturnValue({
        createProjectLink,
      } as never)

      const result = await createProjectLinkAction('tenant-1', 'catalog', {
        target_project_key: 'send',
      })

      expect(result).toEqual({
        success: false,
        error: 'project link already exists',
      })
    })

    it('should validate target_project_key before calling API client', async () => {
      const createProjectLink = vi.fn()
      vi.spyOn(ClientFactory, 'getHarnessClient').mockReturnValue({
        createProjectLink,
      } as never)

      const result = await createProjectLinkAction('tenant-1', 'catalog', {
        target_project_key: '   ',
      })

      expect(result).toEqual({
        success: false,
        error: 'Target project key is required',
      })
      expect(createProjectLink).not.toHaveBeenCalled()
    })
  })

  describe('deleteProjectLinkAction', () => {
    it('should invoke client delete and trigger revalidatePath on success', async () => {
      const deleteProjectLink = vi.fn().mockResolvedValue(undefined)
      vi.spyOn(ClientFactory, 'getHarnessClient').mockReturnValue({
        deleteProjectLink,
      } as never)
      const { revalidatePath } = await import('next/cache')

      const result = await deleteProjectLinkAction('tenant-1', 'catalog', 'send', 'tenant-2')

      expect(result).toEqual({ success: true })
      expect(deleteProjectLink).toHaveBeenCalledWith('tenant-1', 'catalog', 'send', 'tenant-2')
      expect(revalidatePath).toHaveBeenCalledWith('/projects')
    })

    it('should return error string on delete failure', async () => {
      const deleteProjectLink = vi.fn().mockRejectedValue(new Error('Link not found'))
      vi.spyOn(ClientFactory, 'getHarnessClient').mockReturnValue({
        deleteProjectLink,
      } as never)

      const result = await deleteProjectLinkAction('tenant-1', 'catalog', 'send')

      expect(result).toEqual({ success: false, error: 'Link not found' })
    })
  })
})
