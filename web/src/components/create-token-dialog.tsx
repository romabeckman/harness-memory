'use client'

import { useEffect, useState, useCallback } from 'react'
import {
  PlusCircle,
  X,
  ShieldAlert,
  FolderGit2,
  Search,
  AlertCircle,
  Shield,
  Building2,
} from 'lucide-react'
import { createTokenAction } from '@/app/actions/tokens'
import { listTenantProjectsAction } from '@/app/actions/projects'
import { ensureServiceAccountAction } from '@/app/actions/service-accounts'
import { ProjectDto, TenantDto } from '@/application/ports/harness-api-client.port'
import { ServiceAccountTokenOwner } from '@/domain/access-token-order'
import { UserTokenOwner } from '@/domain/user-token-owner'

const ALL_TENANTS_VALUE = '__all_tenants__'
const NO_TENANTS: TenantDto[] = []

interface CreateTokenDialogProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (plaintext: string) => void
  serviceAccountId?: string
  serviceAccountName?: string
  tenantId?: string
  tenantName?: string
  tenants?: TenantDto[]
  userOwner?: UserTokenOwner
  serviceAccountOwner?: ServiceAccountTokenOwner
}

export function CreateTokenDialog({
  isOpen,
  onClose,
  onSuccess,
  serviceAccountId: initialServiceAccountId,
  serviceAccountName: initialServiceAccountName,
  tenantId: initialTenantId,
  tenantName: initialTenantName,
  tenants = NO_TENANTS,
  userOwner,
  serviceAccountOwner,
}: CreateTokenDialogProps) {
  const [name, setName] = useState('')
  const [selectedTenantId, setSelectedTenantId] = useState<string>(ALL_TENANTS_VALUE)
  const [tenantSelectionInitialized, setTenantSelectionInitialized] = useState(false)
  const [currentServiceAccountId, setCurrentServiceAccountId] = useState<string>('')
  const [currentServiceAccountName, setCurrentServiceAccountName] = useState<string>('')
  const [loadingServiceAccount, setLoadingServiceAccount] = useState<boolean>(false)
  const [serviceAccountProjectAccess, setServiceAccountProjectAccess] = useState<'all' | 'owner-tenant'>('all')

  const [scopes, setScopes] = useState<string[]>(['memory:read', 'memory:publish'])
  const [projectKeys, setProjectKeys] = useState<string[]>([])
  const [availableProjects, setAvailableProjects] = useState<ProjectDto[]>([])
  const [loadingProjects, setLoadingProjects] = useState(false)
  const [projectSearch, setProjectSearch] = useState('')
  const [lifetime, setLifetime] = useState<'30' | '90' | '365' | 'never'>('30')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  // Default token destination to all tenants when dialog opens.
  useEffect(() => {
    if (!isOpen) {
      setTenantSelectionInitialized(false)
      return
    }
    setName('')
    setError(null)
    setSelectedTenantId(ALL_TENANTS_VALUE)
    setProjectKeys([])
    setAvailableProjects([])
    setLoadingProjects(false)
    setServiceAccountProjectAccess('all')
    setLifetime('30')
    if (userOwner) {
      setCurrentServiceAccountId('')
      setCurrentServiceAccountName('')
      setTenantSelectionInitialized(false)
      return
    }
    if (serviceAccountOwner) {
      setCurrentServiceAccountId(serviceAccountOwner.id)
      setCurrentServiceAccountName(serviceAccountOwner.name)
      setTenantSelectionInitialized(false)
      return
    }
    if (initialServiceAccountId) {
      setCurrentServiceAccountId(initialServiceAccountId)
    }
    if (initialServiceAccountName) {
      setCurrentServiceAccountName(initialServiceAccountName)
    }
    setTenantSelectionInitialized(true)
  }, [isOpen, initialServiceAccountId, initialServiceAccountName, serviceAccountOwner?.id, userOwner?.id])

  // Fetch Service Account and Projects when selected tenant changes
  const loadTenantContext = useCallback(async (tId: string) => {
    const serviceAccountTenantId =
      tId === ALL_TENANTS_VALUE ? initialTenantId || tenants[0]?.id : tId
    if (!serviceAccountTenantId) {
      setLoadingProjects(false)
      setLoadingServiceAccount(false)
      setCurrentServiceAccountId('')
      setCurrentServiceAccountName('')
      setAvailableProjects([])
      setProjectKeys([])
      setError('No tenant is available to own this token.')
      return
    }
    setLoadingProjects(true)
    setLoadingServiceAccount(true)
    setError(null)

    try {
      // 1. Resolve Service Account for this tenant
      const saRes = await ensureServiceAccountAction(serviceAccountTenantId)
      if (saRes.data) {
        setCurrentServiceAccountId(saRes.data.id)
        setCurrentServiceAccountName(saRes.data.name)
      } else {
        setError(saRes.error || 'Could not find a service account for this tenant.')
      }

      if (tId === ALL_TENANTS_VALUE) {
        setAvailableProjects([])
        setProjectKeys([])
        return
      }

      // Fetch projects only for a selected tenant.
      const projRes = await listTenantProjectsAction(tId)
      if (projRes.data) {
        setAvailableProjects(projRes.data)
        // Default to every project in the selected tenant scope.
        setProjectKeys(projRes.data.map((p) => p.key))
      } else {
        setAvailableProjects([])
        setProjectKeys([])
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load tenant data')
    } finally {
      setLoadingProjects(false)
      setLoadingServiceAccount(false)
    }
  }, [initialTenantId, tenants])

  useEffect(() => {
    if (!userOwner && !serviceAccountOwner && isOpen && tenantSelectionInitialized && selectedTenantId) {
      loadTenantContext(selectedTenantId)
    }
  }, [isOpen, tenantSelectionInitialized, selectedTenantId, loadTenantContext, serviceAccountOwner, userOwner])

  useEffect(() => {
    if (!isOpen || !userOwner || selectedTenantId === ALL_TENANTS_VALUE) return

    let cancelled = false
    setLoadingProjects(true)
    setError(null)

    listTenantProjectsAction(selectedTenantId)
      .then((result) => {
        if (cancelled) return
        if (result.data) {
          setAvailableProjects(result.data)
          setProjectKeys(result.data.map((project) => project.key))
        } else {
          setAvailableProjects([])
          setProjectKeys([])
          setError(result.error || 'Could not load projects for this user.')
        }
      })
      .catch((requestError: unknown) => {
        if (!cancelled) {
          setAvailableProjects([])
          setProjectKeys([])
          setError(requestError instanceof Error ? requestError.message : 'Could not load projects for this user.')
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingProjects(false)
      })

    return () => {
      cancelled = true
    }
  }, [isOpen, userOwner?.id, selectedTenantId])

  useEffect(() => {
    if (!isOpen || !serviceAccountOwner || serviceAccountProjectAccess !== 'owner-tenant') return

    let cancelled = false
    setLoadingProjects(true)
    setError(null)
    listTenantProjectsAction(serviceAccountOwner.tenantId)
      .then((result) => {
        if (cancelled) return
        if (result.data) {
          setAvailableProjects(result.data)
          setProjectKeys(result.data.map((project) => project.key))
        } else {
          setAvailableProjects([])
          setProjectKeys([])
          setError(result.error || 'Could not load projects for this organization.')
        }
      })
      .catch((requestError: unknown) => {
        if (!cancelled) {
          setAvailableProjects([])
          setProjectKeys([])
          setError(requestError instanceof Error ? requestError.message : 'Could not load projects for this organization.')
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingProjects(false)
      })

    return () => {
      cancelled = true
    }
  }, [isOpen, serviceAccountOwner?.tenantId, serviceAccountProjectAccess])

  if (!isOpen) return null

  const handleToggleScope = (scope: string) => {
    setScopes((prev) =>
      prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope]
    )
  }

  const handleToggleProject = (key: string) => {
    setProjectKeys((prev) =>
      prev.includes(key) ? prev.filter((p) => p !== key) : [...prev, key]
    )
  }

  const handleSelectAllProjects = () => {
    if (projectKeys.length === availableProjects.length) {
      setProjectKeys([])
    } else {
      setProjectKeys(availableProjects.map((p) => p.key))
    }
  }

  const filteredProjects = availableProjects.filter(
    (p) =>
      p.key.toLowerCase().includes(projectSearch.toLowerCase()) ||
      (p.name && p.name.toLowerCase().includes(projectSearch.toLowerCase()))
  )

  const activeTenantName =
    serviceAccountOwner
      ? serviceAccountOwner.tenantName
      : selectedTenantId === ALL_TENANTS_VALUE
      ? 'All tenants'
      : tenants.find((t) => t.id === selectedTenantId)?.name ||
        initialTenantName ||
        selectedTenantId

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!name.trim()) {
      setError('Enter a name for the token.')
      return
    }

    if (!userOwner && !serviceAccountOwner && !currentServiceAccountId) {
      setError('No service account is linked to this tenant.')
      return
    }

    if (scopes.length === 0) {
      setError('Select at least one permission scope.')
      return
    }

    const requiresProject = userOwner
      ? selectedTenantId !== ALL_TENANTS_VALUE
      : serviceAccountOwner
        ? serviceAccountProjectAccess === 'owner-tenant'
        : selectedTenantId !== ALL_TENANTS_VALUE
    if (requiresProject && projectKeys.length === 0) {
      setError('Select at least one project for this token.')
      return
    }

    setLoading(true)

    try {
      const lifetimeDays = lifetime === 'never' ? undefined : Number(lifetime)
      const tokenProjectKeys = requiresProject ? projectKeys : []
      const res = await createTokenAction({
        name: name.trim(),
        owner:
          userOwner ||
          serviceAccountOwner ||
          ({
            kind: 'service-account',
            id: currentServiceAccountId,
            name: currentServiceAccountName || 'Service account',
            tenantId: initialTenantId || '',
            tenantName: initialTenantName || '',
          } satisfies ServiceAccountTokenOwner),
        scopes,
        projectKeys: tokenProjectKeys,
        lifetimeDays,
      })

      if (res.success && res.plaintext) {
        setName('')
        onSuccess(res.plaintext)
      } else {
        setError(res.error || 'Failed to issue token.')
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unexpected error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div
        aria-labelledby="create-token-title"
        aria-modal="true"
        className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-200"
        role="dialog"
      >
        <div className="flex items-center justify-between border-b border-border pb-4">
          <div className="flex items-center space-x-2 text-white">
            <PlusCircle className="h-5 w-5 text-blue-400" />
            <h2 className="text-lg font-semibold" id="create-token-title">Issue New Access Token</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300 flex items-center space-x-2">
            <ShieldAlert className="h-4 w-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium uppercase tracking-wider text-gray-400 mb-1" htmlFor="token-name">
              Token Name
            </label>
            <input
              id="token-name"
              type="text"
              required
              placeholder="e.g., github-actions-checkout, cursor-mcp"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-border bg-black/40 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {userOwner ? (
            <>
              <div className="rounded-lg border border-border bg-black/20 p-2.5 text-xs text-gray-400 flex items-center space-x-2">
                <Shield className="h-3.5 w-3.5 text-emerald-400" />
                <span>Owner (User):</span>
                <span className="font-semibold text-white">{userOwner.name}</span>
              </div>
              <div>
                <label htmlFor="user-project-access" className="block text-xs font-medium uppercase tracking-wider text-gray-400 mb-1">
                  Tenant and Project Access
                </label>
                <select
                  id="user-project-access"
                  aria-label="Tenant and project access"
                  value={selectedTenantId}
                  onChange={(event) => {
                    const nextAccess = event.target.value
                    setSelectedTenantId(nextAccess)
                    setProjectKeys([])
                    setAvailableProjects([])
                    if (nextAccess === ALL_TENANTS_VALUE) setLoadingProjects(false)
                  }}
                  disabled={loading || loadingProjects}
                  className="w-full rounded-lg border border-border bg-black/40 px-3 py-2 text-xs text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value={ALL_TENANTS_VALUE}>All projects (all tenants)</option>
                  {tenants.filter((tenant) => tenant.status === 'active').map((tenant) => (
                    <option key={tenant.id} value={tenant.id}>{tenant.name} ({tenant.key})</option>
                  ))}
                </select>
              </div>
            </>
          ) : serviceAccountOwner ? (
            <>
              <div className="rounded-lg border border-border bg-black/20 p-2.5 text-xs text-gray-400">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Shield className="h-3.5 w-3.5 text-emerald-400" />
                    <span>Owner (Service Account):</span>
                    <span className="font-semibold text-white">{serviceAccountOwner.name}</span>
                  </div>
                  <span className="font-mono text-[10px] text-gray-500">ID: {serviceAccountOwner.id.substring(0, 8)}...</span>
                </div>
                <div className="mt-1 pl-5 text-[11px] text-gray-400">
                  Organization: <span className="text-gray-200">{serviceAccountOwner.tenantName}</span>
                </div>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium uppercase tracking-wider text-gray-400" htmlFor="service-account-project-access">
                  Project Access
                </label>
                <select
                  aria-label="Project access"
                  className="w-full rounded-lg border border-border bg-black/40 px-3 py-2 text-xs text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  disabled={loading || loadingProjects}
                  id="service-account-project-access"
                  onChange={(event) => {
                    const nextAccess = event.target.value as 'all' | 'owner-tenant'
                    setServiceAccountProjectAccess(nextAccess)
                    setProjectKeys([])
                    setAvailableProjects([])
                    if (nextAccess === 'all') setLoadingProjects(false)
                  }}
                  value={serviceAccountProjectAccess}
                >
                  <option value="all">All projects (all tenants)</option>
                  <option value="owner-tenant">Projects in owner organization</option>
                </select>
              </div>
            </>
          ) : (
            <>
              <div>
                <label className="block text-xs font-medium uppercase tracking-wider text-gray-400 mb-1">
                  Destination Organization (Tenant)
                </label>
                {tenants.length > 0 ? (
                  <div className="relative">
                    <select
                      value={selectedTenantId}
                      onChange={(e) => setSelectedTenantId(e.target.value)}
                      disabled={loading || loadingProjects || loadingServiceAccount}
                      className="w-full rounded-lg border border-border bg-black/40 px-3 py-2 text-xs text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    >
                      <option value={ALL_TENANTS_VALUE}>All projects (all tenants)</option>
                      {tenants.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name} ({t.key})
                        </option>
                      ))}
                    </select>
                  </div>
                ) : (
                  <div className="w-full rounded-lg border border-border bg-black/20 px-3 py-2 text-xs text-gray-300 flex items-center space-x-2">
                    <Building2 className="h-3.5 w-3.5 text-blue-400" />
                    <span>{activeTenantName}</span>
                  </div>
                )}
              </div>

              <div className="rounded-lg border border-border bg-black/20 p-2.5 text-xs text-gray-400 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Shield className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Owner (Service Account):</span>
                  <span className="font-semibold text-white">
                    {loadingServiceAccount
                      ? 'Identifying...'
                      : currentServiceAccountName || 'default-automation'}
                  </span>
                </div>
                {currentServiceAccountId && (
                  <span className="text-[10px] font-mono text-gray-500">
                    ID: {currentServiceAccountId.substring(0, 8)}...
                  </span>
                )}
              </div>
            </>
          )}

          {/* Project Permissions Selector */}
          {(userOwner
            ? selectedTenantId !== ALL_TENANTS_VALUE
            : serviceAccountOwner
              ? serviceAccountProjectAccess === 'owner-tenant'
              : selectedTenantId !== ALL_TENANTS_VALUE) && (
          <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-xs font-medium uppercase tracking-wider text-gray-400">
                  Authorized Projects (Required)
                </label>
                {availableProjects.length > 0 && (
                  <button
                    type="button"
                    onClick={handleSelectAllProjects}
                    disabled={loading || loadingProjects || loadingServiceAccount}
                    className="text-xs text-blue-400 hover:text-blue-300 transition"
                  >
                    {projectKeys.length === availableProjects.length
                      ? 'Deselect All'
                      : 'Select All'}
                  </button>
                )}
              </div>

            {loadingProjects ? (
              <div className="rounded-lg border border-border bg-black/20 p-4 text-center text-xs text-gray-400">
                Loading projects...
              </div>
            ) : availableProjects.length === 0 ? (
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300 flex items-start space-x-2">
                <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                <span>
                  No projects found in {activeTenantName}. Create at least one project before issuing access tokens.
                </span>
              </div>
            ) : (
              <div className="space-y-2">
                {availableProjects.length > 4 && (
                  <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-gray-500" />
                    <input
                      type="text"
                      placeholder="Filter projects..."
                      value={projectSearch}
                      onChange={(e) => setProjectSearch(e.target.value)}
                      className="w-full rounded-lg border border-border bg-black/30 pl-8 pr-3 py-1.5 text-xs text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
                    />
                  </div>
                )}
                <div className="max-h-36 overflow-y-auto space-y-1.5 rounded-lg border border-border bg-black/20 p-2">
                  {filteredProjects.map((project) => {
                    const isSelected = projectKeys.includes(project.key)
                    return (
                      <label
                        key={project.id}
                        className={`flex items-center space-x-2.5 p-2 rounded-md border cursor-pointer transition ${
                          isSelected
                            ? 'border-blue-500/40 bg-blue-500/10 text-white'
                            : 'border-border/50 bg-black/20 text-gray-400 hover:bg-black/30'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => handleToggleProject(project.key)}
                          className="rounded border-gray-700 bg-gray-900 text-blue-600 focus:ring-blue-500"
                        />
                        <FolderGit2 className="h-3.5 w-3.5 text-cyan-400 flex-shrink-0" />
                        <div className="flex flex-col min-w-0">
                          <span className="text-xs font-medium text-white truncate">{project.key}</span>
                          {project.name && (
                            <span className="text-[10px] text-gray-400 truncate">{project.name}</span>
                          )}
                        </div>
                      </label>
                    )
                  })}
                  {filteredProjects.length === 0 && (
                    <div className="p-2 text-center text-xs text-gray-500">
                      No projects match the filter.
                    </div>
                  )}
                </div>
                <div className="text-[11px] text-gray-400">
                  {projectKeys.length} of {availableProjects.length} projects selected.
                </div>
              </div>
            )}
          </div>

          )}

          <div>
            <label className="block text-xs font-medium uppercase tracking-wider text-gray-400 mb-2">
              Allowed Scopes (Least Privilege)
            </label>
            <div className="space-y-2">
              <label className="flex items-start space-x-3 p-2.5 rounded-lg border border-border bg-black/20 hover:bg-black/30 cursor-pointer">
                <input
                  type="checkbox"
                  checked={scopes.includes('memory:read')}
                  onChange={() => handleToggleScope('memory:read')}
                  className="mt-0.5 rounded border-gray-700 bg-gray-900 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <span className="block text-sm font-medium text-white">memory:read</span>
                  <span className="block text-xs text-gray-400">
                    Allows contextual reads and FastMCP queries for AI agents and developers.
                  </span>
                </div>
              </label>

              <label className="flex items-start space-x-3 p-2.5 rounded-lg border border-border bg-black/20 hover:bg-black/30 cursor-pointer">
                <input
                  type="checkbox"
                  checked={scopes.includes('memory:publish')}
                  onChange={() => handleToggleScope('memory:publish')}
                  className="mt-0.5 rounded border-gray-700 bg-gray-900 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <span className="block text-sm font-medium text-white">memory:publish</span>
                  <span className="block text-xs text-gray-400">
                    Allows publishing immutable snapshots from CI/CD pipelines (SDK Publisher).
                  </span>
                </div>
              </label>

              <label className="flex items-start space-x-3 p-2.5 rounded-lg border border-border bg-black/20 hover:bg-black/30 cursor-pointer">
                <input
                  type="checkbox"
                  checked={scopes.includes('memory:impact')}
                  onChange={() => handleToggleScope('memory:impact')}
                  className="mt-0.5 rounded border-gray-700 bg-gray-900 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <span className="block text-sm font-medium text-white">memory:impact</span>
                  <span className="block text-xs text-gray-400">
                    Allows impact and blast radius analysis across the graph.
                  </span>
                </div>
              </label>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium uppercase tracking-wider text-gray-400 mb-2">
              Validity / Expiration
            </label>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setLifetime('30')}
                className={`rounded-lg border px-3 py-2 text-xs font-medium transition ${
                  lifetime === '30'
                    ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                    : 'border-border bg-black/20 text-gray-400 hover:bg-black/40'
                }`}
              >
                30 Days
              </button>
              <button
                type="button"
                onClick={() => setLifetime('90')}
                className={`rounded-lg border px-3 py-2 text-xs font-medium transition ${
                  lifetime === '90'
                    ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                    : 'border-border bg-black/20 text-gray-400 hover:bg-black/40'
                }`}
              >
                90 Days
              </button>
              {userOwner && (
                <button
                  type="button"
                  onClick={() => setLifetime('365')}
                  className={`rounded-lg border px-3 py-2 text-xs font-medium transition ${
                    lifetime === '365'
                      ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                      : 'border-border bg-black/20 text-gray-400 hover:bg-black/40'
                  }`}
                >
                  1 Year (365 Days)
                </button>
              )}
              {!userOwner && (
                <button
                  type="button"
                  onClick={() => setLifetime('never')}
                  className={`rounded-lg border px-3 py-2 text-xs font-medium transition ${
                    lifetime === 'never'
                      ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                      : 'border-border bg-black/20 text-gray-400 hover:bg-black/40'
                  }`}
                >
                  Never Expires
                </button>
              )}
            </div>
          </div>

          <div className="flex justify-end space-x-3 pt-3 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="rounded-lg border border-border bg-gray-800 px-4 py-2 text-sm font-medium text-gray-300 hover:bg-gray-700 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || loadingProjects || loadingServiceAccount}
              className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-500 transition disabled:opacity-50"
            >
              {loading ? 'Issuing...' : 'Create Token'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
