'use client'

import { useState, useEffect } from 'react'
import { X, Layers, AlertCircle } from 'lucide-react'
import { TenantDto, ProjectDto } from '@/application/ports/harness-api-client.port'
import { createProjectAction, updateProjectAction } from '@/app/actions/projects'

interface ProjectDialogProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  tenants: TenantDto[]
  defaultTenantId?: string
  projectToEdit?: ProjectDto | null
}

export function ProjectDialog({
  isOpen,
  onClose,
  onSuccess,
  tenants,
  defaultTenantId,
  projectToEdit,
}: ProjectDialogProps) {
  const isEditing = !!projectToEdit
  const [tenantId, setTenantId] = useState(
    projectToEdit?.tenant_id || defaultTenantId || tenants[0]?.id || ''
  )
  const [key, setKey] = useState(projectToEdit?.key || '')
  const [name, setName] = useState(projectToEdit?.name || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen) {
      setTenantId(projectToEdit?.tenant_id || defaultTenantId || tenants[0]?.id || '')
      setKey(projectToEdit?.key || '')
      setName(projectToEdit?.name || '')
      setError(null)
    }
  }, [isOpen, projectToEdit, defaultTenantId, tenants])

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    if (isEditing && projectToEdit) {
      const res = await updateProjectAction(projectToEdit.tenant_id, projectToEdit.key, {
        name: name.trim() || null,
      })
      if (res.success) {
        onSuccess()
      } else {
        setError(res.error || 'Erro ao atualizar projeto.')
      }
    } else {
      const res = await createProjectAction({
        tenant_id: tenantId,
        key: key.trim().toLowerCase(),
        name: name.trim() || undefined,
      })
      if (res.success) {
        onSuccess()
      } else {
        setError(res.error || 'Erro ao criar projeto.')
      }
    }
    setLoading(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-2xl space-y-5">
        <div className="flex items-center justify-between border-b border-border pb-4">
          <div className="flex items-center space-x-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600/10 border border-blue-500/20 text-blue-400">
              <Layers className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-white">
                {isEditing ? 'Editar Projeto' : 'Novo Projeto'}
              </h2>
              <p className="text-[11px] text-gray-400">
                {isEditing
                  ? 'Atualize o nome de exibição do projeto'
                  : 'Cadastre um projeto sob uma organização'}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white p-1 rounded-lg">
            <X className="h-4 w-4" />
          </button>
        </div>

        {error && (
          <div className="flex items-center space-x-2 rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-xs text-red-400">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1.5">
              Organização Proprietária (Tenant)
            </label>
            <select
              value={tenantId}
              onChange={(e) => setTenantId(e.target.value)}
              disabled={isEditing}
              required
              className="w-full rounded-lg border border-border bg-black/30 px-3 py-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
            >
              {tenants.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} ({t.key})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1.5">
              Chave do Projeto (Slug)
            </label>
            <input
              type="text"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              disabled={isEditing}
              placeholder="ex: core-service"
              required
              className="w-full rounded-lg border border-border bg-black/30 px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50 font-mono"
            />
            {!isEditing && (
              <p className="text-[10px] text-gray-500 mt-1">
                Identificador único dentro desta organização. Imutável após cadastro.
              </p>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1.5">
              Nome Amigável (Opcional)
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="ex: Core Processing Service"
              className="w-full rounded-lg border border-border bg-black/30 px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div className="flex items-center justify-end space-x-2 pt-3 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-3.5 py-2 text-xs font-medium text-gray-400 hover:text-white rounded-lg hover:bg-white/5 transition"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow hover:bg-blue-500 transition disabled:opacity-50"
            >
              {loading ? 'Salvando...' : isEditing ? 'Salvar Alterações' : 'Criar Projeto'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
