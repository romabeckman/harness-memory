'use server'

import { revalidatePath } from 'next/cache'
import { ClientFactory } from '@/infrastructure/api/client-factory'
import {
  ProjectDto,
  CreateProjectDto,
  UpdateProjectDto,
} from '@/application/ports/harness-api-client.port'

export async function listProjectsAction(
  tenantId?: string,
  query?: string,
  limit?: number,
  offset?: number
): Promise<{ data?: ProjectDto[]; error?: string }> {
  try {
    const client = ClientFactory.getHarnessClient()
    const data = await client.listProjects(tenantId, query, limit, offset)
    return { data }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Falha ao listar projetos'
    return { error: msg }
  }
}

export async function listAllProjectsAction(): Promise<{
  data?: ProjectDto[]
  error?: string
}> {
  try {
    const client = ClientFactory.getHarnessClient()
    const pageSize = 500
    const projects: ProjectDto[] = []
    let offset = 0

    while (true) {
      const page = await client.listProjects(undefined, undefined, pageSize, offset)
      projects.push(...page)
      if (page.length < pageSize) break
      offset += page.length
    }

    return { data: projects }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Failed to list projects'
    return { error: msg }
  }
}

export async function createProjectAction(
  payload: CreateProjectDto
): Promise<{ success: boolean; data?: ProjectDto; error?: string }> {
  try {
    if (!payload.tenant_id?.trim()) {
      return { success: false, error: 'Tenant é obrigatório' }
    }
    if (!payload.key?.trim()) {
      return { success: false, error: 'Chave do projeto é obrigatória' }
    }
    const client = ClientFactory.getHarnessClient()
    const data = await client.createProject({
      tenant_id: payload.tenant_id.trim(),
      key: payload.key.trim().toLowerCase(),
      name: payload.name?.trim() || null,
      metadata: payload.metadata || {},
    })
    revalidatePath('/projects')
    return { success: true, data }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Erro ao criar projeto'
    return { success: false, error: msg }
  }
}

export async function updateProjectAction(
  tenantId: string,
  projectKey: string,
  payload: UpdateProjectDto
): Promise<{ success: boolean; data?: ProjectDto; error?: string }> {
  try {
    const client = ClientFactory.getHarnessClient()
    const data = await client.updateProject(tenantId, projectKey, payload)
    revalidatePath('/projects')
    return { success: true, data }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Erro ao atualizar projeto'
    return { success: false, error: msg }
  }
}

export async function deleteProjectAction(
  tenantId: string,
  projectKey: string
): Promise<{ success: boolean; error?: string }> {
  try {
    const client = ClientFactory.getHarnessClient()
    await client.deleteProject(tenantId, projectKey)
    revalidatePath('/projects')
    return { success: true }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Erro ao excluir projeto'
    return { success: false, error: msg }
  }
}
