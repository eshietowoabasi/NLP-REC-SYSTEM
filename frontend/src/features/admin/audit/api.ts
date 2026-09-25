import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { apiGet } from '@/lib/api'
import type { AuditLogList, AuditLogParams } from '@/types/api'

export function cleanAuditParams(params: AuditLogParams): Record<string, string | number> {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== ''),
  ) as Record<string, string | number>
}

export function useAuditLogs(params: AuditLogParams) {
  const cleaned = cleanAuditParams(params)
  return useQuery({
    queryKey: ['admin', 'audit-logs', cleaned],
    queryFn: () => apiGet<AuditLogList>('/admin/audit-logs', cleaned),
    placeholderData: keepPreviousData,
  })
}

/** The CSV export URL for the same filters (downloaded with the session cookie). */
export function exportUrl(params: AuditLogParams): string {
  const query = new URLSearchParams(
    Object.entries(cleanAuditParams(params))
      .filter(([key]) => key !== 'page' && key !== 'per_page')
      .map(([key, value]) => [key, String(value)]),
  ).toString()
  return `/api/admin/audit-logs/export${query ? `?${query}` : ''}`
}
