'use client'

import { useState } from 'react'
import { KeyRound, ShieldAlert, ArrowRight } from 'lucide-react'
import { loginAction } from '@/app/actions/auth'

export default function LoginPage() {
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    const formData = new FormData(e.currentTarget)
    try {
      const res = await loginAction(formData)
      if (res?.error) {
        setError(res.error)
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-4 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-blue-950/20 via-background to-background">
      <div className="w-full max-w-md rounded-2xl border border-border bg-card/90 p-8 shadow-2xl backdrop-blur space-y-6">
        <div className="space-y-2 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600/10 border border-blue-500/20 text-blue-400">
            <KeyRound className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Harness Memory</h1>
          <p className="text-xs text-gray-400 uppercase tracking-widest font-semibold">
            Admin Console [Alpha]
          </p>
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3.5 text-xs text-red-300 flex items-center space-x-2">
            <ShieldAlert className="h-4 w-4 flex-shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="token"
              className="block text-xs font-medium uppercase tracking-wider text-gray-400 mb-1.5"
            >
              Admin Key (API_ADMIN_TOKEN)
            </label>
            <input
              id="token"
              name="token"
              type="password"
              required
              autoFocus
              placeholder="Paste the infrastructure API_ADMIN_TOKEN"
              className="w-full rounded-lg border border-border bg-black/40 px-3.5 py-2.5 text-sm text-white placeholder-gray-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <p className="text-xs text-gray-500 leading-relaxed">
            The secret is validated on the BFF server and is never saved in the browser.
          </p>

          <button
            type="submit"
            disabled={loading}
            className="w-full inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-card transition disabled:opacity-50"
          >
            {loading ? (
              'Signing in...'
            ) : (
              <>
                Open Dashboard <ArrowRight className="ml-2 h-4 w-4" />
              </>
            )}
          </button>
        </form>
      </div>
    </main>
  )
}
