export interface TenantDto {
  id: string
  name: string
  created_at?: string
}

export interface ServiceAccountDto {
  id: string
  tenant_id: string
  name: string
  created_at?: string
}

export interface TokenMetadataDto {
  id: string
  name: string
  user_id?: string | null
  service_account_id?: string | null
  scopes: string[]
  created_at: string
  expires_at?: string | null
  revoked_at?: string | null
  is_active: boolean
}

export interface CreateTokenDto {
  name: string
  service_account_id?: string
  user_id?: string
  scopes: string[]
  expires_at?: string | null
}

export interface CreatedTokenDto {
  id: string
  name: string
  token: string
  service_account_id?: string | null
  user_id?: string | null
  scopes: string[]
  created_at: string
  expires_at?: string | null
}

export interface CreateTenantDto {
  name: string
}

export interface CreateServiceAccountDto {
  tenant_id: string
  name: string
}

export interface HarnessApiClientPort {
  listTenants(): Promise<TenantDto[]>
  createTenant(payload: CreateTenantDto): Promise<TenantDto>
  listServiceAccounts(tenantId?: string): Promise<ServiceAccountDto[]>
  createServiceAccount(payload: CreateServiceAccountDto): Promise<ServiceAccountDto>
  listTokens(): Promise<TokenMetadataDto[]>
  createToken(payload: CreateTokenDto): Promise<CreatedTokenDto>
  revokeToken(tokenId: string): Promise<void>
}
