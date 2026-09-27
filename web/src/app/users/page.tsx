'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { RefreshCw, Users } from 'lucide-react'
import { listUsersAction } from '@/app/actions/users'
import { listAllTenantsAction } from '@/app/actions/tenants'
import { AdminSidebar } from '@/components/admin-sidebar'
import { CreateTokenDialog } from '@/components/create-token-dialog'
import { SecretRevealModal } from '@/components/secret-reveal-modal'
import { UserTable } from '@/components/user-table'
import { TenantDto, UserDto } from '@/application/ports/harness-api-client.port'
import { UserTokenOwner } from '@/domain/user-token-owner'

const PAGE_SIZE = 20

export default function UsersPage() {
  const [users, setUsers] = useState<UserDto[]>([])
  const [tenants, setTenants] = useState<TenantDto[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [page, setPage] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [tokenOwner, setTokenOwner] = useState<UserTokenOwner | null>(null)
  const [plaintextToken, setPlaintextToken] = useState<string | null>(null)
  const requestVersion = useRef(0)

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch(search.trim())
      setPage(0)
    }, 300)
    return () => window.clearTimeout(timer)
  }, [search])

  const refreshUsers = useCallback(async () => {
    const version = ++requestVersion.current
    setLoading(true)
    setError(null)
    const result = await listUsersAction(
      debouncedSearch || undefined,
      PAGE_SIZE,
      page * PAGE_SIZE
    )
    if (version !== requestVersion.current) return

    if (result.data) {
      setUsers(result.data)
      setHasMore(result.data.length === PAGE_SIZE)
    } else {
      setError(result.error || 'Failed to load users.')
    }
    setLoading(false)
  }, [debouncedSearch, page])

  useEffect(() => {
    void refreshUsers()
  }, [refreshUsers])

  useEffect(() => {
    void listAllTenantsAction().then((result) => {
      if (result.data) setTenants(result.data)
      else setError(result.error || 'Failed to load organizations.')
    })
  }, [])

  const handlePageChange = (nextPage: number) => {
    setPage(Math.max(0, nextPage))
  }

  const handleTokenCreated = (token: string) => {
    setTokenOwner(null)
    setPlaintextToken(token)
  }

  return (
    <div className="flex min-h-screen bg-background text-gray-100">
      <AdminSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center justify-between border-b border-border bg-card/60 px-6 py-3.5 backdrop-blur">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-blue-500/20 bg-blue-600/10 text-blue-400">
              <Users aria-hidden="true" className="h-4 w-4" />
            </span>
            <div>
              <h1 className="text-sm font-bold tracking-tight text-white">Users</h1>
              <p className="text-[11px] text-gray-400">Manage human identities and their access</p>
            </div>
          </div>
          <button
            aria-label="Refresh users"
            className="rounded-lg p-2 text-gray-400 transition hover:bg-white/5 hover:text-white disabled:opacity-50"
            disabled={loading}
            onClick={() => void refreshUsers()}
            title="Refresh users"
            type="button"
          >
            <RefreshCw aria-hidden="true" className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </header>

        <main className="mx-auto w-full max-w-6xl flex-1 space-y-6 px-6 py-8">
          {error && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-xs text-red-300" role="alert">
              <span className="mb-0.5 block font-semibold">Connection error:</span>
              {error}
            </div>
          )}
          <UserTable
            hasMore={hasMore}
            loading={loading}
            onCreateToken={(user) => setTokenOwner({ kind: 'user', id: user.id, name: user.name })}
            onPageChange={handlePageChange}
            onRefresh={refreshUsers}
            onSearchChange={setSearch}
            page={page}
            search={search}
            users={users}
          />
        </main>
      </div>

      <CreateTokenDialog
        isOpen={Boolean(tokenOwner)}
        onClose={() => setTokenOwner(null)}
        onSuccess={handleTokenCreated}
        userOwner={tokenOwner ?? undefined}
        tenants={tenants}
      />
      {plaintextToken && (
        <SecretRevealModal token={plaintextToken} onClose={() => setPlaintextToken(null)} />
      )}
    </div>
  )
}
