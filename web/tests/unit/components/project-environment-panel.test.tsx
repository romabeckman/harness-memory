import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import { ProjectEnvironmentPanel } from '@/components/project-environment-panel'

vi.mock('next/cache', () => ({ revalidatePath: vi.fn() }))

describe('ProjectEnvironmentPanel', () => {
  it('renders a labelled keyboard control and starts closed', () => {
    const markup = renderToStaticMarkup(
      React.createElement(ProjectEnvironmentPanel, {
        project: { tenantId: 'tenant-1', projectKey: 'catalog' },
      })
    )

    expect(markup).toContain('aria-label="View environments for catalog"')
    expect(markup).toContain('aria-expanded="false"')
    expect(markup).not.toContain('Loading environments')
    expect(markup).not.toContain('name="environment-name"')
  })
})
