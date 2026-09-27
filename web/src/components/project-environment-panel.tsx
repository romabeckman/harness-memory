'use client'

import { FormEvent, useState } from 'react'
import {
  EnvironmentDto,
  ProjectEnvironmentRef,
} from '@/application/ports/harness-api-client.port'
import {
  addProjectEnvironmentAction,
  listProjectEnvironmentsAction,
} from '@/app/actions/projects'

type PanelState = 'closed' | 'loading' | 'loaded' | 'adding' | 'error'

interface ProjectEnvironmentPanelProps {
  project: ProjectEnvironmentRef
}

export function ProjectEnvironmentPanel({
  project,
}: ProjectEnvironmentPanelProps) {
  const [state, setState] = useState<PanelState>('closed')
  const [environments, setEnvironments] = useState<EnvironmentDto[]>([])
  const [selectedName, setSelectedName] = useState('development')
  const [customName, setCustomName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const isOpen = state !== 'closed'

  const loadEnvironments = async () => {
    setError(null)
    setState('loading')
    const result = await listProjectEnvironmentsAction(project)
    if (result.data) {
      setEnvironments(result.data)
      setState('loaded')
    } else {
      setError(result.error || 'Failed to load environments.')
      setState('error')
    }
  }

  const togglePanel = () => {
    if (isOpen) {
      setState('closed')
      return
    }
    void loadEnvironments()
  }

  const submitEnvironment = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const submittedName = selectedName === 'other' ? customName : selectedName
    setError(null)
    setState('adding')
    const result = await addProjectEnvironmentAction(project, submittedName)
    if (!result.success || !result.data) {
      setError(result.error || 'Failed to add environment.')
      setState('error')
      return
    }
    const created = result.data

    setEnvironments((current) => [
      ...current.filter((environment) => environment.name !== created.name),
      created,
    ])
    setSelectedName('development')
    setCustomName('')

    const refreshed = await listProjectEnvironmentsAction(project)
    if (refreshed.data) {
      setEnvironments(refreshed.data)
      setState('loaded')
    } else {
      setError(`Environment added, but refresh failed: ${refreshed.error || 'unknown error'}`)
      setState('error')
    }
  }

  return (
    <div className="inline-block text-left">
      <button
        type="button"
        aria-label={`View environments for ${project.projectKey}`}
        aria-expanded={isOpen}
        onClick={togglePanel}
        className="rounded px-2 py-1 text-gray-400 hover:bg-white/5 hover:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
      >
        Environments
      </button>
      {isOpen && (
        <section
          aria-label={`Environments for ${project.projectKey}`}
          aria-busy={state === 'loading' || state === 'adding'}
          className="mt-2 min-w-64 rounded-lg border border-border bg-black/30 p-3 text-left"
        >
          {state === 'loading' && <p role="status">Loading environments...</p>}
          {error && <p role="alert" className="mb-3 text-red-300">{error}</p>}
          {state === 'error' && (
            <button
              type="button"
              onClick={() => void loadEnvironments()}
              className="mb-3 rounded border border-border px-2 py-1 text-xs hover:bg-white/5"
            >
              Retry loading
            </button>
          )}
          {state !== 'loading' && (
            <>
              <ul aria-label={`Environment list for ${project.projectKey}`} className="mb-3 space-y-1">
                {environments.map((environment) => (
                  <li key={environment.id} className="flex justify-between gap-4">
                    <span>{environment.name}</span>
                    <span className="text-gray-400">{environment.type}</span>
                  </li>
                ))}
                {environments.length === 0 && (
                  <li className="text-gray-400">No environments found.</li>
                )}
              </ul>
              <form onSubmit={submitEnvironment} className="space-y-2">
                <label className="block text-xs text-gray-300">
                  Environment name
                  <select
                    aria-label="Environment name"
                    name="environment-name"
                    value={selectedName}
                    onChange={(event) => setSelectedName(event.target.value)}
                    disabled={state === 'adding'}
                    className="mt-1 block w-full rounded border border-border bg-card px-2 py-1.5 text-white"
                  >
                    <option value="development">development</option>
                    <option value="staging">staging</option>
                    <option value="production">production</option>
                    <option value="other">Other</option>
                  </select>
                </label>
                {selectedName === 'other' && (
                  <label className="block text-xs text-gray-300">
                    Custom environment name
                    <input
                      aria-label="Custom environment name"
                      value={customName}
                      onChange={(event) => setCustomName(event.target.value)}
                      maxLength={64}
                      required
                      disabled={state === 'adding'}
                      className="mt-1 block w-full rounded border border-border bg-card px-2 py-1.5 text-white"
                    />
                  </label>
                )}
                <button
                  type="submit"
                  disabled={state === 'adding'}
                  className="rounded bg-blue-600 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
                >
                  {state === 'adding' ? 'Adding...' : 'Add environment'}
                </button>
              </form>
            </>
          )}
        </section>
      )}
    </div>
  )
}
