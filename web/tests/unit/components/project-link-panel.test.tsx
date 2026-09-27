import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import {
  ProjectLinkPanel,
  getSelectableProjects,
} from '@/components/project-link-panel'
import { ProjectDto, TenantDto } from '@/application/ports/harness-api-client.port'

vi.mock('next/cache', () => ({ revalidatePath: vi.fn() }))
vi.mock('@/app/actions/project-links', () => ({
  listProjectLinksAction: vi.fn().mockResolvedValue({ data: [] }),
  createProjectLinkAction: vi.fn().mockResolvedValue({ success: true }),
  deleteProjectLinkAction: vi.fn().mockResolvedValue({ success: true }),
}))

describe('ProjectLinkPanel', () => {
  const sampleProject = {
    tenantId: 'tenant-1',
    projectKey: 'catalog',
    name: 'Catalog Service',
  }

  const sampleAllProjects: ProjectDto[] = [
    {
      id: 'p1',
      tenant_id: 'tenant-1',
      key: 'catalog',
      name: 'Catalog Service',
    },
    {
      id: 'p2',
      tenant_id: 'tenant-1',
      key: 'send',
      name: 'Send Service',
    },
    {
      id: 'p3',
      tenant_id: 'tenant-2',
      key: 'billing',
      name: 'Billing API',
    },
  ]

  const sampleTenants: TenantDto[] = [
    { id: 'tenant-1', name: 'Tenant 1' },
    { id: 'tenant-2', name: 'Tenant 2' },
  ]

  it('renders a labelled trigger button and starts closed', () => {
    const markup = renderToStaticMarkup(
      React.createElement(ProjectLinkPanel, {
        project: sampleProject,
        allProjects: sampleAllProjects,
        tenants: sampleTenants,
      })
    )

    expect(markup).toContain('aria-label="Manage links for catalog"')
    expect(markup).toContain('aria-expanded="false"')
    expect(markup).not.toContain('Loading links...')
    expect(markup).not.toContain('No linked projects')
  })

  it('filters out current project and already linked projects from selectable options', () => {
    const existingLinks = [
      {
        project_id: 'p2',
        key: 'send',
        name: 'Send Service',
        tenant_id: 'tenant-1',
      },
    ]

    const selectable = getSelectableProjects(sampleProject, sampleAllProjects, existingLinks)
    expect(selectable).toHaveLength(1)
    expect(selectable[0].key).toBe('billing')
    expect(selectable[0].tenant_id).toBe('tenant-2')
  })
})
