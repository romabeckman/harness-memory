'use client'

import { useState } from 'react'
import { PlusCircle, X, ShieldAlert } from 'lucide-react'
import { createTokenAction } from '@/app/actions/tokens'

interface CreateTokenDialogProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (plaintext: string) => void
  serviceAccountId: string
  serviceAccountName: string
  tenantName: string
}

export function CreateTokenDialog({
  isOpen,
  onClose,
  onSuccess,
  serviceAccountId,
  serviceAccountName,
  tenantName,
}: CreateTokenDialogProps) {
  const [name, setName] = useState('')
  const [scopes, setScopes] = useState<string[]>(['memory:read', 'memory:publish'])
  const [lifetime, setLifetime] = useState<'30' | '90' | 'never'>('30')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  if (!isOpen) return null

  const handleToggleScope = (scope: string) => {
    setScopes((prev) =>
      prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope]
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!name.trim()) {
      setError('Por favor, defina um nome para o token.')
      return
    }

    if (scopes.length === 0) {
      setError('Selecione pelo menos um escopo de permissão.')
      return
    }

    setLoading(true)

    try {
      const lifetimeDays = lifetime === 'never' ? undefined : Number(lifetime)
      const res = await createTokenAction({
        name: name.trim(),
        serviceAccountId,
        scopes,
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
      <div className="w-full max-w-lg rounded-xl border border-border bg-card p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-200">
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

          <div className="rounded-lg border border-border bg-black/20 p-3 text-xs text-gray-400 space-y-1">
            <div>
              <span className="font-semibold text-gray-300">Tenant Destino:</span> {tenantName}
            </div>
            <div>
              <span className="font-semibold text-gray-300">Titular (Service Account):</span>{' '}
              {serviceAccountName} ({serviceAccountId})
            </div>
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
              disabled={loading}
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
