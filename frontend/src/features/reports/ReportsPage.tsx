import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Download,
  FileBarChart,
  Loader2,
  Plus,
  Trash2,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { toast } from 'sonner'

import { PaginationControls } from '@/components/shared/PaginationControls'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useAuth } from '@/features/auth/useAuth'
import { formatBytes, formatDateTime } from '@/lib/format'
import type { Report, ReportFormat, ReportStatus } from '@/types/api'

import { downloadUrl, useDeleteReport, useReports } from './api'
import { GenerateReportDialog } from './GenerateReportDialog'
import { FORMAT_LABELS, REPORT_SECTIONS, REPORT_STATUS_LABELS } from './labels'

const PER_PAGE = 20

const STATUS_STYLES: Record<ReportStatus, string> = {
  queued: 'text-muted-foreground',
  processing: 'text-sky-700 dark:text-sky-400',
  completed: 'text-emerald-700 dark:text-emerald-400',
  failed: 'text-destructive',
}
const STATUS_ICONS = {
  queued: Clock,
  processing: Loader2,
  completed: CheckCircle2,
  failed: AlertCircle,
} as const

function ReportStatusBadge({ status }: { status: ReportStatus }) {
  const Icon = STATUS_ICONS[status]
  return (
    <Badge variant="outline" className={STATUS_STYLES[status]}>
      <Icon aria-hidden="true" className={status === 'processing' ? 'animate-spin' : undefined} />
      {REPORT_STATUS_LABELS[status]}
    </Badge>
  )
}

function sectionSummary(report: Report) {
  if (report.sections.length === REPORT_SECTIONS.length) return 'All sections'
  return REPORT_SECTIONS.filter((s) => report.sections.includes(s.id))
    .map((s) => s.label)
    .join(', ')
}

