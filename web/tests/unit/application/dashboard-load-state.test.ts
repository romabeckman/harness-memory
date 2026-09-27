import { describe, expect, it } from 'vitest'
import { nextDashboardLoadState } from '@/application/dashboard-load-state'

const previous = {
  data: { credentials: [{ token: { id: 'revoked-token' } }], hasMore: false, page: 0 },
  error: null,
}

describe('dashboard refresh state', () => {
  it('removes stale credential rows after a failed refresh', () => {
    const state = nextDashboardLoadState(previous, { error: 'Failed to load credential review data' })
    expect(state.data).toBeNull()
    expect(state.error).toBe('Failed to load credential review data')
  })

  it('does not show a revoked credential when deletion succeeds but reload fails', () => {
    const state = nextDashboardLoadState(previous, { error: 'Failed to load credential review data' })
    expect(state.data?.credentials).toBeUndefined()
  })

  it('removes a revoked row only when refreshed data succeeds', () => {
    const state = nextDashboardLoadState(previous, {
      data: { credentials: [], hasMore: false, page: 0 },
    })
    expect(state.data?.credentials).toEqual([])
    expect(state.error).toBeNull()
  })
})
