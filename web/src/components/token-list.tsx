'use client'

import { useState } from 'react'
import { CredentialReviewItem } from '@/domain/credential-review-item'
import { revokeTokenAction } from '@/app/actions/tokens'
import { Trash2, Key, CheckCircle, Clock, FolderGit2 } from 'lucide-react'

interface TokenListProps {
  credentials?: readonly CredentialReviewItem[]
  items?: readonly CredentialReviewItem[]
  onTokenRevoked: () => void | boolean | Promise<void | boolean>
}

export function TokenList({ credentials, items, onTokenRevoked }: TokenListProps) {
  const reviewItems = items ?? credentials ?? []
  const [searchTerm, setSearchTerm] = useState('')
  const [revokingId, setRevokingId] = useState<string | null>(null)
  const [confirmRevokeId, setConfirmRevokeId] = useState<string | null>(null)
  const [revokeError, setRevokeError] = useState<{ tokenId: string; message: string } | null>(null)

  const handleRevoke = async (id: string) => {
    if (revokingId !== null) return
    setRevokingId(id)
    try {
      const result = await revokeTokenAction(id)
      if (result.success) {
        const refreshed = await onTokenRevoked()
        if (refreshed === false) {
          setRevokeError({ tokenId: id, message: 'Credential revoked, but review refresh failed. Refresh to confirm current state.' })
        } else {
          setConfirmRevokeId(null)
          setRevokeError(null)
        }
      } else {
        setRevokeError({ tokenId: id, message: result.error || 'Failed to revoke token' })
      }
    } finally {
      setRevokingId(null)
    }
  }

  const filteredCredentials = reviewItems.filter(
    (t) =>
      t.token.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.ownerName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.ownerType.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (t.organizationName && t.organizationName.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (t.token.project_keys && t.token.project_keys.some((p) => p.toLowerCase().includes(searchTerm.toLowerCase())))
  )

  const renderProjectBadges = (projects?: string[]) => {
    if (!projects || projects.length === 0 || projects.includes('*')) {
      return (
        <span className="inline-flex items-center rounded-full bg-cyan-500/10 px-2 py-0.5 text-[11px] font-medium text-cyan-400 border border-cyan-500/20">
          <FolderGit2 className="mr-1 h-3 w-3" /> All (*)
        </span>
      )
    }
    return (
      <div className="flex flex-wrap gap-1 max-w-[200px]">
        {projects.map((p) => (
          <span
            key={p}
            className="inline-flex items-center rounded-full bg-cyan-500/10 px-2 py-0.5 text-[11px] font-medium text-cyan-400 border border-cyan-500/20"
          >
            <FolderGit2 className="mr-1 h-3 w-3" /> {p}
          </span>
        ))}
      </div>
    )
  }

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

  const isExpired = (token: CredentialReviewItem['token']) => {
    return token.expires_at ? new Date(token.expires_at).getTime() < Date.now() : false
  }

  const renderStatus = (token: CredentialReviewItem['token']) => {
    if (isExpired(token)) {
      return (
        <span className="inline-flex items-center text-xs text-amber-400">
          <Clock className="mr-1 h-3.5 w-3.5" /> Expired
        </span>
      )
    }

    return (
      <span className="inline-flex items-center text-xs text-emerald-400">
        <CheckCircle className="mr-1 h-3.5 w-3.5" /> Active
      </span>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <input
          type="text"
          placeholder="Filter tokens by name..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-72 rounded-lg border border-border bg-card px-3 py-2 text-xs text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
        />
        <div className="text-xs text-gray-400">
          Total: <span className="font-semibold text-white">{filteredCredentials.length}</span> token(s)
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        <table className="min-w-full divide-y divide-border text-left text-xs">
          <thead className="bg-black/30 text-gray-400 uppercase tracking-wider font-semibold">
            <tr>
              <th className="px-4 py-3">Credential Name</th>
              <th className="px-4 py-3">Allowed Scopes</th>
              <th className="px-4 py-3">Authorized Projects</th>
              <th className="px-4 py-3">Created</th>
              <th className="px-4 py-3">Expiration</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border font-normal text-gray-300">
            {filteredCredentials.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                  <Key className="mx-auto h-8 w-8 text-gray-600 mb-2 opacity-50" />
                  No tokens found.
                </td>
              </tr>
            ) : (
              filteredCredentials.map((credential) => {
                const token = credential.token
                return (
                <tr key={token.id} className="hover:bg-white/[0.02] transition">
                  <td className="px-4 py-3.5 font-medium text-white">
                    <div className="flex items-center space-x-2">
                      <Key className="h-4 w-4 text-blue-400 flex-shrink-0" />
                      <span>{token.name}</span>
                    </div>
                    <div className="ml-6 mt-1 text-[11px] text-gray-400">
                      <span className="text-gray-300">{credential.ownerName}</span>
                      <span className="ml-2 rounded-full border border-blue-500/20 bg-blue-500/10 px-1.5 py-0.5 text-blue-300">
                        {credential.ownerType}
                      </span>
                      {credential.organizationName && (
                        <span className="ml-2 text-gray-500">{credential.organizationName}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex flex-wrap gap-1">
                      {token.scopes.map(renderScopeBadge)}
                    </div>
                  </td>
                  <td className="px-4 py-3.5">
                    {renderProjectBadges(token.project_keys)}
                  </td>
                  <td className="px-4 py-3.5 text-gray-400">
                    {token.created_at ? new Date(token.created_at).toLocaleDateString('en-US') : '-'}
                  </td>
                  <td className="px-4 py-3.5 text-gray-400">
                    {token.expires_at ? (
                      new Date(token.expires_at).toLocaleDateString('en-US')
                    ) : (
                      <span className="text-gray-500 italic">Never expires</span>
                    )}
                  </td>
                  <td className="px-4 py-3.5">{renderStatus(token)}</td>
                  <td className="px-4 py-3.5 text-right">
                    {confirmRevokeId === token.id ? (
                      <div className="flex items-center justify-end space-x-2">
                        <button
                          onClick={() => handleRevoke(token.id)}
                          disabled={revokingId === token.id}
                          className="rounded bg-red-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-red-500"
                        >
                          {revokingId === token.id ? 'Revoking...' : 'Confirm'}
                        </button>
                        <button
                          onClick={() => {
                            setConfirmRevokeId(null)
                            setRevokeError(null)
                          }}
                          className="rounded bg-gray-800 px-2 py-1 text-xs text-gray-400 hover:text-white"
                        >
                          Cancel
                        </button>
                        {revokeError?.tokenId === token.id && (
                          <span className="block text-left text-[11px] text-red-300">
                            {revokeError.message}
                          </span>
                        )}
                      </div>
                    ) : (
                      <button
                        onClick={() => {
                          setRevokeError(null)
                          setConfirmRevokeId(token.id)
                        }}
                        className="inline-flex items-center text-xs text-gray-400 hover:text-red-400 transition"
                        title="Revoke token"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </td>
                </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
