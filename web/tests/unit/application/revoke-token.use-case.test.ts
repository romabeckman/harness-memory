import { describe, it, expect, vi, beforeEach } from 'vitest'
import { RevokeTokenUseCase } from '@/application/use-cases/revoke-token.use-case'
import { HarnessApiClientPort } from '@/application/ports/harness-api-client.port'

describe('RevokeTokenUseCase', () => {
  let mockClient: HarnessApiClientPort
  let useCase: RevokeTokenUseCase

  beforeEach(() => {
    mockClient = {
      listUsers: vi.fn(),
      createUser: vi.fn(),
      updateUser: vi.fn(),
      deleteUser: vi.fn(),
      listTenants: vi.fn(),
      createTenant: vi.fn(),
      listServiceAccounts: vi.fn(),
      createServiceAccount: vi.fn(),
      updateServiceAccount: vi.fn(),
      deleteServiceAccount: vi.fn(),
      listTokens: vi.fn(),
      createToken: vi.fn(),
      revokeToken: vi.fn(),
    }
    useCase = new RevokeTokenUseCase(mockClient)
  })

  it('SCN-18: should call client revokeToken with validated tokenId', async () => {
    vi.mocked(mockClient.revokeToken).mockResolvedValueOnce()

    await useCase.execute('token-id-123')

    expect(mockClient.revokeToken).toHaveBeenCalledWith('token-id-123')
  })

  it('should reject revocation when tokenId is empty', async () => {
    await expect(useCase.execute('   ')).rejects.toThrow('Token ID cannot be empty')
  })
})
