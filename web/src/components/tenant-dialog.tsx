'use client'

import { useState } from 'react'
import { X, Building2, AlertCircle } from 'lucide-react'
import { TenantDto } from '@/application/ports/harness-api-client.port'
import { createTenantAction, updateTenantAction } from '@/app/actions/tenants'

interface TenantDialogProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  tenantToEdit?: TenantDto | null
}

export function TenantDialog({ isOpen, onClose, onSuccess, tenantToEdit }: TenantDialogProps) {
  const isEditing = !!tenantToEdit
  const [key, setKey] = useState(tenantToEdit?.key || '')
  const [name, setName] = useState(tenantToEdit?.name || '')
  const [status, setStatus] = useState<'active' | 'disabled'>(tenantToEdit?.status || 'active')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    if (isEditing && tenantToEdit) {
      const res = await updateTenantAction(tenantToEdit.id, {
        name: name.trim(),
        status,
      })
      if (res.success) {
        onSuccess()
      } else {
        setError(res.error || 'Erro ao atualizar tenant.')
      }
    } else {
      const res = await createTenantAction({
        key: key.trim().toLowerCase(),
        name: name.trim(),
      })
      if (res.success) {
        onSuccess()
      } else {
        setError(res.error || 'Erro ao criar tenant.')
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
              <Building2 className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-white">
                {isEditing ? 'Editar Organização (Tenant)' : 'Novo Tenant'}
              </h2>
              <p className="text-[11px] text-gray-400">
                {isEditing
                  ? 'Atualize o nome ou altere o status de operação'
                  : 'Cadastre uma nova organização no Harness Memory'}
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
              Chave Identificadora (Slug)
            </label>
            <input
              type="text"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              disabled={isEditing}
              placeholder="ex: acme-corp"
              required
              className="w-full rounded-lg border border-border bg-black/30 px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50 font-mono"
            />
            {!isEditing && (
              <p className="text-[10px] text-gray-500 mt-1">
                Identificador único global, imutável após criação. Use letras, números e hífens.
              </p>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1.5">
              Nome da Organização
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="ex: Acme Corporation"
              required
              className="w-full rounded-lg border border-border bg-black/30 px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {isEditing && (
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1.5">Status</label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as 'active' | 'disabled')}
                className="w-full rounded-lg border border-border bg-black/30 px-3 py-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="active">Ativo (Permite leituras e publicações)</option>
                <option value="disabled">Desativado (Operações suspensas)</option>
              </select>
            </div>
          )}

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
              {loading ? 'Salvando...' : isEditing ? 'Salvar Alterações' : 'Criar Tenant'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