export function ReportsPage() {
  const { canEdit } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const sessionFilter = Number(searchParams.get('session')) || undefined
  const [format, setFormat] = useState<'all' | ReportFormat>('all')
  const [page, setPage] = useState(1)
  const [generating, setGenerating] = useState(canEdit && searchParams.get('generate') === '1')
  const [deleting, setDeleting] = useState<Report | null>(null)
  const reports = useReports({
    page,
    per_page: PER_PAGE,
    session_id: sessionFilter,
    format: format === 'all' ? undefined : format,
  })
  const remove = useDeleteReport()

  const clearSession = () => {
    setSearchParams({})
    setPage(1)
  }
  const confirmDelete = () => {
    if (!deleting) return
    remove.mutate(deleting.id, {
      onSuccess: () => toast.success('Report deleted.'),
      onError: (error) => toast.error(error.message),
      onSettled: () => setDeleting(null),
    })
  }
  const filteredSession = sessionFilter
    ? reports.data?.items.find((r) => r.session.id === sessionFilter)?.session.session_name
    : undefined
  const empty = reports.isSuccess && reports.data.pagination.total === 0

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-2xl font-semibold tracking-tight">Reports</h2>
          <p className="text-sm text-muted-foreground">
            PDF and Word reports of completed sessions: findings, recommendations, decisions and
            proposed courses.
          </p>
        </div>
        {canEdit && (
          <Button onClick={() => setGenerating(true)}>
            <Plus aria-hidden="true" /> Generate report
          </Button>
        )}
      </div>

      <div className="flex flex-wrap items-end gap-4">
        <div className="grid gap-1.5">
          <Label htmlFor="report-format">Format</Label>
          <Select
            value={format}
            onValueChange={(value) => {
              setFormat(value as typeof format)
              setPage(1)
            }}
          >
            <SelectTrigger id="report-format" className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All formats</SelectItem>
              <SelectItem value="pdf">PDF</SelectItem>
              <SelectItem value="docx">Word (DOCX)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        {sessionFilter && (
          <Badge variant="secondary" className="h-8 gap-1 pr-1 text-sm">
            Session: {filteredSession ?? `#${sessionFilter}`}
            <button
              type="button"
              onClick={clearSession}
              aria-label="Show reports of all sessions"
              className="rounded-sm p-0.5 hover:bg-muted-foreground/20"
            >
              <X className="size-3.5" aria-hidden="true" />
            </button>
          </Badge>
        )}
      </div>

      {reports.isError ? (
        <Alert variant="destructive">
          <AlertTitle>Could not load reports</AlertTitle>
          <AlertDescription className="space-y-2">
            <p>{reports.error.message}</p>
            <Button variant="outline" size="sm" onClick={() => void reports.refetch()}>
              Try again
            </Button>
          </AlertDescription>
        </Alert>
      ) : empty ? (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed px-6 py-14 text-center">
          <FileBarChart className="size-10 text-muted-foreground" aria-hidden="true" />
          <h3 className="text-lg font-semibold">No reports yet</h3>
          <p className="max-w-md text-sm text-muted-foreground">
            Generate a report once a session has completed and its recommendations have been
            reviewed.
          </p>
          {canEdit && (
            <Button onClick={() => setGenerating(true)}>Generate the first report</Button>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <Table aria-label="Reports">
            <TableHeader>
              <TableRow>
                <TableHead>Session</TableHead>
                <TableHead>Format</TableHead>
                <TableHead>Sections</TableHead>
                <TableHead>Generated by</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">
                  <span className="sr-only">Actions</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {reports.isPending
                ? Array.from({ length: 3 }, (_, i) => (
                    <TableRow key={i}>
                      <TableCell colSpan={7}>
                        <Skeleton className="h-6 w-full" />
                      </TableCell>
                    </TableRow>
                  ))
                : reports.data.items.map((report) => (
                    <TableRow key={report.id}>
                      <TableCell className="font-medium">
                        <Link to={`/sessions/${report.session.id}`} className="hover:underline">
                          {report.session.session_name}
                        </Link>
                      </TableCell>
                      <TableCell>{report.format.toUpperCase()}</TableCell>
                      <TableCell className="max-w-56 text-sm whitespace-normal text-muted-foreground">
                        {sectionSummary(report)}
                      </TableCell>
                      <TableCell>{report.created_by.full_name}</TableCell>
                      <TableCell className="whitespace-nowrap">
                        {formatDateTime(report.created_at)}
                      </TableCell>
                      <TableCell className="whitespace-normal">
                        <ReportStatusBadge status={report.status} />
                        {report.status === 'failed' && report.error_message && (
                          <p className="mt-1 max-w-64 text-xs text-destructive">
                            {report.error_message}
                          </p>
                        )}
                      </TableCell>
                      <TableCell className="text-right whitespace-nowrap">
                        {report.status === 'completed' && (
                          <Button variant="outline" size="sm" asChild>
                            <a
                              href={downloadUrl(report)}
                              download
                              aria-label={`Download ${FORMAT_LABELS[report.format]} report of ${report.session.session_name}`}
                            >
                              <Download aria-hidden="true" />
                              Download
                              {report.file_size != null && (
                                <span className="text-muted-foreground">
                                  {formatBytes(report.file_size)}
                                </span>
                              )}
                            </a>
                          </Button>
                        )}
                        {canEdit &&
                          report.status !== 'queued' &&
                          report.status !== 'processing' && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="ml-1"
                              aria-label={`Delete report of ${report.session.session_name}`}
                              onClick={() => setDeleting(report)}
                            >
                              <Trash2 aria-hidden="true" />
                            </Button>
                          )}
                      </TableCell>
                    </TableRow>
                  ))}
            </TableBody>
          </Table>
        </div>
      )}

      {reports.data && reports.data.pagination.pages > 1 && (
        <PaginationControls
          pagination={reports.data.pagination}
          onPageChange={setPage}
          itemLabel="reports"
        />
      )}

      <GenerateReportDialog
        open={generating}
        onOpenChange={setGenerating}
        sessionId={sessionFilter}
      />

      <AlertDialog open={deleting !== null} onOpenChange={(open) => !open && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this report?</AlertDialogTitle>
            <AlertDialogDescription>
              The {deleting?.format.toUpperCase()} report of {deleting?.session.session_name} and
              its file are deleted. The session and its decisions are not affected.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={confirmDelete}>
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
