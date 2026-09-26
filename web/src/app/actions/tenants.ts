'use server'

import { revalidatePath } from 'next/cache'
import { ClientFactory } from '@/infrastructure/api/client-factory'
import { TenantDto, CreateTenantDto, UpdateTenantDto } from '@/application/ports/harness-api-client.port'

export async function listTenantsAction(
  query?: string,
  limit?: number,
  offset?: number
): Promise<{ data?: TenantDto[]; error?: string }> {
  try {
    const client = ClientFactory.getHarnessClient()
    const data = await client.listTenants(query, limit, offset)
    return { data }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Falha ao listar tenants'
    return { error: msg }
  }
}

export async function createTenantAction(
  payload: CreateTenantDto
): Promise<{ success: boolean; data?: TenantDto; error?: string }> {
  try {
    if (!payload.key?.trim()) {
      return { success: false, error: 'Chave do tenant é obrigatória' }
    }
    if (!payload.name?.trim()) {
      return { success: false, error: 'Nome do tenant é obrigatório' }
    }
    const client = ClientFactory.getHarnessClient()
    const data = await client.createTenant({
      key: payload.key.trim().toLowerCase(),
      name: payload.name.trim(),
      metadata: payload.metadata || {},
    })
    revalidatePath('/tenants')
    return { success: true, data }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Erro ao criar tenant'
    return { success: false, error: msg }
  }
}

export async function updateTenantAction(
  tenantId: string,
  payload: UpdateTenantDto
): Promise<{ success: boolean; data?: TenantDto; error?: string }> {
  try {
    const client = ClientFactory.getHarnessClient()
    const data = await client.updateTenant(tenantId, payload)
    revalidatePath('/tenants')
    return { success: true, data }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Erro ao atualizar tenant'
    return { success: false, error: msg }
  }
}

export async function deleteTenantAction(
  tenantId: string
): Promise<{ success: boolean; error?: string }> {
  try {
    const client = ClientFactory.getHarnessClient()
    await client.deleteTenant(tenantId)
    revalidatePath('/tenants')
    return { success: true }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Erro ao excluir tenant'
    return { success: false, error: msg }
  }
}
