'use client'

import { useState, useEffect } from 'react'
import { AlertTriangle, X, Trash2 } from 'lucide-react'

interface ConfirmDeleteDialogProps {
  isOpen: boolean
  title: string
  description: string
  targetKey: string
  onConfirm: () => Promise<void> | void
  onClose: () => void
  isDeleting?: boolean
}

export function ConfirmDeleteDialog({
  isOpen,
  title,
  description,
  targetKey,
  onConfirm,
  onClose,
  isDeleting = false,
}: ConfirmDeleteDialogProps) {
  const [typedKey, setTypedKey] = useState('')

  useEffect(() => {
    if (isOpen) {
      setTypedKey('')
    }
  }, [isOpen])

  if (!isOpen) return null

  const isMatch = typedKey.trim().toLowerCase() === targetKey.trim().toLowerCase()

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isMatch || isDeleting) return
    await onConfirm()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in">
      <div className="w-full max-w-md rounded-xl border border-red-500/30 bg-[#0f172a] shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/10 px-5 py-4 bg-red-950/20">
          <div className="flex items-center space-x-2.5 text-red-400">
            <AlertTriangle className="h-5 w-5" />
            <h3 className="text-sm font-semibold text-white">{title}</h3>
          </div>
          <button
            onClick={onClose}
            disabled={isDeleting}
            className="rounded-lg p-1 text-gray-400 hover:bg-white/10 hover:text-white transition"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleConfirm} className="p-5 space-y-4">
          <p className="text-xs text-gray-300 leading-relaxed">{description}</p>

          <div className="rounded-lg border border-red-500/20 bg-red-950/30 p-3 text-xs text-red-200">
            To confirm, type exactly <strong className="font-mono text-white select-all">{targetKey}</strong> below:
          </div>

          <div>
            <label className="block text-[11px] font-medium text-gray-400 mb-1">
              Confirmation key
            </label>
            <input
              type="text"
              value={typedKey}
              onChange={(e) => setTypedKey(e.target.value)}
              placeholder={targetKey}
              autoFocus
              disabled={isDeleting}
              className="w-full rounded-lg border border-border bg-black/40 px-3 py-2 text-xs text-white placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-red-500 font-mono"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isDeleting}
              className="rounded-lg border border-border px-3.5 py-2 text-xs text-gray-400 hover:bg-white/5 hover:text-white transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!isMatch || isDeleting}
              className={`flex items-center space-x-1.5 rounded-lg px-4 py-2 text-xs font-semibold transition ${
                isMatch && !isDeleting
                  ? 'bg-red-600 text-white hover:bg-red-500 shadow-lg shadow-red-600/30'
                  : 'bg-red-950/40 text-red-300/40 cursor-not-allowed border border-red-900/30'
              }`}
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span>{isDeleting ? 'Deleting...' : 'Delete Permanently'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
