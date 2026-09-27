'use client'

import { useEffect, useState, useCallback } from 'react'
import { LogOut, RefreshCw, Key } from 'lucide-react'
import { loadDashboardDataAction, DashboardData } from '@/app/actions/tokens'
import { logoutAction } from '@/app/actions/auth'
import { TokenList } from '@/components/token-list'
import { AdminSidebar } from '@/components/admin-sidebar'
import { nextDashboardLoadState } from '@/application/dashboard-load-state'

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(0)

  const fetchData = useCallback(async (selectedPage: number): Promise<boolean> => {
    setLoading(true)
    setError(null)
    try {
      const res = await loadDashboardDataAction(selectedPage)
      const state = nextDashboardLoadState<DashboardData>({ data: null, error: null }, res)
      setData(state.data)
      setError(state.error)
      if (state.data) {
        setPage(selectedPage)
        return true
      }
      return false
    } catch {
      setData(null)
      setError('Failed to load data.')
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchData(0)
  }, [fetchData])

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

        <div className="flex items-center space-x-2">
          <button
            onClick={() => void fetchData(page)}
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
              Review active credentials, owner context, scopes, and revocation status.
            </p>
          </div>
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-xs text-red-300">
            <span className="font-semibold block mb-0.5">Connection error:</span>
            {error}
          </div>
        )}

        {loading ? (
          <div className="py-16 text-center text-xs text-gray-500">
            <RefreshCw className="mx-auto h-6 w-6 animate-spin text-gray-600 mb-2" />
            Loading credentials...
          </div>
        ) : (
          data && <>
            <TokenList credentials={data.credentials} onTokenRevoked={() => fetchData(page)} />
            <div className="flex justify-end gap-3 text-xs">
              <button disabled={loading || page === 0} onClick={() => void fetchData(page - 1)}>Previous</button>
              <span>Page {page + 1}</span>
              <button disabled={loading || !data.hasMore} onClick={() => void fetchData(page + 1)}>Next</button>
            </div>
          </>
        )}
      </main>
      </div>
    </div>
  )
}
