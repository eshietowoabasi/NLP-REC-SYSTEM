import {
  AlertTriangle,
  BookOpenCheck,
  FileBarChart,
  FileText,
  FlaskConical,
  ListChecks,
  Plus,
  Upload,
  type LucideIcon,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
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
import { SessionStatusBadge } from '@/features/sessions/SessionStatusBadge'
import { SystemStatusCard } from '@/features/system/SystemStatusCard'
import { formatDate } from '@/lib/format'
import type { DashboardSummary } from '@/types/api'

import { useDashboardSummary } from './api'

export function DashboardPage() {
  const summary = useDashboardSummary()
  const { user, isAdmin } = useAuth()

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <section className="space-y-1">
        <h2 className="text-2xl font-semibold tracking-tight">
          Welcome, {user.full_name.split(' ')[0]}
        </h2>
        <p className="max-w-prose text-sm text-muted-foreground">
          Evidence-based recommendations for the institution-designed 30% of the Computer Science
          curriculum under the NUC CCMAS framework.
        </p>
      </section>

      {summary.isPending ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4" aria-label="Loading summary">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : summary.isError ? (
        <Alert variant="destructive">
          <AlertTitle>Could not load the dashboard</AlertTitle>
          <AlertDescription className="space-y-2">
            <p>{summary.error.message}</p>
            <Button variant="outline" size="sm" onClick={() => void summary.refetch()}>
              Try again
            </Button>
          </AlertDescription>
        </Alert>
      ) : (
        <Overview data={summary.data} />
      )}

      {isAdmin && (
        <div className="max-w-xl">
          <SystemStatusCard />
        </div>
      )}
    </div>
  )
}

function Overview({ data }: { data: DashboardSummary }) {
  const { canEdit, isAdmin } = useAuth()
  const firstRun = data.documents.total === 0 && data.sessions.total === 0

  if (firstRun) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed px-6 py-14 text-center">
        <Upload className="size-10 text-muted-foreground" aria-hidden="true" />
        <h3 className="text-lg font-semibold">Start by uploading documents</h3>
        <p className="max-w-md text-sm text-muted-foreground">
          Upload job adverts, policy, institutional and academic documents. Once they are processed,
          create an analysis session to discover candidate course topics.
        </p>
        {canEdit && (
          <Button asChild>
            <Link to="/documents">Upload documents</Link>
          </Button>
        )}
        {!data.nuc_core_version && <NucCoreHint isAdmin={isAdmin} />}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {!data.nuc_core_version && <NucCoreHint isAdmin={isAdmin} />}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          icon={FileText}
          label="Documents"
          value={data.documents.total}
          to="/documents"
          detail={
            <>
              {data.documents.ready} ready
              {data.documents.processing > 0 && ` · ${data.documents.processing} processing`}
              {data.documents.failed > 0 && ` · ${data.documents.failed} failed`}
            </>
          }
        />
        <StatTile
          icon={FlaskConical}
          label="Analysis sessions"
          value={data.sessions.total}
          to="/sessions"
          detail={
            <>
              {data.sessions.by_status.completed} completed
              {data.sessions.by_status.processing > 0 &&
                ` · ${data.sessions.by_status.processing} running`}
            </>
          }
        />
        <StatTile
          icon={ListChecks}
          label="Awaiting review"
          value={data.recommendations.pending_review}
          detail={
            <>
              of {data.recommendations.total} recommendation
              {data.recommendations.total === 1 ? '' : 's'} · {data.recommendations.accepted}{' '}
              accepted
            </>
          }
        />
        <StatTile
          icon={BookOpenCheck}
          label="Courses mapped"
          value={data.courses_mapped}
          to="/reports"
          detail={
            <>
              {data.reports} report{data.reports === 1 ? '' : 's'} generated
            </>
          }
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_18rem]">
        <Card>
          <CardHeader>
            <CardTitle>Recent sessions</CardTitle>
          </CardHeader>
          <CardContent>
            {data.recent_sessions.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No analysis sessions yet.
                {canEdit && (
                  <>
                    {' '}
                    <Link to="/sessions/new" className="underline">
                      Create one
                    </Link>{' '}
                    from the ready documents.
                  </>
                )}
              </p>
            ) : (
              <div className="overflow-x-auto">
                <Table aria-label="Recent sessions">
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Documents</TableHead>
                      <TableHead className="text-right">Recommendations</TableHead>
                      <TableHead>Created</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.recent_sessions.map((session) => (
                      <TableRow key={session.id}>
                        <TableCell className="font-medium">
                          <Link to={`/sessions/${session.id}`} className="hover:underline">
                            {session.session_name}
                          </Link>
                        </TableCell>
                        <TableCell>
                          <SessionStatusBadge
                            status={session.status}
                            stage={session.current_stage}
                          />
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {session.document_count}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {session.recommendation_count}
                        </TableCell>
                        <TableCell className="whitespace-nowrap">
                          {formatDate(session.created_at)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="self-start">
          <CardHeader>
            <CardTitle>Quick actions</CardTitle>
            <CardDescription>
              NUC core: {data.nuc_core_version?.version_label ?? 'not set'}
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2">
            {canEdit && (
              <>
                <Button variant="outline" className="justify-start" asChild>
                  <Link to="/documents">
                    <Upload aria-hidden="true" /> Upload documents
                  </Link>
                </Button>
                <Button variant="outline" className="justify-start" asChild>
                  <Link to="/sessions/new">
                    <Plus aria-hidden="true" /> New analysis session
                  </Link>
                </Button>
              </>
            )}
            <Button variant="outline" className="justify-start" asChild>
              <Link to="/sessions">
                <FlaskConical aria-hidden="true" /> Review sessions
              </Link>
            </Button>
            <Button variant="outline" className="justify-start" asChild>
              <Link to="/reports">
                <FileBarChart aria-hidden="true" /> Reports
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

/** A headline number with its label and one line of context. */
function StatTile({
  icon: Icon,
  label,
  value,
  detail,
  to,
}: {
  icon: LucideIcon
  label: string
  value: number
  detail: ReactNode
  to?: string
}) {
  const body = (
    <Card className="h-full transition-colors hover:bg-muted/40">
      <CardContent className="space-y-1">
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Icon className="size-4" aria-hidden="true" /> {label}
        </p>
        <p className="text-3xl font-semibold">{value.toLocaleString()}</p>
        <p className="text-xs text-muted-foreground">{detail}</p>
      </CardContent>
    </Card>
  )
  return to ? (
    <Link
      to={to}
      aria-label={`${label}: ${value}`}
      className="rounded-xl focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
    >
      {body}
    </Link>
  ) : (
    <section aria-label={`${label}: ${value}`}>{body}</section>
  )
}

function NucCoreHint({ isAdmin }: { isAdmin: boolean }) {
  return (
    <Alert className="text-left">
      <AlertTriangle aria-hidden="true" className="text-amber-600" />
      <AlertTitle>No active NUC core reference</AlertTitle>
      <AlertDescription>
        Sessions cannot run until an administrator uploads the NUC CCMAS core.
        {isAdmin && (
          <>
            {' '}
            <Link to="/admin/nuc-core" className="underline">
              Upload it now
            </Link>
            .
          </>
        )}
      </AlertDescription>
    </Alert>
  )
}
