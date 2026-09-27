'use client'

import { useEffect, useState } from 'react'
import { AlertCircle, Building2, X } from 'lucide-react'
import { createServiceAccountAction, updateServiceAccountAction } from '@/app/actions/service-accounts'
import { ServiceAccountDto, TenantDto } from '@/application/ports/harness-api-client.port'

interface ServiceAccountDialogProps {
  account?: ServiceAccountDto | null
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  organizations: TenantDto[]
}

export function getInitialServiceAccountTenantId(
  account?: ServiceAccountDto | null,
  _organizations?: TenantDto[]
): string {
  return account?.tenant_id || ''
}

export function ServiceAccountDialog({
  account,
  isOpen,
  onClose,
  onSuccess,
  organizations,
}: ServiceAccountDialogProps) {
  const isEditing = Boolean(account)
  const activeOrganizations = organizations.filter((organization) => organization.status !== 'disabled')
  const [name, setName] = useState(account?.name || '')
  const [tenantId, setTenantId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen) return
    setName(account?.name || '')
    setTenantId(getInitialServiceAccountTenantId(account, organizations))
    setError(null)
  }, [account, isOpen, organizations])

  if (!isOpen) return null

  const organizationName =
    organizations.find((organization) => organization.id === account?.tenant_id)?.name ||
    account?.tenant_id ||
    'Unknown organization'

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    const trimmedName = name.trim()
    setError(null)
    if (!trimmedName) {
      setError('Service account name is required.')
      return
    }
    if (trimmedName.length > 120) {
      setError('Service account name cannot exceed 120 characters.')
      return
    }
    if (!isEditing && !tenantId) {
      setError('Organization is required.')
      return
    }

    setLoading(true)
    const result = isEditing && account
      ? await updateServiceAccountAction(account.id, { name: trimmedName })
      : await createServiceAccountAction({ name: trimmedName, tenantId })
    setLoading(false)
    if (result.success) {
      onSuccess()
    } else {
      setError(result.error || 'Failed to save service account.')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <section
        aria-labelledby="service-account-dialog-title"
        aria-modal="true"
        className="w-full max-w-md space-y-5 rounded-xl border border-border bg-card p-6 shadow-2xl"
        role="dialog"
      >
        <header className="flex items-center justify-between border-b border-border pb-4">
          <div className="flex items-center gap-2.5">
            <Building2 aria-hidden="true" className="h-5 w-5 text-blue-400" />
            <div>
              <h2 className="text-sm font-semibold text-white" id="service-account-dialog-title">
                {isEditing ? 'Edit Service Account' : 'New Service Account'}
              </h2>
              <p className="text-[11px] text-gray-400">Manage automation identity name and organization.</p>
            </div>
          </div>
          <button aria-label="Close service account dialog" className="rounded-lg p-1 text-gray-400 hover:text-white" disabled={loading} onClick={onClose} type="button">
            <X aria-hidden="true" className="h-4 w-4" />
          </button>
        </header>

        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-300" role="alert">
            <AlertCircle aria-hidden="true" className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form className="space-y-4" onSubmit={handleSubmit}>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-300" htmlFor="service-account-name">Name</label>
            <input
              autoComplete="off"
              className="w-full rounded-lg border border-border bg-black/30 px-3 py-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
              disabled={loading}
              id="service-account-name"
              maxLength={120}
              onChange={(event) => setName(event.target.value)}
              required
              type="text"
              value={name}
            />
          </div>

          {isEditing ? (
            <p className="rounded-lg border border-border bg-black/20 px-3 py-2 text-xs text-gray-300">
              {`Organization: ${organizationName}`}
            </p>
          ) : (
            <div>
              <label className="mb-1.5 block text-xs font-medium text-gray-300" htmlFor="service-account-organization">
                Organization <span className="text-red-300">(required)</span>
              </label>
              <select
                className="w-full rounded-lg border border-border bg-black/30 px-3 py-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                disabled={loading}
                id="service-account-organization"
                onChange={(event) => setTenantId(event.target.value)}
                required
                value={tenantId}
              >
                <option value="">Select an active organization</option>
                {activeOrganizations.map((organization) => (
                  <option key={organization.id} value={organization.id}>{organization.name}</option>
                ))}
              </select>
            </div>
          )}

          <footer className="flex justify-end gap-2 border-t border-border pt-3">
            <button className="rounded-lg border border-border px-3.5 py-2 text-xs text-gray-300 hover:bg-white/5 disabled:opacity-50" disabled={loading} onClick={onClose} type="button">Cancel</button>
            <button className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50" disabled={loading} type="submit">
              {loading ? 'Saving...' : isEditing ? 'Save Changes' : 'Create Service Account'}
            </button>
          </footer>
        </form>
      </section>
    </div>
  )
}
