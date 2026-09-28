'use client'

import { FormEvent, useState } from 'react'
import {
  LinkedProjectDto,
  ProjectDto,
  TenantDto,
  UserDto,
} from '@/application/ports/harness-api-client.port'
import {
  listProjectLinksAction,
  createProjectLinkAction,
  deleteProjectLinkAction,
} from '@/app/actions/project-links'
import { Link2, Trash2, AlertCircle } from 'lucide-react'

export type PanelState = 'closed' | 'loading' | 'loaded' | 'submitting' | 'error'

export interface ProjectLinkPanelProps {
  project: { tenantId: string; projectKey: string; name?: string | null }
  allProjects?: ProjectDto[]
  tenants?: TenantDto[]
  users?: UserDto[]
}

export function getSelectableProjects(
  currentProject: { tenantId: string; projectKey: string },
  allProjects: ProjectDto[] = [],
  existingLinks: LinkedProjectDto[] = []
): ProjectDto[] {
  return allProjects.filter((p) => {
    if (p.tenant_id === currentProject.tenantId && p.key === currentProject.projectKey) {
      return false
    }
    const isAlreadyLinked = existingLinks.some(
      (link) => link.tenant_id === p.tenant_id && link.key === p.key
    )
    return !isAlreadyLinked
  })
}

