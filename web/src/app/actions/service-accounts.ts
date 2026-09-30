'use server'

import { revalidatePath } from 'next/cache'
import {
  HarnessApiClientPort,
  ServiceAccountDto,
  ServiceAccountListQuery,
  UpdateServiceAccountDto,
} from '@/application/ports/harness-api-client.port'
import { ClientFactory } from '@/infrastructure/api/client-factory'

const SERVICE_ACCOUNTS_PATH = '/service-accounts'

type ServiceAccountListInput = ServiceAccountListQuery | string

export interface CreateServiceAccountInput {
  name: string
  tenantId?: string
  tenant_id?: string
}

function safeError(error: unknown, fallback: string): string {
  const message = error instanceof Error ? error.message : fallback
  if (/api_admin_token|authorization|bearer|header|cookie|request/i.test(message)) {
    return fallback
  }
  return message || fallback
}

function normalizeListQuery(query: ServiceAccountListQuery): ServiceAccountListQuery {
  return {
    ...query,
    limit: query.limit ?? 100,
    offset: query.offset ?? 0,
  }
}

export async function listServiceAccountsAction(
  input?: ServiceAccountListInput,
  query?: string,
  limit?: number,
  offset?: number
): Promise<{ data?: ServiceAccountDto[]; error?: string }> {
  try {
    const client = ClientFactory.getHarnessClient()
    const hasPositionalPage = query !== undefined || limit !== undefined || offset !== undefined
    const data = hasPositionalPage
      ? await client.listServiceAccounts(
          normalizeListQuery({
            tenantId: typeof input === 'string' ? input : input?.tenantId,
            query: typeof input === 'string' ? query : input?.query,
            limit: typeof input === 'string' ? limit : input?.limit,
            offset: typeof input === 'string' ? offset : input?.offset,
          })
        )
      : typeof input === 'string'
        ? await client.listServiceAccounts(input)
        : await client.listServiceAccounts(normalizeListQuery(input ?? {}))
    return { data }
  } catch (error: unknown) {
    return { error: safeError(error, 'Failed to list service accounts') }
  }
}

export async function createServiceAccountAction(
  input: CreateServiceAccountInput
): Promise<{ success: boolean; data?: ServiceAccountDto; error?: string }> {
  const name = input.name?.trim() ?? ''
  const tenantId = input.tenantId?.trim() || input.tenant_id?.trim() || ''
  if (!name) return { success: false, error: 'Service account name is required' }
  if (name.length > 120) {
    return { success: false, error: 'Service account name cannot exceed 120 characters' }
  }
  if (!tenantId) return { success: false, error: 'Organization is required' }

  try {
    const client = ClientFactory.getHarnessClient()
    const data = await client.createServiceAccount({ name, tenant_id: tenantId })
    revalidatePath(SERVICE_ACCOUNTS_PATH)
    return { success: true, data }
  } catch (error: unknown) {
    return { success: false, error: safeError(error, 'Failed to create service account') }
  }
}

export async function updateServiceAccountAction(
  serviceAccountId: string,
  input: UpdateServiceAccountDto
): Promise<{ success: boolean; data?: ServiceAccountDto; error?: string }> {
  const id = serviceAccountId?.trim() ?? ''
  const name = input.name?.trim() ?? ''
  if (!id) return { success: false, error: 'Service account ID is required' }
  if (!name) return { success: false, error: 'Service account name is required' }
  if (name.length > 120) {
    return { success: false, error: 'Service account name cannot exceed 120 characters' }
  }

  try {
    const client = ClientFactory.getHarnessClient()
    const data = await client.updateServiceAccount(id, { name })
    revalidatePath(SERVICE_ACCOUNTS_PATH)
    return { success: true, data }
  } catch (error: unknown) {
    return { success: false, error: safeError(error, 'Failed to update service account') }
  }
}

export async function deleteServiceAccountAction(
  serviceAccountId: string
): Promise<{ success: boolean; error?: string }> {
  const id = serviceAccountId?.trim() ?? ''
  if (!id) return { success: false, error: 'Service account ID is required' }

  try {
    const client: HarnessApiClientPort = ClientFactory.getHarnessClient()
    await client.deleteServiceAccount(id)
    revalidatePath(SERVICE_ACCOUNTS_PATH)
    return { success: true }
  } catch (error: unknown) {
    return { success: false, error: safeError(error, 'Failed to delete service account') }
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
        const found = accounts.find((account) => account.name === preferredName)
        if (found) return { data: found }
      }
      return { data: accounts[0] }
    }
    const created = await client.createServiceAccount({
      tenant_id: tenantId,
      name: preferredName || 'default-automation',
    })
    return { data: created }
  } catch (error: unknown) {
    return {
      error: safeError(error, 'Failed to provision a service account for the tenant'),
    }
  }
}
