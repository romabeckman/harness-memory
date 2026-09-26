import { describe, it, expect } from 'vitest'
import { SessionManager } from '@/infrastructure/auth/session-manager'

describe('SessionManager', () => {
  const SECRET = 'test_session_secret_at_least_32_characters_long_12345678'
  const manager = new SessionManager(SECRET)

  it('SCN-15: should sign and verify session token preserving sessionId', async () => {
    const sessionId = 'uuid-session-12345'
    const token = await manager.signSession(sessionId)

    expect(typeof token).toBe('string')
    expect(token.split('.')).toHaveLength(3) // JWT format

    const verified = await manager.verifySession(token)
    expect(verified).not.toBeNull()
    expect(verified?.sessionId).toBe(sessionId)
  })

  it('should return null for tampered or invalid token', async () => {
    const invalidToken = 'invalid.jwt.token'
    const result = await manager.verifySession(invalidToken)
    expect(result).toBeNull()
  })

  it('should provide standard secure cookie options matching SCN-15', () => {
    const options = manager.getCookieOptions()
    expect(options.httpOnly).toBe(true)
    expect(options.sameSite).toBe('strict')
    expect(options.path).toBe('/')
    expect(options.maxAge).toBe(7200) // 2 hours in seconds
  })
})
