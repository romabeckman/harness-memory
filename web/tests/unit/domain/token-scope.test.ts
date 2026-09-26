import { describe, it, expect } from 'vitest'
import { TokenScope } from '@/domain/token-scope'

describe('TokenScope', () => {
  it('SCN-07: should accept only recognized platform scopes', () => {
    expect(TokenScope.isValid('memory:read')).toBe(true)
    expect(TokenScope.isValid('memory:publish')).toBe(true)
    expect(TokenScope.isValid('memory:impact')).toBe(true)

    const scopeRead = TokenScope.create('memory:read')
    expect(scopeRead.value).toBe('memory:read')
  })

  it('SCN-08: should reject unauthorized or malformed scope strings', () => {
    expect(TokenScope.isValid('admin:all')).toBe(false)
    expect(TokenScope.isValid('memory:delete')).toBe(false)
    expect(TokenScope.isValid('')).toBe(false)

    expect(() => TokenScope.create('invalid_scope')).toThrow(
      'Invalid scope: "invalid_scope". Allowed scopes: memory:read, memory:publish, memory:impact'
    )
  })
})
