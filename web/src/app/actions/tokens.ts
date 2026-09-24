'use server'

import { revalidatePath } from 'next/cache'
import { ClientFactory } from '@/infrastructure/api/client-factory'
import { BootstrapTenantUseCase, BootstrapResult } from '@/application/use-cases/bootstrap-tenant.use-case'
import { IssueTokenUseCase } from '@/application/use-cases/issue-token.use-case'
import { RevokeTokenUseCase } from '@/application/use-cases/revoke-token.use-case'
import { AccessTokenOrder } from '@/domain/access-token-order'
import { TokenScope } from '@/domain/token-scope'
import { TokenMetadataDto } from '@/application/ports/harness-api-client.port'

export interface DashboardData {
  bootstrap: BootstrapResult
  tokens: TokenMetadataDto[]
}

export async function loadDashboardDataAction(): Promise<{ data?: DashboardData; error?: string }> {
  try {
    const client = ClientFactory.getHarnessClient()
    const bootstrapUseCase = new BootstrapTenantUseCase(client)
    const bootstrap = await bootstrapUseCase.execute()
    const tokens = await client.listTokens()

    return { data: { bootstrap, tokens } }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Falha ao carregar dados do dashboard'
    return { error: msg }
  }
}

export interface CreateTokenInput {
  name: string
  serviceAccountId: string
  scopes: string[]
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
      lifetimeDays: input.lifetimeDays,
    })

    const issueUseCase = new IssueTokenUseCase(client)
    const result = await issueUseCase.execute(order)

    revalidatePath('/')
    return { success: true, plaintext: result.plaintextToken }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Erro ao emitir token'
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
    const msg = err instanceof Error ? err.message : 'Erro ao revogar token'
    return { success: false, error: msg }
  }
}
