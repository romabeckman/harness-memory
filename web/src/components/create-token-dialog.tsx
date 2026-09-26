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
import { listAllProjectsAction, listProjectsAction } from '@/app/actions/projects'
import { ensureServiceAccountAction } from '@/app/actions/service-accounts'
import { ProjectDto, TenantDto } from '@/application/ports/harness-api-client.port'

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
}: CreateTokenDialogProps) {
  const [name, setName] = useState('')
  const [selectedTenantId, setSelectedTenantId] = useState<string>('')
  const [tenantSelectionInitialized, setTenantSelectionInitialized] = useState(false)
  const [currentServiceAccountId, setCurrentServiceAccountId] = useState<string>('')
  const [currentServiceAccountName, setCurrentServiceAccountName] = useState<string>('')
  const [loadingServiceAccount, setLoadingServiceAccount] = useState<boolean>(false)

  const [scopes, setScopes] = useState<string[]>(['memory:read', 'memory:publish'])
  const [projectKeys, setProjectKeys] = useState<string[]>([])
  const [availableProjects, setAvailableProjects] = useState<ProjectDto[]>([])
  const [loadingProjects, setLoadingProjects] = useState(false)
  const [projectSearch, setProjectSearch] = useState('')
  const [lifetime, setLifetime] = useState<'30' | '90' | 'never'>('30')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  // Default token destination to all tenants when dialog opens.
  useEffect(() => {
    if (!isOpen) {
      setTenantSelectionInitialized(false)
      return
    }
    setSelectedTenantId(ALL_TENANTS_VALUE)
    setProjectKeys([])
    if (initialServiceAccountId) {
      setCurrentServiceAccountId(initialServiceAccountId)
    }
    if (initialServiceAccountName) {
      setCurrentServiceAccountName(initialServiceAccountName)
    }
    setTenantSelectionInitialized(true)
  }, [isOpen, initialServiceAccountId, initialServiceAccountName])

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
      setError('Nenhum tenant disponível para titular do token.')
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
        setError(saRes.error || 'Não foi possível resolver a Service Account do tenant.')
      }

      // 2. Fetch Projects for this tenant
      const projRes =
        tId === ALL_TENANTS_VALUE
          ? await listAllProjectsAction()
          : await listProjectsAction(tId, undefined, 100, 0)
      if (projRes.data) {
        setAvailableProjects(projRes.data)
        // Default to every project in the selected tenant scope.
        setProjectKeys(projRes.data.map((p) => p.key))
      } else {
        setAvailableProjects([])
        setProjectKeys([])
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Falha ao carregar dados do tenant')
    } finally {
      setLoadingProjects(false)
      setLoadingServiceAccount(false)
    }
  }, [initialTenantId, tenants])

  useEffect(() => {
    if (isOpen && tenantSelectionInitialized && selectedTenantId) {
      loadTenantContext(selectedTenantId)
    }
  }, [isOpen, tenantSelectionInitialized, selectedTenantId, loadTenantContext])

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
    selectedTenantId === ALL_TENANTS_VALUE
      ? 'Todos os tenants'
      : tenants.find((t) => t.id === selectedTenantId)?.name ||
        initialTenantName ||
        selectedTenantId

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!name.trim()) {
      setError('Por favor, defina um nome para o token.')
      return
    }

    if (!currentServiceAccountId) {
      setError('Nenhuma conta de serviço vinculada para este tenant.')
      return
    }

    if (scopes.length === 0) {
      setError('Selecione pelo menos um escopo de permissão.')
      return
    }

    if (projectKeys.length === 0) {
      setError('Selecione pelo menos um projeto para autorizar o token.')
      return
    }

    setLoading(true)

    try {
      const lifetimeDays = lifetime === 'never' ? undefined : Number(lifetime)
      const tokenProjectKeys =
        selectedTenantId === ALL_TENANTS_VALUE &&
        projectKeys.length === availableProjects.length
          ? ['*']
          : projectKeys
      const res = await createTokenAction({
        name: name.trim(),
        serviceAccountId: currentServiceAccountId,
        scopes,
        projectKeys: tokenProjectKeys,
        lifetimeDays,
      })

      if (res.success && res.plaintext) {
        setName('')
        onSuccess(res.plaintext)
      } else {
        setError(res.error || 'Falha ao emitir token.')
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erro inesperado')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between border-b border-border pb-4">
          <div className="flex items-center space-x-2 text-white">
            <PlusCircle className="h-5 w-5 text-blue-400" />
            <h2 className="text-lg font-semibold">Emitir Novo Access Token</h2>
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
            <label className="block text-xs font-medium uppercase tracking-wider text-gray-400 mb-1">
              Nome do Token
            </label>
            <input
              type="text"
              required
              placeholder="ex: github-actions-checkout, cursor-mcp"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-border bg-black/40 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Tenant Selector */}
          <div>
            <label className="block text-xs font-medium uppercase tracking-wider text-gray-400 mb-1">
              Organização Destino (Tenant)
            </label>
            {tenants.length > 0 ? (
              <div className="relative">
                <select
                  value={selectedTenantId}
                  onChange={(e) => setSelectedTenantId(e.target.value)}
                  disabled={loading || loadingProjects || loadingServiceAccount}
                  className="w-full rounded-lg border border-border bg-black/40 px-3 py-2 text-xs text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value={ALL_TENANTS_VALUE}>
                    Todos os projetos (todos os tenants)
                  </option>
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

          {/* Service Account Context */}
          <div className="rounded-lg border border-border bg-black/20 p-2.5 text-xs text-gray-400 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Shield className="h-3.5 w-3.5 text-emerald-400" />
              <span>Titular (Service Account):</span>
              <span className="font-semibold text-white">
                {loadingServiceAccount
                  ? 'Identificando...'
                  : currentServiceAccountName || 'default-automation'}
              </span>
            </div>
            {currentServiceAccountId && (
              <span className="text-[10px] font-mono text-gray-500">
                ID: {currentServiceAccountId.substring(0, 8)}...
              </span>
            )}
          </div>

          {/* Project Permissions Selector */}
          <div>
            {selectedTenantId !== ALL_TENANTS_VALUE && (
              <div className="flex items-center justify-between mb-2">
                <label className="block text-xs font-medium uppercase tracking-wider text-gray-400">
                  Projetos Autorizados (Obrigatório)
                </label>
                {availableProjects.length > 0 && (
                  <button
                    type="button"
                    onClick={handleSelectAllProjects}
                    disabled={loading || loadingProjects || loadingServiceAccount}
                    className="text-xs text-blue-400 hover:text-blue-300 transition"
                  >
                    {projectKeys.length === availableProjects.length
                      ? 'Desmarcar Todos'
                      : 'Selecionar Todos'}
                  </button>
                )}
              </div>
            )}

            {loadingProjects ? (
              <div className="rounded-lg border border-border bg-black/20 p-4 text-center text-xs text-gray-400">
                Carregando projetos...
              </div>
            ) : availableProjects.length === 0 ? (
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300 flex items-start space-x-2">
                <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                <span>
                  Nenhum projeto encontrado em {activeTenantName}. Cadastre ao menos um projeto antes de emitir tokens de acesso.
                </span>
              </div>
            ) : (
              <div className="space-y-2">
                {availableProjects.length > 4 && (
                  <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-gray-500" />
                    <input
                      type="text"
                      placeholder="Filtrar projetos..."
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
                      Nenhum projeto corresponde ao filtro.
                    </div>
                  )}
                </div>
                <div className="text-[11px] text-gray-400">
                  {projectKeys.length} de {availableProjects.length} projeto(s) selecionado(s).
                </div>
              </div>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium uppercase tracking-wider text-gray-400 mb-2">
              Escopos Permitidos (Menor Privilégio)
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
                    Permite leitura contextual e consultas via FastMCP para agentes de IA e desenvolvedores.
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
                    Permite publicação de snapshots imutáveis em esteiras de CI/CD (SDK Publisher).
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
                    Permite execução de análises de impacto e raio de alcance transversal no grafo.
                  </span>
                </div>
              </label>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium uppercase tracking-wider text-gray-400 mb-2">
              Prazo de Validade / Expiração
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
                30 Dias
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
                90 Dias
              </button>
              <button
                type="button"
                onClick={() => setLifetime('never')}
                className={`rounded-lg border px-3 py-2 text-xs font-medium transition ${
                  lifetime === 'never'
                    ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                    : 'border-border bg-black/20 text-gray-400 hover:bg-black/40'
                }`}
              >
                Nunca Expira
              </button>
            </div>
          </div>

          <div className="flex justify-end space-x-3 pt-3 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="rounded-lg border border-border bg-gray-800 px-4 py-2 text-sm font-medium text-gray-300 hover:bg-gray-700 transition"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading || loadingProjects || loadingServiceAccount}
              className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-500 transition disabled:opacity-50"
            >
              {loading ? 'Emitindo...' : 'Criar Token'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
