'use client'

import { useEffect, useState, useCallback } from 'react'
import { Plus, LogOut, Shield, Database, RefreshCw, Key } from 'lucide-react'
import { loadDashboardDataAction, DashboardData } from '@/app/actions/tokens'
import { logoutAction } from '@/app/actions/auth'
import { TokenList } from '@/components/token-list'
import { CreateTokenDialog } from '@/components/create-token-dialog'
import { SecretRevealModal } from '@/components/secret-reveal-modal'
import { AdminSidebar } from '@/components/admin-sidebar'

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [selectedTenantId, setSelectedTenantId] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [revealedToken, setRevealedToken] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    const res = await loadDashboardDataAction()
    if (res.data) {
      setData(res.data)
    } else {
      setError(res.error || 'Failed to load data.')
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleTokenCreated = (plaintext: string) => {
    setIsCreateOpen(false)
    setRevealedToken(plaintext)
    fetchData()
  }

  return (
    <div className="min-h-screen bg-background text-gray-100 flex">
      {/* Sidebar Navigation */}
      <AdminSidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Navbar */}
        <header className="border-b border-border bg-card/60 backdrop-blur sticky top-0 z-30 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600/10 border border-blue-500/20 text-blue-400">
            <Key className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-sm tracking-tight text-white">Harness Memory</span>
              <span className="rounded bg-blue-500/10 border border-blue-500/20 px-1.5 py-0.5 text-[10px] font-bold text-blue-400 uppercase tracking-wider">
                Admin Alpha
              </span>
            </div>
            <p className="text-[11px] text-gray-400">Corporate Engineering Knowledge Governance</p>
          </div>
        </div>

        {data?.bootstrap && (
          <div className="hidden md:flex items-center space-x-3 text-xs">
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-black/40 border border-border text-gray-300">
              <Database className="h-3.5 w-3.5 text-blue-400" />
              <span className="text-gray-500">Tenant:</span>
              {data.tenants && data.tenants.length > 1 ? (
                <select
                  value={selectedTenantId || data.bootstrap.tenantId}
                  onChange={(e) => setSelectedTenantId(e.target.value)}
                  className="bg-transparent text-white font-medium focus:outline-none cursor-pointer pr-1"
                >
                  {data.tenants.map((t) => (
                    <option key={t.id} value={t.id} className="bg-gray-900 text-white">
                      {t.name} ({t.key})
                    </option>
                  ))}
                </select>
              ) : (
                <span className="font-medium text-white">{data.bootstrap.tenantName}</span>
              )}
            </div>
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-black/40 border border-border text-gray-300">
              <Shield className="h-3.5 w-3.5 text-emerald-400" />
              <span className="text-gray-500">Service Account:</span>
              <span className="font-medium text-white">{data.bootstrap.serviceAccountName}</span>
            </div>
          </div>
        )}

        <div className="flex items-center space-x-2">
          <button
            onClick={() => fetchData()}
            disabled={loading}
            className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-white/5 transition"
            title="Refresh data"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <form action={logoutAction}>
            <button
              type="submit"
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span>Sign Out</span>
            </button>
          </form>
        </div>
      </header>

      {/* Main Body */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-6">
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">
              Access Tokens & Credentials
            </h1>
            <p className="text-xs text-gray-400 mt-1 max-w-xl leading-relaxed">
              Issue and manage secure credentials prefixed with <code className="text-emerald-400 font-mono">hm_</code> with least-privilege scopes (<code className="text-blue-400 font-mono">memory:read</code>, <code className="text-blue-400 font-mono">memory:publish</code>, <code className="text-blue-400 font-mono">memory:impact</code>).
            </p>
          </div>

          <button
            onClick={() => setIsCreateOpen(true)}
            className="inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-blue-500 transition focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <Plus className="mr-1.5 h-4 w-4" />
            New Token
          </button>
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-xs text-red-300">
            <span className="font-semibold block mb-0.5">Connection error:</span>
            {error}
          </div>
        )}

        {loading && !data ? (
          <div className="py-16 text-center text-xs text-gray-500">
            <RefreshCw className="mx-auto h-6 w-6 animate-spin text-gray-600 mb-2" />
            Loading credentials...
          </div>
        ) : (
          data && <TokenList tokens={data.tokens} onTokenRevoked={fetchData} />
        )}
      </main>

      {/* Modals */}
      {data?.bootstrap && (
        <CreateTokenDialog
          isOpen={isCreateOpen}
          onClose={() => setIsCreateOpen(false)}
          onSuccess={handleTokenCreated}
          serviceAccountId={data.bootstrap.serviceAccountId}
          serviceAccountName={data.bootstrap.serviceAccountName}
          tenantId={selectedTenantId || data.bootstrap.tenantId}
          tenantName={
            data.tenants?.find((t) => t.id === (selectedTenantId || data.bootstrap.tenantId))?.name ||
            data.bootstrap.tenantName
          }
          tenants={data.tenants || []}
        />
      )}

      {revealedToken && (
        <SecretRevealModal
          token={revealedToken}
          onClose={() => setRevealedToken(null)}
        />
      )}
      </div>
    </div>
  )
}
