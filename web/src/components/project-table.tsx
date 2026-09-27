'use client'

import { useState } from 'react'
import { Edit2, Trash2, Search, Layers, GitBranch, ChevronLeft, ChevronRight } from 'lucide-react'
import { TenantDto, ProjectDto } from '@/application/ports/harness-api-client.port'
import { deleteProjectAction } from '@/app/actions/projects'
import { ProjectDialog } from './project-dialog'
import { ConfirmDeleteDialog } from './confirm-delete-dialog'
import { ProjectEnvironmentPanel } from './project-environment-panel'

interface ProjectTableProps {
  projects: ProjectDto[]
  tenants: TenantDto[]
  selectedTenantId?: string
  onSelectTenant: (tenantId: string) => void
  onRefresh: () => void
  search: string
  onSearchChange: (search: string) => void
  page: number
  onPageChange: (page: number) => void
  hasMore: boolean
  loading?: boolean
}

export function ProjectTable({
  projects,
  tenants,
  selectedTenantId,
  onSelectTenant,
  onRefresh,
  search,
  onSearchChange,
  page,
  onPageChange,
  hasMore,
  loading = false,
}: ProjectTableProps) {
  const [editingProject, setEditingProject] = useState<ProjectDto | null>(null)
  const [projectToDelete, setProjectToDelete] = useState<ProjectDto | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const handleConfirmDelete = async () => {
    if (!projectToDelete) return
    setIsDeleting(true)
    setDeleteError(null)
    const res = await deleteProjectAction(projectToDelete.tenant_id, projectToDelete.key)
    if (res.success) {
      setProjectToDelete(null)
      onRefresh()
    } else {
      setDeleteError(res.error || 'Failed to delete project.')
    }
    setIsDeleting(false)
  }

  const getTenantName = (tId: string) => {
    const t = tenants.find((item) => item.id === tId)
    return t ? t.name : tId
  }

  return (
    <div className="space-y-4">
      {deleteError && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-300">
          <span className="font-semibold">Deletion blocked: </span>
          {deleteError}
        </div>
      )}

      {/* Filter / Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center space-x-3 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-gray-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search by key or name..."
              className="w-full rounded-lg border border-border bg-black/30 pl-9 pr-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div className="w-48">
            <select
              value={selectedTenantId || ''}
              onChange={(e) => onSelectTenant(e.target.value)}
              className="w-full rounded-lg border border-border bg-black/30 px-3 py-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">All Organizations</option>
              {tenants.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-border bg-black/20 text-gray-400 font-semibold">
            <tr>
              <th className="px-5 py-3">Project Key</th>
              <th className="px-5 py-3">Display Name</th>
              <th className="px-5 py-3">Organization (Tenant)</th>
              <th className="px-5 py-3">Active Snapshot</th>
              <th className="px-5 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {projects.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-12 text-center text-gray-500">
                  <Layers className="mx-auto h-6 w-6 text-gray-600 mb-2" />
                  {loading ? 'Loading projects...' : 'No projects found.'}
                </td>
              </tr>
            ) : (
              projects.map((proj) => (
                <tr key={`${proj.tenant_id}-${proj.key}`} className="hover:bg-white/[0.02] transition">
                  <td className="px-5 py-3.5 font-mono font-medium text-white">{proj.key}</td>
                  <td className="px-5 py-3.5 text-gray-300">{proj.name || '—'}</td>
                  <td className="px-5 py-3.5 text-gray-400">{getTenantName(proj.tenant_id)}</td>
                  <td className="px-5 py-3.5">
                    {proj.active_snapshot_id ? (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono text-[10px]">
                        <GitBranch className="h-3 w-3 mr-1" />
                        {proj.active_snapshot_id.substring(0, 8)}...
                      </span>
                    ) : (
                      <span className="text-gray-500 text-[11px]">No publications</span>
                    )}
                  </td>
                  <td className="px-5 py-3.5 text-right space-x-1">
                    <ProjectEnvironmentPanel
                      project={{ tenantId: proj.tenant_id, projectKey: proj.key }}
                    />
                    <button
                      onClick={() => setEditingProject(proj)}
                      className="p-1.5 text-gray-400 hover:text-white rounded hover:bg-white/5 transition"
                      title="Edit project"
                    >
                      <Edit2 className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => setProjectToDelete(proj)}
                      className="p-1.5 text-gray-400 hover:text-red-400 rounded hover:bg-red-500/10 transition"
                      title="Delete project with confirmation"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* Server-side Pagination Bar */}
        <div className="flex items-center justify-between border-t border-border px-5 py-3 bg-black/10 text-xs text-gray-400">
          <div>
            <span>Page {page + 1}</span>
            {loading && <span className="ml-2 text-blue-400 text-[11px]">(Updating...)</span>}
          </div>
          <div className="flex items-center space-x-1.5">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page === 0 || loading}
              className="flex items-center space-x-1 rounded-lg border border-border px-2.5 py-1 text-xs hover:bg-white/5 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              <span>Previous</span>
            </button>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={!hasMore || loading}
              className="flex items-center space-x-1 rounded-lg border border-border px-2.5 py-1 text-xs hover:bg-white/5 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              <span>Next</span>
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {editingProject && (
        <ProjectDialog
          isOpen={true}
          projectToEdit={editingProject}
          tenants={tenants}
          onClose={() => setEditingProject(null)}
          onSuccess={() => {
            setEditingProject(null)
            onRefresh()
          }}
        />
      )}

      {projectToDelete && (
        <ConfirmDeleteDialog
          isOpen={true}
          title="Confirm Project Deletion"
          description={`This will permanently delete the project "${projectToDelete.name || projectToDelete.key}". Deletion will fail if active environments or snapshots are linked to it.`}
          targetKey={projectToDelete.key}
          onConfirm={handleConfirmDelete}
          onClose={() => setProjectToDelete(null)}
          isDeleting={isDeleting}
        />
      )}
    </div>
  )
}
