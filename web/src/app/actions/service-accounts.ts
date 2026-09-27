'use server'

import { ClientFactory } from '@/infrastructure/api/client-factory'
import { ServiceAccountDto } from '@/application/ports/harness-api-client.port'

export async function listServiceAccountsAction(
  tenantId: string
): Promise<{ data?: ServiceAccountDto[]; error?: string }> {
  try {
    const client = ClientFactory.getHarnessClient()
    const data = await client.listServiceAccounts(tenantId)
    return { data }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Failed to list service accounts'
    return { error: msg }
  }
}

export async function ensureServiceAccountAction(
  tenantId: string,
  preferredName?: string
): Promise<{ data?: ServiceAccountDto; error?: string }> {
  try {
    const client = ClientFactory.getHarnessClient()
    const accounts = await client.listServiceAccounts(tenantId)
    if (accounts.length > 0) {
      if (preferredName) {
        const found = accounts.find((a) => a.name === preferredName)
        if (found) return { data: found }
      }
      return { data: accounts[0] }
    }
    const created = await client.createServiceAccount({
      tenant_id: tenantId,
      name: preferredName || 'default-automation',
    })
    return { data: created }
  } catch (err: unknown) {
    const msg =
      err instanceof Error
        ? err.message
        : 'Failed to provision a service account for the tenant'
    return { error: msg }
  }
}
