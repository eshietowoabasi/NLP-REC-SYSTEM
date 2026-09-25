import { Download, ScrollText, X } from 'lucide-react'
import { useState } from 'react'

import { PaginationControls } from '@/components/shared/PaginationControls'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectSeparator,
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
import { useUsers } from '@/features/admin/users/api'
import { formatDateTime } from '@/lib/format'
import type { AuditLogEntry, AuditLogParams } from '@/types/api'

import { exportUrl, useAuditLogs } from './api'

const PER_PAGE = 50
const ALL = 'all'

const AREA_LABELS: Record<string, string> = {
  auth: 'Sign-in',
  user: 'Users',
  document: 'Documents',
  nuc_core: 'NUC core',
  session: 'Sessions',
  recommendation: 'Recommendations',
  mapping: 'Course mappings',
  report: 'Reports',
  settings: 'Settings',
  skill_pattern: 'Skill patterns',
  stop_word: 'Stop words',
  audit_log: 'Audit log',
}

/** "recommendation.decided" → "Recommendation decided". */
function actionLabel(action: string) {
  const text = action.replace(/[._]/g, ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

function detailSummary(detail: Record<string, unknown>) {
  return Object.entries(detail)
    .map(([key, value]) => `${key}: ${typeof value === 'string' ? value : JSON.stringify(value)}`)
    .join(' · ')
}

export function AuditLogPage() {
  const [userId, setUserId] = useState(ALL)
  const [action, setAction] = useState(ALL)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [page, setPage] = useState(1)
  const users = useUsers({ per_page: 100 })
  const params: AuditLogParams = {
    page,
    per_page: PER_PAGE,
    user_id: userId === ALL ? undefined : Number(userId),
    action: action === ALL ? undefined : action,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  }
  const logs = useAuditLogs(params)
  const actions = logs.data?.actions ?? []
  const areas = [...new Set(actions.map((a) => a.split('.')[0]))]
  const filtered = userId !== ALL || action !== ALL || dateFrom || dateTo
  const datesInvalid = Boolean(dateFrom && dateTo && dateFrom > dateTo)

  const change =
    <T,>(setter: (value: T) => void) =>
    (value: T) => {
      setter(value)
      setPage(1)
    }
  const clear = () => {
    setUserId(ALL)
    setAction(ALL)
    setDateFrom('')
    setDateTo('')
    setPage(1)
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-2xl font-semibold tracking-tight">Audit log</h2>
          <p className="text-sm text-muted-foreground">
            Sign-ins, uploads, sessions, decisions, mappings, reports and every administrative
            change. Times are shown in your local time zone; date filters use UTC days.
          </p>
        </div>
        <Button variant="outline" asChild>
          <a href={exportUrl(params)} download>
            <Download aria-hidden="true" /> Export CSV
          </a>
        </Button>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <div className="grid gap-1.5">
          <Label htmlFor="audit-user">User</Label>
          <Select value={userId} onValueChange={change(setUserId)}>
            <SelectTrigger id="audit-user" className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All users</SelectItem>
              {users.data?.items.map((user) => (
                <SelectItem key={user.id} value={String(user.id)}>
                  {user.full_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="audit-action">Action</Label>
          <Select value={action} onValueChange={change(setAction)}>
            <SelectTrigger id="audit-action" className="w-56">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All actions</SelectItem>
              <SelectSeparator />
              <SelectGroup>
                <SelectLabel>Areas</SelectLabel>
                {areas.map((area) => (
                  <SelectItem key={area} value={area}>
                    {AREA_LABELS[area] ?? actionLabel(area)} (all)
                  </SelectItem>
                ))}
              </SelectGroup>
              <SelectSeparator />
              <SelectGroup>
                <SelectLabel>Actions</SelectLabel>
                {actions.map((value) => (
                  <SelectItem key={value} value={value}>
                    {actionLabel(value)}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="audit-from">From</Label>
          <Input
            id="audit-from"
            type="date"
            className="w-40"
            value={dateFrom}
            max={dateTo || undefined}
            onChange={(event) => change(setDateFrom)(event.target.value)}
          />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="audit-to">To</Label>
          <Input
            id="audit-to"
            type="date"
            className="w-40"
            value={dateTo}
            min={dateFrom || undefined}
            aria-invalid={datesInvalid}
            onChange={(event) => change(setDateTo)(event.target.value)}
          />
        </div>
        {filtered && (
          <Button variant="ghost" onClick={clear}>
            <X aria-hidden="true" /> Clear filters
          </Button>
        )}
      </div>

      {logs.isError ? (
        <Alert variant="destructive">
          <AlertTitle>Could not load the audit log</AlertTitle>
          <AlertDescription className="space-y-2">
            <p>
              {datesInvalid
                ? 'The start date must be on or before the end date.'
                : logs.error.message}
            </p>
            {!datesInvalid && (
              <Button variant="outline" size="sm" onClick={() => void logs.refetch()}>
                Try again
              </Button>
            )}
          </AlertDescription>
        </Alert>
      ) : logs.isSuccess && logs.data.items.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed px-6 py-12 text-center">
          <ScrollText className="size-8 text-muted-foreground" aria-hidden="true" />
          <p className="font-medium">No entries match these filters</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <Table aria-label="Audit log">
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Entity</TableHead>
                <TableHead className="min-w-72">Detail</TableHead>
                <TableHead>IP address</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {logs.isPending
                ? Array.from({ length: 5 }, (_, i) => (
                    <TableRow key={i}>
                      <TableCell colSpan={6}>
                        <Skeleton className="h-6 w-full" />
                      </TableCell>
                    </TableRow>
                  ))
                : logs.data.items.map((entry) => <AuditRow key={entry.id} entry={entry} />)}
            </TableBody>
          </Table>
        </div>
      )}
      {logs.data && logs.data.pagination.pages > 1 && (
        <PaginationControls
          pagination={logs.data.pagination}
          onPageChange={setPage}
          itemLabel="entries"
        />
      )}
    </div>
  )
}

function AuditRow({ entry }: { entry: AuditLogEntry }) {
  const summary = detailSummary(entry.detail)
  return (
    <TableRow className="align-top">
      <TableCell className="whitespace-nowrap tabular-nums">
        {formatDateTime(entry.created_at)}
      </TableCell>
      <TableCell className="whitespace-nowrap">
        {entry.user?.full_name ?? <span className="text-muted-foreground">Anonymous</span>}
      </TableCell>
      <TableCell className="whitespace-nowrap">
        <code className="rounded bg-muted px-1 py-0.5 text-xs" title={entry.action_type}>
          {entry.action_type}
        </code>
      </TableCell>
      <TableCell className="whitespace-nowrap text-muted-foreground">
        {entry.entity_type
          ? `${entry.entity_type}${entry.entity_id ? ` #${entry.entity_id}` : ''}`
          : '—'}
      </TableCell>
      <TableCell className="max-w-md text-xs whitespace-normal text-muted-foreground">
        {summary ? (
          <details>
            <summary className="line-clamp-2 cursor-pointer [overflow-wrap:anywhere]">
              {summary}
            </summary>
            <pre className="mt-1 overflow-x-auto rounded bg-muted p-2 text-[11px] text-foreground">
              {JSON.stringify(entry.detail, null, 2)}
            </pre>
          </details>
        ) : (
          '—'
        )}
      </TableCell>
      <TableCell className="whitespace-nowrap text-muted-foreground tabular-nums">
        {entry.ip_address ?? '—'}
      </TableCell>
    </TableRow>
  )
}