export function ProjectLinkPanel({
  project,
  allProjects = [],
  tenants = [],
  users = [],
}: ProjectLinkPanelProps) {
  const [state, setState] = useState<PanelState>('closed')
  const [links, setLinks] = useState<LinkedProjectDto[]>([])
  const [selectedTargetKey, setSelectedTargetKey] = useState('')
  const [selectedTargetTenantId, setSelectedTargetTenantId] = useState('')
  const [selectedUserId, setSelectedUserId] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [actionInProgress, setActionInProgress] = useState(false)

  const isOpen = state !== 'closed'

  const getTenantDisplayName = (tenantId: string) => {
    const t = tenants.find((item) => item.id === tenantId)
    return t ? t.name : tenantId
  }

  const loadLinks = async () => {
    setError(null)
    setState('loading')
    const result = await listProjectLinksAction(project.tenantId, project.projectKey)
    if (result.data) {
      setLinks(result.data)
      setState('loaded')
    } else {
      setError(result.error || 'Failed to load project links.')
      setState('error')
    }
  }

  const togglePanel = () => {
    if (isOpen) {
      setState('closed')
      return
    }
    void loadLinks()
  }

  const selectableProjects = getSelectableProjects(project, allProjects, links)

  const handleSelectChange = (value: string) => {
    if (!value) {
      setSelectedTargetKey('')
      setSelectedTargetTenantId('')
      return
    }
    const [tId, pKey] = value.split(':::')
    setSelectedTargetTenantId(tId || '')
    setSelectedTargetKey(pKey || '')
  }

  const handleAddLink = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!selectedTargetKey) return

    setError(null)
    setState('submitting')
    setActionInProgress(true)

    const result = await createProjectLinkAction(project.tenantId, project.projectKey, {
      target_project_key: selectedTargetKey,
      target_tenant_id: selectedTargetTenantId || undefined,
      created_by: selectedUserId || undefined,
    })

    if (!result.success) {
      setError(result.error || 'Failed to create project link.')
      setState('loaded')
      setActionInProgress(false)
      return
    }

    setSelectedTargetKey('')
    setSelectedTargetTenantId('')
    setSelectedUserId('')

    const refreshed = await listProjectLinksAction(project.tenantId, project.projectKey)
    if (refreshed.data) {
      setLinks(refreshed.data)
      setState('loaded')
    } else {
      setError(
        `Link created, but refresh failed: ${refreshed.error || 'unknown error'}`
      )
      setState('loaded')
    }
    setActionInProgress(false)
  }

  const handleDeleteLink = async (targetKey: string, targetTenantId: string) => {
    setError(null)
    setActionInProgress(true)

    const result = await deleteProjectLinkAction(
      project.tenantId,
      project.projectKey,
      targetKey,
      targetTenantId
    )

    if (!result.success) {
      setError(result.error || 'Failed to remove project link.')
      setActionInProgress(false)
      return
    }

    setLinks((current) =>
      current.filter(
        (link) => !(link.key === targetKey && link.tenant_id === targetTenantId)
      )
    )

    const refreshed = await listProjectLinksAction(project.tenantId, project.projectKey)
    if (refreshed.data) {
      setLinks(refreshed.data)
    }
    setActionInProgress(false)
  }

  return (
    <div className="inline-block text-left relative">
      <button
        type="button"
        aria-label={`Manage links for ${project.projectKey}`}
        aria-expanded={isOpen}
        onClick={togglePanel}
        className="p-1.5 text-gray-400 hover:text-white rounded hover:bg-white/5 transition"
        title="Manage project links"
      >
        <Link2 className="h-3.5 w-3.5" />
      </button>

      {isOpen && (
        <section
          aria-label={`Links for ${project.projectKey}`}
          aria-busy={state === 'loading' || state === 'submitting' || actionInProgress}
          className="absolute right-0 mt-2 w-80 rounded-xl border border-border bg-card p-4 text-left shadow-xl z-50"
        >
          <div className="flex items-center justify-between mb-3 border-b border-border pb-2">
            <h3 className="text-xs font-semibold text-white flex items-center gap-1.5">
              <Link2 className="h-3.5 w-3.5 text-blue-400" />
              Project Links: {project.name || project.projectKey}
            </h3>
            <button
              type="button"
              onClick={() => setState('closed')}
              className="text-gray-400 hover:text-white text-xs"
            >
              ✕
            </button>
          </div>

          {state === 'loading' && (
            <p role="status" className="text-xs text-gray-400 py-2">
              Loading links...
            </p>
          )}

          {error && (
            <div
              role="alert"
              className="mb-3 rounded-lg border border-red-500/30 bg-red-500/10 p-2 text-xs text-red-300 flex items-start gap-1.5"
            >
              <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {state === 'error' && (
            <button
              type="button"
              onClick={() => void loadLinks()}
              className="mb-3 rounded border border-border px-2.5 py-1 text-xs text-white hover:bg-white/5"
            >
              Retry loading
            </button>
          )}

          {state !== 'loading' && (
            <>
              <div className="mb-3 max-h-48 overflow-y-auto space-y-1.5">
                {links.length === 0 ? (
                  <p className="text-xs text-gray-500 py-1">No linked projects</p>
                ) : (
                  links.map((link) => (
                    <div
                      key={`${link.tenant_id}-${link.key}`}
                      className="flex items-center justify-between p-2 rounded-lg border border-border bg-black/20 text-xs"
                    >
                      <div className="space-y-0.5 min-w-0 pr-2">
                        <div className="font-mono font-medium text-white truncate">
                          {link.key}
                          {link.name ? (
                            <span className="text-gray-400 font-sans ml-1">
                              ({link.name})
                            </span>
                          ) : null}
                        </div>
                        <span className="inline-block px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px]">
                          {getTenantDisplayName(link.tenant_id)}
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => void handleDeleteLink(link.key, link.tenant_id)}
                        disabled={actionInProgress}
                        className="p-1 text-gray-400 hover:text-red-400 rounded hover:bg-red-500/10 transition disabled:opacity-40 shrink-0"
                        title="Remove link"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))
                )}
              </div>

              <form onSubmit={handleAddLink} className="space-y-2 border-t border-border pt-3">
                <label className="block text-xs text-gray-300">
                  Add related project
                  <select
                    aria-label="Select project to link"
                    value={
                      selectedTargetKey
                        ? `${selectedTargetTenantId}:::${selectedTargetKey}`
                        : ''
                    }
                    onChange={(e) => handleSelectChange(e.target.value)}
                    disabled={
                      state === 'submitting' ||
                      actionInProgress ||
                      selectableProjects.length === 0
                    }
                    className="mt-1 block w-full rounded border border-border bg-black/30 px-2 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="">
                      {selectableProjects.length === 0
                        ? 'No available projects to link'
                        : 'Select project...'}
                    </option>
                    {selectableProjects.map((p) => (
                      <option
                        key={`${p.tenant_id}-${p.key}`}
                        value={`${p.tenant_id}:::${p.key}`}
                      >
                        {p.key} {p.name ? `(${p.name})` : ''} — [
                        {getTenantDisplayName(p.tenant_id)}]
                      </option>
                    ))}
                  </select>
                </label>

                {users.length > 0 && (
                  <label className="block text-xs text-gray-300">
                    Created by user (optional)
                    <select
                      aria-label="Select creator user"
                      value={selectedUserId}
                      onChange={(e) => setSelectedUserId(e.target.value)}
                      disabled={state === 'submitting' || actionInProgress}
                      className="mt-1 block w-full rounded border border-border bg-black/30 px-2 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                    >
                      <option value="">Admin / System (None)</option>
                      {users.map((u) => (
                        <option key={u.id} value={u.id}>
                          {u.name} ({u.email})
                        </option>
                      ))}
                    </select>
                  </label>
                )}

                <button
                  type="submit"
                  disabled={
                    !selectedTargetKey || state === 'submitting' || actionInProgress
                  }
                  className="w-full rounded bg-blue-600 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50 transition"
                >
                  {state === 'submitting' ? 'Linking...' : 'Link project'}
                </button>
              </form>
            </>
          )}
        </section>
      )}
    </div>
  )
}
