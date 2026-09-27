import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import { ProjectTable } from '@/components/project-table'
import { ProjectDto, TenantDto } from '@/application/ports/harness-api-client.port'

vi.mock('next/cache', () => ({ revalidatePath: vi.fn() }))

describe('ProjectTable links integration', () => {
  const sampleProjects: ProjectDto[] = [
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
  ]

  const sampleTenants: TenantDto[] = [
    { id: 'tenant-1', name: 'Tenant 1' },
  ]

  it('renders link management trigger for each project row in the table', () => {
    const markup = renderToStaticMarkup(
      React.createElement(ProjectTable, {
        projects: sampleProjects,
        tenants: sampleTenants,
        onSelectTenant: vi.fn(),
        onRefresh: vi.fn(),
        search: '',
        onSearchChange: vi.fn(),
        page: 0,
        onPageChange: vi.fn(),
        hasMore: false,
      })
    )

    expect(markup).toContain('aria-label="Manage links for catalog"')
    expect(markup).toContain('aria-label="Manage links for send"')
  })
})
