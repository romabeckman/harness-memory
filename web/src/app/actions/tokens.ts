'use server'

import { revalidatePath } from 'next/cache'
import { ClientFactory } from '@/infrastructure/api/client-factory'
import { IssueTokenUseCase } from '@/application/use-cases/issue-token.use-case'
import { RevokeTokenUseCase } from '@/application/use-cases/revoke-token.use-case'
import { AccessTokenOrder, TokenOwner } from '@/domain/access-token-order'
import { TokenScope } from '@/domain/token-scope'
import {
  HarnessApiClientPort,
  ServiceAccountDto,
  TenantDto,
  TokenMetadataDto,
  UserDto,
} from '@/application/ports/harness-api-client.port'
import { CredentialReviewItem, resolveCredentialReviewItems } from '@/domain/credential-review-item'

export interface DashboardData {
  credentials: readonly CredentialReviewItem[]
  hasMore: boolean
  page: number
}

const CATALOG_PAGE_SIZE = 100
const REVIEW_PAGE_SIZE = 100

interface CredentialReviewCatalogs {
  tokens: TokenMetadataDto[]
  users: UserDto[]
  serviceAccounts: ServiceAccountDto[]
  tenants: TenantDto[]
}

async function loadCatalogPages<T>(
  loadPage: (limit: number, offset: number) => Promise<T[]>,
  pageSize: number
): Promise<T[]> {
  const values: T[] = []
  let offset = 0

  while (true) {
    const page = await loadPage(pageSize, offset)
    values.push(...page)
    if (page.length < pageSize) return values
    offset += pageSize
  }
}

export async function loadAllCredentialReviewCatalogs(
  client: HarnessApiClientPort,
  pageSize = CATALOG_PAGE_SIZE
): Promise<CredentialReviewCatalogs> {
  if (!Number.isInteger(pageSize) || pageSize < 1 || pageSize > 500) {
    throw new Error('Credential review page size is invalid')
  }

  const [tokens, users, serviceAccounts, tenants] = await Promise.all([
    loadCatalogPages((limit, offset) => client.listTokens(limit, offset), pageSize),
    loadCatalogPages((limit, offset) => client.listUsers(undefined, limit, offset), pageSize),
    loadCatalogPages(
      (limit, offset) => client.listServiceAccounts({ limit, offset }),
      pageSize
    ),
    loadCatalogPages((limit, offset) => client.listTenants(undefined, limit, offset), pageSize),
  ])

  return { tokens, users, serviceAccounts, tenants }
}

export async function loadDashboardDataAction(page = 0): Promise<{ data?: DashboardData; error?: string }> {
  try {
    if (!Number.isSafeInteger(page) || page < 0 || page > Math.floor(Number.MAX_SAFE_INTEGER / REVIEW_PAGE_SIZE)) {
      throw new Error('Invalid review page')
    }
    const client = ClientFactory.getHarnessClient()
    const [tokens, users, serviceAccounts, tenants] = await Promise.all([
      client.listTokens(REVIEW_PAGE_SIZE + 1, page * REVIEW_PAGE_SIZE),
      loadCatalogPages((limit, offset) => client.listUsers(undefined, limit, offset), CATALOG_PAGE_SIZE),
      loadCatalogPages((limit, offset) => client.listServiceAccounts({ limit, offset }), CATALOG_PAGE_SIZE),
      loadCatalogPages((limit, offset) => client.listTenants(undefined, limit, offset), CATALOG_PAGE_SIZE),
    ])
    const credentials = resolveCredentialReviewItems({
      tokens: tokens.slice(0, REVIEW_PAGE_SIZE), users, serviceAccounts, tenants,
    })

    return { data: { credentials, hasMore: tokens.length > REVIEW_PAGE_SIZE, page } }
  } catch (err: unknown) {
    return { error: 'Failed to load credential review data' }
  }
}

export interface CreateTokenInput {
  name: string
  owner: TokenOwner
  scopes: string[]
  projectKeys: string[]
  lifetimeDays?: number
}

function safeTokenError(error: unknown, fallback: string): string {
  const message = error instanceof Error ? error.message : fallback
  if (
    !message ||
    /api_admin_token|authorization|bearer|header|cookie|hm_[a-z0-9_-]+|request failed|status \d+/i.test(
      message
    )
  ) {
    return fallback
  }
  return message === 'Token ID cannot be empty' ? message : fallback
}

const OWNER_IDENTIFIER_FIELDS = ['user_id', 'service_account_id', 'userId', 'serviceAccountId']

function hasOwnerIdentifier(value: unknown): boolean {
  return value !== undefined && value !== null && (typeof value !== 'string' || value.trim() !== '')
}

function hasAdditionalOwnerIdentifier(input: CreateTokenInput): boolean {
  const rawInput = input as unknown as Record<string, unknown>
  if (OWNER_IDENTIFIER_FIELDS.some((field) => hasOwnerIdentifier(rawInput[field]))) {
    return true
  }

  const owner = rawInput.owner
  return (
    typeof owner === 'object' &&
    owner !== null &&
    OWNER_IDENTIFIER_FIELDS.some((field) =>
      hasOwnerIdentifier((owner as Record<string, unknown>)[field])
    )
  )
}

export async function createTokenAction(
  input: CreateTokenInput
): Promise<{ success: boolean; plaintext?: string; error?: string }> {
  try {
    if (hasAdditionalOwnerIdentifier(input)) {
      return { success: false, error: 'Exactly one token owner must be selected' }
    }

    const client = ClientFactory.getHarnessClient()
    const domainScopes = input.scopes.map((s) => TokenScope.create(s))

    const order = AccessTokenOrder.create({
      name: input.name,
      owner: input.owner,
      scopes: domainScopes,
      projectKeys: input.projectKeys,
      lifetimeDays: input.lifetimeDays,
    })

    const issueUseCase = new IssueTokenUseCase(client)
    const result = await issueUseCase.execute(order)

    revalidatePath('/')
    return { success: true, plaintext: result.plaintextToken }
  } catch (err: unknown) {
    return { success: false, error: safeTokenError(err, 'Failed to issue token') }
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
    return { success: false, error: safeTokenError(err, 'Failed to revoke token') }
  }
}
