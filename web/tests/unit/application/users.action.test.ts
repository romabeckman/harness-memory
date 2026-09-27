import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  createUserAction,
  deleteUserAction,
  listUsersAction,
  updateUserAction,
} from '@/app/actions/users'
import { ClientFactory } from '@/infrastructure/api/client-factory'
import { HarnessApiClientPort } from '@/application/ports/harness-api-client.port'

vi.mock('next/cache', () => ({ revalidatePath: vi.fn() }))

describe('user server actions', () => {
  const mockClient: Partial<HarnessApiClientPort> = {
    listUsers: vi.fn(),
    createUser: vi.fn(),
    updateUser: vi.fn(),
    deleteUser: vi.fn(),
  }

  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(ClientFactory, 'getHarnessClient').mockReturnValue(mockClient as HarnessApiClientPort)
  })

  it('lists users globally and forwards page controls', async () => {
    vi.mocked(mockClient.listUsers!).mockResolvedValueOnce([])

    await expect(listUsersAction('ada', 20, 40)).resolves.toEqual({ data: [] })
    expect(mockClient.listUsers).toHaveBeenCalledWith('ada', 20, 40)
  })

  it('revalidates users only after successful mutation', async () => {
    const user = { id: 'user-1', name: 'Ada', email: 'ada@example.com' }
    vi.mocked(mockClient.createUser!).mockResolvedValueOnce(user)
    vi.mocked(mockClient.updateUser!).mockResolvedValueOnce(user)
    vi.mocked(mockClient.deleteUser!).mockResolvedValueOnce()

    await expect(createUserAction({ name: ' Ada ', email: 'ADA@EXAMPLE.COM' })).resolves.toEqual({
      success: true,
      data: user,
    })
    await expect(updateUserAction('user-1', { name: 'Ada' })).resolves.toEqual({
      success: true,
      data: user,
    })
    await expect(deleteUserAction('user-1')).resolves.toEqual({ success: true })
  })

  it('returns safe failure and does not invent mutation state', async () => {
    vi.mocked(mockClient.createUser!).mockRejectedValueOnce(new Error('email already exists'))

    await expect(createUserAction({ name: 'Other', email: 'ada@example.com' })).resolves.toEqual({
      success: false,
      error: 'email already exists',
    })
  })
})
