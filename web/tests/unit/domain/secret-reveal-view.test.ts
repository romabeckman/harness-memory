import { describe, it, expect } from 'vitest'
import { SecretRevealView } from '@/domain/secret-reveal-view'

describe('SecretRevealView', () => {
  it('SCN-09: should format plaintext token with prefix and mark as unacknowledged initially', () => {
    const rawPlaintext = 'hm_live_token_secret_123456789'
    const view = SecretRevealView.create(rawPlaintext)

    expect(view.plaintextToken).toBe(rawPlaintext)
    expect(view.isAcknowledged).toBe(false)
    expect(view.maskedPreview).toBe('hm_live...6789')
  })

  it('should acknowledge view and toggle flag', () => {
    const view = SecretRevealView.create('hm_abc1234567890xyz')
    expect(view.isAcknowledged).toBe(false)
    view.acknowledge()
    expect(view.isAcknowledged).toBe(true)
  })

  it('should reject creation if token does not start with hm_ prefix', () => {
    expect(() => SecretRevealView.create('invalid_raw_token')).toThrow(
      'Plaintext token must start with "hm_"'
    )
  })
})
