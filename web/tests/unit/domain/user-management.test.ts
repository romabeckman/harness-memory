import { describe, expect, it } from 'vitest'
import { AccessTokenOrder } from '@/domain/access-token-order'
import { TokenScope } from '@/domain/token-scope'

describe('user-owned access token orders', () => {
  const owner = { kind: 'user' as const, id: 'user-ada', name: 'Ada Lovelace' }
  const scope = TokenScope.create('memory:read')

  it('creates a finite 30-day order for an immutable user owner', () => {
    const order = AccessTokenOrder.create({
      owner,
      name: 'local-agent',
      scopes: [scope],
      projectKeys: [],
      lifetimeDays: 30,
    })

    expect(order.owner).toEqual(owner)
    expect(order.calculateExpiresAt(new Date('2026-09-26T00:00:00Z'))).toBe(
      '2026-10-26T00:00:00.000Z'
    )
    expect(order.serviceAccountId).toBeUndefined()
    expect(Object.isFrozen(order.owner)).toBe(true)
  })

  it('accepts 90 days and rejects absent or unsupported user lifetimes', () => {
    expect(
      AccessTokenOrder.create({
        owner,
        name: 'long-lived-agent',
        scopes: [scope],
        projectKeys: [],
        lifetimeDays: 90,
      }).lifetimeDays
    ).toBe(90)

    expect(() =>
      AccessTokenOrder.create({
        owner,
        name: 'missing-lifetime',
        scopes: [scope],
        projectKeys: [],
      })
    ).toThrow('User token lifetime must be 30, 90, or 365 days')

    expect(() =>
      AccessTokenOrder.create({
        owner,
        name: 'unsupported-lifetime',
        scopes: [scope],
        projectKeys: [],
        lifetimeDays: 31,
      })
    ).toThrow('User token lifetime must be 30, 90, or 365 days')
  })

  it('preserves service-account order compatibility', () => {
    const order = AccessTokenOrder.create({
      serviceAccountId: 'service-account-1',
      name: 'permanent-agent',
      scopes: [scope],
      projectKeys: [],
    })

    expect(order.serviceAccountId).toBe('service-account-1')
    expect(order.owner.kind).toBe('service-account')
    expect(order.calculateExpiresAt()).toBeNull()
  })
})
