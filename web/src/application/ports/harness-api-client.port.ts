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

export type EnvironmentTypeDto = 'development' | 'staging' | 'production' | 'other'

export interface EnvironmentDto {
  id: string
  tenant_id?: string
  project_key?: string
  name: string
  type: EnvironmentTypeDto
}

export interface ProjectEnvironmentRef {
  tenantId: string
  projectKey: string
}

export interface ServiceAccountListQuery {
  tenantId?: string
  tenant_id?: string
  query?: string
  limit?: number
  offset?: number
}

export interface UpdateServiceAccountDto {
  name: string
}

export interface UserDto {
  id: string
  name: string
  email: string
}

export interface CreateUserDto {
  name: string
  email: string
}

export interface UpdateUserDto {
  name?: string
  email?: string
}

export interface TokenMetadataDto {
  id: string
  name: string
  user_id?: string | null
  service_account_id?: string | null
  scopes: string[]
  project_keys?: string[]
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
  project_keys: string[]
  expires_at?: string | null
}

export interface CreatedTokenDto {
  id: string
  name: string
  token: string
  service_account_id?: string | null
  user_id?: string | null
  scopes: string[]
  project_keys?: string[]
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

export interface LinkedProjectDto {
  project_id: string
  key: string
  name: string | null
  tenant_id: string
}

export interface CreateProjectLinkDto {
  target_project_key: string
  target_tenant_id?: string
}

export function validateCreateProjectLinkDto(dto: CreateProjectLinkDto): {
  valid: boolean
  error?: string
} {
  if (!dto.target_project_key || !dto.target_project_key.trim()) {
    return { valid: false, error: 'Target project key is required' }
  }
  return { valid: true }
}

export interface HarnessApiClientPort {
  listUsers(query?: string, limit?: number, offset?: number): Promise<UserDto[]>
  createUser(payload: CreateUserDto): Promise<UserDto>
  updateUser(userId: string, payload: UpdateUserDto): Promise<UserDto>
  deleteUser(userId: string): Promise<void>
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
  listProjectEnvironments(reference: ProjectEnvironmentRef): Promise<EnvironmentDto[]>
  addProjectEnvironment(
    reference: ProjectEnvironmentRef,
    name: string
  ): Promise<EnvironmentDto>
  listProjectLinks(tenantId: string, projectKey: string): Promise<LinkedProjectDto[]>
  createProjectLink(
    tenantId: string,
    projectKey: string,
    payload: CreateProjectLinkDto
  ): Promise<void>
  deleteProjectLink(
    tenantId: string,
    projectKey: string,
    targetKey: string,
    targetTenantId?: string
  ): Promise<void>
  listServiceAccounts(
    queryOrTenantId?: ServiceAccountListQuery | string,
    query?: string,
    limit?: number,
    offset?: number
  ): Promise<ServiceAccountDto[]>
  createServiceAccount(payload: CreateServiceAccountDto): Promise<ServiceAccountDto>
  updateServiceAccount(
    serviceAccountId: string,
    payload: UpdateServiceAccountDto
  ): Promise<ServiceAccountDto>
  deleteServiceAccount(serviceAccountId: string): Promise<void>
  listTokens(limit?: number, offset?: number): Promise<TokenMetadataDto[]>
  createToken(payload: CreateTokenDto): Promise<CreatedTokenDto>
  revokeToken(tokenId: string): Promise<void>
}
