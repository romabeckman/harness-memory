'use server'

import { revalidatePath } from 'next/cache'
import { ClientFactory } from '@/infrastructure/api/client-factory'
import {
  ProjectDto,
  CreateProjectDto,
  UpdateProjectDto,
  EnvironmentDto,
  ProjectEnvironmentRef,
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
    const msg = err instanceof Error ? err.message : 'Failed to list projects'
    return { error: msg }
  }
}

export async function listTenantProjectsAction(tenantId: string): Promise<{
  data?: ProjectDto[]
  error?: string
}> {
  try {
    const client = ClientFactory.getHarnessClient()
    const pageSize = 100
    const projects: ProjectDto[] = []
    let offset = 0
    while (true) {
      const page = await client.listProjects(tenantId, undefined, pageSize, offset)
      projects.push(...page)
      if (page.length < pageSize) break
      offset += page.length
    }
    return { data: projects }
  } catch (err: unknown) {
    return { error: err instanceof Error ? err.message : 'Failed to list projects' }
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
      return { success: false, error: 'Tenant is required' }
    }
    if (!payload.key?.trim()) {
      return { success: false, error: 'Project key is required' }
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
    const msg = err instanceof Error ? err.message : 'Failed to create project'
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
    const msg = err instanceof Error ? err.message : 'Failed to update project'
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
    const msg = err instanceof Error ? err.message : 'Failed to delete project'
    return { success: false, error: msg }
  }
}

export async function listProjectEnvironmentsAction(
  reference: ProjectEnvironmentRef
): Promise<{ data?: EnvironmentDto[]; error?: string }> {
  try {
    const client = ClientFactory.getHarnessClient()
    const data = await client.listProjectEnvironments(reference)
    return { data }
  } catch (err: unknown) {
    return { error: err instanceof Error ? err.message : 'Failed to list environments' }
  }
}

export async function addProjectEnvironmentAction(
  reference: ProjectEnvironmentRef,
  submittedName: string
): Promise<{ success: boolean; data?: EnvironmentDto; error?: string }> {
  const name = submittedName.trim()
  if (!reference.tenantId.trim() || !reference.projectKey.trim()) {
    return { success: false, error: 'Tenant and project are required' }
  }
  if (!name) {
    return { success: false, error: 'Environment name is required' }
  }
  if (name.length > 64) {
    return { success: false, error: 'Environment name must be 64 characters or fewer' }
  }
  if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
    return { success: false, error: 'Environment name contains invalid characters' }
  }

  try {
    const client = ClientFactory.getHarnessClient()
    const data = await client.addProjectEnvironment(reference, name)
    revalidatePath('/projects')
    return { success: true, data }
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : 'Failed to add environment',
    }
  }
}
