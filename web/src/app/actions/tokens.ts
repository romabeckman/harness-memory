'use server'

import { revalidatePath } from 'next/cache'
import { ClientFactory } from '@/infrastructure/api/client-factory'
import { BootstrapTenantUseCase, BootstrapResult } from '@/application/use-cases/bootstrap-tenant.use-case'
import { IssueTokenUseCase } from '@/application/use-cases/issue-token.use-case'
import { RevokeTokenUseCase } from '@/application/use-cases/revoke-token.use-case'
import { AccessTokenOrder } from '@/domain/access-token-order'
import { TokenScope } from '@/domain/token-scope'
import { TokenMetadataDto, TenantDto } from '@/application/ports/harness-api-client.port'

export interface DashboardData {
  bootstrap: BootstrapResult
  tokens: TokenMetadataDto[]
  tenants: TenantDto[]
}

export async function loadDashboardDataAction(): Promise<{ data?: DashboardData; error?: string }> {
  try {
    const client = ClientFactory.getHarnessClient()
    const bootstrapUseCase = new BootstrapTenantUseCase(client)
    const bootstrap = await bootstrapUseCase.execute()
    const tokens = await client.listTokens()
    const tenants = await client.listTenants(undefined, 500, 0)

    return { data: { bootstrap, tokens, tenants } }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Failed to load dashboard data'
    return { error: msg }
  }
}

export interface CreateTokenInput {
  name: string
  serviceAccountId: string
  scopes: string[]
  projectKeys: string[]
  lifetimeDays?: number
}

export async function createTokenAction(
  input: CreateTokenInput
): Promise<{ success: boolean; plaintext?: string; error?: string }> {
  try {
    const client = ClientFactory.getHarnessClient()
    const domainScopes = input.scopes.map((s) => TokenScope.create(s))

    const order = AccessTokenOrder.create({
      name: input.name,
      serviceAccountId: input.serviceAccountId,
      scopes: domainScopes,
      projectKeys: input.projectKeys,
      lifetimeDays: input.lifetimeDays,
    })

    const issueUseCase = new IssueTokenUseCase(client)
    const result = await issueUseCase.execute(order)

    revalidatePath('/')
    return { success: true, plaintext: result.plaintextToken }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Failed to issue token'
    return { success: false, error: msg }
  }
}

export async function revokeTokenAction(tokenId: string): Promise<{ success: boolean; error?: string }> {
  try {
    const client = ClientFactory.getHarnessClient()
    const revokeUseCase = new RevokeTokenUseCase(client)
    await revokeUseCase.execute(tokenId)

    revalidatePath('/')
    return { success: true }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Failed to revoke token'
    return { success: false, error: msg }
  }
}
