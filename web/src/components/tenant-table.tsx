'use client'

import { useState } from 'react'
import { Edit2, Trash2, Search, Database, ChevronLeft, ChevronRight } from 'lucide-react'
import { TenantDto } from '@/application/ports/harness-api-client.port'
import { deleteTenantAction } from '@/app/actions/tenants'
import { TenantDialog } from './tenant-dialog'
import { ConfirmDeleteDialog } from './confirm-delete-dialog'

interface TenantTableProps {
  tenants: TenantDto[]
  onRefresh: () => void
  search: string
  onSearchChange: (search: string) => void
  page: number
  onPageChange: (page: number) => void
  hasMore: boolean
  loading?: boolean
}

export function TenantTable({
  tenants,
  onRefresh,
  search,
  onSearchChange,
  page,
  onPageChange,
  hasMore,
  loading = false,
}: TenantTableProps) {
  const [editingTenant, setEditingTenant] = useState<TenantDto | null>(null)
  const [tenantToDelete, setTenantToDelete] = useState<TenantDto | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const handleConfirmDelete = async () => {
    if (!tenantToDelete) return
    setIsDeleting(true)
    setDeleteError(null)
    const res = await deleteTenantAction(tenantToDelete.id)
    if (res.success) {
      setTenantToDelete(null)
      onRefresh()
    } else {
      setDeleteError(res.error || 'Failed to delete tenant.')
    }
    setIsDeleting(false)
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
      <div className="flex items-center space-x-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-gray-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search by name or key..."
            className="w-full rounded-lg border border-border bg-black/30 pl-9 pr-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-border bg-black/20 text-gray-400 font-semibold">
            <tr>
              <th className="px-5 py-3">Organization</th>
              <th className="px-5 py-3">Key (Slug)</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3">Date Created</th>
              <th className="px-5 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {tenants.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-12 text-center text-gray-500">
                  <Database className="mx-auto h-6 w-6 text-gray-600 mb-2" />
                  {loading ? 'Loading tenants...' : 'No tenants found.'}
                </td>
              </tr>
            ) : (
              tenants.map((tenant) => (
                <tr key={tenant.id} className="hover:bg-white/[0.02] transition">
                  <td className="px-5 py-3.5 font-medium text-white">{tenant.name}</td>
                  <td className="px-5 py-3.5 font-mono text-gray-300">{tenant.key || '—'}</td>
                  <td className="px-5 py-3.5">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                        tenant.status === 'disabled'
                          ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                          : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      }`}
                    >
                      {tenant.status === 'disabled' ? 'Disabled' : 'Active'}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-gray-400">
                    {tenant.created_at ? new Date(tenant.created_at).toLocaleDateString('en-US') : '—'}
                  </td>
                  <td className="px-5 py-3.5 text-right space-x-1">
                    <button
                      onClick={() => setEditingTenant(tenant)}
                      className="p-1.5 text-gray-400 hover:text-white rounded hover:bg-white/5 transition"
                      title="Edit tenant"
                    >
                      <Edit2 className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => setTenantToDelete(tenant)}
                      className="p-1.5 text-gray-400 hover:text-red-400 rounded hover:bg-red-500/10 transition"
                      title="Delete tenant with confirmation"
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

      {editingTenant && (
        <TenantDialog
          isOpen={true}
          tenantToEdit={editingTenant}
          onClose={() => setEditingTenant(null)}
          onSuccess={() => {
            setEditingTenant(null)
            onRefresh()
          }}
        />
      )}

      {tenantToDelete && (
        <ConfirmDeleteDialog
          isOpen={true}
          title="Confirm Organization Deletion"
          description={`This will permanently delete the organization "${tenantToDelete.name}". Deletion will fail if projects or service accounts are associated with it.`}
          targetKey={tenantToDelete.key || tenantToDelete.name}
          onConfirm={handleConfirmDelete}
          onClose={() => setTenantToDelete(null)}
          isDeleting={isDeleting}
        />
      )}
    </div>
  )
}
