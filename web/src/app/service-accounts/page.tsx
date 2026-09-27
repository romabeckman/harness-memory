'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { Plus, RefreshCw, Shield } from 'lucide-react'
import { listAllTenantsAction } from '@/app/actions/tenants'
import {
  deleteServiceAccountAction,
  listServiceAccountsAction,
} from '@/app/actions/service-accounts'
import { AdminSidebar } from '@/components/admin-sidebar'
import { ConfirmDeleteDialog } from '@/components/confirm-delete-dialog'
import { CreateTokenDialog } from '@/components/create-token-dialog'
import { SecretRevealModal } from '@/components/secret-reveal-modal'
import { ServiceAccountDialog } from '@/components/service-account-dialog'
import { ServiceAccountTable } from '@/components/service-account-table'
import {
  ServiceAccountDto,
  TenantDto,
} from '@/application/ports/harness-api-client.port'
import { ServiceAccountTokenOwner as TokenOwner } from '@/domain/access-token-order'

const PAGE_SIZE = 20

function toTokenOwner(account: ServiceAccountDto, organizations: TenantDto[]): TokenOwner {
  const organization = organizations.find((item) => item.id === account.tenant_id)
  return Object.freeze({
    kind: 'service-account' as const,
    id: account.id,
    name: account.name,
    tenantId: account.tenant_id,
    tenantName: organization?.name || account.tenant_id,
  })
}

export default function ServiceAccountsPage() {
  const [accounts, setAccounts] = useState<ServiceAccountDto[]>([])
  const [organizations, setOrganizations] = useState<TenantDto[]>([])
  const [selectedOrganizationId, setSelectedOrganizationId] = useState('')
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [page, setPage] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isAccountDialogOpen, setIsAccountDialogOpen] = useState(false)
  const [editingAccount, setEditingAccount] = useState<ServiceAccountDto | null>(null)
  const [deleteAccount, setDeleteAccount] = useState<ServiceAccountDto | null>(null)
  const [deleteError, setDeleteError] = useState<string | undefined>()
  const [deleting, setDeleting] = useState(false)
  const [tokenOwner, setTokenOwner] = useState<TokenOwner | null>(null)
  const [plaintextToken, setPlaintextToken] = useState<string | null>(null)
  const requestVersion = useRef(0)

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch(search.trim())
      setPage(0)
    }, 300)
    return () => window.clearTimeout(timer)
  }, [search])

  const refresh = useCallback(async () => {
    const version = ++requestVersion.current
    setLoading(true)
    setError(null)

    const [accountResult, organizationResult] = await Promise.all([
      listServiceAccountsAction({
        tenantId: selectedOrganizationId || undefined,
        query: debouncedSearch || undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
      listAllTenantsAction(),
    ])

    if (version !== requestVersion.current) return

    const errors: string[] = []
    if (accountResult.data) {
      setAccounts(accountResult.data)
      setHasMore(accountResult.data.length === PAGE_SIZE)
    } else {
      errors.push(accountResult.error || 'Failed to load service accounts.')
    }
    if (organizationResult.data) {
      setOrganizations(organizationResult.data)
    } else {
      errors.push(organizationResult.error || 'Failed to load organizations.')
    }
    setError(errors.length > 0 ? errors.join(' ') : null)
    setLoading(false)
  }, [debouncedSearch, page, selectedOrganizationId])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const openCreateDialog = () => {
    setEditingAccount(null)
    setIsAccountDialogOpen(true)
  }

  const openEditDialog = (account: ServiceAccountDto) => {
    setEditingAccount(account)
    setIsAccountDialogOpen(true)
  }

  const closeAccountDialog = () => {
    setIsAccountDialogOpen(false)
    setEditingAccount(null)
  }

  const handleDelete = async () => {
    if (!deleteAccount) return
    setDeleting(true)
    setDeleteError(undefined)
    const result = await deleteServiceAccountAction(deleteAccount.id)
    setDeleting(false)
    if (!result.success) {
      setDeleteError(result.error || 'Failed to delete service account.')
      return
    }
    setDeleteAccount(null)
    await refresh()
  }

  return (
    <div className="flex min-h-screen bg-background text-gray-100">
      <AdminSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center justify-between border-b border-border bg-card/60 px-6 py-3.5 backdrop-blur">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-blue-500/20 bg-blue-600/10 text-blue-400">
              <Shield aria-hidden="true" className="h-4 w-4" />
            </span>
            <div>
              <h1 className="text-sm font-bold tracking-tight text-white">Service Accounts</h1>
              <p className="text-[11px] text-gray-400">Manage automation identities and owned credentials</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button aria-label="Refresh service accounts" className="rounded-lg p-2 text-gray-400 hover:bg-white/5 hover:text-white disabled:opacity-50" disabled={loading} onClick={() => void refresh()} type="button">
              <RefreshCw aria-hidden="true" className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button className="inline-flex items-center rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-blue-500" onClick={openCreateDialog} type="button">
              <Plus aria-hidden="true" className="mr-1.5 h-3.5 w-3.5" /> New Service Account
            </button>
          </div>
        </header>

        <main className="mx-auto w-full max-w-6xl flex-1 space-y-6 px-6 py-8">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-300" htmlFor="service-account-organization-filter">
              Filter by organization
            </label>
            <select
              className="w-full max-w-sm rounded-lg border border-border bg-card px-3 py-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
              id="service-account-organization-filter"
              onChange={(event) => {
                setSelectedOrganizationId(event.target.value)
                setPage(0)
              }}
              value={selectedOrganizationId}
            >
              <option value="">Global</option>
              {organizations.filter((organization) => organization.status !== 'disabled').map((organization) => (
                <option key={organization.id} value={organization.id}>{organization.name}</option>
              ))}
            </select>
          </div>

          {error && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-xs text-red-300" role="alert">
              <span className="mb-0.5 block font-semibold">Connection error:</span>
              {error}
            </div>
          )}

          <ServiceAccountTable
            accounts={accounts}
            hasMore={hasMore}
            loading={loading}
            onCreateToken={(account) => setTokenOwner(toTokenOwner(account, organizations))}
            onDelete={(account) => {
              setDeleteError(undefined)
              setDeleteAccount(account)
            }}
            onEdit={openEditDialog}
            onPageChange={(nextPage) => setPage(Math.max(0, nextPage))}
            onRefresh={refresh}
            onSearchChange={setSearch}
            organizations={organizations}
            page={page}
            search={search}
          />
        </main>
      </div>

      <ServiceAccountDialog
        account={editingAccount}
        isOpen={isAccountDialogOpen}
        onClose={closeAccountDialog}
        onSuccess={() => {
          closeAccountDialog()
          void refresh()
        }}
        organizations={organizations}
      />

      {deleteAccount && (
        <ConfirmDeleteDialog
          description={`Deleting ${deleteAccount.name} will permanently revoke all tokens owned by this service account.`}
          error={deleteError}
          isDeleting={deleting}
          isOpen
          onClose={() => setDeleteAccount(null)}
          onConfirm={handleDelete}
          targetKey={deleteAccount.name}
          title="Delete service account"
        />
      )}

      <CreateTokenDialog
        isOpen={Boolean(tokenOwner)}
        onClose={() => setTokenOwner(null)}
        onSuccess={(token) => {
          setTokenOwner(null)
          setPlaintextToken(token)
        }}
        serviceAccountOwner={tokenOwner || undefined}
        tenants={organizations}
      />
      {plaintextToken && <SecretRevealModal onClose={() => setPlaintextToken(null)} token={plaintextToken} />}
    </div>
  )
}
