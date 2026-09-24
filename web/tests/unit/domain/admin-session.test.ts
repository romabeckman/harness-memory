import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { AdminSession } from '@/domain/admin-session'

describe('AdminSession', () => {
  const MOCK_ADMIN_SECRET = 'secret_master_token_1234567890'

  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('SCN-01: should create valid AdminSession when valid API_ADMIN_TOKEN matches server environment', async () => {
    const now = new Date('2026-09-23T20:00:00Z')
    vi.setSystemTime(now)

    const session = await AdminSession.authenticate(MOCK_ADMIN_SECRET, MOCK_ADMIN_SECRET)

    expect(session).toBeDefined()
    expect(session.isValid()).toBe(true)
    // 2 hours = 7200000 ms
    const expectedExpiry = new Date(now.getTime() + 2 * 60 * 60 * 1000)
    expect(session.expiresAt.toISOString()).toBe(expectedExpiry.toISOString())
  })

  it('SCN-02: should reject AdminSession creation when provided token is incorrect', async () => {
    const wrongToken = 'wrong_token'

    await expect(
      AdminSession.authenticate(wrongToken, MOCK_ADMIN_SECRET)
    ).rejects.toThrow('Invalid administrative credentials')
  })

  it('SCN-03: should invalidate AdminSession when 2 hours of inactivity elapsed', async () => {
    const now = new Date('2026-09-23T20:00:00Z')
    vi.setSystemTime(now)

    const session = await AdminSession.authenticate(MOCK_ADMIN_SECRET, MOCK_ADMIN_SECRET)
    expect(session.isValid()).toBe(true)

    // Advance 2 hours and 1 second
    vi.advanceTimersByTime(2 * 60 * 60 * 1000 + 1000)

    expect(session.isValid()).toBe(false)
  })
})
