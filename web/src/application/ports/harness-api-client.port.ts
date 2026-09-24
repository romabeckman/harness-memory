export interface TenantDto {
  id: string
  name: string
  key?: string
  status?: 'active' | 'disabled'
  metadata?: Record<string, unknown>
  created_at?: string
  updated_at?: string
}

export interface UpdateTenantDto {
  name?: string
  status?: 'active' | 'disabled'
  metadata?: Record<string, unknown>
}

export interface ProjectDto {
  id: string
  tenant_id: string
  key: string
  name?: string | null
  active_snapshot_id?: string | null
  metadata?: Record<string, unknown>
  created_at?: string
  updated_at?: string
}

export interface CreateProjectDto {
  tenant_id: string
  key: string
  name?: string | null
  metadata?: Record<string, unknown>
}

export interface UpdateProjectDto {
  name?: string | null
  metadata?: Record<string, unknown>
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
  key?: string
  metadata?: Record<string, unknown>
}

export interface CreateServiceAccountDto {
  tenant_id: string
  name: string
}

export interface HarnessApiClientPort {
  listTenants(query?: string, limit?: number, offset?: number): Promise<TenantDto[]>
  createTenant(payload: CreateTenantDto): Promise<TenantDto>
  updateTenant(tenantId: string, payload: UpdateTenantDto): Promise<TenantDto>
  deleteTenant(tenantId: string): Promise<void>
  listProjects(
    tenantId?: string,
    query?: string,
    limit?: number,
    offset?: number
  ): Promise<ProjectDto[]>
  getProject(tenantId: string, projectKey: string): Promise<ProjectDto>
  createProject(payload: CreateProjectDto): Promise<ProjectDto>
  updateProject(tenantId: string, projectKey: string, payload: UpdateProjectDto): Promise<ProjectDto>
  deleteProject(tenantId: string, projectKey: string): Promise<void>
  listServiceAccounts(tenantId?: string): Promise<ServiceAccountDto[]>
  createServiceAccount(payload: CreateServiceAccountDto): Promise<ServiceAccountDto>
  listTokens(): Promise<TokenMetadataDto[]>
  createToken(payload: CreateTokenDto): Promise<CreatedTokenDto>
  revokeToken(tokenId: string): Promise<void>
}
