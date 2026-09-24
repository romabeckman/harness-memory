'use client'

import { useState } from 'react'
import { TokenMetadataDto } from '@/application/ports/harness-api-client.port'
import { revokeTokenAction } from '@/app/actions/tokens'
import { Trash2, Key, CheckCircle, Clock, Ban } from 'lucide-react'

interface TokenListProps {
  tokens: TokenMetadataDto[]
  onTokenRevoked: () => void
}

export function TokenList({ tokens, onTokenRevoked }: TokenListProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [revokingId, setRevokingId] = useState<string | null>(null)
  const [confirmRevokeId, setConfirmRevokeId] = useState<string | null>(null)

  const handleRevoke = async (id: string) => {
    setRevokingId(id)
    try {
      await revokeTokenAction(id)
      setConfirmRevokeId(null)
      onTokenRevoked()
    } finally {
      setRevokingId(null)
    }
  }

  const filteredTokens = tokens.filter(
    (t) =>
      t.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (t.service_account_id && t.service_account_id.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  const renderScopeBadge = (scope: string) => {
    switch (scope) {
      case 'memory:read':
        return (
          <span
            key={scope}
            className="inline-flex items-center rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-medium text-emerald-400 border border-emerald-500/20"
          >
            read
          </span>
        )
      case 'memory:publish':
        return (
          <span
            key={scope}
            className="inline-flex items-center rounded-full bg-blue-500/10 px-2.5 py-0.5 text-xs font-medium text-blue-400 border border-blue-500/20"
          >
            publish
          </span>
        )
      case 'memory:impact':
        return (
          <span
            key={scope}
            className="inline-flex items-center rounded-full bg-purple-500/10 px-2.5 py-0.5 text-xs font-medium text-purple-400 border border-purple-500/20"
          >
            impact
          </span>
        )
      default:
        return (
          <span
            key={scope}
            className="inline-flex items-center rounded-full bg-gray-500/10 px-2.5 py-0.5 text-xs font-medium text-gray-400 border border-gray-500/20"
          >
            {scope}
          </span>
        )
    }
  }

  const renderStatus = (token: TokenMetadataDto) => {
    if (token.revoked_at || !token.is_active) {
      return (
        <span className="inline-flex items-center text-xs text-red-400">
          <Ban className="mr-1 h-3.5 w-3.5" /> Revogado
        </span>
      )
    }

    if (token.expires_at && new Date(token.expires_at).getTime() < Date.now()) {
      return (
        <span className="inline-flex items-center text-xs text-amber-400">
          <Clock className="mr-1 h-3.5 w-3.5" /> Expirado
        </span>
      )
    }

    return (
      <span className="inline-flex items-center text-xs text-emerald-400">
        <CheckCircle className="mr-1 h-3.5 w-3.5" /> Ativo
      </span>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <input
          type="text"
          placeholder="Filtrar tokens por nome..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-72 rounded-lg border border-border bg-card px-3 py-2 text-xs text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
        />
        <div className="text-xs text-gray-400">
          Total: <span className="font-semibold text-white">{filteredTokens.length}</span> token(s)
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        <table className="min-w-full divide-y divide-border text-left text-xs">
          <thead className="bg-black/30 text-gray-400 uppercase tracking-wider font-semibold">
            <tr>
              <th className="px-4 py-3">Nome da Credencial</th>
              <th className="px-4 py-3">Escopos Permitidos</th>
              <th className="px-4 py-3">Criado em</th>
              <th className="px-4 py-3">Expiração</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Ação</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border font-normal text-gray-300">
            {filteredTokens.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                  <Key className="mx-auto h-8 w-8 text-gray-600 mb-2 opacity-50" />
                  Nenhum token encontrado.
                </td>
              </tr>
            ) : (
              filteredTokens.map((token) => (
                <tr key={token.id} className="hover:bg-white/[0.02] transition">
                  <td className="px-4 py-3.5 font-medium text-white">
                    <div className="flex items-center space-x-2">
                      <Key className="h-4 w-4 text-blue-400 flex-shrink-0" />
                      <span>{token.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex flex-wrap gap-1">
                      {token.scopes.map(renderScopeBadge)}
                    </div>
                  </td>
                  <td className="px-4 py-3.5 text-gray-400">
                    {new Date(token.created_at).toLocaleDateString('pt-BR')}
                  </td>
                  <td className="px-4 py-3.5 text-gray-400">
                    {token.expires_at ? (
                      new Date(token.expires_at).toLocaleDateString('pt-BR')
                    ) : (
                      <span className="text-gray-500 italic">Nunca expira</span>
                    )}
                  </td>
                  <td className="px-4 py-3.5">{renderStatus(token)}</td>
                  <td className="px-4 py-3.5 text-right">
                    {token.is_active && !token.revoked_at ? (
                      confirmRevokeId === token.id ? (
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            onClick={() => handleRevoke(token.id)}
                            disabled={revokingId === token.id}
                            className="rounded bg-red-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-red-500"
                          >
                            {revokingId === token.id ? 'Revogando...' : 'Confirmar'}
                          </button>
                          <button
                            onClick={() => setConfirmRevokeId(null)}
                            className="rounded bg-gray-800 px-2 py-1 text-xs text-gray-400 hover:text-white"
                          >
                            Cancelar
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setConfirmRevokeId(token.id)}
                          className="inline-flex items-center text-xs text-gray-400 hover:text-red-400 transition"
                          title="Revogar token"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )
                    ) : (
                      <span className="text-gray-600 text-xs italic">Inativo</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
