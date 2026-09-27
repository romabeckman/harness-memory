'use client'

import { useEffect, useState, useCallback } from 'react'
import { Plus, RefreshCw, Layers } from 'lucide-react'
import { AdminSidebar } from '@/components/admin-sidebar'
import { ProjectTable } from '@/components/project-table'
import { ProjectDialog } from '@/components/project-dialog'
import { listProjectsAction } from '@/app/actions/projects'
import { listTenantsAction } from '@/app/actions/tenants'
import { TenantDto, ProjectDto } from '@/application/ports/harness-api-client.port'

const PAGE_SIZE = 20

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectDto[]>([])
  const [tenants, setTenants] = useState<TenantDto[]>([])
  const [selectedTenantId, setSelectedTenantId] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [page, setPage] = useState(0)
  const [hasMore, setHasMore] = useState(false)

  // Load tenants once on mount
  const fetchTenants = useCallback(async () => {
    const res = await listTenantsAction(undefined, 500, 0)
    if (res.data) {
      setTenants(res.data)
    }
  }, [])

  useEffect(() => {
    fetchTenants()
  }, [fetchTenants])

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search)
      setPage(0)
    }, 300)
    return () => clearTimeout(timer)
  }, [search])

  const fetchProjects = useCallback(async () => {
    setLoading(true)
    setError(null)
    const offset = page * PAGE_SIZE
    const res = await listProjectsAction(
      selectedTenantId || undefined,
      debouncedSearch || undefined,
      PAGE_SIZE,
      offset
    )

    if (res.data) {
      setProjects(res.data)
      setHasMore(res.data.length === PAGE_SIZE)
    } else {
      setError(res.error || 'Failed to load projects.')
    }
    setLoading(false)
  }, [selectedTenantId, debouncedSearch, page])

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  const handleSelectTenant = (tenantId: string) => {
    setSelectedTenantId(tenantId)
    setPage(0)
  }

  return (
    <div className="min-h-screen bg-background text-gray-100 flex">
      {/* Sidebar Navigation */}
      <AdminSidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="border-b border-border bg-card/60 backdrop-blur sticky top-0 z-30 px-6 py-3.5 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600/10 border border-blue-500/20 text-blue-400">
              <Layers className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-white tracking-tight">Software Projects</h1>
              <p className="text-[11px] text-gray-400">Manage namespaces and snapshots</p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => {
                fetchTenants()
                fetchProjects()
              }}
              disabled={loading}
              className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-white/5 transition"
              title="Refresh list"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={() => setIsCreateOpen(true)}
              disabled={tenants.length === 0}
              className="inline-flex items-center justify-center rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow hover:bg-blue-500 transition disabled:opacity-50"
            >
              <Plus className="mr-1.5 h-3.5 w-3.5" />
              New Project
            </button>
          </div>
        </header>

        <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8 space-y-6">
          {error && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-xs text-red-300">
              <span className="font-semibold block mb-0.5">Connection error:</span>
              {error}
            </div>
          )}

          {loading && projects.length === 0 ? (
            <div className="py-16 text-center text-xs text-gray-500">
              <RefreshCw className="mx-auto h-6 w-6 animate-spin text-gray-600 mb-2" />
              Loading projects...
            </div>
          ) : (
            <ProjectTable
              projects={projects}
              tenants={tenants}
              selectedTenantId={selectedTenantId}
              onSelectTenant={handleSelectTenant}
              onRefresh={fetchProjects}
              search={search}
              onSearchChange={setSearch}
              page={page}
              onPageChange={setPage}
              hasMore={hasMore}
              loading={loading}
            />
          )}
        </main>
      </div>

      <ProjectDialog
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onSuccess={() => {
          setIsCreateOpen(false)
          fetchProjects()
        }}
        tenants={tenants}
        defaultTenantId={selectedTenantId}
      />
    </div>
  )
}
