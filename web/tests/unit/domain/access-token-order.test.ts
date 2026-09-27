import { describe, it, expect } from 'vitest'
import { AccessTokenOrder } from '@/domain/access-token-order'
import { TokenScope } from '@/domain/token-scope'

describe('AccessTokenOrder', () => {
  const VALID_SA_ID = 'sa-uuid-123'
  const SCOPE_PUBLISH = TokenScope.create('memory:publish')
  const SCOPE_READ = TokenScope.create('memory:read')

  it('preserves an immutable service-account owner selected from a row', () => {
    const owner = {
      kind: 'service-account' as const,
      id: VALID_SA_ID,
      name: 'Release bot',
      tenantId: 'tenant-1',
      tenantName: 'Platform',
    }

    const order = AccessTokenOrder.create({
      name: 'release-token',
      owner,
      scopes: [SCOPE_READ],
      projectKeys: [],
      lifetimeDays: 30,
    })

    owner.name = 'Changed outside order'
    owner.tenantId = 'tenant-2'

    expect(order.owner).toEqual({
      kind: 'service-account',
      id: VALID_SA_ID,
      name: 'Release bot',
      tenantId: 'tenant-1',
      tenantName: 'Platform',
    })
    expect(Object.isFrozen(order.owner)).toBe(true)
  })

  it('rejects a service-account owner with a blank ID', () => {
    expect(() =>
      AccessTokenOrder.create({
        name: 'invalid-owner',
        owner: {
          kind: 'service-account',
          id: '   ',
          name: 'Release bot',
          tenantId: 'tenant-1',
          tenantName: 'Platform',
        },
        scopes: [SCOPE_READ],
        projectKeys: [],
        lifetimeDays: 30,
      })
    ).toThrow('Token owner ID cannot be empty')
  })

  it('rejects a service-account owner without complete organization context', () => {
    expect(() =>
      AccessTokenOrder.create({
        name: 'invalid-owner-context',
        owner: {
          kind: 'service-account',
          id: VALID_SA_ID,
          name: 'Release bot',
          tenantId: '   ',
          tenantName: 'Platform',
        },
        scopes: [SCOPE_READ],
        projectKeys: [],
        lifetimeDays: 30,
      })
    ).toThrow('Service-account organization ID cannot be empty')
  })

  it.each([
    { lifetimeDays: 30, expected: '2026-10-23T20:00:00.000Z' },
    { lifetimeDays: 90, expected: '2026-12-22T20:00:00.000Z' },
    { lifetimeDays: undefined, expected: null },
  ])('supports service-account lifetime $lifetimeDays', ({ lifetimeDays, expected }) => {
    const order = AccessTokenOrder.create({
      name: 'lifetime-token',
      owner: {
        kind: 'service-account',
        id: VALID_SA_ID,
        name: 'Release bot',
        tenantId: 'tenant-1',
        tenantName: 'Platform',
      },
      scopes: [SCOPE_READ],
      projectKeys: [],
      lifetimeDays,
    })

    expect(order.calculateExpiresAt(new Date('2026-09-23T20:00:00Z'))).toBe(expected)
  })

  it('SCN-04: should create AccessTokenOrder when required fields and valid scopes are provided', () => {
    const order = AccessTokenOrder.create({
      name: 'github-ci-runner',
      serviceAccountId: VALID_SA_ID,
      scopes: [SCOPE_PUBLISH, SCOPE_READ],
      projectKeys: ['catalog', 'billing'],
      lifetimeDays: 30,
    })

    expect(order.name).toBe('github-ci-runner')
    expect(order.serviceAccountId).toBe(VALID_SA_ID)
    expect(order.scopes).toHaveLength(2)
    expect(order.projectKeys).toEqual(['catalog', 'billing'])
    expect(order.lifetimeDays).toBe(30)
  })

  it('SCN-05: should reject AccessTokenOrder creation when no scope is selected', () => {
    expect(() =>
      AccessTokenOrder.create({
        name: 'test-token',
        serviceAccountId: VALID_SA_ID,
        scopes: [],
        projectKeys: ['catalog'],
      })
    ).toThrow('At least one scope must be selected')
  })

  it('should reject AccessTokenOrder when name is empty', () => {
    expect(() =>
      AccessTokenOrder.create({
        name: '   ',
        serviceAccountId: VALID_SA_ID,
        scopes: [SCOPE_READ],
        projectKeys: ['catalog'],
      })
    ).toThrow('Token name cannot be empty')
  })

  it('should allow an empty project list for global access but reject blank keys', () => {
    expect(
      AccessTokenOrder.create({
        name: 'test-token',
        serviceAccountId: VALID_SA_ID,
        scopes: [SCOPE_READ],
        projectKeys: [],
      }).projectKeys
    ).toEqual([])

    expect(() =>
      AccessTokenOrder.create({
        name: 'test-token',
        serviceAccountId: VALID_SA_ID,
        scopes: [SCOPE_READ],
        projectKeys: ['   ', ''],
      })
    ).toThrow('At least one project must be selected')
  })

  it('should deduplicate and trim projectKeys', () => {
    const order = AccessTokenOrder.create({
      name: 'test-token',
      serviceAccountId: VALID_SA_ID,
      scopes: [SCOPE_READ],
      projectKeys: ['  catalog ', 'catalog', 'billing  '],
    })

    expect(order.projectKeys).toEqual(['catalog', 'billing'])
  })

  it('SCN-06: should allow null/undefined expiration for Service Account token order', () => {
    const order = AccessTokenOrder.create({
      name: 'permanent-ci-token',
      serviceAccountId: VALID_SA_ID,
      scopes: [SCOPE_PUBLISH],
      projectKeys: ['catalog'],
    })

    expect(order.lifetimeDays).toBeUndefined()
    expect(order.calculateExpiresAt(new Date('2026-09-23T20:00:00Z'))).toBeNull()
  })

  it('should calculate correct expiresAt ISO string when lifetimeDays is specified', () => {
    const order = AccessTokenOrder.create({
      name: 'temp-token',
      serviceAccountId: VALID_SA_ID,
      scopes: [SCOPE_READ],
      projectKeys: ['catalog'],
      lifetimeDays: 90,
    })

    const base = new Date('2026-09-23T20:00:00Z')
    const expiresAt = order.calculateExpiresAt(base)
    expect(expiresAt).toBeDefined()
    const expected = new Date(base.getTime() + 90 * 24 * 60 * 60 * 1000).toISOString()
    expect(expiresAt).toBe(expected)
  })

  it('should reject lifetimeDays exceeding 90 days', () => {
    expect(() =>
      AccessTokenOrder.create({
        name: 'invalid-lifetime',
        serviceAccountId: VALID_SA_ID,
        scopes: [SCOPE_READ],
        projectKeys: ['catalog'],
        lifetimeDays: 91,
      })
    ).toThrow('Lifetime cannot exceed 90 days')
  })
})
