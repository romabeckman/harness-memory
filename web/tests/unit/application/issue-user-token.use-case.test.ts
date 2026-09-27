import { beforeEach, describe, expect, it, vi } from 'vitest'
import { IssueTokenUseCase } from '@/application/use-cases/issue-token.use-case'
import { HarnessApiClientPort } from '@/application/ports/harness-api-client.port'
import { AccessTokenOrder } from '@/domain/access-token-order'
import { TokenScope } from '@/domain/token-scope'

describe('IssueTokenUseCase user ownership', () => {
  let client: HarnessApiClientPort

  beforeEach(() => {
    client = {
      listTenants: vi.fn(),
      createTenant: vi.fn(),
      updateTenant: vi.fn(),
      deleteTenant: vi.fn(),
      listProjects: vi.fn(),
      getProject: vi.fn(),
      createProject: vi.fn(),
      updateProject: vi.fn(),
      deleteProject: vi.fn(),
      listProjectEnvironments: vi.fn(),
      addProjectEnvironment: vi.fn(),
      listServiceAccounts: vi.fn(),
      createServiceAccount: vi.fn(),
      updateServiceAccount: vi.fn(),
      deleteServiceAccount: vi.fn(),
      listUsers: vi.fn(),
      createUser: vi.fn(),
      updateUser: vi.fn(),
      deleteUser: vi.fn(),
      listTokens: vi.fn(),
      createToken: vi.fn(),
      revokeToken: vi.fn(),
    }
  })

  it('sends exactly one user owner and returns one-time plaintext reveal', async () => {
    vi.mocked(client.createToken).mockResolvedValueOnce({
      id: 'token-1',
      name: 'agent',
      token: 'hm_user_secret',
      user_id: 'user-1',
      scopes: ['memory:read'],
      created_at: '2026-09-26T00:00:00Z',
      expires_at: '2026-10-26T00:00:00Z',
    })
    const order = AccessTokenOrder.create({
      owner: { kind: 'user', id: 'user-1', name: 'Ada' },
      name: 'agent',
      scopes: [TokenScope.create('memory:read')],
      projectKeys: [],
      lifetimeDays: 30,
    })

    const result = await new IssueTokenUseCase(client).execute(order)

    expect(client.createToken).toHaveBeenCalledWith({
      name: 'agent',
      user_id: 'user-1',
      scopes: ['memory:read'],
      project_keys: [],
      expires_at: expect.any(String),
    })
    expect(client.createToken).toHaveBeenCalledWith(
      expect.not.objectContaining({ service_account_id: expect.anything() })
    )
    expect(result.plaintextToken).toBe('hm_user_secret')
    expect(result.isAcknowledged).toBe(false)
  })

  it('sends selected project grants without binding the token to a tenant', async () => {
    vi.mocked(client.createToken).mockResolvedValueOnce({
      id: 'token-2',
      name: 'tenant-project-token',
      token: 'hm_project_secret',
      user_id: 'user-1',
      scopes: ['memory:read'],
      created_at: '2026-09-27T00:00:00Z',
      expires_at: '2026-10-27T00:00:00Z',
    })
    const order = AccessTokenOrder.create({
      owner: { kind: 'user', id: 'user-1', name: 'Ada' },
      name: 'tenant-project-token',
      scopes: [TokenScope.create('memory:read')],
      projectKeys: ['platform-api'],
      lifetimeDays: 30,
    })

    await new IssueTokenUseCase(client).execute(order)

    expect(client.createToken).toHaveBeenCalledWith(expect.objectContaining({
      user_id: 'user-1',
      project_keys: ['platform-api'],
    }))
    expect(client.createToken).toHaveBeenCalledWith(
      expect.not.objectContaining({ tenant_id: expect.anything() })
    )
  })
})
