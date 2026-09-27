import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { TokenList } from '@/components/token-list'

const baseToken = {
  id: 'token-1',
  name: 'release-token',
  scopes: ['memory:read'],
  project_keys: [],
  created_at: '2026-09-27T00:00:00Z',
  expires_at: null,
  revoked_at: null,
  is_active: true,
}

describe('TokenList', () => {
  it('renders owner name, owner type, and available organization', () => {
    const markup = renderToStaticMarkup(
      React.createElement(TokenList, {
        credentials: [
          { token: { ...baseToken, user_id: 'user-1', service_account_id: null }, ownerName: 'Ada', ownerType: 'User' },
          {
            token: { ...baseToken, id: 'token-2', user_id: null, service_account_id: 'sa-1' },
            ownerName: 'release-bot',
            ownerType: 'Service Account',
            organizationName: 'Platform',
          },
        ],
        onTokenRevoked: () => undefined,
      })
    )

    expect(markup).toContain('Ada')
    expect(markup).toContain('User')
    expect(markup).toContain('release-bot')
    expect(markup).toContain('Service Account')
    expect(markup).toContain('Platform')
  })

  it('omits unavailable organization lines and issuance controls', () => {
    const markup = renderToStaticMarkup(
      React.createElement(TokenList, {
        credentials: [
          {
            token: { ...baseToken, user_id: null, service_account_id: 'sa-1' },
            ownerName: 'release-bot',
            ownerType: 'Service Account',
          },
        ],
        onTokenRevoked: () => undefined,
      })
    )

    expect(markup).toContain('release-bot')
    expect(markup).toContain('Service Account')
    expect(markup).not.toContain('undefined')
    expect(markup).not.toContain('New Token')
    expect(markup).toContain('Revoke token')
  })
})
