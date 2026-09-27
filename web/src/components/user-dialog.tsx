'use client'

import { useEffect, useState } from 'react'
import { AlertCircle, UserRound, X } from 'lucide-react'
import { createUserAction, updateUserAction } from '@/app/actions/users'
import { UserDto } from '@/application/ports/harness-api-client.port'

interface UserDialogProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  onFailure?: (error: string) => void
  user?: UserDto
}

export function UserDialog({ isOpen, onClose, onSuccess, onFailure, user }: UserDialogProps) {
  const isEditing = Boolean(user)
  const [name, setName] = useState(user?.name ?? '')
  const [email, setEmail] = useState(user?.email ?? '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen) return
    setName(user?.name ?? '')
    setEmail(user?.email ?? '')
    setError(null)
  }, [isOpen, user])

  if (!isOpen) return null

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (loading) return
    setError(null)
    setLoading(true)

    try {
      const result = isEditing && user
        ? await updateUserAction(user.id, { name: name.trim(), email: email.trim() })
        : await createUserAction({ name: name.trim(), email: email.trim() })

      if (result.success) {
        onSuccess()
      } else {
        const message = result.error || `Failed to ${isEditing ? 'update' : 'create'} user.`
        setError(message)
        onFailure?.(message)
      }
    } catch (submitError: unknown) {
      const message = submitError instanceof Error ? submitError.message : 'User could not be saved.'
      setError(message)
      onFailure?.(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <section
        aria-labelledby="user-dialog-title"
        aria-modal="true"
        className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-2xl space-y-5"
        role="dialog"
      >
        <header className="flex items-center justify-between border-b border-border pb-4">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-blue-500/20 bg-blue-600/10 text-blue-400">
              <UserRound aria-hidden="true" className="h-5 w-5" />
            </span>
            <div>
              <h2 className="text-sm font-semibold text-white" id="user-dialog-title">
                {isEditing ? 'Edit User' : 'Create User'}
              </h2>
              <p className="text-[11px] text-gray-400">Manage name and email only.</p>
            </div>
          </div>
          <button
            aria-label="Close user dialog"
            className="rounded-lg p-1 text-gray-400 hover:bg-white/5 hover:text-white"
            disabled={loading}
            onClick={onClose}
            type="button"
          >
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
            <label className="mb-1.5 block text-xs font-medium text-gray-300" htmlFor="user-name">
              Name
            </label>
            <input
              autoComplete="name"
              className="w-full rounded-lg border border-border bg-black/30 px-3 py-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
              disabled={loading}
              id="user-name"
              maxLength={120}
              onChange={(event) => setName(event.target.value)}
              required
              type="text"
              value={name}
            />
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-300" htmlFor="user-email">
              Email
            </label>
            <input
              autoComplete="email"
              className="w-full rounded-lg border border-border bg-black/30 px-3 py-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
              disabled={loading}
              id="user-email"
              maxLength={320}
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </div>

          <footer className="flex justify-end gap-2 border-t border-border pt-3">
            <button
              className="rounded-lg border border-border px-3.5 py-2 text-xs text-gray-300 hover:bg-white/5 disabled:opacity-50"
              disabled={loading}
              onClick={onClose}
              type="button"
            >
              Cancel
            </button>
            <button
              className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
              disabled={loading}
              type="submit"
            >
              {loading ? 'Saving...' : isEditing ? 'Save Changes' : 'Create User'}
            </button>
          </footer>
        </form>
      </section>
    </div>
  )
}
