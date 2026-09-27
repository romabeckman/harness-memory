'use client'

import { useState } from 'react'
import { ChevronLeft, ChevronRight, Edit2, Plus, Search, Trash2, UserRoundPlus } from 'lucide-react'
import { deleteUserAction } from '@/app/actions/users'
import { UserDto } from '@/application/ports/harness-api-client.port'
import { ConfirmDeleteDialog } from './confirm-delete-dialog'
import { UserDialog } from './user-dialog'

interface UserTableProps {
  users: UserDto[]
  onRefresh: () => void | Promise<void>
  search: string
  onSearchChange: (search: string) => void
  page: number
  onPageChange: (page: number) => void
  hasMore: boolean
  loading?: boolean
  onCreateToken: (user: UserDto) => void
}

export function UserTable({
  users,
  onRefresh,
  search,
  onSearchChange,
  page,
  onPageChange,
  hasMore,
  loading = false,
  onCreateToken,
}: UserTableProps) {
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<UserDto | null>(null)
  const [deletingUser, setDeletingUser] = useState<UserDto | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const closeUserDialog = () => {
    setIsCreateOpen(false)
    setEditingUser(null)
  }

  const handleUserSaved = () => {
    closeUserDialog()
    void onRefresh()
  }

  const handleDelete = async () => {
    if (!deletingUser || isDeleting) return
    setIsDeleting(true)
    setDeleteError(null)
    try {
      const result = await deleteUserAction(deletingUser.id)
      if (result.success) {
        setDeletingUser(null)
        await onRefresh()
      } else {
        setDeleteError(result.error || 'Failed to delete user.')
      }
    } catch (error: unknown) {
      setDeleteError(error instanceof Error ? error.message : 'Failed to delete user.')
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="relative w-full max-w-sm">
          <Search aria-hidden="true" className="absolute left-3 top-2.5 h-3.5 w-3.5 text-gray-500" />
          <input
            aria-label="Search users"
            className="w-full rounded-lg border border-border bg-black/30 py-2 pl-9 pr-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Search users by name or email..."
            type="search"
            value={search}
          />
        </div>
        <button
          className="inline-flex shrink-0 items-center rounded-lg bg-blue-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-blue-500"
          onClick={() => setIsCreateOpen(true)}
          type="button"
        >
          <Plus aria-hidden="true" className="mr-1.5 h-3.5 w-3.5" />
          New User
        </button>
      </div>

      <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-border bg-black/20 font-semibold text-gray-400">
              <tr>
                <th className="px-5 py-3" scope="col">Name</th>
                <th className="px-5 py-3" scope="col">Email</th>
                <th className="px-5 py-3 text-right" scope="col">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {users.length === 0 ? (
                <tr>
                  <td className="py-12 text-center text-gray-500" colSpan={3}>
                    <UserRoundPlus aria-hidden="true" className="mx-auto mb-2 h-6 w-6 text-gray-600" />
                    {loading ? 'Loading users...' : 'No users found.'}
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr className="hover:bg-white/[0.02]" key={user.id}>
                    <td className="px-5 py-3.5 font-medium text-white">{user.name}</td>
                    <td className="px-5 py-3.5 text-gray-300">{user.email}</td>
                    <td className="space-x-1 px-5 py-3.5 text-right">
                      <button
                        aria-label={`Create token for ${user.name}`}
                        className="rounded p-1.5 text-gray-400 hover:bg-emerald-500/10 hover:text-emerald-400"
                        onClick={() => onCreateToken(user)}
                        title={`Create token for ${user.name}`}
                        type="button"
                      >
                        <UserRoundPlus aria-hidden="true" className="h-3.5 w-3.5" />
                      </button>
                      <button
                        aria-label={`Edit user ${user.name}`}
                        className="rounded p-1.5 text-gray-400 hover:bg-white/5 hover:text-white"
                        onClick={() => setEditingUser(user)}
                        title={`Edit user ${user.name}`}
                        type="button"
                      >
                        <Edit2 aria-hidden="true" className="h-3.5 w-3.5" />
                      </button>
                      <button
                        aria-label={`Delete user ${user.name}`}
                        className="rounded p-1.5 text-gray-400 hover:bg-red-500/10 hover:text-red-400"
                        onClick={() => {
                          setDeleteError(null)
                          setDeletingUser(user)
                        }}
                        title={`Delete user ${user.name}`}
                        type="button"
                      >
                        <Trash2 aria-hidden="true" className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between border-t border-border bg-black/10 px-5 py-3 text-xs text-gray-400">
          <span>
            Page {page + 1}
            {loading && <span className="ml-2 text-blue-400">Updating...</span>}
          </span>
          <div className="flex items-center gap-1.5">
            <button
              className="flex items-center gap-1 rounded-lg border border-border px-2.5 py-1 hover:bg-white/5 hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
              disabled={page === 0 || loading}
              onClick={() => onPageChange(page - 1)}
              type="button"
            >
              <ChevronLeft aria-hidden="true" className="h-3.5 w-3.5" />
              Previous
            </button>
            <button
              className="flex items-center gap-1 rounded-lg border border-border px-2.5 py-1 hover:bg-white/5 hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!hasMore || loading}
              onClick={() => onPageChange(page + 1)}
              type="button"
            >
              Next
              <ChevronRight aria-hidden="true" className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      <UserDialog
        isOpen={isCreateOpen || Boolean(editingUser)}
        onClose={closeUserDialog}
        onFailure={() => void onRefresh()}
        onSuccess={handleUserSaved}
        user={editingUser ?? undefined}
      />
      <ConfirmDeleteDialog
        description={
          deletingUser
            ? `Deleting ${deletingUser.name} will permanently revoke all tokens owned by this user.`
            : ''
        }
        error={deleteError ?? undefined}
        isDeleting={isDeleting}
        isOpen={Boolean(deletingUser)}
        onClose={() => {
          if (!isDeleting) {
            setDeletingUser(null)
            setDeleteError(null)
          }
        }}
        onConfirm={handleDelete}
        targetKey={deletingUser?.name ?? ''}
        title="Confirm User Deletion"
      />
    </div>
  )
}
