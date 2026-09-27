'use server'

import { revalidatePath } from 'next/cache'
import { ClientFactory } from '@/infrastructure/api/client-factory'
import {
  LinkedProjectDto,
  CreateProjectLinkDto,
  validateCreateProjectLinkDto,
} from '@/application/ports/harness-api-client.port'

export async function listProjectLinksAction(
  tenantId: string,
  projectKey: string
): Promise<{ data?: LinkedProjectDto[]; error?: string }> {
  try {
    const client = ClientFactory.getHarnessClient()
    const data = await client.listProjectLinks(tenantId, projectKey)
    return { data }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Failed to list project links'
    return { error: msg }
  }
}

export async function createProjectLinkAction(
  tenantId: string,
  projectKey: string,
  dto: CreateProjectLinkDto
): Promise<{ success: boolean; error?: string }> {
  const validation = validateCreateProjectLinkDto(dto)
  if (!validation.valid) {
    return { success: false, error: validation.error || 'Invalid project link payload' }
  }

  try {
    const client = ClientFactory.getHarnessClient()
    await client.createProjectLink(tenantId, projectKey, {
      target_project_key: dto.target_project_key.trim(),
      target_tenant_id: dto.target_tenant_id?.trim() || undefined,
    })
    revalidatePath('/projects')
    return { success: true }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Failed to create project link'
    return { success: false, error: msg }
  }
}

export async function deleteProjectLinkAction(
  tenantId: string,
  projectKey: string,
  targetKey: string,
  targetTenantId?: string
): Promise<{ success: boolean; error?: string }> {
  try {
    const client = ClientFactory.getHarnessClient()
    await client.deleteProjectLink(
      tenantId,
      projectKey,
      targetKey,
      targetTenantId?.trim() || undefined
    )
    revalidatePath('/projects')
    return { success: true }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Failed to delete project link'
    return { success: false, error: msg }
  }
}
