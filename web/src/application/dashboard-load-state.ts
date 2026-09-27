export interface DashboardLoadState<T> {
  data: T | null
  error: string | null
}

export function nextDashboardLoadState<T>(
  _previous: DashboardLoadState<T>,
  result: { data?: T; error?: string }
): DashboardLoadState<T> {
  return result.data
    ? { data: result.data, error: null }
    : { data: null, error: result.error || 'Failed to load data.' }
}
