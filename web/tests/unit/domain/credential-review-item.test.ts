import { describe, expect, it } from 'vitest'
import {
  resolveCredentialReviewItems,
  CredentialReviewItemInput,
} from '@/domain/credential-review-item'

const token = (overrides: Partial<CredentialReviewItemInput['tokens'][number]> = {}) => ({
  id: 'token-1',
  name: 'release-token',
  user_id: 'user-1',
  service_account_id: null,
  scopes: ['memory:read'],
  project_keys: [],
  created_at: '2026-09-27T00:00:00Z',
  expires_at: null,
  revoked_at: null,
  is_active: true,
  ...overrides,
})

describe('resolveCredentialReviewItems', () => {
  it('resolves a User owner by immutable ID', () => {
    const result = resolveCredentialReviewItems(
      { tokens: [token()], users: [{ id: 'user-1', name: 'Ada', email: 'ada@example.com' }], serviceAccounts: [], tenants: [] }
    )

    expect(result).toEqual([
      expect.objectContaining({ ownerName: 'Ada', ownerType: 'User' }),
    ])
    expect(result[0].organizationName).toBeUndefined()
  })

  it('resolves a Service Account owner and organization', () => {
    const result = resolveCredentialReviewItems({
      tokens: [token({ user_id: null, service_account_id: 'sa-1' })],
      users: [],
      serviceAccounts: [{ id: 'sa-1', name: 'release-bot', tenant_id: 'tenant-1' }],
      tenants: [{ id: 'tenant-1', name: 'Platform' }],
    })

    expect(result[0]).toEqual(
      expect.objectContaining({
        ownerName: 'release-bot',
        ownerType: 'Service Account',
        organizationName: 'Platform',
      })
    )
  })

  it('omits unavailable Service Account organization names', () => {
    const result = resolveCredentialReviewItems({
      tokens: [token({ user_id: null, service_account_id: 'sa-1' })],
      users: [],
      serviceAccounts: [{ id: 'sa-1', name: 'release-bot', tenant_id: 'missing-tenant' }],
      tenants: [],
    })

    expect(result[0]).toEqual(
      expect.objectContaining({ ownerName: 'release-bot', ownerType: 'Service Account' })
    )
    expect(result[0].organizationName).toBeUndefined()
  })

  it.each([
    ['no owner', token({ user_id: null, service_account_id: null })],
    ['ambiguous owner', token({ service_account_id: 'sa-1' })],
  ])('rejects a token with %s', (_label, input) => {
    const ambiguous = input.user_id ? { ...input, service_account_id: 'sa-1' } : input

    expect(() =>
      resolveCredentialReviewItems({
        tokens: [ambiguous],
        users: [{ id: 'user-1', name: 'Ada', email: 'ada@example.com' }],
        serviceAccounts: [{ id: 'sa-1', name: 'release-bot', tenant_id: 'tenant-1' }],
        tenants: [],
      })
    ).toThrow('Credential ownership is inconsistent')
  })

  it('rejects an owner absent from the complete catalog', () => {
    expect(() =>
      resolveCredentialReviewItems({
        tokens: [token()],
        users: [],
        serviceAccounts: [],
        tenants: [],
      })
    ).toThrow('Credential ownership is inconsistent')
  })

  it('does not mutate dependencies and freezes the returned projection', () => {
    const sourceToken = token()
    const sourceUser = { id: 'user-1', name: 'Ada', email: 'ada@example.com' }
    const result = resolveCredentialReviewItems({
      tokens: [sourceToken],
      users: [sourceUser],
      serviceAccounts: [],
      tenants: [],
    })

    expect(sourceToken.name).toBe('release-token')
    expect(sourceToken.scopes).toEqual(['memory:read'])
    expect(sourceUser.name).toBe('Ada')
    expect(result[0]).not.toBe(sourceToken)
    expect(Object.isFrozen(result)).toBe(true)
    expect(Object.isFrozen(result[0])).toBe(true)
    expect(Object.isFrozen(result[0].token)).toBe(true)
    expect(Object.isFrozen(result[0].token.scopes)).toBe(true)
  })
})
