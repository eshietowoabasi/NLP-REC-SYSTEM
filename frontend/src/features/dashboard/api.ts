import { useQuery } from '@tanstack/react-query'

import { apiGet } from '@/lib/api'
import type { DashboardSummary } from '@/types/api'

/** Headline counts for one programme (its documents plus general ones), or all of the user's. */
export function useDashboardSummary(programmeId?: number, enabled = true) {
  return useQuery({
    enabled,
    queryKey: ['dashboard', 'summary', programmeId ?? 'all'],
    queryFn: () =>
      apiGet<DashboardSummary>(
        '/dashboard/summary',
        programmeId ? { programme_id: programmeId } : undefined,
      ),
    // Running sessions change the counts; refresh while the page is open.
    refetchInterval: (query) =>
      query.state.data?.recent_sessions.some((s) => s.status === 'processing') ? 5000 : false,
  })
}
