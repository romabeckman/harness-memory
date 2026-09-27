import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'

vi.mock('next/navigation', () => ({ usePathname: () => '/service-accounts' }))

import ServiceAccountsPage from '@/app/service-accounts/page'

describe('Service Accounts page', () => {
  it('renders a dedicated global management page with organization filtering', () => {
    const markup = renderToStaticMarkup(React.createElement(ServiceAccountsPage))

    expect(markup).toContain('Service Accounts')
    expect(markup).toContain('Global')
    expect(markup).toContain('Filter by organization')
    expect(markup).toContain('New Service Account')
  })
})
