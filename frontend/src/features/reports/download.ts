import type { QueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { apiGet, apiPost } from '@/lib/api'
import type { CreateReportRequest, Report } from '@/types/api'

import { downloadUrl, REPORT_POLL_MS, reportsQueryKey } from './api'

/** Give up waiting after this long (the report still appears on the Reports page). */
const MAX_WAIT_MS = 5 * 60 * 1000

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

/** Start the browser download of a finished report through its authorised endpoint. */
export function saveReport(report: Report) {
  const link = document.createElement('a')
  link.href = downloadUrl(report)
  link.download = ''
  document.body.append(link)
  link.click()
  link.remove()
}

/**
 * Queue a report, wait for it to be generated and download it. Runs outside any component, so
 * it finishes even if the user navigates away; progress is shown in one toast.
 */
export async function generateAndDownload(
  queryClient: QueryClient,
  sessionId: number,
  request: CreateReportRequest = { format: 'docx' },
): Promise<Report | null> {
  const toastId = toast.loading('Preparing your report…')
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: reportsQueryKey })
    void queryClient.invalidateQueries({ queryKey: ['review', 'progress', sessionId] })
  }
  try {
    let report = await apiPost<Report>(`/sessions/${sessionId}/reports`, request)
    refresh()
    const started = Date.now()
    while (report.status === 'queued' || report.status === 'processing') {
      if (Date.now() - started > MAX_WAIT_MS) {
        toast.info('The report is taking longer than usual. It will appear on the Reports page.', {
          id: toastId,
        })
        return null
      }
      await sleep(REPORT_POLL_MS)
      report = await apiGet<Report>(`/reports/${report.id}`)
    }
    refresh()
    if (report.status === 'failed') {
      toast.error(report.error_message ?? 'The report could not be generated.', { id: toastId })
      return report
    }
    toast.success('Report ready. The download has started.', { id: toastId })
    saveReport(report)
    return report
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'The report could not be generated.', {
      id: toastId,
    })
    return null
  }
}
