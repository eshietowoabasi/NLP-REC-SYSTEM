import { FlaskConical, Plus, Search, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'

import { PaginationControls } from '@/components/shared/PaginationControls'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
import { useDebouncedValue } from '@/hooks/use-debounced-value'
import { formatDateTime } from '@/lib/format'
import type { SessionStatus, SessionSummary } from '@/types/api'

import { useSessions } from './api'
import { DeleteSessionDialog } from './DeleteSessionDialog'
import { SessionStatusBadge } from './SessionStatusBadge'
import { STATUS_LABELS } from './stages'

const PER_PAGE = 20
type StatusFilter = SessionStatus | 'all'
const STATUSES: SessionStatus[] = ['pending', 'processing', 'completed', 'failed']

export function SessionsPage() {
  const { canEdit } = useAuth()
  const [status, setStatus] = useState<StatusFilter>('all')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [deleting, setDeleting] = useState<SessionSummary | null>(null)
  const debouncedSearch = useDebouncedValue(search.trim())

  const sessions = useSessions({
    page,
    per_page: PER_PAGE,
    status: status === 'all' ? undefined : status,
    search: debouncedSearch || undefined,
  })
  const filtersActive = status !== 'all' || debouncedSearch !== ''
  const empty = !filtersActive && sessions.data?.pagination.total === 0

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold">Analysis sessions</h2>
          <p className="text-sm text-muted-foreground">
            Each session analyses a set of documents and proposes ranked course topics.
          </p>
        </div>
        {canEdit && (
          <Button asChild>
            <Link to="/sessions/new">
              <Plus aria-hidden="true" /> New session
            </Link>
          </Button>
        )}
      </div>

      <div className="flex flex-wrap items-end gap-3" role="search">
        <div className="grid min-w-56 flex-1 gap-1.5">
          <Label htmlFor="session-search">Search</Label>
          <div className="relative">
            <Search
              className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              id="session-search"
              className="pl-8"
              placeholder="Session name"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value)
                setPage(1)
              }}
            />
          </div>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="session-status">Status</Label>
          <Select
            value={status}
            onValueChange={(value) => {
              setStatus(value as StatusFilter)
              setPage(1)
            }}
          >
            <SelectTrigger id="session-status" className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              {STATUSES.map((value) => (
                <SelectItem key={value} value={value}>
                  {STATUS_LABELS[value]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {sessions.isError ? (
        <Alert variant="destructive">
          <AlertTitle>Could not load sessions</AlertTitle>
          <AlertDescription className="space-y-2">
            <p>{sessions.error.message}</p>
            <Button variant="outline" size="sm" onClick={() => void sessions.refetch()}>
              Try again
            </Button>
          </AlertDescription>
        </Alert>
      ) : empty ? (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed px-6 py-14 text-center">
          <FlaskConical className="size-10 text-muted-foreground" aria-hidden="true" />
          <h3 className="text-lg font-semibold">No analysis sessions yet</h3>
          <p className="max-w-md text-sm text-muted-foreground">
            A session selects documents from the library, discovers themes in them and ranks
            candidate course topics against the NUC core.
          </p>
          {canEdit && (
            <Button asChild>
              <Link to="/sessions/new">Create the first session</Link>
            </Button>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Created by</TableHead>
                <TableHead className="text-right">Documents</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Completed</TableHead>
                {canEdit && (
                  <TableHead className="w-12">
                    <span className="sr-only">Actions</span>
                  </TableHead>
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {sessions.isPending ? (
                Array.from({ length: 4 }, (_, index) => (
                  <TableRow key={index} aria-hidden="true">
                    <TableCell colSpan={7}>
                      <Skeleton className="h-6 w-full" />
                    </TableCell>
                  </TableRow>
                ))
              ) : sessions.data.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="py-10 text-center text-muted-foreground">
                    No sessions match these filters.
                  </TableCell>
                </TableRow>
              ) : (
                sessions.data.items.map((session) => (
                  <TableRow key={session.id}>
                    <TableCell className="max-w-72">
                      <Link
                        to={`/sessions/${session.id}`}
                        className="block truncate font-medium hover:underline"
                      >
                        {session.session_name}
                      </Link>
                    </TableCell>
                    <TableCell>{session.created_by.full_name}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {session.document_count}
                    </TableCell>
                    <TableCell>
                      <SessionStatusBadge status={session.status} stage={session.current_stage} />
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      {formatDateTime(session.created_at)}
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      {formatDateTime(session.completed_at)}
                    </TableCell>
                    {canEdit && (
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label={`Delete ${session.session_name}`}
                          disabled={session.status === 'processing'}
                          onClick={() => setDeleting(session)}
                        >
                          <Trash2 aria-hidden="true" />
                        </Button>
                      </TableCell>
                    )}
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}

      {sessions.data && sessions.data.pagination.pages > 1 && (
        <PaginationControls
          pagination={sessions.data.pagination}
          onPageChange={setPage}
          itemLabel="sessions"
        />
      )}
      <DeleteSessionDialog session={deleting} onClose={() => setDeleting(null)} />
    </div>
  )
}
