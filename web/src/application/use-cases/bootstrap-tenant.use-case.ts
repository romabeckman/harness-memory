import { HarnessApiClientPort, TenantDto, ServiceAccountDto } from '@/application/ports/harness-api-client.port'

export interface BootstrapResult {
  tenantId: string
  tenantName: string
  serviceAccountId: string
  serviceAccountName: string
  isNewBootstrap: boolean
}

export class BootstrapTenantUseCase {
  private readonly client: HarnessApiClientPort

  public constructor(client: HarnessApiClientPort) {
    this.client = client
  }

  public async execute(): Promise<BootstrapResult> {
    const tenants = await this.client.listTenants()

    let activeTenant: TenantDto
    let isNewBootstrap = false

    if (tenants.length === 0) {
      activeTenant = await this.client.createTenant({ name: 'default' })
      isNewBootstrap = true
    } else {
      activeTenant = tenants[0]
    }

    const serviceAccounts = await this.client.listServiceAccounts(activeTenant.id)

    let activeServiceAccount: ServiceAccountDto
    if (serviceAccounts.length === 0) {
      activeServiceAccount = await this.client.createServiceAccount({
        tenant_id: activeTenant.id,
        name: 'default-automation',
      })
    } else {
      activeServiceAccount = serviceAccounts[0]
    }

    return {
      tenantId: activeTenant.id,
      tenantName: activeTenant.name,
      serviceAccountId: activeServiceAccount.id,
      serviceAccountName: activeServiceAccount.name,
      isNewBootstrap,
    }
  }
}
