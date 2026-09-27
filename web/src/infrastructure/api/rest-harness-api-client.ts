import {
  HarnessApiClientPort,
  TenantDto,
  ServiceAccountDto,
  TokenMetadataDto,
  CreateTokenDto,
  CreatedTokenDto,
  CreateTenantDto,
  UpdateTenantDto,
  ProjectDto,
  CreateProjectDto,
  UpdateProjectDto,
  CreateServiceAccountDto,
  ServiceAccountListQuery,
  UpdateServiceAccountDto,
  UserDto,
  CreateUserDto,
  UpdateUserDto,
} from '@/application/ports/harness-api-client.port'

export class RestHarnessApiClient implements HarnessApiClientPort {
  private readonly baseUrl: string
  private readonly adminToken: string

  public constructor(baseUrl: string, adminToken: string) {
    this.baseUrl = baseUrl.replace(/\/$/, '')
    this.adminToken = adminToken
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${path}`
    const headers = {
      Authorization: `Bearer ${this.adminToken}`,
      'Content-Type': 'application/json',
      ...options.headers,
    }

    const response = await fetch(url, { ...options, headers })

    if (response.status === 401 || response.status === 403) {
      throw new Error('Harness API authorization failed: unauthorized administrative request')
    }

    if (!response.ok) {
      throw new Error(`Harness API request failed with status ${response.status}`)
    }

    if (response.status === 204) {
      return undefined as unknown as T
    }

    return (await response.json()) as T
  }

  public async listUsers(
    query?: string,
    limit?: number,
    offset?: number
  ): Promise<UserDto[]> {
    const params = new URLSearchParams()
    if (query) params.set('q', query)
    if (limit !== undefined) params.set('limit', String(limit))
    if (offset !== undefined) params.set('offset', String(offset))
    const qs = params.toString() ? `?${params.toString()}` : ''
    return this.request<UserDto[]>(`/v1/users${qs}`, { method: 'GET' })
  }

  public async createUser(payload: CreateUserDto): Promise<UserDto> {
    return this.request<UserDto>('/v1/users', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  public async updateUser(userId: string, payload: UpdateUserDto): Promise<UserDto> {
    return this.request<UserDto>(`/v1/users/${encodeURIComponent(userId)}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  }

  public async deleteUser(userId: string): Promise<void> {
    await this.request<void>(`/v1/users/${encodeURIComponent(userId)}`, {
      method: 'DELETE',
    })
  }

  public async listTenants(
    query?: string,
    limit?: number,
    offset?: number
  ): Promise<TenantDto[]> {
    const params = new URLSearchParams()
    if (query) params.set('q', query)
    if (limit !== undefined) params.set('limit', String(limit))
    if (offset !== undefined) params.set('offset', String(offset))
    const qs = params.toString() ? `?${params.toString()}` : ''
    return this.request<TenantDto[]>(`/v1/tenants${qs}`, { method: 'GET' })
  }

  public async createTenant(payload: CreateTenantDto): Promise<TenantDto> {
    const key = payload.key || payload.name.toLowerCase().replace(/[^a-z0-9_-]/g, '-')
    return this.request<TenantDto>('/v1/tenants', {
      method: 'POST',
      body: JSON.stringify({ ...payload, key }),
    })
  }

