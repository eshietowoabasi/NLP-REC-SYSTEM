import { useQuery } from '@tanstack/react-query'

import { ApiError, apiGet } from '@/lib/api'
import type { HealthChecks, HealthFailureDetails, HealthStatus } from '@/types/api'

/** API health as the UI needs it: a 503 is a readable "degraded" state, not a failure. */
export interface SystemHealth {
  status: 'ok' | 'degraded'
  version: string
  checks: HealthChecks
}

export async function fetchSystemHealth(): Promise<SystemHealth> {
  try {
    const data = await apiGet<HealthStatus>('/health')
    return { status: 'ok', version: data.version, checks: data.checks }
  } catch (error) {
    if (error instanceof ApiError && error.code === 'SERVICE_UNAVAILABLE') {
      const details = error.details as unknown as HealthFailureDetails
      return { status: 'degraded', version: details.version, checks: details.checks }
    }
    throw error
  }
}

export const systemHealthQueryKey = ['system', 'health'] as const

/** Poll API health every 30 seconds. */
export function useSystemHealth() {
  return useQuery({
    queryKey: systemHealthQueryKey,
    queryFn: fetchSystemHealth,
    refetchInterval: 30_000,
    staleTime: 10_000,
    retry: false,
  })
}
