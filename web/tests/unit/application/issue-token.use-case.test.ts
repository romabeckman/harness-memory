import { describe, it, expect, vi, beforeEach } from 'vitest'
import { IssueTokenUseCase } from '@/application/use-cases/issue-token.use-case'
import { HarnessApiClientPort, CreatedTokenDto } from '@/application/ports/harness-api-client.port'
import { AccessTokenOrder } from '@/domain/access-token-order'
import { TokenScope } from '@/domain/token-scope'

describe('IssueTokenUseCase', () => {
  let mockClient: HarnessApiClientPort
  let useCase: IssueTokenUseCase

  beforeEach(() => {
    mockClient = {
      listTenants: vi.fn(),
      createTenant: vi.fn(),
      listServiceAccounts: vi.fn(),
      createServiceAccount: vi.fn(),
      listTokens: vi.fn(),
      createToken: vi.fn(),
      revokeToken: vi.fn(),
    }
    useCase = new IssueTokenUseCase(mockClient)
  })

  it('SCN-12: should invoke API port and return SecretRevealView on successful issuance', async () => {
    const mockCreated: CreatedTokenDto = {
      id: 'token-uuid-1',
      name: 'ci-runner',
      token: 'hm_secret_token_value_999',
      service_account_id: 'sa-uuid-1',
      scopes: ['memory:publish'],
      created_at: '2026-09-23T20:00:00Z',
    }

    vi.mocked(mockClient.createToken).mockResolvedValueOnce(mockCreated)

    const order = AccessTokenOrder.create({
      name: 'ci-runner',
      serviceAccountId: 'sa-uuid-1',
      scopes: [TokenScope.create('memory:publish')],
      lifetimeDays: 30,
    })

    const result = await useCase.execute(order)

    expect(mockClient.createToken).toHaveBeenCalledWith({
      name: 'ci-runner',
      service_account_id: 'sa-uuid-1',
      scopes: ['memory:publish'],
      expires_at: expect.any(String),
    })

    expect(result.plaintextToken).toBe('hm_secret_token_value_999')
    expect(result.isAcknowledged).toBe(false)
  })
})
