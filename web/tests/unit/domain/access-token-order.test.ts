import { describe, it, expect } from 'vitest'
import { AccessTokenOrder } from '@/domain/access-token-order'
import { TokenScope } from '@/domain/token-scope'

describe('AccessTokenOrder', () => {
  const VALID_SA_ID = 'sa-uuid-123'
  const SCOPE_PUBLISH = TokenScope.create('memory:publish')
  const SCOPE_READ = TokenScope.create('memory:read')

  it('SCN-04: should create AccessTokenOrder when required fields and valid scopes are provided', () => {
    const order = AccessTokenOrder.create({
      name: 'github-ci-runner',
      serviceAccountId: VALID_SA_ID,
      scopes: [SCOPE_PUBLISH, SCOPE_READ],
      lifetimeDays: 30,
    })

    expect(order.name).toBe('github-ci-runner')
    expect(order.serviceAccountId).toBe(VALID_SA_ID)
    expect(order.scopes).toHaveLength(2)
    expect(order.lifetimeDays).toBe(30)
  })

  it('SCN-05: should reject AccessTokenOrder creation when no scope is selected', () => {
    expect(() =>
      AccessTokenOrder.create({
        name: 'test-token',
        serviceAccountId: VALID_SA_ID,
        scopes: [],
      })
    ).toThrow('At least one scope must be selected')
  })

  it('should reject AccessTokenOrder when name is empty', () => {
    expect(() =>
      AccessTokenOrder.create({
        name: '   ',
        serviceAccountId: VALID_SA_ID,
        scopes: [SCOPE_READ],
      })
    ).toThrow('Token name cannot be empty')
  })

  it('SCN-06: should allow null/undefined expiration for Service Account token order', () => {
    const order = AccessTokenOrder.create({
      name: 'permanent-ci-token',
      serviceAccountId: VALID_SA_ID,
      scopes: [SCOPE_PUBLISH],
    })

    expect(order.lifetimeDays).toBeUndefined()
    expect(order.calculateExpiresAt(new Date('2026-09-23T20:00:00Z'))).toBeNull()
  })

  it('should calculate correct expiresAt ISO string when lifetimeDays is specified', () => {
    const order = AccessTokenOrder.create({
      name: 'temp-token',
      serviceAccountId: VALID_SA_ID,
      scopes: [SCOPE_READ],
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
        lifetimeDays: 91,
      })
    ).toThrow('Lifetime cannot exceed 90 days')
  })
})
