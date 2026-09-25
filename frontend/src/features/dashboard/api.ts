import { useQuery } from '@tanstack/react-query'

import { apiGet } from '@/lib/api'
import type { DashboardSummary } from '@/types/api'

export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: () => apiGet<DashboardSummary>('/dashboard/summary'),
    // Running sessions change the counts; refresh while the page is open.
    refetchInterval: (query) =>
      query.state.data?.recent_sessions.some((s) => s.status === 'processing') ? 5000 : false,
  })
}