  public async updateTenant(tenantId: string, payload: UpdateTenantDto): Promise<TenantDto> {
    return this.request<TenantDto>(`/v1/tenants/${encodeURIComponent(tenantId)}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  }

  public async deleteTenant(tenantId: string): Promise<void> {
    await this.request<void>(`/v1/tenants/${encodeURIComponent(tenantId)}`, {
      method: 'DELETE',
    })
  }

  public async listProjects(
    tenantId?: string,
    query?: string,
    limit?: number,
    offset?: number
  ): Promise<ProjectDto[]> {
    const params = new URLSearchParams()
    if (tenantId) params.set('tenant_id', tenantId)
    if (query) params.set('q', query)
    if (limit !== undefined) params.set('limit', String(limit))
    if (offset !== undefined) params.set('offset', String(offset))
    const qs = params.toString() ? `?${params.toString()}` : ''
    return this.request<ProjectDto[]>(`/v1/projects${qs}`, { method: 'GET' })
  }

  public async getProject(tenantId: string, projectKey: string): Promise<ProjectDto> {
    return this.request<ProjectDto>(
      `/v1/projects/${encodeURIComponent(projectKey)}?tenant_id=${encodeURIComponent(tenantId)}`,
      { method: 'GET' }
    )
  }

  public async createProject(payload: CreateProjectDto): Promise<ProjectDto> {
    return this.request<ProjectDto>('/v1/projects', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  public async updateProject(
    tenantId: string,
    projectKey: string,
    payload: UpdateProjectDto
  ): Promise<ProjectDto> {
    return this.request<ProjectDto>(
      `/v1/projects/${encodeURIComponent(projectKey)}?tenant_id=${encodeURIComponent(tenantId)}`,
      {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }
    )
  }

  public async deleteProject(tenantId: string, projectKey: string): Promise<void> {
    await this.request<void>(
      `/v1/projects/${encodeURIComponent(projectKey)}?tenant_id=${encodeURIComponent(tenantId)}`,
      {
        method: 'DELETE',
      }
    )
  }

  public async listServiceAccounts(query?: ServiceAccountListQuery): Promise<ServiceAccountDto[]>
  public async listServiceAccounts(
    tenantId?: string,
    search?: string,
    limit?: number,
    offset?: number
  ): Promise<ServiceAccountDto[]>
  public async listServiceAccounts(
    queryOrTenantId?: ServiceAccountListQuery | string,
    search?: string,
    limit?: number,
    offset?: number
  ): Promise<ServiceAccountDto[]> {
    const query: ServiceAccountListQuery =
      typeof queryOrTenantId === 'string'
        ? { tenantId: queryOrTenantId, query: search, limit, offset }
        : queryOrTenantId || {}
    const params = new URLSearchParams()
    if (query.tenantId || query.tenant_id) {
      params.set('tenant_id', query.tenantId || query.tenant_id || '')
    }
    if (query.query) params.set('q', query.query)
    if (query.limit !== undefined) params.set('limit', String(query.limit))
    if (query.offset !== undefined) params.set('offset', String(query.offset))
    const suffix = params.toString() ? `?${params.toString()}` : ''
    return this.request<ServiceAccountDto[]>(`/v1/service-accounts${suffix}`, { method: 'GET' })
  }

  public async createServiceAccount(payload: CreateServiceAccountDto): Promise<ServiceAccountDto> {
    return this.request<ServiceAccountDto>('/v1/service-accounts', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  public async updateServiceAccount(
    serviceAccountId: string,
    payload: UpdateServiceAccountDto
  ): Promise<ServiceAccountDto> {
    return this.request<ServiceAccountDto>(
      `/v1/service-accounts/${encodeURIComponent(serviceAccountId)}`,
      {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }
    )
  }

  public async deleteServiceAccount(serviceAccountId: string): Promise<void> {
    await this.request<void>(`/v1/service-accounts/${encodeURIComponent(serviceAccountId)}`, {
      method: 'DELETE',
    })
  }

  public async listTokens(limit?: number, offset?: number): Promise<TokenMetadataDto[]> {
    const params = new URLSearchParams()
    if (limit !== undefined) params.set('limit', String(limit))
    if (offset !== undefined) params.set('offset', String(offset))
    const qs = params.toString() ? `?${params.toString()}` : ''
    return this.request<TokenMetadataDto[]>(`/v1/tokens${qs}`, { method: 'GET' })
  }

  public async createToken(payload: CreateTokenDto): Promise<CreatedTokenDto> {
    return this.request<CreatedTokenDto>('/v1/tokens', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  public async revokeToken(tokenId: string): Promise<void> {
    await this.request<void>(`/v1/tokens/${encodeURIComponent(tokenId)}`, {
      method: 'DELETE',
    })
  }
}
