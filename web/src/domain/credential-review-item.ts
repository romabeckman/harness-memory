import {
  ServiceAccountDto,
  TenantDto,
  TokenMetadataDto,
  UserDto,
} from '@/application/ports/harness-api-client.port'

export type CredentialOwnerType = 'User' | 'Service Account'

export interface CredentialReviewItem {
  readonly token: Readonly<TokenMetadataDto>
  readonly ownerName: string
  readonly ownerType: CredentialOwnerType
  readonly organizationName?: string
}

export interface CredentialReviewItemInput {
  readonly tokens: readonly TokenMetadataDto[]
  readonly users: readonly UserDto[]
  readonly serviceAccounts: readonly ServiceAccountDto[]
  readonly tenants: readonly TenantDto[]
}

const INCONSISTENT_OWNERSHIP_ERROR = 'Credential ownership is inconsistent'

function requireNonblank(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value.trim() : undefined
}

function indexById<T extends { id: string }>(values: readonly T[]): Map<string, T> {
  const result = new Map<string, T>()
  for (const value of values) {
    const id = requireNonblank(value.id)
    if (!id || result.has(id)) {
      throw new Error(INCONSISTENT_OWNERSHIP_ERROR)
    }
    result.set(id, value)
  }
  return result
}

function copyTokenMetadata(token: TokenMetadataDto): Readonly<TokenMetadataDto> {
  const id = requireNonblank(token.id)
  const name = requireNonblank(token.name)
  if (!id || !name || !Array.isArray(token.scopes)) {
    throw new Error(INCONSISTENT_OWNERSHIP_ERROR)
  }

  const copiedToken: TokenMetadataDto = {
    id,
    name,
    user_id: token.user_id ?? null,
    service_account_id: token.service_account_id ?? null,
    scopes: [...token.scopes],
    project_keys: token.project_keys ? [...token.project_keys] : token.project_keys,
    created_at: token.created_at,
    expires_at: token.expires_at ?? null,
    revoked_at: token.revoked_at ?? null,
    is_active: token.is_active,
  }

  Object.freeze(copiedToken.scopes)
  if (copiedToken.project_keys) Object.freeze(copiedToken.project_keys)
  return Object.freeze(copiedToken)
}

export function resolveCredentialReviewItems(
  input: CredentialReviewItemInput
): readonly CredentialReviewItem[]
export function resolveCredentialReviewItems(
  tokens: readonly TokenMetadataDto[],
  users: readonly UserDto[],
  serviceAccounts: readonly ServiceAccountDto[],
  tenants: readonly TenantDto[]
): readonly CredentialReviewItem[]
export function resolveCredentialReviewItems(
  inputOrTokens: CredentialReviewItemInput | readonly TokenMetadataDto[],
  userCatalog: readonly UserDto[] = [],
  serviceAccountCatalog: readonly ServiceAccountDto[] = [],
  tenantCatalog: readonly TenantDto[] = []
): readonly CredentialReviewItem[] {
  const input: CredentialReviewItemInput = Array.isArray(inputOrTokens)
    ? {
        tokens: inputOrTokens,
        users: userCatalog,
        serviceAccounts: serviceAccountCatalog,
        tenants: tenantCatalog,
      }
    : (inputOrTokens as CredentialReviewItemInput)
  const users = indexById(input.users)
  const serviceAccounts = indexById(input.serviceAccounts)
  const tenants = indexById(input.tenants)
  const result: CredentialReviewItem[] = []

  for (const token of input.tokens) {
    const userId = requireNonblank(token.user_id)
    const serviceAccountId = requireNonblank(token.service_account_id)
    if ((userId ? 1 : 0) + (serviceAccountId ? 1 : 0) !== 1) {
      throw new Error(INCONSISTENT_OWNERSHIP_ERROR)
    }

    let ownerName: string | undefined
    let ownerType: CredentialOwnerType
    let organizationName: string | undefined

    if (userId) {
      const user = users.get(userId)
      ownerName = user ? requireNonblank(user.name) : undefined
      ownerType = 'User'
    } else {
      const serviceAccount = serviceAccounts.get(serviceAccountId!)
      ownerName = serviceAccount ? requireNonblank(serviceAccount.name) : undefined
      ownerType = 'Service Account'
      const tenantId = serviceAccount ? requireNonblank(serviceAccount.tenant_id) : undefined
      const tenant = tenantId ? tenants.get(tenantId) : undefined
      organizationName = tenant ? requireNonblank(tenant.name) : undefined
    }

    if (!ownerName) {
      throw new Error(INCONSISTENT_OWNERSHIP_ERROR)
    }

    const item: CredentialReviewItem = {
      token: copyTokenMetadata(token),
      ownerName,
      ownerType,
      ...(organizationName ? { organizationName } : {}),
    }
    result.push(Object.freeze(item))
  }

  return Object.freeze(result)
}
