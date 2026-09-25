import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiDelete, apiGet, apiPost } from '@/lib/api'
import type {
  CreateReportRequest,
  Paginated,
  Report,
  ReportListParams,
  SessionSummary,
} from '@/types/api'

export const reportsQueryKey = ['reports'] as const
/** Reports being generated are polled like running sessions. */
export const REPORT_POLL_MS = 2500

const inProgress = (report: Report) => report.status === 'queued' || report.status === 'processing'

/** Same-origin URL of the authorised download endpoint (the session cookie authenticates). */
export const downloadUrl = (report: Report) => `/api/reports/${report.id}/download`

export function useReports(params: ReportListParams) {
  const cleaned = Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== ''),
  )
  return useQuery({
    queryKey: [...reportsQueryKey, 'list', cleaned],
    queryFn: () => apiGet<Paginated<Report>>('/reports', cleaned),
    placeholderData: keepPreviousData,
    refetchInterval: (query) => (query.state.data?.items.some(inProgress) ? REPORT_POLL_MS : false),
  })
}

/** Completed sessions, the only ones reports can be generated for. */
export function useCompletedSessions() {
  return useQuery({
    queryKey: ['sessions', 'list', { status: 'completed', per_page: 100 }],
    queryFn: () =>
      apiGet<Paginated<SessionSummary>>('/sessions', { status: 'completed', per_page: 100 }),
  })
}

export function useGenerateReport() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ sessionId, ...input }: CreateReportRequest & { sessionId: number }) =>
      apiPost<Report>(`/sessions/${sessionId}/reports`, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [...reportsQueryKey, 'list'] }),
  })
}

export function useDeleteReport() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiDelete<{ deleted: boolean }>(`/reports/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [...reportsQueryKey, 'list'] }),
  })
}
