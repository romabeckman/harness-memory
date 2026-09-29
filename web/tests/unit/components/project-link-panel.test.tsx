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

  it('renders correctly when users list is provided', () => {
    const sampleUsers = [
      { id: 'user-1', name: 'Alice', email: 'alice@example.com' },
      { id: 'user-2', name: 'Bob', email: 'bob@example.com' },
    ]

    const markup = renderToStaticMarkup(
      React.createElement(ProjectLinkPanel, {
        project: sampleProject,
        allProjects: sampleAllProjects,
        tenants: sampleTenants,
        users: sampleUsers,
      })
    )

    expect(markup).toContain('aria-label="Manage links for catalog"')
  })

  it('renders full modal dialog structure when opened', () => {
    const markup = renderToStaticMarkup(
      React.createElement(ProjectLinkPanel, {
        project: sampleProject,
        allProjects: sampleAllProjects,
        tenants: sampleTenants,
        initialState: 'loaded',
      })
    )

    // Modal dialog attributes and backdrop
    expect(markup).toContain('role="dialog"')
    expect(markup).toContain('aria-modal="true"')
    expect(markup).toContain('fixed inset-0')
    expect(markup).toContain('Project Links: Catalog Service')
    expect(markup).toContain('aria-label="Close dialog"')

    // Sections
    expect(markup).toContain('Linked Projects (0)')
    expect(markup).toContain('No linked projects')
    expect(markup).toContain('Add New Link')
    expect(markup).toContain('Target Project')
    expect(markup).toContain('Link Project')
    expect(markup).toContain('Close')
  })

  it('renders creator user selector in modal dialog when users are provided', () => {
    const sampleUsers = [
      { id: 'u1', name: 'Admin User', email: 'admin@corp.io' },
      { id: 'u2', name: 'Dev User', email: 'dev@corp.io' },
    ]

    const markup = renderToStaticMarkup(
      React.createElement(ProjectLinkPanel, {
        project: sampleProject,
        allProjects: sampleAllProjects,
        tenants: sampleTenants,
        users: sampleUsers,
        initialState: 'loaded',
      })
    )

    expect(markup).toContain('Created by user (optional)')
    expect(markup).toContain('Admin / System (None)')
    expect(markup).toContain('Admin User (admin@corp.io)')
    expect(markup).toContain('Dev User (dev@corp.io)')
  })

  it('renders loading feedback inside modal dialog when state is loading', () => {
    const markup = renderToStaticMarkup(
      React.createElement(ProjectLinkPanel, {
        project: sampleProject,
        allProjects: sampleAllProjects,
        tenants: sampleTenants,
        initialState: 'loading',
      })
    )

    expect(markup).toContain('role="dialog"')
    expect(markup).toContain('Loading links...')
  })
})
