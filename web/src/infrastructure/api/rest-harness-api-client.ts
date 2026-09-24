import {
  HarnessApiClientPort,
  TenantDto,
  ServiceAccountDto,
  TokenMetadataDto,
  CreateTokenDto,
  CreatedTokenDto,
  CreateTenantDto,
  CreateServiceAccountDto,
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
      const errorText = await response.text()
      throw new Error(`Harness API request failed with status ${response.status}: ${errorText}`)
    }

    if (response.status === 204) {
      return undefined as unknown as T
    }

    return (await response.json()) as T
  }

  public async listTenants(): Promise<TenantDto[]> {
    return this.request<TenantDto[]>('/v1/tenants', { method: 'GET' })
  }

  public async createTenant(payload: CreateTenantDto): Promise<TenantDto> {
    return this.request<TenantDto>('/v1/tenants', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  public async listServiceAccounts(tenantId?: string): Promise<ServiceAccountDto[]> {
    const query = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : ''
    return this.request<ServiceAccountDto[]>(`/v1/service-accounts${query}`, { method: 'GET' })
  }

  public async createServiceAccount(payload: CreateServiceAccountDto): Promise<ServiceAccountDto> {
    return this.request<ServiceAccountDto>('/v1/service-accounts', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  public async listTokens(): Promise<TokenMetadataDto[]> {
    return this.request<TokenMetadataDto[]>('/v1/tokens', { method: 'GET' })
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
