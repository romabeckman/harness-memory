'use client'

import { Building2, ChevronLeft, ChevronRight, Edit3, KeyRound, RefreshCw, Trash2 } from 'lucide-react'
import { ServiceAccountDto, TenantDto } from '@/application/ports/harness-api-client.port'

interface ServiceAccountTableProps {
  accounts: ServiceAccountDto[]
  organizations: TenantDto[]
  hasMore: boolean
  loading: boolean
  onCreateToken: (account: ServiceAccountDto) => void
  onDelete: (account: ServiceAccountDto) => void
  onEdit: (account: ServiceAccountDto) => void
  onPageChange: (page: number) => void
  onRefresh: () => void | Promise<void>
  onSearchChange: (value: string) => void
  page: number
  search: string
}

export function ServiceAccountTable({
  accounts,
  organizations,
  hasMore,
  loading,
  onCreateToken,
  onDelete,
  onEdit,
  onPageChange,
  onRefresh,
  onSearchChange,
  page,
  search,
}: ServiceAccountTableProps) {
  const organizationNames = new Map(organizations.map((organization) => [organization.id, organization.name]))

  return (
    <section className="overflow-hidden rounded-xl border border-border bg-card/50" aria-label="Service accounts">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4">
        <div>
          <h2 className="text-sm font-semibold text-white">Service accounts</h2>
          <p className="text-[11px] text-gray-400">Automation identities grouped by organization.</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="sr-only" htmlFor="service-account-search">Search service accounts</label>
          <input
            className="rounded-lg border border-border bg-black/30 px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            id="service-account-search"
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Search service accounts..."
            type="search"
            value={search}
          />
          <button
            aria-label="Refresh service accounts"
            className="rounded-lg p-2 text-gray-400 hover:bg-white/5 hover:text-white disabled:opacity-50"
            disabled={loading}
            onClick={() => void onRefresh()}
            type="button"
          >
            <RefreshCw aria-hidden="true" className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-border bg-black/10 text-[10px] uppercase tracking-wider text-gray-500">
            <tr>
              <th className="px-5 py-3 font-medium">Name</th>
              <th className="px-5 py-3 font-medium">Organization</th>
              <th className="px-5 py-3 text-right font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/70">
            {accounts.map((account) => (
              <tr key={account.id} className="text-gray-300 hover:bg-white/[0.02]">
                <td className="px-5 py-3 font-medium text-white">{account.name}</td>
                <td className="px-5 py-3">
                  <span className="inline-flex items-center gap-1.5 text-gray-300">
                    <Building2 aria-hidden="true" className="h-3.5 w-3.5 text-blue-400" />
                    {organizationNames.get(account.tenant_id) || account.tenant_id}
                  </span>
                </td>
                <td className="px-5 py-3">
                  <div className="flex justify-end gap-1">
                    <button
                      aria-label={`Create token for ${account.name}`}
                      className="rounded-md p-2 text-emerald-400 hover:bg-emerald-500/10"
                      onClick={() => onCreateToken(account)}
                      title={`Create token for ${account.name}`}
                      type="button"
                    >
                      <KeyRound aria-hidden="true" className="h-4 w-4" />
                    </button>
                    <button
                      aria-label={`Edit service account ${account.name}`}
                      className="rounded-md p-2 text-blue-400 hover:bg-blue-500/10"
                      onClick={() => onEdit(account)}
                      title={`Edit service account ${account.name}`}
                      type="button"
                    >
                      <Edit3 aria-hidden="true" className="h-4 w-4" />
                    </button>
                    <button
                      aria-label={`Delete service account ${account.name}`}
                      className="rounded-md p-2 text-red-400 hover:bg-red-500/10"
                      onClick={() => onDelete(account)}
                      title={`Delete service account ${account.name}`}
                      type="button"
                    >
                      <Trash2 aria-hidden="true" className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {!loading && accounts.length === 0 && (
              <tr>
                <td className="px-5 py-12 text-center text-gray-500" colSpan={3}>
                  No service accounts found.
                </td>
              </tr>
            )}
            {loading && accounts.length === 0 && (
              <tr>
                <td className="px-5 py-12 text-center text-gray-500" colSpan={3}>
                  Loading service accounts...
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between border-t border-border bg-black/10 px-5 py-3 text-xs text-gray-400">
        <span>Page {page + 1}{loading && <span className="ml-2 text-blue-400">(Updating...)</span>}</span>
        <div className="flex gap-2">
          <button
            className="inline-flex items-center gap-1 rounded-lg border border-border px-2.5 py-1.5 hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-40"
            disabled={page === 0 || loading}
            onClick={() => onPageChange(page - 1)}
            type="button"
          >
            <ChevronLeft aria-hidden="true" className="h-3.5 w-3.5" /> Previous
          </button>
          <button
            className="inline-flex items-center gap-1 rounded-lg border border-border px-2.5 py-1.5 hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-40"
            disabled={!hasMore || loading}
            onClick={() => onPageChange(page + 1)}
            type="button"
          >
            Next <ChevronRight aria-hidden="true" className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </section>
  )
}
